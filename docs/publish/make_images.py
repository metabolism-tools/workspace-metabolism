"""Generate launch images for workspace-metabolism (Pillow, no external assets).

Outputs:
  docs/publish/images/cover-zh.png         (1242x1656, portrait, recommended title)
  docs/publish/images/cover-alt-zh.png     (1242x1656, portrait, alternate title)
  docs/publish/images/four-phases-zh.png   (1536x864, landscape, X/Zhihu/Xiaohongshu)
  docs/publish/images/stack-l5-zh.png      (1536x864, landscape, X/Zhihu)
  docs/publish/images/experiment-30-zh.png (1080x1080, square, Xiaohongshu)
  docs/publish/images/four-phases-zh-v.png (1242x1656, portrait, Xiaohongshu)
  docs/publish/images/stack-l5-zh-v.png    (1242x1656, portrait, Xiaohongshu)
  docs/publish/images/experiment-30-zh-v.png (1242x1656, portrait, Xiaohongshu)
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent / "images"
OUT.mkdir(exist_ok=True)

# Palette: dark, clean, "metabolism" green accent
BG = (14, 20, 32)
CARD = (27, 36, 52)
CARD_LIGHT = (35, 47, 66)
BORDER = (58, 74, 98)
TEXT = (241, 245, 249)
MUTED = (148, 163, 184)
ACCENT = (61, 220, 151)
ACCENT_DIM = (52, 211, 153)
CYAN = (125, 211, 252)
WARN = (251, 191, 36)
RED = (248, 113, 113)


def font(size, bold=False, code=False):
    candidates = [
        (code and "C:/Windows/Fonts/consola.ttf")
        or (bold and "C:/Windows/Fonts/msyhbd.ttc")
        or "C:/Windows/Fonts/msyh.ttc",
        bold and "C:/Windows/Fonts/msyhbd.ttc",
        "C:/Windows/Fonts/msyh.ttc",
    ]
    for path in candidates:
        if path:
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    raise RuntimeError("no usable font found")


def new_canvas(w, h):
    img = Image.new("RGB", (w, h), BG)
    return img, ImageDraw.Draw(img)


def center_text(draw, cx, cy, text, fnt, fill):
    draw.text((cx, cy), text, font=fnt, fill=fill, anchor="mm")


def center_rect(draw, cx, cy, w, h, radius, fill, outline=None, width=1):
    x0, y0 = cx - w // 2, cy - h // 2
    draw.rounded_rectangle(
        (x0, y0, x0 + w, y0 + h), radius=radius, fill=fill,
        outline=outline, width=width,
    )


def arrow(draw, x1, y, x2, color=ACCENT, width=6):
    draw.line((x1, y, x2 - 14, y), fill=color, width=width)
    draw.polygon(
        [(x2 - 16, y - 12), (x2 - 16, y + 12), (x2 + 8, y)],
        fill=color,
    )


def wrap(draw, text, fnt, max_w):
    lines = []
    for raw in text.split("\n"):
        line = ""
        for ch in raw:
            if draw.textlength(line + ch, font=fnt) <= max_w:
                line += ch
            else:
                lines.append(line)
                line = ch
        lines.append(line)
    return lines


def cover(title_lines, filename):
    w, h = 1242, 1656
    img, d = new_canvas(w, h)

    # soft accent glow at top
    d.ellipse((-260, -320, 620, 420), fill=(24, 50, 46))
    d.ellipse((820, 1180, 1520, 1880), fill=(22, 38, 58))

    # badge
    badge = "开源工具 · workspace-metabolism"
    bf = font(34)
    bw = int(d.textlength(badge, font=bf)) + 64
    center_rect(d, w // 2, 150, bw, 74, 37, CARD_LIGHT, outline=BORDER, width=2)
    center_text(d, w // 2, 150, badge, bf, MUTED)

    # main title
    t1 = font(96, bold=True)
    t2 = font(96, bold=True)
    center_text(d, w // 2, 400, title_lines[0], t1, TEXT)
    center_text(d, w // 2, 640, title_lines[1], t2, TEXT)

    # accent underline
    d.rounded_rectangle((w // 2 - 130, 722, w // 2 + 130, 734), radius=6, fill=ACCENT)

    # subtitle
    sf = font(54, bold=True)
    center_text(d, w // 2, 850, "这个框架叫「智能体代谢工程」", sf, ACCENT)
    ef = font(30)
    center_text(d, w // 2, 912, "Agentic Metabolic Engineering · agentic 工程栈 L5", ef, MUTED)

    # four mini chips
    chips = ["检查", "回收", "验证", "回滚"]
    cw, cgap = 170, 36
    total = cw * 4 + cgap * 3
    x = (w - total) // 2 + cw // 2
    cy = 1090
    cf = font(42, bold=True)
    for i, name in enumerate(chips):
        center_rect(d, x + i * (cw + cgap), cy, cw, cw, 24, CARD, outline=BORDER, width=2)
        center_text(d, x + i * (cw + cgap), cy, name, cf, TEXT if i % 2 == 0 else ACCENT)

    # bottom hint
    hf = font(34, bold=True)
    center_text(d, w // 2, 1460, "GitHub 搜索 workspace-metabolism", hf, TEXT)
    nf = font(28)
    center_text(d, w // 2, 1520, "零依赖 · Windows / Linux / macOS · 开源可审计", nf, MUTED)

    img.save(OUT / filename)


def experiment_30():
    w, h = 1080, 1080
    img, d = new_canvas(w, h)
    d.ellipse((-220, -260, 460, 420), fill=(23, 50, 46))
    d.ellipse((760, 820, 1380, 1440), fill=(22, 38, 58))

    badge = "30 轮对照实验 · 可复现"
    bf = font(34, bold=True)
    bw = int(d.textlength(badge, font=bf)) + 64
    center_rect(d, w // 2, 120, bw, 78, 39, CARD_LIGHT, outline=BORDER, width=2)
    center_text(d, w // 2, 120, badge, bf, ACCENT)

    sf = font(40, bold=True)
    center_text(d, w // 2, 218, "两个一模一样的工作区，各跑 30 轮 AI 循环", sf, TEXT)

    panel_w, panel_h = 450, 470
    y0 = 330
    x1, x2 = 70, 560
    big = font(170, bold=True)
    small = font(40, bold=True)
    sub = font(28)

    # left: governed
    d.rounded_rectangle((x1, y0, x1 + panel_w, y0 + panel_h), radius=30, fill=CARD, outline=ACCENT, width=3)
    center_text(d, x1 + panel_w // 2, y0 + 70, "有代谢", small, ACCENT)
    center_text(d, x1 + panel_w // 2, y0 + 210, "2", big, TEXT)
    center_text(d, x1 + panel_w // 2, y0 + 310, "个文件", small, MUTED)
    center_text(d, x1 + panel_w // 2, y0 + 392, "始终干净，全部可回滚", sub, MUTED)

    # right: ungoverned
    d.rounded_rectangle((x2, y0, x2 + panel_w, y0 + panel_h), radius=30, fill=CARD, outline=RED, width=3)
    center_text(d, x2 + panel_w // 2, y0 + 70, "无代谢", small, RED)
    center_text(d, x2 + panel_w // 2, y0 + 210, "242", big, TEXT)
    center_text(d, x2 + panel_w // 2, y0 + 310, "个文件", small, MUTED)
    center_text(d, x2 + panel_w // 2, y0 + 392, "240 个过期候选", sub, RED)

    nf = font(38, bold=True)
    center_text(d, w // 2, 890, "循环让 Agent 一直跑，代谢让工作区一直活", nf, ACCENT)
    cf = font(26, code=True)
    center_text(d, w // 2, 958, "examples/metabolism_benchmark.py", cf, MUTED)

    img.save(OUT / "experiment-30-zh.png")


def four_phases():
    w, h = 1536, 864
    img, d = new_canvas(w, h)
    d.ellipse((-200, -260, 480, 360), fill=(22, 46, 44))
    d.ellipse((1120, 620, 1760, 1260), fill=(20, 36, 56))

    tf = font(60, bold=True)
    center_text(d, w // 2, 92, "工作区消化系统：四个阶段", tf, TEXT)
    sf = font(30)
    center_text(d, w // 2, 152, "Agentic Metabolic Engineering · 智能体代谢工程", sf, MUTED)

    phases = [
        ("01", "检查", "audit", "wm audit", "只体检，不处理\n给文件贴营养标签"),
        ("02", "回收", "clean", "wm clean", "移入回收区\n绝不直接删除"),
        ("03", "验证", "verify", "wm verify", "哈希链日志\n防篡改可审计"),
        ("04", "回滚", "rollback", "wm rollback", "重新注入工作区\n废物变成原料"),
    ]

    margin, gap = 78, 58
    cw = (w - margin * 2 - gap * 3) // 4
    ch = 440
    y0 = 250
    for i, (num, cn, en, cmd, desc) in enumerate(phases):
        x0 = margin + i * (cw + gap)
        d.rounded_rectangle((x0, y0, x0 + cw, y0 + ch), radius=28, fill=CARD, outline=BORDER, width=2)
        cx = x0 + cw // 2
        center_text(d, cx, y0 + 56, num, font(30, bold=True), ACCENT)
        center_text(d, cx, y0 + 128, cn, font(52, bold=True), TEXT)
        center_text(d, cx, y0 + 182, en, font(28), MUTED)
        d.rounded_rectangle((x0 + 46, y0 + 218, x0 + cw - 46, y0 + 272), radius=27, fill=CARD_LIGHT)
        center_text(d, cx, y0 + 245, cmd, font(26, code=True), CYAN)
        yy = y0 + 320
        df = font(28)
        for line in desc.split("\n"):
            center_text(d, cx, yy, line, df, TEXT)
            yy += 46
        if i < 3:
            arrow(d, x0 + cw + 6, y0 + ch // 2, x0 + cw + gap - 6)

    img.save(OUT / "four-phases-zh.png")


def stack_l5():
    w, h = 1536, 864
    img, d = new_canvas(w, h)
    d.ellipse((1090, -280, 1760, 380), fill=(24, 52, 48))

    tf = font(60, bold=True)
    center_text(d, w // 2, 82, "Agentic 工程栈的第五层", tf, TEXT)
    sf = font(30)
    center_text(d, w // 2, 142, "L5 · Agentic Metabolic Engineering 智能体代谢工程", sf, MUTED)

    layers = [
        ("L1", "Prompt Engineering", "提示工程", "我们跟模型说什么？", False),
        ("L2", "Context Engineering", "上下文工程", "我们给模型读什么？", False),
        ("L3", "Harness Engineering", "约束工程", "怎么让 agent 可靠？", False),
        ("L4", "Loop Engineering", "循环工程", "怎么让 agent 自己跑？", False),
        ("L5", "Agentic Metabolic Engineering", "智能体代谢工程", "每轮循环后，副产物怎么办？", True),
    ]

    bw, bh, gap = 1240, 100, 20
    x0 = (w - bw) // 2
    y0 = 210
    for i, (num, en, cn, q, hot) in enumerate(layers):
        y = y0 + i * (bh + gap)
        fill = CARD_LIGHT if hot else CARD
        outline = ACCENT if hot else BORDER
        width = 3 if hot else 2
        d.rounded_rectangle((x0, y, x0 + bw, y + bh), radius=22, fill=fill, outline=outline, width=width)
        # layer number block
        d.rounded_rectangle((x0 + 12, y + 12, x0 + 96, y + bh - 12), radius=16, fill=CARD if hot else (19, 26, 38))
        center_text(d, x0 + 54, y + bh // 2, num, font(30, bold=True), ACCENT if hot else CYAN)
        # names
        center_text(d, x0 + 280, y + bh // 2 - 20, en, font(28, bold=True, code=(i == 4 and False)), TEXT)
        center_text(d, x0 + 280, y + bh // 2 + 22, cn, font(24), MUTED)
        # question
        center_text(d, x0 + bw - 260, y + bh // 2, q, font(28), ACCENT if hot else TEXT)

    img.save(OUT / "stack-l5-zh.png")


def four_phases_vertical():
    w, h = 1242, 1656
    img, d = new_canvas(w, h)
    d.ellipse((-220, -260, 460, 420), fill=(23, 50, 46))
    d.ellipse((920, 1320, 1540, 1940), fill=(20, 36, 56))

    center_text(d, w // 2, 100, "工作区消化系统：四个阶段", font(58, bold=True), TEXT)
    center_text(d, w // 2, 160, "Agentic Metabolic Engineering · 智能体代谢工程", font(28), MUTED)

    phases = [
        ("01", "检查", "audit", "wm audit", "只体检，不处理", "给文件贴营养标签"),
        ("02", "回收", "clean", "wm clean", "移入回收区", "绝不直接删除"),
        ("03", "验证", "verify", "wm verify", "哈希链日志", "防篡改可审计"),
        ("04", "回滚", "rollback", "wm rollback", "重新注入工作区", "废物变成原料"),
    ]

    x0, cw = 101, 1040
    ch, gap = 300, 60
    y0 = 230
    for i, (num, cn, en, cmd, d1, d2) in enumerate(phases):
        y = y0 + i * (ch + gap)
        d.rounded_rectangle((x0, y, x0 + cw, y + ch), radius=28, fill=CARD, outline=BORDER, width=2)
        center_text(d, x0 + 80, y + 55, num, font(32, bold=True), ACCENT)
        center_text(d, x0 + 80, y + 120, cn, font(50, bold=True), TEXT)
        center_text(d, x0 + 80, y + 180, en, font(26), MUTED)
        # command chip (right)
        chip_cx, chip_cy = x0 + cw - 190, y + 80
        center_rect(d, chip_cx, chip_cy, 270, 68, 34, CARD_LIGHT, outline=BORDER, width=2)
        center_text(d, chip_cx, chip_cy, cmd, font(25, code=True), CYAN)
        center_text(d, x0 + cw // 2, y + 236, d1, font(28), TEXT)
        center_text(d, x0 + cw // 2, y + 282, d2, font(28), TEXT)
        if i < 3:
            ax = w // 2
            ay1 = y + ch
            ay2 = y + ch + gap
            d.line((ax, ay1, ax, ay2 - 14), fill=ACCENT, width=6)
            d.polygon([(ax - 12, ay2 - 16), (ax + 12, ay2 - 16), (ax, ay2 + 8)], fill=ACCENT)

    img.save(OUT / "four-phases-zh-v.png")


def stack_l5_vertical():
    w, h = 1242, 1656
    img, d = new_canvas(w, h)
    d.ellipse((1080, -280, 1760, 380), fill=(24, 52, 48))

    center_text(d, w // 2, 100, "Agentic 工程栈的第五层", font(58, bold=True), TEXT)
    center_text(d, w // 2, 160, "L5 · Agentic Metabolic Engineering 智能体代谢工程", font(28), MUTED)

    layers = [
        ("L1", "Prompt Engineering", "提示工程", "我们跟模型说什么？", False),
        ("L2", "Context Engineering", "上下文工程", "我们给模型读什么？", False),
        ("L3", "Harness Engineering", "约束工程", "怎么让 agent 可靠？", False),
        ("L4", "Loop Engineering", "循环工程", "怎么让 agent 自己跑？", False),
        ("L5", "Agentic Metabolic Engineering", "智能体代谢工程", "每轮循环后，副产物怎么办？", True),
    ]

    x0, bw = 81, 1080
    bh, gap = 180, 48
    y0 = 230
    for i, (num, en, cn, q, hot) in enumerate(layers):
        y = y0 + i * (bh + gap)
        fill = CARD_LIGHT if hot else CARD
        outline = ACCENT if hot else BORDER
        d.rounded_rectangle((x0, y, x0 + bw, y + bh), radius=24, fill=fill, outline=outline, width=3 if hot else 2)
        # layer number chip
        d.rounded_rectangle((x0 + 16, y + 16, x0 + 150, y + bh - 16), radius=18, fill=CARD if hot else (19, 26, 38))
        center_text(d, x0 + 83, y + bh // 2, num, font(34, bold=True), ACCENT if hot else CYAN)
        # names
        center_text(d, x0 + 360, y + bh // 2 - 28, cn, font(42, bold=True), TEXT)
        center_text(d, x0 + 360, y + bh // 2 + 30, en, font(24), MUTED)
        # question
        center_text(d, x0 + bw - 250, y + bh // 2, q, font(26), ACCENT if hot else TEXT)

    center_text(d, w // 2, 1460, "循环让 Agent 一直跑，代谢让工作区一直活", font(40, bold=True), ACCENT)
    center_text(d, w // 2, 1528, "Agentic Metabolic Engineering · L5", font(28), MUTED)

    img.save(OUT / "stack-l5-zh-v.png")


def experiment_30_vertical():
    w, h = 1242, 1656
    img, d = new_canvas(w, h)
    d.ellipse((-220, -260, 460, 420), fill=(23, 50, 46))
    d.ellipse((920, 1320, 1540, 1940), fill=(22, 38, 58))

    badge = "30 轮对照实验 · 可复现"
    bf = font(34, bold=True)
    bw = int(d.textlength(badge, font=bf)) + 64
    center_rect(d, w // 2, 120, bw, 78, 39, CARD_LIGHT, outline=BORDER, width=2)
    center_text(d, w // 2, 120, badge, bf, ACCENT)
    center_text(d, w // 2, 210, "两个一模一样的工作区，各跑 30 轮 AI 循环", font(40, bold=True), TEXT)

    panel_w, panel_h = 1000, 460
    x0 = (w - panel_w) // 2
    y0 = 320
    gap = 70

    # governed panel
    d.rounded_rectangle((x0, y0, x0 + panel_w, y0 + panel_h), radius=30, fill=CARD, outline=ACCENT, width=3)
    cx = x0 + panel_w // 2
    center_text(d, cx, y0 + 82, "有代谢", font(44, bold=True), ACCENT)
    center_text(d, cx, y0 + 215, "2", font(190, bold=True), TEXT)
    center_text(d, cx, y0 + 335, "个文件", font(44, bold=True), MUTED)
    center_text(d, cx, y0 + 405, "始终干净，全部可回滚", font(30), MUTED)

    # ungoverned panel
    y1 = y0 + panel_h + gap
    d.rounded_rectangle((x0, y1, x0 + panel_w, y1 + panel_h), radius=30, fill=CARD, outline=RED, width=3)
    center_text(d, cx, y1 + 82, "无代谢", font(44, bold=True), RED)
    center_text(d, cx, y1 + 215, "242", font(190, bold=True), TEXT)
    center_text(d, cx, y1 + 335, "个文件", font(44, bold=True), MUTED)
    center_text(d, cx, y1 + 405, "240 个过期候选", font(30), RED)

    center_text(d, w // 2, 1410, "循环让 Agent 一直跑，代谢让工作区一直活", font(40, bold=True), ACCENT)
    center_text(d, w // 2, 1480, "examples/metabolism_benchmark.py", font(26, code=True), MUTED)
    center_text(d, w // 2, 1545, "GitHub 搜索 workspace-metabolism", font(32, bold=True), TEXT)

    img.save(OUT / "experiment-30-zh-v.png")


def _comparison_panels(d, w, panels, y0, panel_w, panel_h, gap, fnt_header, fnt_row, row_gap):
    x0 = (w - panel_w * 2 - gap) // 2
    for i, (title, rows, color) in enumerate(panels):
        x = x0 + i * (panel_w + gap)
        d.rounded_rectangle((x, y0, x + panel_w, y0 + panel_h), radius=30, fill=CARD, outline=color, width=3)
        cx = x + panel_w // 2
        center_text(d, cx, y0 + 66, title, fnt_header, color)
        yy = y0 + 150
        row_fnt = fnt_row
        for row in rows:
            d.ellipse((x + 62, yy - 9, x + 78, yy + 7), fill=color)
            d.text((x + 100, yy), row, font=row_fnt, fill=TEXT, anchor="lm")
            yy += row_gap


def scheduled_vs_metabolism():
    w, h = 1536, 864
    img, d = new_canvas(w, h)
    d.ellipse((-200, -260, 480, 360), fill=(22, 46, 44))
    d.ellipse((1120, 620, 1760, 1260), fill=(20, 36, 56))

    center_text(d, w // 2, 92, "定时清理 ≠ 代谢系统", font(60, bold=True), TEXT)
    center_text(
        d, w // 2, 152,
        "Scheduling answers WHEN · policy answers WHAT, HOW, and HOW TO UNDO",
        font(26), MUTED,
    )

    panels = [
        (
            "定时清理任务",
            ["规则在对话里，每次可能不一样", "删了不可逆，没有回收区", "没有审计账本", "只回答：到点删"],
            RED,
        ),
        (
            "代谢系统",
            ["策略进仓库，可评审可版本化", "回收区 + SHA-256，删错可回滚", "哈希链审计，篡改会被发现", "每台机器、每次运行行为一致"],
            ACCENT,
        ),
    ]
    _comparison_panels(d, w, panels, 230, 620, 470, 50, font(44, bold=True), font(30), 86)

    center_text(d, w // 2, 772, "调度器是闹钟，策略是消化系统", font(38, bold=True), ACCENT)
    center_text(d, w // 2, 830, "可以组合：cron · Windows 任务计划 · CI 定时跑 wm", font(26), MUTED)

    img.save(OUT / "scheduled-vs-metabolism-zh.png")


def scheduled_vs_metabolism_vertical():
    w, h = 1242, 1656
    img, d = new_canvas(w, h)
    d.ellipse((-220, -260, 460, 420), fill=(23, 50, 46))
    d.ellipse((920, 1320, 1540, 1940), fill=(20, 36, 56))

    center_text(d, w // 2, 100, "定时清理 ≠ 代谢系统", font(58, bold=True), TEXT)
    center_text(d, w // 2, 160, "调度器是闹钟，策略是消化系统", font(30), MUTED)

    panels = [
        (
            "定时清理任务",
            ["规则在对话里，每次可能不一样", "删了不可逆，没有回收区", "没有审计账本", "只回答：到点删"],
            RED,
        ),
        (
            "代谢系统",
            ["策略进仓库，可评审可版本化", "回收区 + SHA-256，删错可回滚", "哈希链审计，篡改会被发现", "每台机器、每次运行行为一致"],
            ACCENT,
        ),
    ]
    _comparison_panels(d, w, panels, 240, 1040, 560, 70, font(48, bold=True), font(34), 100)

    center_text(d, w // 2, 1480, "循环让 Agent 一直跑，代谢让工作区一直活", font(40, bold=True), ACCENT)
    center_text(d, w // 2, 1545, "可以组合：cron · 任务计划 · CI 定时跑 wm", font(28), MUTED)
    center_text(d, w // 2, 1610, "GitHub 搜索 workspace-metabolism", font(32, bold=True), TEXT)

    img.save(OUT / "scheduled-vs-metabolism-zh-v.png")


if __name__ == "__main__":
    cover(["循环让 Agent 一直跑，", "代谢让工作区一直活"], "cover-zh.png")
    cover(["AI 写代码后，", "工作区谁来收拾？"], "cover-alt-zh.png")
    four_phases()
    stack_l5()
    experiment_30()
    four_phases_vertical()
    stack_l5_vertical()
    experiment_30_vertical()
    scheduled_vs_metabolism()
    scheduled_vs_metabolism_vertical()
    print("saved to", OUT)
