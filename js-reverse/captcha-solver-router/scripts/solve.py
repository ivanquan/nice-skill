#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# captcha-solver-router / scripts/solve.py
# 统一打码平台客户端（注册表驱动，支持内置 + 用户外接适配器）。
#
# 用法：
#   python solve.py --platform yescaptcha --op token --sitekey 6Le-xxx --url https://...
#   python solve.py --platform jfbym     --op token --captcha-type 40010 --sitekey 6Le-xxx --url https://...
#   python solve.py --platform bingtop   --op slide --captcha-type <按platforms.md选定> --image bg乱序.jpg --slice slice.png --gt3-restore
#   python solve.py --platform jfbym     --op slide --captcha-type 20111 --slice piece.png --bg bg.png
#   python solve.py --platform bingtop   --op image --captcha-type 10011 --image cap.png
#   python solve.py --platform jfbym     --op click --captcha-type 30100 --image cap.png --extra 请点击字
#   python solve.py --list                # 列出所有已注册平台及其支持的操作
#
# 外接平台：把 .py 放进 scripts/adapters/，或在 scripts/config.json 的
# external_adapters 登记绝对路径（见 scripts/adapters/template.py）。
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ADAPTERS_DIR = os.path.join(HERE, "adapters")


def load_config():
    from config_paths import load_project_config
    cfg, _path = load_project_config()
    return cfg


def build_registry(config):
    from adapters.base import discover
    external = config.get("external_adapters") or []
    return discover(ADAPTERS_DIR, external_paths=external)


def main():
    ap = argparse.ArgumentParser(description="captcha-solver-router unified client (registry-driven)")
    ap.add_argument("--platform", help="平台名（--list 查看可用）")
    ap.add_argument("--op", choices=["token", "image", "slide", "click", "rotate", "track"])
    ap.add_argument("--list", action="store_true", help="列出所有已注册平台及支持的操作")
    # token
    ap.add_argument("--sitekey", help="token: google/hcaptcha sitekey")
    ap.add_argument("--url", help="token: page url")
    ap.add_argument("--task-type", help="yescaptcha token task type (default NoCaptchaTaskProxyless)")
    # image/slide/click/rotate
    ap.add_argument("--image", help="image/click/rotate: 主图路径（bingtop 滑块=背景图）")
    ap.add_argument("--slice", help="slide: 小滑块图路径（jfbym/bingtop 的滑块块）")
    ap.add_argument("--bg", help="slide (jfbym): 背景图路径")
    ap.add_argument("--extra", help="click: 需点选的汉字/提示")
    ap.add_argument("--captcha-type", help="bingtop/jfbym 数值或字符串类型 ID")
    ap.add_argument("--gt3-restore", action="store_true",
                    help="极验 GT3：先将乱序 bg/fullbg 还原为 260x160 再上传打码平台")
    ap.add_argument("--node", help="yescaptcha node override")
    args = ap.parse_args()

    config = load_config()
    registry = build_registry(config)

    if args.list or not args.platform:
        print("已注册平台：")
        for name, cls in sorted(registry.items()):
            sup = ", ".join(op for op, ok in cls.supports.items() if ok)
            print(f"  - {name:12s} ({cls.display})  支持: {sup}")
        if not args.platform:
            if args.list:
                return
            raise SystemExit("请用 --platform 指定平台；--list 查看可用平台")
        return

    if args.platform not in registry:
        avail = ", ".join(sorted(registry.keys()))
        raise SystemExit(f"未知平台 '{args.platform}'。可用: {avail}（外接平台见 adapters/template.py）")

    cls = registry[args.platform]
    cfg = dict(config.get(args.platform, {}))
    if args.node and args.platform == "yescaptcha":
        cfg["node"] = args.node

    # 调平台前预检密钥；缺失则打印引导并退出
    try:
        from preflight import run_preflight
        pf = run_preflight(route="R1" if args.op == "token" else "R2", platform=args.platform)
        plat_checks = [c for c in pf["data"]["checks"] if c.get("id") == f"platform_{args.platform}"]
        if plat_checks and plat_checks[0].get("ok") is False:
            import json as _json
            print(_json.dumps(pf, ensure_ascii=False, indent=2), file=sys.stderr)
            raise SystemExit(
                f"平台 {args.platform} 密钥未配置。请在本机运行：cd scripts && python setup.py\n"
                "（密钥勿发到聊天；可设环境变量或 python preflight.py 查看详情）"
            )
    except ImportError:
        pass

    solver = cls(cfg)

    if not args.op:
        raise SystemExit(f"--platform {args.platform} 需要 --op（支持: {[o for o,ok in cls.supports.items() if ok]}）")

    from adapters.base import img_to_b64

    if args.op == "token":
        result = solver.solve(
            "token",
            task_type=args.task_type,
            website_url=args.url, website_key=args.sitekey,
            googlekey=args.sitekey, pageurl=args.url,
            captcha_type=args.captcha_type,
        )
    elif args.op == "image":
        if not args.image:
            raise SystemExit("--image required for image")
        result = solver.solve("image", b64=img_to_b64(args.image), captcha_type=args.captcha_type)
    elif args.op == "slide":
        if not (args.slice or args.bg or args.image):
            raise SystemExit("--slice/--bg 或 --image required for slide")
        bg_path = args.bg or args.image
        if args.gt3_restore:
            if not bg_path:
                raise SystemExit("--gt3-restore 需要 --image 或 --bg（GT3 乱序背景图）")
            if not args.slice:
                raise SystemExit("--gt3-restore 需要 --slice（滑块小图）")
            from gt3_restore import restore_gt3_bg, img_to_b64_png
            restored = restore_gt3_bg(bg_path)
            bg_b64 = img_to_b64_png(restored)
            slice_b64 = img_to_b64(args.slice)
            print("[gt3] 已还原乱序背景 → 260x160 PNG 再上传", file=sys.stderr)
        else:
            slice_b64 = img_to_b64(args.slice) if args.slice else None
            bg_b64 = img_to_b64(args.bg) if args.bg else img_to_b64(args.image) if args.image else None
        result = solver.solve("slide", slice_b64=slice_b64, bg_b64=bg_b64, captcha_type=args.captcha_type)
    elif args.op == "click":
        if not (args.image and args.extra):
            raise SystemExit("--image 和 --extra required for click")
        result = solver.solve("click", b64=img_to_b64(args.image), extra_text=args.extra, captcha_type=args.captcha_type)
    elif args.op == "rotate":
        if not args.image:
            raise SystemExit("--image required for rotate")
        result = solver.solve("rotate", b64=img_to_b64(args.image), captcha_type=args.captcha_type)
    elif args.op == "track":
        if not args.image:
            raise SystemExit("--image required for track")
        result = solver.solve("track", b64=img_to_b64(args.image), captcha_type=args.captcha_type)
    else:
        raise SystemExit(f"不支持的操作: {args.op}")

    # token 类：附加便于 automate.py 读取的 token 字段
    if args.op == "token" and isinstance(result, dict):
        sol = result.get("solution") or {}
        tok = (
            sol.get("gRecaptchaResponse")
            or sol.get("hCaptchaResponse")
            or sol.get("token")
            or result.get("token")
        )
        if tok:
            result = dict(result)
            result["token"] = tok

    # 统一输出：dict/list 走 json，其余直接打印
    if isinstance(result, (dict, list)):
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(result)


if __name__ == "__main__":
    main()
