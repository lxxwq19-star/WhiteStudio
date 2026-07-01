"""
BiRefNet 推理核心模块
- 加载 BiRefNet 模型（支持通用 matting / 肖像 / 抠图多个权重）
- 单张图片推理：返回高质量 alpha mask
- 包含主体包围盒检测、居中裁切、白底合成、文字叠加等后处理

依赖：torch >= 2.0, transformers, timm, einops, pillow, numpy
"""
from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass
from typing import Optional, Tuple, List

# 1) 设置 HF 镜像（国内网络常见问题；用户可手动覆盖为 https://huggingface.co）
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
# 2) 安静 huggingface 警告
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ---------------------------------------------------------------------------
# BiRefNet 模型加载
# ---------------------------------------------------------------------------

# 可用模型权重（HuggingFace ID）
BIREFNET_MODELS = {
    # 通用抠图，电商商品/通用主体（推荐）
    "general": "ZhengPeng7/BiRefNet",
    # 高分辨率 matting
    "matting": "ZhengPeng7/BiRefNet-matting",
    # 肖像专用
    "portrait": "ZhengPeng7/BiRefNet-portrait",
    # 轻量（速度快）
    "lite": "ZhengPeng7/BiRefNet_lite",
    # 动态分辨率
    "dynamic": "ZhengPeng7/BiRefNet_dynamic",
}

# ImageNet mean/std（BiRefNet 官方预处理）
_IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
_IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


# 全局缓存：避免重复加载
_MODEL_CACHE: dict = {}


def get_device(prefer_gpu: bool = True) -> torch.device:
    """获取推理设备（支持环境变量 BIREFNET_DEVICE=cpu/cuda 强制）"""
    env = os.environ.get("BIREFNET_DEVICE", "").strip().lower()
    if env == "cpu":
        return torch.device("cpu")
    if env == "cuda":
        if torch.cuda.is_available():
            return torch.device("cuda")
        return torch.device("cpu")
    if prefer_gpu and torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def _resolve_model_source(model_key: str) -> str:
    """
    决定模型从哪加载：
    1) 如果本地 models_cache/<key>_local 目录存在  →  本地路径
    2) 否则返回 HF 仓库 ID（需网络）
    """
    # 打包后用户不一定会传 cache_dir；尝试标准本地位置
    candidates = []
    # 项目根目录的 models_cache
    try:
        here = os.path.dirname(os.path.abspath(__file__))
        candidates.append(os.path.normpath(os.path.join(here, "..", "models_cache", f"{model_key}_local")))
    except Exception:
        pass
    # 用户主目录下的缓存
    home = os.path.expanduser("~")
    candidates.append(os.path.join(home, ".birefnet_models", f"{model_key}_local"))
    # 进程 cwd
    candidates.append(os.path.join(os.getcwd(), "models_cache", f"{model_key}_local"))

    for c in candidates:
        if os.path.isdir(c) and os.path.exists(os.path.join(c, "config.json")):
            return c
    return BIREFNET_MODELS.get(model_key, BIREFNET_MODELS["general"])


def load_birefnet(
    model_key: str = "general",
    device: Optional[torch.device] = None,
    cache_dir: Optional[str] = None,
):
    """
    加载 BiRefNet 模型（含缓存）
    返回 (model, processor, device, config_dict)
    """
    if model_key in _MODEL_CACHE:
        return _MODEL_CACHE[model_key]

    from transformers import AutoModelForImageSegmentation

    source = _resolve_model_source(model_key)
    if device is None:
        device = get_device()

    model = AutoModelForImageSegmentation.from_pretrained(
        source,
        trust_remote_code=True,
        cache_dir=cache_dir,
    )
    model = model.to(device).eval()

    # 半精度（GPU 加速 + 节省显存）
    if device.type == "cuda":
        try:
            model = model.half()
        except Exception:
            pass

    info = {
        "model_id": source,
        "device": str(device),
    }
    _MODEL_CACHE[model_key] = (model, None, device, info)  # processor=None, 用内部预处理
    return _MODEL_CACHE[model_key]


def _preprocess_image(img: Image.Image, input_size: int) -> torch.Tensor:
    """
    BiRefNet 标准预处理：
    - 缩放（保持比例）到 input_size
    - ImageNet 归一化
    - 转 tensor (1, 3, H, W)
    """
    w0, h0 = img.size
    scale = input_size / max(w0, h0)
    if scale < 1.0:
        new_w = max(64, int(round(w0 * scale)))
        new_h = max(64, int(round(h0 * scale)))
    else:
        new_w, new_h = w0, h0
    new_w = (new_w // 32) * 32 or 32
    new_h = (new_h // 32) * 32 or 32
    img_resized = img.resize((new_w, new_h), Image.BILINEAR)
    arr = np.array(img_resized).astype(np.float32) / 255.0
    arr = (arr - _IMAGENET_MEAN) / _IMAGENET_STD
    x = torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0).contiguous()
    return x


def clear_model_cache():
    """释放模型显存"""
    global _MODEL_CACHE
    for k, (model, _, _, _) in list(_MODEL_CACHE.items()):
        try:
            del model
        except Exception:
            pass
    _MODEL_CACHE.clear()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


# ---------------------------------------------------------------------------
# 单图推理
# ---------------------------------------------------------------------------

@dataclass
class InferenceResult:
    """单张图推理结果"""
    image: Image.Image           # 原图 PIL (RGB)
    mask: Image.Image            # alpha mask PIL (L, 0~255)
    bbox: Tuple[int, int, int, int]  # 主体包围盒 (x0, y0, x1, y1)
    subject_size: Tuple[int, int]    # 主体尺寸 (w, h)
    original_size: Tuple[int, int]   # 原图尺寸 (w, h)
    inference_ms: float


def _find_subject_bbox(mask: np.ndarray, threshold: int = 10) -> Tuple[int, int, int, int]:
    """
    根据 alpha mask 找到主体包围盒
    返回 (x0, y0, x1, y1) ，含 x1/y1 为排他坐标
    """
    ys, xs = np.where(mask >= threshold)
    if len(xs) == 0:
        h, w = mask.shape
        return 0, 0, w, h
    x0, x1 = int(xs.min()), int(xs.max()) + 1
    y0, y1 = int(ys.min()), int(ys.max()) + 1
    return x0, y0, x1, y1


def run_inference(
    image_path: str,
    model_key: str = "general",
    input_size: int = 1024,
    cache_dir: Optional[str] = None,
) -> InferenceResult:
    """
    对单张图片运行 BiRefNet 推理
    - 智能高分辨率：保留原图比例，最长边缩放到 input_size
    - 返回原图 + 高分辨率 mask
    """
    t0 = time.time()
    model, processor, device, _ = load_birefnet(model_key, cache_dir=cache_dir)

    img = Image.open(image_path).convert("RGB")
    w0, h0 = img.size

    # 预处理（ImageNet 归一化）
    pixel_values = _preprocess_image(img, input_size).to(device)
    if device.type == "cuda":
        pixel_values = pixel_values.half()

    # 推理
    with torch.no_grad():
        outputs = model(pixel_values)

    # 提取 mask（BiRefNet 返回多尺度 list，取最后一层）
    if isinstance(outputs, (list, tuple)):
        logits = outputs[-1]
    else:
        logits = outputs

    # 插值回原图尺寸
    mask_tensor = torch.sigmoid(logits)
    if mask_tensor.dim() == 3:
        mask_tensor = mask_tensor.unsqueeze(1)
    mask_tensor = F.interpolate(
        mask_tensor.float(),
        size=(h0, w0),
        mode="bilinear",
        align_corners=False,
    )
    mask_np = (mask_tensor.squeeze().cpu().numpy() * 255).clip(0, 255).astype(np.uint8)

    # 轻度模糊去除锯齿
    mask_img = Image.fromarray(mask_np, mode="L").filter(ImageFilter.GaussianBlur(radius=0.8))

    # 包围盒
    bbox = _find_subject_bbox(np.array(mask_img))

    t1 = time.time()
    return InferenceResult(
        image=img,
        mask=mask_img,
        bbox=bbox,
        subject_size=(bbox[2] - bbox[0], bbox[3] - bbox[1]),
        original_size=(w0, h0),
        inference_ms=(t1 - t0) * 1000,
    )


# ---------------------------------------------------------------------------
# 后处理：合成 / 居中裁切 / 文字
# ---------------------------------------------------------------------------

@dataclass
class ProcessParams:
    """后处理参数（与 UI 滑块绑定）"""
    # 输出画布
    canvas_width: int = 1024         # 画布宽
    canvas_height: int = 1024        # 画布高
    # 主体居中裁切开关
    center_subject: bool = True      # True=按主体包围盒裁切
    # 边距（仅在 center_subject=False 时为四边留白；True 时是主体周围留白）
    padding: int = 64
    # 白底（True=白底；False=透明）
    white_background: bool = True
    # 文字
    add_text: bool = True
    text_size: int = 36              # 文字大小 px
    text_color: str = "#000000"      # 文字颜色
    text_position: str = "bottom"    # bottom | top
    text_band_height: int = 24       # 文字带高度（主体/底边与文字之间留白，0=紧贴）
    letter_spacing: int = 0          # 字距（字符间距）px
    # 文件名模板（支持 {name} {stem} {w} {h}）
    # 注意：{stem} 自动不带后缀
    name_template: str = ""  # 空=使用原文件名（与源文件同名）
    # 输出格式
    output_format: str = "PNG"       # PNG | JPEG
    jpeg_quality: int = 95
    # 文字字体（None=使用默认）
    font_path: Optional[str] = None


def _load_font(font_size: int, font_path: Optional[str] = None) -> ImageFont.FreeTypeFont:
    """加载字体（跨平台 + 兜底）
    font_path 可以是:
    1. 完整 .ttf/.ttc 路径 -> 直接加载
    2. 字体名 (e.g. "微软雅黑" / "Arial") -> 在 Windows Fonts/ 其他系统字体路径下按名匹配
    3. None/空 -> 走系统默认优先级 (微软雅黑→黑体→宋体)
    """
    # 路径模式: 指向一个真实文件
    if font_path and os.path.isfile(font_path):
        try:
            return ImageFont.truetype(font_path, font_size)
        except Exception:
            pass

    # 中文 family → Windows 英文文件关键词 的别名映射
    FONT_ALIASES = {
        "微软雅黑": ["msyh", "yahei", "microsoft yahei"],
        "黑体": ["simhei", "hei"],
        "宋体": ["simsun", "sun"],
        "仿宋": ["simfang", "fang"],
        "楷体": ["simkai", "kai"],
        "幼圆": ["simyou", "you"],
        "FangSong": ["simfang", "fang"],
        "KaiTi": ["simkai", "kai"],
        "SimHei": ["simhei", "hei"],
        "SimSun": ["simsun", "sun"],
        "华文细黑": ["stxihei", "xihei"],
        "STXihei": ["stxihei", "xihei"],
    }
    # 解析需要匹配的关键字: 如果 family 是中文字, 用 alias 列表; 否则原样
    family_keys = [font_path]
    if font_path in FONT_ALIASES:
        family_keys = [font_path] + FONT_ALIASES[font_path]
    else:
        for cn, en_list in FONT_ALIASES.items():
            if font_path.lower() in [x.lower() for x in en_list]:
                family_keys = [font_path] + en_list
                break

    # 字体名模式: 试系统字体目录里所有 .ttf/.ttc, 用 Pillow 的 load + name 匹配
    if font_path and not os.path.isfile(font_path):
        # Windows 常见: C:\Windows\Fonts\
        # 字体名可能出现在多种文件名上, 列出并逐个尝试
        font_dirs = []
        if sys.platform.startswith("win"):
            font_dirs.append(r"C:\Windows\Fonts")
            # 用户自己安装的字体会在 %LOCALAPPDATA%\Microsoft\Windows\Fonts
            # （如华文细黑、思源字体等通过右键安装的字体）
            _local_fonts = os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Microsoft\Windows\Fonts")
            if os.path.isdir(_local_fonts):
                font_dirs.append(_local_fonts)
        elif sys.platform == "darwin":
            font_dirs += ["/System/Library/Fonts", "/Library/Fonts", "~/Library/Fonts"]
        else:
            font_dirs += [
                "/usr/share/fonts",
                "/usr/local/share/fonts",
                "~/.local/share/fonts",
                "~/.fonts",
            ]
        for d in font_dirs:
            if not os.path.isdir(d):
                continue
            for fname in os.listdir(d):
                if not (fname.lower().endswith(".ttf") or fname.lower().endswith(".ttc") or fname.lower().endswith(".otf")):
                    continue
                full = os.path.join(d, fname)
                try:
                    f = ImageFont.truetype(full, font_size)
                    # Pillow font 的 name 不一定等于 Windows 字体家族名, 只能名字包含判断
                    # 关键字匹配: 检查 family_keys 列表里每个 key 是否在文件名中
                    name_l = fname.lower()
                    font_name_l = (getattr(f, "name", "") or "").lower()
                    for key in family_keys:
                        if key.lower() in name_l or key.lower() in font_name_l:
                            return f
                except Exception:
                    continue
        # 如果上面没找到, 最后尝试 Pillow truetype(font_path) 让系统自己解析
        try:
            return ImageFont.truetype(font_path, font_size)
        except Exception:
            pass

# 优先尝试系统自带
    candidates = []
    if sys.platform.startswith("win"):
        candidates += [
            r"C:\Windows\Fonts\msyh.ttc",      # 微软雅黑
            r"C:\Windows\Fonts\msyh.ttf",
            r"C:\Windows\Fonts\simhei.ttf",     # 黑体
            r"C:\Windows\Fonts\simsun.ttc",     # 宋体
        ]
    elif sys.platform == "darwin":
        candidates += [
            "/System/Library/Fonts/PingFang.ttc",
            "/System/Library/Fonts/Helvetica.ttc",
        ]
    else:
        candidates += [
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]

    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, font_size)
            except Exception:
                continue

    # 兜底
    try:
        return ImageFont.truetype("arial.ttf", font_size)
    except Exception:
        return ImageFont.load_default()


def _hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """#rrggbb -> (r,g,b)"""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    try:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return (r, g, b)
    except Exception:
        return (0, 0, 0)


def render_final(
    result: InferenceResult,
    params: ProcessParams,
    text_content: Optional[str] = None,
) -> Image.Image:
    """
    合成最终输出图：
    1) 提取主体（带 alpha）
    2) 居中裁切到目标画布（保持主体在中心）
    3) 合成白底（或透明）
    4) 可选：在主体下方叠加文字
    """
    img = result.image
    mask = result.mask
    W0, H0 = result.original_size
    bx0, by0, bx1, by1 = result.bbox
    bw, bh = bx1 - bx0, by1 - by0

    if bw <= 0 or bh <= 0:
        # 退化情况：直接用整图
        bx0, by0, bx1, by1 = 0, 0, W0, H0
        bw, bh = W0, H0

    if params.center_subject:
        # ---------------- 模式 A：主体居中裁切 ----------------
        # 在原图上裁出一个固定比例的画布，使主体居于中心
        # 计算包含主体 + 上下/左右填充 padding 的裁切框
        # 但限制裁切框不超过原图边界
        cx = (bx0 + bx1) // 2
        cy = (by0 + by1) // 2

        # 画布长宽比
        target_ratio = params.canvas_width / max(1, params.canvas_height)

        # 裁切框至少需要 (bw + 2*pad, bh + 2*pad) 大小（保证主体完整 + 边距）
        need_w = bw + 2 * params.padding
        need_h = bh + 2 * params.padding
        need_w = max(need_w, int(need_h * target_ratio))
        need_h = max(need_h, int(need_w / target_ratio))

        # 不能超过原图
        need_w = min(need_w, W0)
        need_h = min(need_h, H0)

        # 以 (cx, cy) 为中心，确定裁切框
        crop_x0 = max(0, cx - need_w // 2)
        crop_y0 = max(0, cy - need_h // 2)
        crop_x1 = crop_x0 + need_w
        crop_y1 = crop_y0 + need_h

        # 边界修正
        if crop_x1 > W0:
            crop_x0 -= crop_x1 - W0
            crop_x1 = W0
            crop_x0 = max(0, crop_x0)
        if crop_y1 > H0:
            crop_y0 -= crop_y1 - H0
            crop_y1 = H0
            crop_y0 = max(0, crop_y0)

        cropped_img = img.crop((crop_x0, crop_y0, crop_x1, crop_y1))
        cropped_mask = mask.crop((crop_x0, crop_y0, crop_x1, crop_y1))

        # 将裁切后的内容 resize 到目标画布尺寸（保持原比例，背景留白）
        cw, ch = cropped_img.size
        scale = min(params.canvas_width / cw, params.canvas_height / ch)
        new_w = max(1, int(round(cw * scale)))
        new_h = max(1, int(round(ch * scale)))
        scaled_img = cropped_img.resize((new_w, new_h), Image.LANCZOS)
        scaled_mask = cropped_mask.resize((new_w, new_h), Image.LANCZOS)

        canvas = Image.new("RGB", (params.canvas_width, params.canvas_height), (255, 255, 255))
        # 中心位置
        ox = (params.canvas_width - new_w) // 2
        oy = (params.canvas_height - new_h) // 2
        # 先叠 alpha 图层
        base_rgba = Image.new("RGBA", (params.canvas_width, params.canvas_height), (255, 255, 255, 0))
        subject_rgba = scaled_img.convert("RGBA")
        # 应用 mask
        alpha_data = subject_rgba.split()[-1]
        # 将 mask 替换 alpha
        scaled_mask = scaled_mask.convert("L")
        subject_rgba.putalpha(Image.eval(scaled_mask, lambda v: int(v)))
        base_rgba.paste(subject_rgba, (ox, oy), subject_rgba)
        canvas = base_rgba.convert("RGB") if params.white_background else base_rgba

        final = canvas
    else:
        # ---------------- 模式 B：保持原图尺寸 + 四边留白 ----------------
        # 简单留白
        pad = params.padding
        new_w = min(W0 + 2 * pad, params.canvas_width)
        new_h = min(H0 + 2 * pad, params.canvas_height)
        new_w = max(new_w, W0 + 2 * pad)
        new_h = max(new_h, H0 + 2 * pad)
        final = Image.new("RGBA", (new_w, new_h), (255, 255, 255, 0))
        offset_x = (new_w - W0) // 2
        offset_y = (new_h - H0) // 2
        # 应用 mask
        img_rgba = img.convert("RGBA")
        img_rgba.putalpha(mask.convert("L"))
        final.paste(img_rgba, (offset_x, offset_y), img_rgba)
        if params.white_background:
            final = final.convert("RGB")
        # 限制最大画布
        if final.size[0] > params.canvas_width or final.size[1] > params.canvas_height:
            final.thumbnail((params.canvas_width, params.canvas_height), Image.LANCZOS)

    # ---------------- 文字叠加 ----------------
    if params.add_text and text_content:
        final = _overlay_text(final, text_content, params)

    return final


def _overlay_text(base: Image.Image, text: str, params: ProcessParams) -> Image.Image:
    """
    在画布内部绘制文字（不改变画布尺寸）
    几何定义：
      text_band_height = 文字到画布底边（top 模式为顶边）的距离 (px)
      文字带在画布内占 = text_band_height + 文字实际高度
      文字以画布水平中心对齐
    自动模式（text_band_height = -1）：text_band_height = max(8, text_size // 2)
    text_band_height = 0：文字底部紧贴画布底边
    支持 letter_spacing（字距）：逐字绘制 + 字符间距
    """
    if not text:
        return base

    if base.mode != "RGB":
        base = base.convert("RGB")
    W, H = base.size
    font = _load_font(params.text_size, params.font_path)
    spacing = params.letter_spacing if params.letter_spacing > 0 else 0

    # 计算文字包围盒（不带间距的字高，带间距的总宽）
    dummy = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(dummy)
    bbox_text = d.textbbox((0, 0), text, font=font)
    th = bbox_text[3] - bbox_text[1]

    # 计算总宽度：逐字符累加
    if spacing > 0:
        char_widths = []
        for ch in text:
            cb = d.textbbox((0, 0), ch, font=font)
            char_widths.append(cb[2] - cb[0])
        tw = sum(char_widths) + spacing * (len(text) - 1)
    else:
        char_widths = None
        tw = bbox_text[2] - bbox_text[0]

    # 文字带高度 = 文字底部到画布边距离
    if params.text_band_height < 0:
        text_pad_v = max(8, params.text_size // 2)  # 自动
    else:
        text_pad_v = int(params.text_band_height)   # 用户指定
    text_pad_v = max(0, text_pad_v)

    # 总占用 = 文字到底边距离 + 文字高
    band_h = text_pad_v + th
    band_h = min(band_h, H)                          # 边界保护
    text_pad_v = min(text_pad_v, max(0, H - th))     # 边界保护

    # 画白底覆盖
    if params.text_position == "top":
        ImageDraw.Draw(base).rectangle([(0, 0), (W, band_h)], fill=(255, 255, 255))
        ty = text_pad_v - bbox_text[1]
    else:
        # 底部：覆盖区为 [H-band_h, H]
        ImageDraw.Draw(base).rectangle([(0, H - band_h), (W, H)], fill=(255, 255, 255))
        # 文字底在 H - text_pad_v；文字顶 = 文字底 - 文字高
        ty = (H - text_pad_v) - th - bbox_text[1]

    d = ImageDraw.Draw(base)
    color = _hex_to_rgb(params.text_color)

    if spacing > 0 and char_widths:
        # 逐字绘制（支持字距）
        x_offset = (W - tw) // 2 - bbox_text[0]
        for i, ch in enumerate(text):
            d.text((x_offset, ty), ch, font=font, fill=color)
            x_offset += char_widths[i] + spacing
    else:
        # 无字距时整段绘制（更快）
        tx = (W - tw) // 2 - bbox_text[0]
        d.text((tx, ty), text, font=font, fill=color)

    return base


# ---------------------------------------------------------------------------
# 文件名模板
# ---------------------------------------------------------------------------

def build_output_name(template: str, src_path: str, params: ProcessParams, suffix: str = "") -> str:
    """
    根据模板生成输出文件名（不含扩展名）
    可用占位符:
      {name}   - 含扩展名的原文件名，如 "img.jpg"
      {stem}   - 不含扩展名的原文件名，如 "img"
      {w}      - 输出画布宽
      {h}      - 输出画布高
    空模板=使用 {stem}（与源文件同名，扩展名在调用处根据 output_format 添加）
    """
    base = os.path.basename(src_path)
    stem, ext = os.path.splitext(base)
    if not template or not template.strip():
        template = "{stem}"
    name = template.format(
        name=base,
        stem=stem,
        w=params.canvas_width,
        h=params.canvas_height,
        suffix=suffix,
    )
    # 兜底（防止出现 {stem} 残留）
    if "{" in name and "}" in name:
        name = name.replace("{stem}", stem).replace("{name}", base)
    return name


# ---------------------------------------------------------------------------
# 一站式处理接口（供 worker 调用）
# ---------------------------------------------------------------------------

def process_one(
    src_path: str,
    dst_dir: str,
    model_key: str,
    params: ProcessParams,
    input_size: int = 1024,
    cache_dir: Optional[str] = None,
    on_progress=None,
) -> dict:
    """
    处理单张图片：推理 + 后处理 + 保存
    返回 dict:
      {
        "ok": bool,
        "src": str,
        "out": str,
        "inference_ms": float,
        "subject_size": (w, h),
        "original_size": (w, h),
        "error": str (失败时)
      }
    """
    try:
        if on_progress:
            on_progress("infer", 10)
        result = run_inference(
            src_path, model_key=model_key, input_size=input_size, cache_dir=cache_dir
        )

        if on_progress:
            on_progress("post", 70)
        # 文字内容：模板为 "{stem}_whitebg"，并渲染主体下方的文字
        stem, _ = os.path.splitext(os.path.basename(src_path))
        text_content = stem  # 不加文件格式后缀的文件名

        final = render_final(result, params, text_content=text_content)

        if on_progress:
            on_progress("save", 90)
        # 文件名生成
        out_name = build_output_name(params.name_template, src_path, params)
        # 输出格式映射: PNG -> .png ; JPG / JPEG -> .jpg
        fmt_upper = params.output_format.upper().strip()
        if fmt_upper in ("PNG",):
            ext = ".png"
        else:  # JPG / JPEG
            ext = ".jpg"
        out_path = os.path.join(dst_dir, out_name + ext)
        # 避免覆盖
        i = 1
        base_out = out_path
        while os.path.exists(out_path):
            stem_only, _ = os.path.splitext(base_out)
            out_path = f"{stem_only}_{i}{ext}"
            i += 1

        if fmt_upper == "PNG":
            # PNG 模式: 透明背景可用（取决于 white_background）
            if final.mode == "RGBA" and not params.white_background:
                final.save(out_path, "PNG", optimize=True)
            else:
                # 白底模式: 转 RGB 节省体积
                if final.mode != "RGB":
                    final = final.convert("RGB")
                final.save(out_path, "PNG", optimize=True)
        else:
            # JPG 模式: 强制 RGB（JPG 不支持透明）
            if final.mode != "RGB":
                final = final.convert("RGB")
            final.save(out_path, "JPEG", quality=params.jpeg_quality, optimize=True)

        if on_progress:
            on_progress("done", 100)
        return {
            "ok": True,
            "src": src_path,
            "out": out_path,
            "inference_ms": result.inference_ms,
            "subject_size": result.subject_size,
            "original_size": result.original_size,
        }
    except Exception as e:
        return {
            "ok": False,
            "src": src_path,
            "out": "",
            "error": str(e),
        }
