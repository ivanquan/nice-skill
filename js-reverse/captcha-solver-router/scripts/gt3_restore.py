#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
极验 GT3 乱序背景图还原为 260x160 清晰图。

GT3 的 bg/fullbg 下载下来是 52 块乱序拼接，第三方打码平台（冰拓等）识别前
需要先还原，不能把乱序原图直接 base64 上传。

用法：
  python gt3_restore.py --input 背景2.jpg --output restored_bg.png
"""

import argparse
import io
import os
import sys

# GT3 经典 52 块置换表（见 captcha-slide-reverse geetest-gt3-workflow.md）
SLICE_POSITIONS = [
    39, 38, 48, 49, 41, 40, 46, 47, 35, 34, 50, 51, 33, 32, 28, 29, 27, 26,
    36, 37, 31, 30, 44, 45, 43, 42, 12, 13, 23, 22, 14, 15, 21, 20, 8, 9,
    25, 24, 6, 7, 3, 2, 0, 1, 11, 10, 4, 5, 19, 18, 16, 17,
]


def restore_gt3_bg(input_path_or_bytes, output_path=None):
    """
    将 GT3 乱序 bg/fullbg 还原为 260x160 RGB 图。

    乱序图布局：宽 312（26×12），高 160；每块有效宽 10、高 80；
    第 0–25 块在上半行，第 26–51 块在下半行。
    """
    from PIL import Image

    if isinstance(input_path_or_bytes, (bytes, bytearray)):
        src = Image.open(io.BytesIO(input_path_or_bytes)).convert("RGB")
    else:
        src = Image.open(input_path_or_bytes).convert("RGB")

    w, h = src.size
    if w < 260 or h < 160:
        raise ValueError(f"GT3 乱序图尺寸异常: {w}x{h}，期望宽约 312、高 160")

    out = Image.new("RGB", (260, 160))
    for i in range(52):
        pos = SLICE_POSITIONS[i]
        dst_x = (pos % 26) * 10
        dst_y = 80 if pos >= 26 else 0
        src_x = (i % 26) * 12
        src_y = 0 if i < 26 else 80
        block = src.crop((src_x, src_y, src_x + 10, src_y + 80))
        out.paste(block, (dst_x, dst_y))

    if output_path:
        out.save(output_path, format="PNG")
    return out


def img_to_b64_png(img_or_path):
    """PIL Image 或文件路径转 PNG base64（冰拓要求无 data: 前缀）。"""
    import base64
    from PIL import Image

    if isinstance(img_or_path, str):
        with open(img_or_path, "rb") as f:
            raw = f.read()
        return base64.b64encode(raw).decode("ascii")
    buf = io.BytesIO()
    img_or_path.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def main():
    ap = argparse.ArgumentParser(description="GT3 乱序背景还原")
    ap.add_argument("--input", "-i", required=True, help="乱序 bg/fullbg 路径")
    ap.add_argument("--output", "-o", help="输出 PNG 路径（默认与输入同目录 _restored.png）")
    args = ap.parse_args()
    if not os.path.exists(args.input):
        raise SystemExit(f"文件不存在: {args.input}")
    out = args.output or os.path.splitext(args.input)[0] + "_restored.png"
    restore_gt3_bg(args.input, out)
    print(out)


if __name__ == "__main__":
    main()
