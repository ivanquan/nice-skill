#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
极验 GT3 滑块图片获取与预处理（协议层，非特定站点自动化）。

从 get.php / slide get.php 的 JSONP 响应、或已知的 bg/slice URL 下载图片；
乱序 bg 可选还原后交给 solve.py + 第三方打码平台（冰拓/JFBYM）。

用法：
  # 从抓包保存的 JSONP 文本提取并下载
  python gt3_capture.py --jsonp-file slide_get.txt --out-dir ./gt3_imgs

  # 已知 URL（相对路径会自动补 static 域名）
  python gt3_capture.py --bg /pictures/gt/xxx.jpg --slice /pictures/gt/yyy.png --out-dir ./gt3_imgs

  # 下载 + 还原乱序 bg + 调冰拓（类型须自行按 platforms.md §2.3.1 选定）
  python gt3_capture.py --jsonp-file slide_get.txt --restore --solve --platform bingtop --captcha-type 1310
"""

import argparse
import base64
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_STATIC_HOSTS = ["static.geetest.com", "static.geevisit.com"]


def parse_geetest_jsonp(text):
    """
    从极验 JSONP 响应体解析 JSON 对象。

    支持 geetest_123({...}) 或纯 JSON。
    """
    if not text or not str(text).strip():
        raise ValueError("JSONP 文本为空")
    raw = str(text).strip()
    m = re.search(r"\(({.*})\)\s*;?\s*$", raw, re.S)
    if m:
        raw = m.group(1)
    return json.loads(raw)


def extract_slide_images(payload, prefer="bg"):
    """
    从 get.php / slide get.php 的 data 字段提取 bg、fullbg、slice 路径。

    prefer: 背景优先用 bg 还是 fullbg（默认 bg，缺口图常用 bg）。
    """
    if not isinstance(payload, dict):
        raise ValueError("payload 不是 dict")
    data = payload.get("data")
    if not isinstance(data, dict):
        # 有些响应直接平铺在根级
        data = payload
    bg_key = "bg" if prefer == "bg" else "fullbg"
    bg = data.get(bg_key) or data.get("fullbg") or data.get("bg")
    sl = data.get("slice")
    if not bg or not sl:
        raise KeyError(f"响应中缺少 bg/fullbg 或 slice，已有键: {list(data.keys())}")
    return {"bg": bg, "slice": sl, "fullbg": data.get("fullbg"), "raw_data": data}


def normalize_geetest_url(path_or_url, static_hosts=None):
    """
    将极验返回的相对路径补全为可下载的 HTTPS URL。
    """
    if not path_or_url:
        return None
    s = str(path_or_url).strip()
    if s.startswith("data:"):
        return s
    if s.startswith("//"):
        return "https:" + s
    if s.startswith("http://") or s.startswith("https://"):
        return s
    hosts = static_hosts or DEFAULT_STATIC_HOSTS
    host = hosts[0]
    if not s.startswith("/"):
        s = "/" + s
    return f"https://{host}{s}"


def decode_data_url(data_url):
    """将 data:image/...;base64,... 解码为 bytes。"""
    if "," not in data_url:
        raise ValueError("无效的 data URL")
    header, b64 = data_url.split(",", 1)
    return base64.b64decode(b64)


def download_image(url, session=None, timeout=30):
    """
    下载单张图片，返回 bytes。

    url 可为 http(s) 或 data: URL；http 请求优先用 requests，否则 urllib。
    """
    if url.startswith("data:"):
        return decode_data_url(url)
    try:
        import requests
    except ImportError:
        requests = None
    if session is None and requests:
        session = requests.Session()
    if session:
        r = session.get(url, timeout=timeout)
        r.raise_for_status()
        return r.content
    from urllib.request import urlopen
    with urlopen(url, timeout=timeout) as resp:
        return resp.read()


def save_gt3_pair(bg_url, slice_url, out_dir, static_hosts=None, session=None):
    """
    下载 GT3 bg + slice 到 out_dir，返回本地路径 dict。

    文件名：bg_raw.jpg / slice.png（按 Content-Type 或 URL 后缀推断）。
    """
    os.makedirs(out_dir, exist_ok=True)
    bg_full = normalize_geetest_url(bg_url, static_hosts)
    sl_full = normalize_geetest_url(slice_url, static_hosts)
    bg_bytes = download_image(bg_full, session=session)
    sl_bytes = download_image(sl_full, session=session)

    def _ext(url, default):
        if url.startswith("data:"):
            if "png" in url[:30]:
                return ".png"
            return default
        for e in (".jpg", ".jpeg", ".png", ".webp"):
            if e in url.lower():
                return e
        return default

    bg_path = os.path.join(out_dir, "bg_raw" + _ext(bg_url, ".jpg"))
    sl_path = os.path.join(out_dir, "slice" + _ext(slice_url, ".png"))
    with open(bg_path, "wb") as f:
        f.write(bg_bytes)
    with open(sl_path, "wb") as f:
        f.write(sl_bytes)
    return {
        "bg_path": bg_path,
        "slice_path": sl_path,
        "bg_url": bg_full,
        "slice_url": sl_full,
    }


def capture_from_jsonp(text, out_dir, static_hosts=None, restore=False):
    """
    一站式：JSONP → 解析 → 下载；可选 gt3_restore 还原 bg。
    """
    payload = parse_geetest_jsonp(text)
    imgs = extract_slide_images(payload)
    paths = save_gt3_pair(imgs["bg"], imgs["slice"], out_dir, static_hosts=static_hosts)
    result = {
        "success": True,
        "data": {**paths, "meta": imgs["raw_data"]},
        "error": None,
    }
    if restore:
        from gt3_restore import restore_gt3_bg
        restored = os.path.join(out_dir, "bg_restored.png")
        restore_gt3_bg(paths["bg_path"], restored)
        result["data"]["bg_restored_path"] = restored
    return result


def solve_via_platform(bg_path, slice_path, platform, captcha_type, gt3_restore=False):
    """
    调用 solve.py，由第三方打码平台识别滑块距离（不用 ddddocr）。
    """
    cmd = [
        sys.executable,
        os.path.join(HERE, "solve.py"),
        "--platform", platform,
        "--op", "slide",
        "--captcha-type", str(captcha_type),
        "--image", bg_path,
        "--slice", slice_path,
    ]
    if gt3_restore:
        cmd.append("--gt3-restore")
    out = subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT)
    for line in reversed(out.strip().splitlines()):
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    m = re.search(r"(\d+)\s*,\s*(\d+)", out)
    if m:
        return {"x": int(m.group(1)), "y": int(m.group(2))}
    raise RuntimeError(f"solve.py 未返回可解析结果: {out[-800:]}")


def main():
    """CLI：从 JSONP 或 URL 获取 GT3 图片，可选还原与打码。"""
    ap = argparse.ArgumentParser(description="GT3 滑块图片获取（协议层）")
    ap.add_argument("--jsonp-file", help="含 get.php/slide 响应的 JSONP 文件")
    ap.add_argument("--jsonp-text", help="JSONP 字符串（短文本可直接传）")
    ap.add_argument("--bg", help="背景图 URL 或极验相对路径")
    ap.add_argument("--slice", help="滑块图 URL 或极验相对路径")
    ap.add_argument("--out-dir", default="./gt3_capture_out", help="输出目录")
    ap.add_argument("--restore", action="store_true", help="还原乱序 bg 为 260x160 PNG")
    ap.add_argument("--solve", action="store_true", help="下载后调用 solve.py（第三方平台）")
    ap.add_argument("--platform", default="bingtop", help="打码平台（solve 时用）")
    ap.add_argument(
        "--captcha-type",
        help="平台类型 ID（必填若 --solve；须对照冰拓文档与样本试跑选定，见 platforms.md §2.3.1）",
    )
    ap.add_argument(
        "--gt3-restore",
        action="store_true",
        help="solve 时对乱序原 bg 先还原（传 bg_raw 时通常需要）",
    )
    args = ap.parse_args()

    try:
        if args.jsonp_file or args.jsonp_text:
            text = args.jsonp_text
            if args.jsonp_file:
                with open(args.jsonp_file, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            envelope = capture_from_jsonp(text, args.out_dir, restore=args.restore)
        elif args.bg and args.slice:
            paths = save_gt3_pair(args.bg, args.slice, args.out_dir)
            envelope = {"success": True, "data": paths, "error": None}
            if args.restore:
                from gt3_restore import restore_gt3_bg
                restored = os.path.join(args.out_dir, "bg_restored.png")
                restore_gt3_bg(paths["bg_path"], restored)
                envelope["data"]["bg_restored_path"] = restored
        else:
            raise SystemExit("需要 --jsonp-file/--jsonp-text，或同时提供 --bg 与 --slice")

        if args.solve:
            if not args.captcha_type:
                raise SystemExit("--solve 必须指定 --captcha-type（见 references/platforms.md §2.3.1）")
            d = envelope["data"]
            bg = d.get("bg_restored_path") or d["bg_path"]
            sl = d["slice_path"]
            use_restore = args.gt3_restore or (bg == d["bg_path"] and not d.get("bg_restored_path"))
            solve_res = solve_via_platform(bg, sl, args.platform, args.captcha_type, gt3_restore=use_restore)
            envelope["data"]["solve"] = solve_res

        print(json.dumps(envelope, ensure_ascii=False, indent=2))
    except Exception as exc:
        print(json.dumps({"success": False, "data": None, "error": str(exc)}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
