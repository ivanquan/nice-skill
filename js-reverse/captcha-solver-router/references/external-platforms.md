# 外接打码平台（插件机制）参考

本 skill 的打码平台接入是**注册表驱动 + 可插拔**的：内置三家，用户可随时外接任意平台。

## 1. 架构

```
scripts/
├── solve.py                 # 注册表驱动的统一客户端，--platform 取适配器
├── adapters/
│   ├── base.py              # BaseSolver 接口 + HTTP/图像辅助 + discover()
│   ├── yescaptcha.py        # 内置
│   ├── bingtop.py           # 内置
│   ├── jfbym.py             # 内置
│   ├── template.py          # 外接适配器模板（复制改四样）
│   └── <your>.py            # 用户外接（自动发现）
├── learn_platform.py        # 按 spec 生成适配器骨架
└── config.json              # 密钥 + external_adapters 路径列表
```

`solve.py` 启动时会 `discover()`：导入 `adapters/` 下所有 `.py`（除 base/template/__init__），再导入 `config.json` 里 `external_adapters` 列出的外部路径，每个适配器用 `@register` 把自己注册进 `REGISTRY`。

## 2. BaseSolver 接口契约

```python
class BaseSolver:
    name = "myplatform"            # 小写唯一，--platform 用它
    display = "MyPlatform"         # 展示名
    supports = {"token": True, "image": True, "slide": False,
                "click": False, "rotate": False}
    secret_fields = ["api_key"]    # 需要的密钥字段（写进 config.json 对应段）

    def __init__(self, cfg=None):  # cfg = config.json 里的 {platform: {...}} 段
        self.api_key = self.secret("api_key", "MYPLATFORM_KEY")

    def solve_token(self, task_type=None, website_url=None, website_key=None, **extra): ...
    def solve_image(self, b64, captcha_type=None, **extra): ...
    def solve_slide(self, slice_b64=None, bg_b64=None, captcha_type=None, **extra): ...
    def solve_click(self, b64, extra_text=None, captcha_type=None, **extra): ...
    def solve_rotate(self, b64, captcha_type=None, **extra): ...
```

辅助函数（从 `adapters.base` 导入）：`post_json(url, payload, timeout, headers)`、`post_form(url, payload, timeout)`、`img_to_b64(path)`、`self.secret(field, env_name)`。

## 3. 两种外接方式

- **A. 丢进目录**：`cp adapters/template.py adapters/myplatform.py` → 改 → 自动发现。
- **B. 外部路径**：文件放别处，在 `config.json` 加 `"external_adapters": ["C:/abs/path/myplatform.py"]`。

## 4. skill 学习新平台 API 的工作流

当用户要接一个未知平台时（详见 SKILL.md「外接打码平台」章节）：

1. WebFetch/WebSearch 抓文档，提取 base URL / 鉴权 / endpoint / 字段 / 类型 / 价格。
2. 整理成 spec JSON（见 `learn_platform.py` 顶部注释）：
   ```json
   {"name":"newcap","display":"NewCap","base_url":"https://api.newcap.com",
    "auth":{"field":"token","env":"NEWCAP_TOKEN"},
    "supports":["token","image","slide"],
    "endpoints":{"create":".../createTask","result":".../getTaskResult","image":".../image","slide":".../slide"},
    "notes":"从 https://newcap.com/docs 提取：createTask 轮询 getTaskResult"}
   ```
3. `python scripts/learn_platform.py --spec spec.json --write` 生成骨架（已填方法签名 + endpoint + 调研备注 + TODO）。
4. 补全每个 `solve_*` 的返回解析（结合真实返回微调）。
5. `config.json` 加密钥段（或 `setup.py`），**不进对话**。
6. 冒烟：`python scripts/solve.py --platform newcap --op image --image cap.png`。

## 5. 已整理的平台（spec 可直接复用）

| 平台 | 形态 | token | 滑块 | 价格量级 | 备注 |
|---|---|---|---|---|---|
| YesCaptcha | 2captcha 兼容 createTask/getTaskResult | ✅ | ❌ | 1元=1000点；token ¥0.015–0.03 | 有中国节点，无滑块类 |
| BingTop 冰拓 | 自研，阻塞式 POST | ❌ | ✅(双图) | 低至 ¥0.001/图 | 类型极全，返回 x/y |
| JFBYM 云码 | 2captcha 风格，customApi+funnelApi | ✅ | ✅(双图) | 滑块¥0.01/recaptcha¥0.032/CF¥0.02 | 类型最均衡 |

> 这三家已内置在 `adapters/`，无需外接。上面表格是「调研维度」模板，新平台学习后同样按这套维度补一行即可。
