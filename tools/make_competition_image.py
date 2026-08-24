"""Generate the competitive-gap image for workspace-metabolism (Pillow, no external assets).

Story: every existing tool is a slice (diagnose / dedupe / age-clean / official
state dirs / community session-cleaners); only workspace-metabolism closes the
loop. Visualized as a capability dot-matrix.

Outputs:
  docs/publish/images/competitive-gap-zh.png (1536x900, landscape, Chinese)
  docs/publish/images/competitive-gap-en.png (1536x900, landscape, English)

Run:  .venv\\Scripts\\python.exe tools/make_competition_image.py
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent.parent / "docs" / "publish" / "images"
OUT.mkdir(exist_ok=True)

BG = (14, 20, 32)
CARD = (27, 36, 52)
CARD_LIGHT = (35, 47, 66)
BORDER = (58, 74, 98)
TEXT = (241, 245, 249)
MUTED = (148, 163, 184)
ACCENT = (61, 220, 151)
CYAN = (125, 211, 252)
WARN = (251, 191, 36)
RED = (248, 113, 113)

# capability states: 2 = full, 1 = partial, 0 = none
MATRIX = [
    ("policy-grading", "策略文件分级", "policy file G1–G4", [0, 0, 0, 0, 0, 2]),
    ("recycle", "可回滚清理", "recycle + rollback", [0, 1, 0, 0, 1, 2]),
    ("sha256", "逐文件哈希校验", "per-file SHA-256", [0, 2, 0, 0, 0, 2]),
    ("audit-chain", "哈希链防篡改审计", "hash-chain journal", [0, 0, 0, 0, 0, 2]),
    ("health-gate", "健康分 + CI 门禁", "health score + CI gate", [0, 0, 0, 0, 0, 2]),
    ("mcp", "MCP / agent 自服务", "MCP self-service", [0, 0, 0, 1, 1, 2]),
]

CATEGORIES = [
    ("磁盘分析", "ncdu · duf · gdu"),
    ("内容去重", "rmlint · czkawka"),
    ("年龄清理", "tmpreaper · logrotate"),
    ("官方内置", "Claude Code · Codex"),
    ("社区清理", "claude-code-cleaner 等"),
    ("workspace-metabolism", "策略生命周期闭环"),
]


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


def center_text(d, cx, cy, text, fnt, fill):
    d.text((cx, cy), text, font=fnt, fill=fill, anchor="mm")


def draw(title, subtitle, caps_labels, cat_labels, filename):
    w, h = 1536, 900
    img = Image.new("RGB", (w, h), BG)
    d = ImageDraw.Draw(img)
    d.ellipse((-220, -280, 460, 380), fill=(22, 46, 44))
    d.ellipse((1120, 620, 1760, 1260), fill=(20, 36, 56))

    center_text(d, w // 2, 84, title, font(54, bold=True), TEXT)
    center_text(d, w // 2, 142, subtitle, font(26), MUTED)

    # table geometry
    label_w = 330
    col_w, col_gap = 172, 12
    x0 = 70
    x_cols = [x0 + label_w + 24 + i * (col_w + col_gap) for i in range(6)]
    y_head = 216
    row_h, row_gap = 70, 12
    y_rows = [316 + i * (row_h + row_gap) for i in range(6)]
    table_bottom = y_rows[-1] + row_h

    # highlight the metabolism column (full column width, centered)
    lx = x_cols[5]
    d.rounded_rectangle(
        (lx - col_w // 2 - 14, y_head - 40, lx + col_w // 2 + 14, table_bottom + 14),
        radius=20, fill=(26, 44, 40), outline=ACCENT, width=3,
    )

    # column headers
    for i, (name, sub) in enumerate(cat_labels):
        cx = x_cols[i]
        is_ours = i == 5
        center_text(d, cx, y_head - 12, name, font(26, bold=True), ACCENT if is_ours else TEXT)
        center_text(d, cx, y_head + 24, sub, font(18), ACCENT if is_ours else MUTED)

    # row labels
    for j, (cn, en, states) in enumerate(caps_labels):
        cy = y_rows[j] + row_h // 2
        d.text((x0, cy), cn, font=font(26, bold=True), fill=TEXT, anchor="lm")
        d.text((x0 + 4, cy + 22), en, font=font(17), fill=MUTED, anchor="lm")
        d.line((x0 + 8, y_rows[j] - 6, x0 + 8, y_rows[j] + row_h + 6), fill=BORDER, width=2)

    # dots
    dot_r = 20
    for j, (cn, en, states) in enumerate(caps_labels):
        cy = y_rows[j] + row_h // 2
        for i, st in enumerate(states):
            cx = x_cols[i]
            if st == 2:
                d.ellipse((cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r), fill=ACCENT)
            elif st == 1:
                d.ellipse((cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r), fill=WARN)
            else:
                d.ellipse((cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r),
                          fill=(20, 28, 42), outline=BORDER, width=3)

    # legend + bottom line
    lx0 = x0 + 8
    ly = table_bottom + 44
    for k, (color, label) in enumerate([(ACCENT, "完整具备"), (WARN, "部分具备"), (BORDER, "不具备")]):
        cx = lx0 + k * 240 + 16
        d.ellipse((cx - 12, ly - 12, cx + 12, ly + 12), fill=color if k < 2 else (20, 28, 42),
                  outline=color if k == 2 else None, width=3)
        center_text(d, cx + 44, ly, label, font(22), MUTED)

    center_text(d, w // 2, table_bottom + 96, "现有工具都是切片，只有我们做完整闭环", font(34, bold=True), ACCENT)

    img.save(OUT / filename)


ZH_CAPS = [
    ("策略文件分级", "policy file G1–G4"),
    ("可回滚清理", "recycle + rollback"),
    ("逐文件哈希校验", "per-file SHA-256"),
    ("哈希链防篡改审计", "hash-chain journal"),
    ("健康分 + CI 门禁", "health score + CI gate"),
    ("MCP / agent 自服务", "MCP self-service"),
]
EN_CAPS = [
    ("Policy grading", "G1–G4 in a policy file"),
    ("Recyclable cleanup", "recycle area + rollback"),
    ("Per-file SHA-256", "integrity check"),
    ("Hash-chain audit", "tamper-evident journal"),
    ("Health score + CI gate", "0-100, badge, gate"),
    ("MCP self-service", "agents run their own wm"),
]
EN_CATS = [
    ("Disk analyzers", "ncdu · duf · gdu"),
    ("Dedup tools", "rmlint · czkawka"),
    ("Age-based cleaners", "tmpreaper · logrotate"),
    ("Official built-ins", "Claude Code · Codex"),
    ("Community cleaners", "claude-code-cleaner etc."),
    ("workspace-metabolism", "full lifecycle loop"),
]

if __name__ == "__main__":
    zh_states = [m[3] for m in MATRIX]
    draw(
        "磁盘工具很多，闭环只有一个",
        "六类现有工具 vs workspace-metabolism · 能力点阵",
        [(cn, en, st) for (cn, en), st in zip(ZH_CAPS, zh_states)],
        CATEGORIES,
        "competitive-gap-zh.png",
    )
    draw(
        "Many cleaners. One lifecycle loop.",
        "Six existing tool categories vs workspace-metabolism · capability matrix",
        [(cn, en, st) for (cn, en), st in zip(EN_CAPS, zh_states)],
        EN_CATS,
        "competitive-gap-en.png",
    )
    print("saved to", OUT)
