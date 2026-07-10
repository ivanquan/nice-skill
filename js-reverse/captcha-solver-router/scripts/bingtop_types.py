#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
冰拓官方 captchaType ID 常量。

文档: https://www.bingtop.com/type/
上传接口: https://www.bingtop.com/ocr/upload/
"""

# 轨迹类 https://www.bingtop.com/type/#type_trajectory
TRACK_3001 = 3001  # 轨迹类型一，返回一系列坐标
TRACK_3002 = 3002  # 轨迹类型二（校准中），京东 JCAP 轨迹绘制常用
TRACK_3003 = 3003  # 箭头须从左到右
TRACK_1356 = 1356  # 专用接口 api2.bingtop.com/type1356/

# 旋转类 https://www.bingtop.com/type/#type_rotate
ROTATE_1120 = 1120    # 单图旋转（百度类）
ROTATE_11201 = 11201  # 单图旋转通用
ROTATE_1121 = 1121    # 双图同时旋转，可传单图
ROTATE_1122 = 1122    # tk 双图旋转
ROTATE_1123 = 1123    # 内旋转，圆图 1-359°，可传单图（京东登录旋转题）
ROTATE_1124 = 1124    # 内旋转，圆位置不固定，须双图

# 滑块类 https://www.bingtop.com/type/#type_slide
SLIDE_1318 = 1318  # 返回缺口 x
SLIDE_1310 = 1310  # 返回缺口 x,y（极验 GT3 / 京东拼图常用）
SLIDE_1326 = 1326  # 多空缺干扰
SLIDE_1327 = 1327  # 两块左上角坐标
SLIDE_1316 = 1316  # 双图滑块

# 京东 JCAP 推荐类型（按官方文档，勿使用 11203/30013 等不存在 ID）
# 京东 JCAP 轨迹类固定 3002（官方轨迹类型二）
JD_TRACK_TYPES = [TRACK_3002]
JD_ROTATE_TYPES = [ROTATE_11201, ROTATE_1120]
JD_SLIDE_TYPES = [SLIDE_1310, SLIDE_1318]

# 按识别类别映射冰拓官方 captchaType
CATEGORY_DEFAULT_TYPE = {
    "track": TRACK_3002,
    "rotate": ROTATE_11201,
    "slide": SLIDE_1310,
}

CATEGORY_TYPE_LABEL = {
    "track": "轨迹类(3002)",
    "rotate": "旋转类(11201/1120)",
    "slide": "滑块类(1310/1318)",
}

# 历史误用 ID → 说明（便于日志提示）
DEPRECATED_TYPE_HINTS = {
    11203: f"不存在，旋转请用 {ROTATE_11201} 或 {ROTATE_1120}",
    112013: f"不存在，旋转请用 {ROTATE_11201} 或 {ROTATE_1120}",
    30013: f"不存在，轨迹请用 {TRACK_3002} 或 {TRACK_3001}",
    13563: f"不存在，轨迹请用 {TRACK_3002}",
    13102: f"不存在，滑块请用 {SLIDE_1310} 或 {SLIDE_1318}",
    13182: f"不存在，滑块请用 {SLIDE_1318} 或 {SLIDE_1310}",
}


def warn_deprecated_type(captcha_type):
    """若 captchaType 为历史误用 ID，打印纠正提示。"""
    hint = DEPRECATED_TYPE_HINTS.get(int(captcha_type))
    if hint:
        print(f"[bingtop] 警告: captchaType={captcha_type} {hint}", flush=True)
        return True
    return False


def resolve_captcha_type(category, track=None, rotate=None, slide=None):
    """
    按验证码识别类别返回冰拓 captchaType；CLI/配置覆盖优先。
    category: track | rotate | slide
    """
    if category not in CATEGORY_DEFAULT_TYPE:
        return None
    overrides = {"track": track, "rotate": rotate, "slide": slide}
    override = overrides.get(category)
    chosen = int(override) if override is not None else CATEGORY_DEFAULT_TYPE[category]
    if int(chosen) in DEPRECATED_TYPE_HINTS:
        fallback = CATEGORY_DEFAULT_TYPE[category]
        print(
            f"[bingtop] captchaType={chosen} 无效，已按类别 {category} 改用 {fallback}",
            flush=True,
        )
        chosen = fallback
    warn_deprecated_type(chosen)
    return int(chosen)


def normalize_track_types(captcha_type=None):
    """返回轨迹类试跑顺序（官方 ID）。"""
    primary = int(captcha_type or TRACK_3002)
    if primary in DEPRECATED_TYPE_HINTS:
        primary = TRACK_3002
    warn_deprecated_type(primary)
    order = [primary]
    for t in JD_TRACK_TYPES:
        if t not in order:
            order.append(t)
    return order


def normalize_rotate_types(captcha_type=None):
    """返回旋转类试跑顺序（官方 ID）。"""
    primary = int(captcha_type or ROTATE_11201)
    if primary in DEPRECATED_TYPE_HINTS:
        print(f"[bingtop] captchaType={primary} 已替换为默认 {ROTATE_11201}", flush=True)
        primary = ROTATE_11201
    warn_deprecated_type(primary)
    order = [primary]
    for t in JD_ROTATE_TYPES:
        if t not in order:
            order.append(t)
    return order


def normalize_slide_types(captcha_type=None):
    """返回滑块类试跑顺序（官方 ID）。"""
    primary = int(captcha_type or SLIDE_1310)
    if primary in DEPRECATED_TYPE_HINTS:
        print(f"[bingtop] captchaType={primary} 已替换为默认 {SLIDE_1310}", flush=True)
        primary = SLIDE_1310
    warn_deprecated_type(primary)
    order = [primary]
    for t in JD_SLIDE_TYPES:
        if t not in order:
            order.append(t)
    return order
