"""Render the animated terminal demo GIF (docs/demo-terminal.gif).

Dev-time tool only; not part of the runtime package. Requires Pillow:
    python -m pip install pillow
    python tools/make_demo_gif.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT = REPO_ROOT / "docs" / "demo-terminal.gif"

W, H = 680, 440
BG = (13, 17, 23)
BAR = (22, 27, 34)
FG = (201, 209, 217)
DIM = (139, 148, 158)
PROMPT = (63, 185, 80)
ACCENT = (88, 166, 255)
WARN = (210, 153, 34)
CURSOR = (240, 246, 252)

LINE_H = 26
PAD_X = 22
PAD_TOP = 56
VISIBLE = (H - PAD_TOP) // LINE_H

FONT_PATH = "C:/Windows/Fonts/consola.ttf"

SCRIPT = [
    [("prompt", "$ "), ("fg", "wm init")],
    [("ok", "policy created: metabolism.json"), ("dim", "   (like `git init`, but for file lifecycle)")],
    [("dim", "next steps:")],
    [("dim", "  wm audit      - first checkup (read-only)")],
    [("dim", "  wm health     - workspace health score (0-100)")],
    [("dim", "  wm explain <path> - why a path is graded the way it is")],
    [],
    [("prompt", "$ "), ("fg", "wm audit")],
    [("fg", "audit done: 0 candidate(s), 0 unregistered")],
    [("dim", "report: ~/.cache/workspace-metabolism/reports/2026-08-15.md")],
    [("ok", "journal: 1 entries, chain OK")],
    [],
    [("prompt", "$ "), ("fg", "wm health")],
    [("fg", "health: 95/100 (A)")],
    [("dim", "  auditability: 25/25   governance: 25/25")],
    [("dim", "  rot burden: 35/35   recycle readiness: 10/15")],
    [],
    [("prompt", "$ "), ("fg", "wm explain logs")],
    [("fg", "path: logs")],
    [("fg", "policy entry: logs  (G4 / auto)")],
    [("fg", "retention: 30 days")],
    [("fg", "intent: high-churn byproduct")],
    [("fg", "status: not a candidate right now")],
    [],
    [("prompt", "$ "), ("fg", "wm clean --grades G4")],
    [("warn", "clean plan (dry-run): 0 item(s), 0.0 MB; blocked 0")],
    [("warn", "--yes not given; dry-run only, nothing was moved.")],
    [],
    [("prompt", "$ "), ("fg", "wm rollback clean-20260815-140735-123456")],
    [("ok", "rollback completed: 8/8")],
    [("ok", "  [restored] loops/run00_draft.py")],
    [("dim", "SHA-256 verified · byte-for-byte")],
]

COLORS = {
    "prompt": PROMPT,
    "fg": FG,
    "dim": DIM,
    "accent": ACCENT,
    "ok": (63, 185, 80),
    "warn": WARN,
}


def font(size: int = 18) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except OSError:
        return ImageFont.load_default()


def build_frames() -> list[Image.Image]:
    fnt = font(18)
    fnt_bar = font(13)
    frames: list[Image.Image] = []

    def render(rows: list[list[tuple[str, str]]], cursor_on: bool) -> Image.Image:
        img = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, W, 34], fill=BAR)
        for x, color in ((18, (255, 95, 87)), (40, (254, 188, 46)), (62, (40, 200, 64))):
            d.ellipse([x, 12, x + 12, 24], fill=color)
        d.text((88, 9), "workspace-metabolism — 60-second demo", font=fnt_bar, fill=DIM)
        visible = rows[-VISIBLE:] if rows else []
        bottom = H - 18
        y = bottom - LINE_H * (len(visible) - 1) if visible else bottom
        for row in visible:
            x = PAD_X
            for color, text in row:
                d.text((x, y), text, font=fnt, fill=COLORS[color])
                x += fnt.getlength(text)
            y += LINE_H
        if cursor_on and visible:
            last_text = "".join(text for _, text in visible[-1])
            x = PAD_X + fnt.getlength(last_text)
            d.rectangle([x, bottom + 4, x + 10, bottom + LINE_H - 4], fill=CURSOR)
        return img

    displayed: list[list[tuple[str, str]]] = []
    frame_idx = 0

    def push(img: Image.Image) -> None:
        nonlocal frame_idx
        frames.append(img)
        frame_idx += 1

    for line in SCRIPT:
        if not line:
            displayed.append([])
            for _ in range(3):
                push(render(displayed, (frame_idx // 3) % 2 == 0))
            continue
        if line[0][1].startswith("$ "):
            full = "".join(text for _, text in line)
            for i in range(3, len(full) + 1, 3):
                partial: list[tuple[str, str]] = []
                remaining = i
                for color, text in line:
                    take = min(len(text), remaining)
                    if take:
                        partial.append((color, text[:take]))
                    remaining -= take
                    if remaining <= 0:
                        break
                if displayed and displayed[-1] and displayed[-1][0][1].startswith("$ "):
                    displayed[-1] = partial
                else:
                    displayed.append(partial)
                push(render(displayed, (frame_idx // 3) % 2 == 0))
            if len(full) % 3 != 0:
                # finish the remaining characters
                partial = []
                remaining = len(full)
                for color, text in line:
                    take = min(len(text), remaining)
                    if take:
                        partial.append((color, text[:take]))
                    remaining -= take
                    if remaining <= 0:
                        break
                displayed[-1] = partial
                push(render(displayed, (frame_idx // 3) % 2 == 0))
            for _ in range(4):
                push(render(displayed, (frame_idx // 3) % 2 == 0))
        else:
            displayed.append(line)
            push(render(displayed, (frame_idx // 3) % 2 == 0))
            for _ in range(4):
                push(render(displayed, (frame_idx // 3) % 2 == 0))
    for _ in range(6):
        push(render(displayed, (frame_idx // 3) % 2 == 0))
    return frames


def main() -> int:
    frames = build_frames()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        OUT,
        save_all=True,
        append_images=frames[1:],
        duration=70,
        loop=0,
        optimize=True,
    )
    print(f"wrote {OUT} ({len(frames)} frames, {OUT.stat().st_size / 1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
