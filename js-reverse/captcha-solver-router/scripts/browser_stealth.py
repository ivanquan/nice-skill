#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Playwright / CloakBrowser 通用反检测上下文、CDP 补丁与拟人鼠标轨迹。

供 automate.py 在为用户编写自动化程序时统一注入，降低 navigator.webdriver、
CDP 残留、headless 指纹、合成鼠标事件等被验证码/风控识别的概率。
"""

import math
import random
import time

# 与 viewport 一致的桌面 Chrome UA（Windows）
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

DEFAULT_VIEWPORT = {"width": 1366, "height": 768}

# Chromium 启动参数（Playwright 后端）
CHROME_STEALTH_LAUNCH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--disable-infobars",
    "--window-size=1366,768",
    "--lang=zh-CN,zh",
    "--disable-dev-shm-usage",
    "--no-first-run",
    "--no-default-browser-check",
]

# Playwright 默认会加 --enable-automation，必须去掉
PLAYWRIGHT_IGNORE_DEFAULT_ARGS = ["--enable-automation"]

# 页面加载前注入的 stealth 脚本
STEALTH_INIT_SCRIPT = """
(() => {
  const patch = (obj, prop, val) => {
    try {
      Object.defineProperty(obj, prop, { get: () => val, configurable: true });
    } catch (e) {}
  };

  patch(navigator, 'webdriver', undefined);
  patch(navigator, 'languages', ['zh-CN', 'zh', 'en-US', 'en']);
  patch(navigator, 'platform', 'Win32');
  patch(navigator, 'hardwareConcurrency', 8);
  patch(navigator, 'deviceMemory', 8);
  patch(navigator, 'maxTouchPoints', 0);

  if (!window.chrome) {
    window.chrome = {
      runtime: {},
      loadTimes: function () {},
      csi: function () {},
      app: { isInstalled: false },
    };
  }

  try {
    const makePlugin = (name, desc, filename) => {
      const p = { name, description: desc, filename, length: 1 };
      p[0] = { type: 'application/pdf', suffixes: 'pdf', description: desc };
      return p;
    };
    patch(navigator, 'plugins', [
      makePlugin('Chrome PDF Plugin', 'Portable Document Format', 'internal-pdf-viewer'),
      makePlugin('Chrome PDF Viewer', '', 'mhjfbmdgcfjbbpaeojofohoefgiehjai'),
      makePlugin('Native Client', '', 'internal-nacl-plugin'),
    ]);
  } catch (e) {}

  try {
    const origQuery = window.navigator.permissions.query.bind(window.navigator.permissions);
    window.navigator.permissions.query = (parameters) => {
      if (parameters && parameters.name === 'notifications') {
        return Promise.resolve({ state: Notification.permission, onchange: null });
      }
      return origQuery(parameters);
    };
  } catch (e) {}

  try {
    if (navigator.userAgentData) {
      const orig = navigator.userAgentData.getHighEntropyValues.bind(navigator.userAgentData);
      navigator.userAgentData.getHighEntropyValues = (hints) => orig(hints).then((v) => ({
        ...v,
        platform: 'Windows',
        platformVersion: '15.0.0',
        architecture: 'x86',
        bitness: '64',
        mobile: false,
      }));
    }
  } catch (e) {}

  for (const key of Object.keys(window)) {
    if (/^cdc_[a-zA-Z0-9_]+/.test(key) || /^\\$cdc_/.test(key)) {
      try { delete window[key]; } catch (e) {}
    }
  }

  try {
    const ow = window.outerWidth || 1366;
    const oh = window.outerHeight || 768;
    patch(window, 'outerWidth', ow);
    patch(window, 'outerHeight', oh);
  } catch (e) {}
})();
"""


def stealth_context_options(locale="zh-CN", timezone_id="Asia/Shanghai"):
    """返回 new_context 的通用指纹参数。"""
    return {
        "user_agent": DEFAULT_USER_AGENT,
        "viewport": dict(DEFAULT_VIEWPORT),
        "locale": locale,
        "timezone_id": timezone_id,
        "color_scheme": "light",
        "device_scale_factor": 1,
        "is_mobile": False,
        "has_touch": False,
        "extra_http_headers": {
            "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        },
    }


def build_playwright_launch_kwargs(headless=True, proxy=None, chrome_path=None):
    """组装 Playwright chromium.launch 参数（含反自动化默认项剥离）。"""
    kw = {
        "headless": headless,
        "args": list(CHROME_STEALTH_LAUNCH_ARGS),
        "ignore_default_args": list(PLAYWRIGHT_IGNORE_DEFAULT_ARGS),
        "proxy": proxy,
    }
    if chrome_path:
        kw["executable_path"] = chrome_path
    return kw


def create_stealth_context(browser, backend="playwright", locale="zh-CN", timezone_id="Asia/Shanghai"):
    """
    创建带反检测 init script 的 BrowserContext。
    CloakBrowser 已内置补丁，仅补充 locale/viewport 一致性。
    """
    opts = stealth_context_options(locale=locale, timezone_id=timezone_id)
    ctx = browser.new_context(**opts)
    if backend == "playwright":
        ctx.add_init_script(STEALTH_INIT_SCRIPT)
    return ctx


def apply_page_stealth(page, backend="playwright"):
    """对已有 Page 补注入 stealth（兜底）。"""
    if backend == "playwright":
        page.add_init_script(STEALTH_INIT_SCRIPT)


def apply_playwright_cdp_stealth(page, backend="playwright"):
    """通过 CDP 再注入一层 stealth，并弱化 Automation 标记。"""
    if backend != "playwright":
        return
    try:
        cdp = page.context.new_cdp_session(page)
        cdp.send("Page.addScriptToEvaluateOnNewDocument", {"source": STEALTH_INIT_SCRIPT})
    except Exception:
        pass


def warn_if_builtin_chromium(chrome_path):
    """未配置本机 Chrome 时提示指纹风险。"""
    if not chrome_path:
        print(
            "[stealth] 警告: 未配置本机 Chrome，Playwright 使用内置 Chromium，"
            "验证码场景易被识别。请在 config.json 设置 automation.chrome_executable",
            flush=True,
        )
    else:
        print(f"[stealth] 使用本机 Chrome: {chrome_path}", flush=True)


def close_page_context(page):
    """关闭 Page 关联的 BrowserContext（若由 create_stealth_context 创建）。"""
    ctx = getattr(page, "_pw_context", None)
    if ctx:
        try:
            ctx.close()
        except Exception:
            pass


# ----------------------------------------------------------------------------
# 拟人鼠标（易盾/验证码会采集 mousemove 轨迹）
# ----------------------------------------------------------------------------
class MouseTraceState:
    """记录上一鼠标位置，用于连续贝塞尔移动。"""

    def __init__(self):
        self.x = None
        self.y = None


def get_mouse_state(page):
    """获取或创建页面级鼠标轨迹状态（全自动化操作共用）。"""
    state = getattr(page, "_pw_mouse_state", None)
    if state is None:
        state = MouseTraceState()
        page._pw_mouse_state = state
    return state


def bezier_path(x0, y0, x1, y1, n=28):
    """生成贝塞尔缓动轨迹点。"""
    ctrl_x = (x0 + x1) / 2 + random.uniform(-25, 25)
    ctrl_y = (y0 + y1) / 2 + random.uniform(-18, 18)
    pts = []
    for i in range(n + 1):
        t = i / n
        mt = 1 - t
        x = mt * mt * x0 + 2 * mt * t * ctrl_x + t * t * x1
        y = mt * mt * y0 + 2 * mt * t * ctrl_y + t * t * y1
        x += random.uniform(-0.8, 0.8)
        y += random.uniform(-0.8, 0.8)
        pts.append((round(x, 1), round(y, 1)))
    return pts


def human_move_to(page, x, y, state=None, steps=None):
    """贝塞尔移动到页面绝对坐标，产生 mousemove 事件链。"""
    if state is None:
        state = get_mouse_state(page)
    if state.x is None or state.y is None:
        state.x = x + random.uniform(-100, 100)
        state.y = y + random.uniform(-80, 80)
    n = steps or random.randint(20, 38)
    pts = bezier_path(state.x, state.y, x, y, n=n)
    for px, py in pts[1:]:
        page.mouse.move(px, py)
        time.sleep(random.uniform(0.006, 0.022))
    state.x, state.y = x, y


def human_click_at(page, x, y, state=None, pause_before=(0.04, 0.12), pause_down=(0.03, 0.09)):
    """拟人移动 + 按下/抬起点击（相对 locator.click 更易被行为风控接受）。"""
    if state is None:
        state = get_mouse_state(page)
    human_move_to(page, x, y, state=state)
    time.sleep(random.uniform(*pause_before))
    page.mouse.down()
    time.sleep(random.uniform(*pause_down))
    page.mouse.up()


def _ease_in_out_cubic(t):
    """三次缓动：起步慢、中段快、收尾慢，模拟人手滑块加速曲线。"""
    if t < 0.5:
        return 4 * t * t * t
    return 1 - pow(-2 * t + 2, 3) / 2


def _build_slide_trajectory(x0, y0, x1, y1, steps=None, overshoot_px=0, jitter_x=True):
    """
    生成滑块拖拽轨迹点：水平主位移 + Y 轴抖动 + 可选末端过冲。
    返回 [(x, y), ...] 不含起点。
    """
    total_dx = x1 - x0
    dist = abs(total_dx)
    n = steps or max(int(dist / 2.5) + random.randint(28, 45), 32)
    end_x = x1 + overshoot_px
    pts = []
    for i in range(1, n + 1):
        t = i / n
        ease = _ease_in_out_cubic(t)
        x = x0 + (end_x - x0) * ease
        # 中段抖动更明显，起止点相对稳定
        jitter_scale = 1.0 - abs(t - 0.5) * 1.4
        y = y0 + random.uniform(-2.8, 2.8) * max(jitter_scale, 0.15)
        # 验证码场景不在 X 轴加抖动，避免落点偏右
        if jitter_x and i < n and random.random() < 0.07:
            x += random.uniform(-1.5, 1.5)
            y += random.uniform(-1.8, 1.8)
        pts.append((round(x, 2), round(y, 2)))
    if overshoot_px:
        corr_n = random.randint(5, 9)
        for j in range(1, corr_n + 1):
            ct = j / corr_n
            cx = end_x + (x1 - end_x) * ct
            cy = y0 + random.uniform(-1.2, 1.2)
            pts.append((round(cx, 2), round(cy, 2)))
    return pts


def human_drag(page, x0, y0, x1, y1, state=None, steps=None):
    """拟人贝塞尔拖拽（旋转手柄等短距离通用）。"""
    if state is None:
        state = get_mouse_state(page)
    human_move_to(page, x0, y0, state=state, steps=random.randint(6, 12))
    time.sleep(random.uniform(0.05, 0.12))
    page.mouse.down()
    n = steps or random.randint(28, 42)
    pts = bezier_path(x0, y0, x1, y1, n=n)
    for px, py in pts[1:]:
        page.mouse.move(px, py)
        time.sleep(random.uniform(0.008, 0.024))
    state.x, state.y = x1, y1
    time.sleep(random.uniform(0.05, 0.14))
    page.mouse.up()
    time.sleep(random.uniform(0.15, 0.35))


def _interpolate_path_points(points, min_segment_len=6.0):
    """在稀疏轨迹关键点之间插值，使回放路径更连续。"""
    if len(points) < 2:
        return list(points)
    out = [tuple(points[0])]
    for x1, y1 in points[1:]:
        x0, y0 = out[-1]
        dist = math.hypot(x1 - x0, y1 - y0)
        steps = max(int(dist / min_segment_len), 1)
        for s in range(1, steps + 1):
            t = s / steps
            out.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
    return out


def human_path_draw(page, points, state=None, interpolate=True):
    """
    沿绝对坐标序列拟人绘制轨迹：移动到起点 → 按下 → 拖拽经过各点 → 抬起。
    适用于「按图中轨迹绘制」类验证码。
    """
    if not points or len(points) < 2:
        raise ValueError("轨迹点不足，至少需要 2 个坐标")
    if state is None:
        state = get_mouse_state(page)

    work = _interpolate_path_points(points) if interpolate else [tuple(p) for p in points]
    x0, y0 = work[0]
    human_move_to(page, x0, y0, state=state, steps=random.randint(10, 18))
    time.sleep(random.uniform(0.08, 0.18))
    page.mouse.down()
    time.sleep(random.uniform(0.04, 0.1))

    total = len(work)
    for i, (px, py) in enumerate(work[1:], 1):
        page.mouse.move(px, py)
        t = i / max(total - 1, 1)
        if t < 0.15 or t > 0.85:
            delay = random.uniform(0.012, 0.028)
        elif random.random() < 0.06:
            delay = random.uniform(0.035, 0.065)
        else:
            delay = random.uniform(0.005, 0.018)
        time.sleep(delay)
        state.x, state.y = px, py

    time.sleep(random.uniform(0.05, 0.14))
    page.mouse.up()
    time.sleep(random.uniform(0.12, 0.28))


def human_slide_drag(page, x0, y0, x1, y1, state=None, allow_overshoot=True, accurate=False):
    """
    拟人滑块拖拽：变速 + Y 轴抖动 + 随机微停顿 + 可选末端小幅过冲回正。
    accurate=True 时禁用 X 抖动与过冲，落点精确吸附到目标坐标（验证码场景）。
    """
    if state is None:
        state = get_mouse_state(page)
    human_move_to(page, x0, y0, state=state, steps=random.randint(8, 16))
    time.sleep(random.uniform(0.08, 0.2))
    page.mouse.down()
    time.sleep(random.uniform(0.04, 0.11))

    dist = abs(x1 - x0)
    overshoot = 0.0
    if allow_overshoot and not accurate and dist > 35 and random.random() < 0.38:
        overshoot = random.uniform(2.0, 7.0) * (1 if x1 >= x0 else -1)

    pts = _build_slide_trajectory(
        x0, y0, x1, y1, overshoot_px=overshoot, jitter_x=not accurate,
    )
    total = len(pts)
    for i, (px, py) in enumerate(pts, 1):
        page.mouse.move(px, py)
        t = i / total
        if t < 0.12 or t > 0.88:
            delay = random.uniform(0.014, 0.032)
        elif random.random() < 0.055:
            delay = random.uniform(0.04, 0.075)
        else:
            delay = random.uniform(0.004, 0.018)
        time.sleep(delay)

    # 精确落点，消除轨迹末段累积偏差
    page.mouse.move(x1, y0)
    state.x, state.y = x1, y0
    time.sleep(random.uniform(0.06, 0.16))
    page.mouse.up()
    time.sleep(random.uniform(0.1, 0.3))
