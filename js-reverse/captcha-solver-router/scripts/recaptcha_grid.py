#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""reCAPTCHA v2 图片九宫格/十六宫格识别与 Playwright 模拟点击。"""

import base64
import io
import random
import re
import sys
import time

from browser_stealth import get_mouse_state, human_click_at

# reCAPTCHA 题面目标词 -> YesCaptcha question ID（/m/...）
# 中文/繁体来源：项目实测 catalog；英文来源：YesCaptcha 官方对照表
CAPTCHA_ITEM_QUESID = {
    "出租车": "/m/0pg52",
    "巴士": "/m/01bjv",
    "摩托车": "/m/04_sv",
    "電單車": "/m/04_sv",
    "拖拉机": "/m/013xlm",
    "烟囱": "/m/01jk_4",
    "人行横道": "/m/014xcs",
    "十字路口": "/m/014xcs",
    "过街人行道": "/m/014xcs",
    "红绿灯": "/m/015qff",
    "交通燈": "/m/015qff",
    "交通灯": "/m/015qff",
    "自行车": "/m/0199g",
    "单车": "/m/0199g",
    "單車": "/m/0199g",
    "停车计价表": "/m/015qbp",
    "汽车": "/m/0k4j",
    "汽車": "/m/0k4j",
    "小轿车": "/m/0k4j",
    "车辆": "/m/0k4j",
    "桥": "/m/015kr",
    "船": "/m/019jd",
    "棕榈树": "/m/0cdl1",
    "山": "/m/09d_r",
    "消防栓": "/m/01pns0",
    "楼梯": "/m/01lynh",
    "樓梯": "/m/01lynh",
    "公交车": "/m/01bjv",
    "校车": "/m/01bjv",
}

ITEM_ENGLISH = {
    "/m/0pg52": "taxis",
    "/m/01bjv": "bus",
    "/m/02yvhj": "school bus",
    "/m/04_sv": "motorcycles",
    "/m/013xlm": "tractors",
    "/m/01jk_4": "chimneys",
    "/m/014xcs": "crosswalks",
    "/m/015qff": "traffic lights",
    "/m/0199g": "bicycles",
    "/m/015qbp": "parking meters",
    "/m/0k4j": "cars",
    "/m/015kr": "bridges",
    "/m/019jd": "boats",
    "/m/0cdl1": "palm trees",
    "/m/09d_r": "mountains or hills",
    "/m/01pns0": "fire hydrant",
    "/m/01lynh": "stairs",
}

# 合并为统一查找表：中文词 + 英文词（含单复数变体）-> quesid
QUESTION_ID_MAP = dict(CAPTCHA_ITEM_QUESID)
for _qid, _en in ITEM_ENGLISH.items():
    QUESTION_ID_MAP[_en] = _qid
    if _en.endswith("s"):
        QUESTION_ID_MAP[_en[:-1]] = _qid
    elif not _en.endswith("s"):
        QUESTION_ID_MAP[_en + "s"] = _qid
QUESTION_ID_MAP.update({
    "taxi": "/m/0pg52",
    "buses": "/m/01bjv",
    "school buses": "/m/02yvhj",
    "motorcycle": "/m/04_sv",
    "chimney": "/m/013xlm",
    "crosswalk": "/m/014xcs",
    "traffic light": "/m/015qff",
    "bicycle": "/m/0199g",
    "parking meter": "/m/015qbp",
    "car": "/m/0k4j",
    "vehicle": "/m/0k4j",
    "vehicles": "/m/0k4j",
    "bridge": "/m/015kr",
    "boat": "/m/019jd",
    "palm tree": "/m/0cdl1",
    "mountains": "/m/09d_r",
    "hills": "/m/09d_r",
    "fire hydrants": "/m/01pns0",
    "a fire hydrant": "/m/01pns0",
    "stair": "/m/01lynh",
})

QUESID_TO_ITEM = {
    "/m/0pg52": "出租车",
    "/m/01bjv": "巴士/公交车/校车",
    "/m/02yvhj": "校车",
    "/m/04_sv": "摩托车",
    "/m/013xlm": "拖拉机",
    "/m/01jk_4": "烟囱",
    "/m/014xcs": "人行横道",
    "/m/015qff": "红绿灯",
    "/m/0199g": "自行车",
    "/m/015qbp": "停车计价表",
    "/m/0k4j": "汽车",
    "/m/015kr": "桥",
    "/m/019jd": "船",
    "/m/0cdl1": "棕榈树",
    "/m/09d_r": "山",
    "/m/01pns0": "消防栓",
    "/m/01lynh": "楼梯",
}


def question_label(quesid):
    """根据 question ID 返回可读中文标签（便于日志）。"""
    return QUESID_TO_ITEM.get(quesid, quesid)


class HumanPacer:
    """拟人节奏控制器：随机停顿，模拟真人思考/移动/点击间隔。"""

    def __init__(self, factor=1.0):
        self.factor = max(0.5, float(factor))

    def pause(self, lo, hi):
        """在 [lo, hi] 秒范围内随机 sleep，并乘以 factor。"""
        time.sleep(random.uniform(lo, hi) * self.factor)

    def sleep_fn(self):
        """返回与 human_sleep(a,b) 兼容的 callable。"""
        return lambda a, b: self.pause(a, b)


def is_recaptcha_solved(page):
    """reCAPTCHA v2 是否已通过（checkbox 或 token）。"""
    return anchor_checked(page) or len(grecaptcha_response(page)) > 20


def question_text_to_id(text):
    """将 reCAPTCHA 题面文字映射为 YesCaptcha question ID。"""
    if not text:
        return None
    raw = text.strip().lower()
    raw = re.sub(r"\s+", " ", raw)
    # 从长句中提取「包含 XXX 的」目标词
    for pat in (
        r"包含[「\"']?(.+?)[」\"']?的(?:所有|全部)?(?:图片|图块|图像|方块)",
        r"select all (?:squares|images|tiles) with (.+?)(?:\.|$)",
        r"with a (.+?)(?:\.|$)",
    ):
        m = re.search(pat, text, re.I)
        if m:
            text = m.group(1).strip()
            raw = text.lower()
            break
    for name in sorted(QUESTION_ID_MAP.keys(), key=len, reverse=True):
        if name in raw or name in text:
            return QUESTION_ID_MAP[name]
    return None


def get_entry_frame(page):
    """定位 reCAPTCHA 入口 iframe（checkbox）。"""
    for frame in page.frames:
        url = (frame.url or "").lower()
        if "anchor" in url:
            return frame
    for frame in page.frames:
        try:
            if frame.locator("#recaptcha-anchor").count():
                return frame
        except Exception:
            pass
    loc = page.locator('iframe[title="reCAPTCHA"]')
    if loc.count():
        handle = loc.first.element_handle()
        if handle:
            return handle.content_frame()
    return None


def get_challenge_frame(page):
    """定位 reCAPTCHA 图片挑战 iframe（bframe）。"""
    for frame in page.frames:
        url = (frame.url or "").lower()
        if "bframe" in url or "api2/bframe" in url:
            return frame
    for frame in page.frames:
        try:
            if frame.locator("#rc-imageselect").count():
                return frame
        except Exception:
            pass
    loc = page.locator('iframe[title*="recaptcha challenge"], iframe[title*="reCAPTCHA 验证"]')
    if loc.count():
        handle = loc.first.element_handle()
        if handle:
            return handle.content_frame()
    return None


def challenge_visible(page):
    """判断图片选择挑战是否已弹出。"""
    frame = get_challenge_frame(page)
    if not frame:
        return False
    try:
        return frame.locator("#rc-imageselect-target").count() > 0
    except Exception:
        return False


def anchor_checked(page):
    """检查 checkbox 是否已通过（aria-checked=true 或 checked class）。"""
    frame = get_entry_frame(page)
    if not frame:
        return False
    try:
        anchor = frame.locator("#recaptcha-anchor")
        if not anchor.count():
            return False
        checked = anchor.first.get_attribute("aria-checked")
        if str(checked).lower() == "true":
            return True
        cls = anchor.first.get_attribute("class") or ""
        return "recaptcha-checkbox-checked" in cls
    except Exception:
        return False


def grecaptcha_response(page):
    """读取主文档 g-recaptcha-response 或 grecaptcha.getResponse()。"""
    try:
        tok = page.evaluate(
            """() => {
                if (window.grecaptcha && typeof window.grecaptcha.getResponse === 'function') {
                    const r = window.grecaptcha.getResponse();
                    if (r && r.length > 20) return r;
                }
                for (const ta of document.querySelectorAll('textarea[name="g-recaptcha-response"]')) {
                    if ((ta.value || '').length > 20) return ta.value;
                }
                return '';
            }"""
        )
        return tok or ""
    except Exception:
        return ""


def read_challenge_question(frame):
    """从挑战 iframe 读取识别目标文字（优先 strong 标签内的目标词）。"""
    selectors = [
        ".rc-imageselect-desc-wrapper strong",
        ".rc-imageselect-desc-no-canonical strong",
        ".rc-imageselect-desc-wrapper",
        ".rc-imageselect-instructions",
    ]
    for sel in selectors:
        loc = frame.locator(sel)
        if loc.count():
            txt = (loc.first.inner_text(timeout=2000) or "").strip()
            if txt:
                qid = question_text_to_id(txt)
                if qid:
                    return txt
                if sel.endswith("strong"):
                    return txt
    for sel in selectors:
        loc = frame.locator(sel)
        if loc.count():
            return (loc.first.inner_text(timeout=2000) or "").strip()
    return ""


def _resize_png(png_bytes, size):
    """将 PNG 缩放到标准尺寸（300/450/100）。"""
    from PIL import Image
    img = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    img = img.resize(size, Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def capture_grid_png(frame):
    """
    截取九宫格/十六宫格 PNG，返回 (base64, grid_side_px, cell_count)。
    grid_side_px: 300（3x3）或 450（4x4）。
    """
    target = frame.locator("#rc-imageselect-target table").first
    if not target.count():
        target = frame.locator("#rc-imageselect-target").first
    png = target.screenshot(timeout=10000)
    cells = frame.locator("#rc-imageselect-target table td").count()
    side = 450 if cells >= 16 else 300
    png = _resize_png(png, (side, side))
    return base64.b64encode(png).decode("ascii"), side, cells


def load_yescaptcha_solver():
    """加载 YesCaptcha 适配器实例。"""
    import os
    from config_paths import load_project_config
    from adapters.base import discover, REGISTRY

    here = os.path.dirname(os.path.abspath(__file__))
    adapters_dir = os.path.join(here, "adapters")
    cfg, _ = load_project_config()
    discover(adapters_dir, external_paths=cfg.get("external_adapters") or [])
    cls = REGISTRY.get("yescaptcha")
    if not cls:
        raise RuntimeError("未找到 yescaptcha 适配器")
    return cls(cfg.get("yescaptcha") or {})


def classify_grid(platform, image_b64, question_id, grid_side=300, confidence=0.5):
    """调用打码平台识别网格，返回 objects 索引列表；4x4 不传 confidence。"""
    if platform != "yescaptcha":
        raise RuntimeError(f"recaptcha-grid 当前仅实现 yescaptcha，收到: {platform}")
    solver = load_yescaptcha_solver()
    conf = confidence if grid_side == 300 else None
    res = solver.solve_recaptcha_v2_classification(
        image_b64, question_id, confidence=conf,
    )
    sol = res.get("solution") or {}
    objs = sol.get("objects") or []
    if isinstance(objs, list):
        return [int(x) for x in objs]
    return []


def click_recaptcha_anchor(page, pacer):
    """拟人点击 reCAPTCHA 复选框（未通过时）。"""
    if is_recaptcha_solved(page):
        return True
    frame = get_entry_frame(page)
    if not frame:
        return False
    anchor = frame.locator("#recaptcha-anchor")
    if not anchor.count():
        return False
    pacer.pause(0.6, 1.4)
    try:
        box = anchor.first.bounding_box()
        if box and page:
            cx = box["x"] + box["width"] / 2 + random.uniform(-4, 4)
            cy = box["y"] + box["height"] / 2 + random.uniform(-3, 3)
            human_click_at(page, cx, cy, state=get_mouse_state(page))
            pacer.pause(1.0, 2.0)
            return True
    except Exception:
        pass
    anchor.first.click()
    pacer.pause(1.0, 2.0)
    return True


def wait_recaptcha_branch(page, timeout_sec=18, pacer=None):
    """
    点击 checkbox 后等待分支结果。
    返回: direct（直接通过）| challenge（图片多轮）| unknown。
    """
    if pacer is None:
        pacer = HumanPacer()
    deadline = time.time() + timeout_sec
    saw_challenge = False
    while time.time() < deadline:
        if challenge_visible(page):
            saw_challenge = True
            return "challenge"
        if is_recaptcha_solved(page):
            return "direct"
        pacer.pause(0.45, 0.95)
    if saw_challenge or challenge_visible(page):
        return "challenge"
    if is_recaptcha_solved(page):
        return "direct"
    return "unknown"


def click_grid_indices(page, frame, indices, pacer):
    """拟人点击九宫格/十六宫格（移动鼠标 + 较长间隔）。"""
    pacer.pause(0.8, 1.8)
    for i, idx in enumerate(indices):
        cells = frame.locator("#rc-imageselect-target table td")
        if idx >= cells.count():
            continue
        cell = cells.nth(idx)
        try:
            box = cell.bounding_box()
            if box:
                cx = box["x"] + box["width"] / 2 + random.uniform(-5, 5)
                cy = box["y"] + box["height"] / 2 + random.uniform(-5, 5)
                human_click_at(page, cx, cy, state=get_mouse_state(page))
                pacer.pause(0.35, 0.85)
                continue
        except Exception:
            pass
        try:
            cell.click(timeout=10000)
        except Exception:
            cell.click(force=True, timeout=6000)
        if i < len(indices) - 1:
            pacer.pause(0.75, 1.55)
        else:
            pacer.pause(0.5, 1.0)


def click_action_button(frame, pacer):
    """拟人点击「验证 / 跳过 / 下一页」按钮。"""
    btn = frame.locator("#recaptcha-verify-button")
    if not btn.count() or not btn.first.is_visible():
        return False, ""
    pacer.pause(0.9, 1.8)
    label = (btn.first.inner_text(timeout=2000) or "").strip()
    btn.first.click()
    pacer.pause(2.2, 4.2)
    return True, label


def wait_challenge_closed(page, timeout_sec=45):
    """等待图片挑战 iframe 关闭或 checkbox 已通过。"""
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if is_recaptcha_solved(page):
            return True
        if not challenge_visible(page):
            time.sleep(0.5)
            if is_recaptcha_solved(page):
                return True
            return True
        time.sleep(0.4)
    return is_recaptcha_solved(page) or not challenge_visible(page)


def wait_for_manual_ready(page, poll_interval=2.0, signal_file=None):
    """
    手动模式：等待用户触发 reCAPTCHA（直接通过或图片挑战均可）。
    signal_file 与页面状态同时满足才继续。
    """
    print(
        "\n=== 手动模式 ===\n"
        "1. 请在浏览器中点击 reCAPTCHA 复选框\n"
        "2. 若出现图片挑战或已直接通过（绿色对勾），再发送继续信号\n"
        f"   信号文件：{signal_file or '(未启用 --wait-signal)'}\n"
        "   （终端输入 q 退出）\n",
        flush=True,
    )
    if signal_file:
        import os
        sig = os.path.abspath(signal_file)

        def _ready():
            return is_recaptcha_solved(page) or challenge_visible(page)

        print(f"[等待] 轮询信号文件: {sig}（需 reCAPTCHA 已响应才继续）", flush=True)
        while True:
            if os.path.isfile(sig) and _ready():
                try:
                    os.remove(sig)
                except OSError:
                    pass
                mode = "direct" if is_recaptcha_solved(page) else "challenge"
                print(f"[信号] reCAPTCHA 已响应（分支={mode}），开始处理。", flush=True)
                return mode
            if _ready():
                print("[提示] reCAPTCHA 已响应，等待继续信号…", flush=True)
            time.sleep(poll_interval)
    while True:
        if is_recaptcha_solved(page) or challenge_visible(page):
            print("[提示] 可按 Enter 继续。", flush=True)
        try:
            line = input(">>> 按 Enter 继续（q 退出）: ").strip().lower()
        except EOFError:
            line = ""
        if line in ("q", "quit", "exit"):
            raise SystemExit("用户取消")
        if is_recaptcha_solved(page):
            return "direct"
        if challenge_visible(page):
            return "challenge"
        return "unknown"


def solve_recaptcha_grid(page, platform, max_rounds=15, confidence=0.5, pacer=None):
    """
    图片多轮分支：识别并点击网格，直到 checkbox 通过或达 max_rounds。
    """
    if pacer is None:
        pacer = HumanPacer()

    rounds = 0
    last_error = None
    while rounds < max_rounds:
        if is_recaptcha_solved(page):
            return _grid_result(page, True, rounds, None)

        if not challenge_visible(page):
            pacer.pause(1.2, 2.2)
            if is_recaptcha_solved(page):
                return _grid_result(page, True, rounds, None)
            if rounds == 0:
                last_error = "未检测到图片挑战"
                break
            pacer.pause(1.8, 3.0)
            if not challenge_visible(page):
                break

        frame = get_challenge_frame(page)
        if not frame:
            last_error = "无法定位挑战 iframe"
            pacer.pause(1.0, 1.8)
            rounds += 1
            continue

        question = read_challenge_question(frame)
        qid = question_text_to_id(question)
        if not qid:
            print(f"[grid] 第 {rounds + 1} 轮: 题面无法映射 {question!r} → 点跳过", flush=True)
            click_action_button(get_challenge_frame(page) or frame, pacer)
            pacer.pause(2.5, 4.0)
            rounds += 1
            continue

        try:
            img_b64, side, cells = capture_grid_png(frame)
        except Exception as exc:
            last_error = f"截图失败: {exc}"
            pacer.pause(1.0, 1.8)
            rounds += 1
            continue

        indices = []
        try:
            indices = classify_grid(
                platform, img_b64, qid, grid_side=side, confidence=confidence,
            )
        except Exception as exc:
            last_error = f"平台识别失败: {exc}"
            print(f"[grid] 识别异常: {exc}，尝试点跳过", flush=True)

        action = "skip"
        if indices:
            action = "click"
            print(
                f"[grid] 第 {rounds + 1} 轮: 题面={question!r} "
                f"qid={qid}({question_label(qid)}) "
                f"grid={side}px cells={cells} 点击={indices}",
                flush=True,
            )
            click_grid_indices(page, frame, indices, pacer)
            pacer.pause(1.0, 2.0)
        else:
            print(
                f"[grid] 第 {rounds + 1} 轮: 题面={question!r} "
                f"qid={qid}({question_label(qid)}) "
                f"grid={side}px 无匹配 → 点跳过",
                flush=True,
            )

        frame = get_challenge_frame(page) or frame
        clicked, btn_label = click_action_button(frame, pacer)
        if clicked:
            print(f"[grid] 已点按钮: {btn_label!r} ({action})", flush=True)
        pacer.pause(2.5, 4.5)
        rounds += 1

        if is_recaptcha_solved(page):
            return _grid_result(page, True, rounds, None)

    return _grid_result(page, is_recaptcha_solved(page), rounds, last_error)


def _grid_result(page, solved, rounds, last_error):
    """组装图片挑战阶段的结果字典。"""
    return {
        "grid_solved": bool(solved),
        "rounds": rounds,
        "grid_rounds": rounds,
        "anchor_checked": anchor_checked(page),
        "token_len": len(grecaptcha_response(page)),
        "last_error": last_error,
    }


def wait_for_token(page, timeout_sec=8, pacer=None):
    """轮询等待 g-recaptcha-response token 写入。"""
    if pacer is None:
        pacer = HumanPacer()
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        tok = grecaptcha_response(page)
        if len(tok) > 20:
            return tok
        pacer.pause(0.35, 0.65)
    return grecaptcha_response(page)


def solve_recaptcha_v2(
    page,
    platform,
    auto_click_anchor=True,
    wait_manual=False,
    wait_signal=None,
    max_rounds=15,
    confidence=0.5,
    humanize_factor=1.0,
):
    """
    通用 Google reCAPTCHA v2 流程：
    1. 可选自动点 checkbox
    2. 判断 direct（直接过）或 challenge（图片多轮）
    3. challenge 时走 YesCaptcha 识别 + 拟人点击
    """
    pacer = HumanPacer(humanize_factor)
    branch = "unknown"

    if wait_manual or wait_signal:
        branch = wait_for_manual_ready(page, signal_file=wait_signal)
        if branch == "direct" or is_recaptcha_solved(page):
            wait_for_token(page, timeout_sec=6, pacer=pacer)
            return {
                "ok": True,
                "branch": "direct",
                "grid_solved": True,
                "grid_rounds": 0,
                "anchor_checked": anchor_checked(page),
                "token_len": len(grecaptcha_response(page)),
                "last_error": None,
            }
    elif auto_click_anchor:
        if not click_recaptcha_anchor(page, pacer):
            return {
                "ok": False,
                "branch": "no_widget",
                "grid_solved": False,
                "grid_rounds": 0,
                "anchor_checked": False,
                "token_len": 0,
                "last_error": "页面上未找到 reCAPTCHA checkbox",
            }
        branch = wait_recaptcha_branch(page, timeout_sec=20, pacer=pacer)
        print(f"[recaptcha] 分支判定: {branch}", flush=True)
        if branch == "direct":
            wait_for_token(page, timeout_sec=6, pacer=pacer)
            return {
                "ok": True,
                "branch": "direct",
                "grid_solved": True,
                "grid_rounds": 0,
                "anchor_checked": anchor_checked(page),
                "token_len": len(grecaptcha_response(page)),
                "last_error": None,
            }

    if branch in ("challenge", "unknown") or challenge_visible(page):
        if not challenge_visible(page) and not is_recaptcha_solved(page):
            pacer.pause(2.0, 3.5)
        if is_recaptcha_solved(page):
            wait_for_token(page, timeout_sec=6, pacer=pacer)
            return {
                "ok": True,
                "branch": "direct",
                "grid_solved": True,
                "grid_rounds": 0,
                "anchor_checked": anchor_checked(page),
                "token_len": len(grecaptcha_response(page)),
                "last_error": None,
            }
        if not challenge_visible(page):
            return {
                "ok": False,
                "branch": branch,
                "grid_solved": False,
                "grid_rounds": 0,
                "anchor_checked": anchor_checked(page),
                "token_len": len(grecaptcha_response(page)),
                "last_error": "未出现图片挑战且未直接通过",
            }
        grid_res = solve_recaptcha_grid(
            page, platform, max_rounds=max_rounds, confidence=confidence, pacer=pacer,
        )
        wait_for_token(page, timeout_sec=8, pacer=pacer)
        grid_res["branch"] = "challenge"
        grid_res["ok"] = grid_res.get("grid_solved", False)
        grid_res["token_len"] = len(grecaptcha_response(page))
        grid_res["anchor_checked"] = anchor_checked(page)
        return grid_res

    wait_for_token(page, timeout_sec=4, pacer=pacer)
    return {
        "ok": is_recaptcha_solved(page),
        "branch": branch,
        "grid_solved": is_recaptcha_solved(page),
        "grid_rounds": 0,
        "anchor_checked": anchor_checked(page),
        "token_len": len(grecaptcha_response(page)),
        "last_error": None if is_recaptcha_solved(page) else f"未知分支: {branch}",
    }
