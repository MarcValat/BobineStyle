"""Draw icon.png (1024 px), the source `npx tauri icon` derives the others from.

Same canvas as SyncSubtitles' icon (full bleed, rx 224, vertical gradient)
in violet; "Aa" in the house style itself: Trebuchet MS bold, white with a
dark outline and shadow, over a subtitle bar. Run with the engine's Python
(it has Pillow): uv run --project ../../../engine python make_icon.py
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

SIZE = 1024
TOP, BOTTOM = (141, 91, 255), (78, 47, 184)
FONT = Path("C:/Windows/Fonts/trebucbd.ttf")

gradient = Image.new("RGB", (1, SIZE))
for y in range(SIZE):
    t = y / (SIZE - 1)
    gradient.putpixel((0, y), tuple(round(a + (b - a) * t) for a, b in zip(TOP, BOTTOM)))
background = gradient.resize((SIZE, SIZE))
mask = Image.new("L", (SIZE, SIZE), 0)
ImageDraw.Draw(mask).rounded_rectangle((0, 0, SIZE - 1, SIZE - 1), radius=224, fill=255)
icon = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
icon.paste(background, (0, 0), mask)

font = ImageFont.truetype(str(FONT), 440)
text = "Aa"
box = font.getbbox(text)
x = (SIZE - (box[2] - box[0])) / 2 - box[0]
# Letters (y 241-601 with the stroke) and bar (691-783) centred on 512.
y = 261 - box[1]

shadow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
ImageDraw.Draw(shadow).text((x + 22, y + 22), text, font=font, fill=(20, 10, 60, 150), stroke_width=22, stroke_fill=(20, 10, 60, 150))
icon.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(6)))
draw = ImageDraw.Draw(icon)
draw.text((x, y), text, font=font, fill=(255, 255, 255), stroke_width=22, stroke_fill=(24, 16, 64))

draw.rounded_rectangle((190, 691, 834, 783), radius=46, fill=(255, 210, 91))
icon.save(Path(__file__).with_name("icon.png"))
