"""生成应用图标：深青圆角方块 + 白色音符，输出多尺寸 .ico。

用法：.venv\\Scripts\\python.exe packaging\\make_icon.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).with_name("shiyin.ico")
SIZE = 256
ACCENT = (15, 157, 144, 255)
LIGHT = (110, 231, 216, 255)
WHITE = (255, 255, 255, 255)


def draw(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = size / 256
    d.rounded_rectangle([6 * s, 6 * s, 250 * s, 250 * s], radius=56 * s, fill=ACCENT)
    # 音符：一个符头 + 竖杆 + 旗
    d.ellipse([74 * s, 158 * s, 132 * s, 208 * s], fill=WHITE)
    d.rounded_rectangle([118 * s, 76 * s, 134 * s, 186 * s], radius=7 * s, fill=WHITE)
    d.polygon([(134 * s, 78 * s), (188 * s, 62 * s), (188 * s, 96 * s), (134 * s, 112 * s)], fill=LIGHT)
    return img


def main() -> None:
    frames = [draw(size) for size in (16, 24, 32, 48, 64, 128, 256)]
    frames[-1].save(OUT, format="ICO", sizes=[(f.width, f.height) for f in frames])
    print("写入", OUT, OUT.stat().st_size, "B")


if __name__ == "__main__":
    main()
