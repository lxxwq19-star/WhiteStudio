"""Smoke test: portrait 权重加载验证"""
import os
os.environ['BIREFNET_DEVICE'] = 'cpu'
import time
t0 = time.time()
from app.worker import load_birefnet, get_device
print(f'load_birefnet(portrait) ...')
m, _, dev, info = load_birefnet('portrait', get_device())
print(f'  loaded in {time.time()-t0:.1f}s, device={dev}, id={info["model_id"]}')

# 再测一张图
from app.worker import run_inference
import glob
imgs = glob.glob(r'D:\23107\Desktop\csq\*.JPG') + glob.glob(r'D:\23107\Desktop\csq\*.jpg')
print(f'找到测试图: {len(imgs)} 张')
if imgs:
    t0 = time.time()
    res = run_inference(imgs[0], 'portrait', input_size=1024)
    print(f'  inference {time.time()-t0:.1f}s, mask={res.mask.size}, bbox={res.bbox}')
else:
    print('  跳过推理测试 (无图片)')
