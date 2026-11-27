#!/usr/bin/env python3
"""把「原照片 + 成图」拼成 4:3 版式：上 35% 照片，下 65% 成图。"""
import argparse, sys
from pathlib import Path
from PIL import Image

W, H = 1800, 2400   # 竖版：高宽比 4:3
TOP = int(H * 0.35)


def cover(im, bw, bh):
    r = max(bw / im.width, bh / im.height)
    im = im.resize((max(bw, int(im.width * r)), max(bh, int(im.height * r))), Image.LANCZOS)
    x = (im.width - bw) // 2
    y = (im.height - bh) // 2
    return im.crop((x, y, x + bw, y + bh))


def fit(im, bw, bh):
    r = min(bw / im.width, bh / im.height)
    return im.resize((max(1, int(im.width * r)), max(1, int(im.height * r))), Image.LANCZOS)


def trim(im, pad=8):
    bg = Image.new('RGB', im.size, im.getpixel((2, 2)))
    from PIL import ImageChops
    d = ImageChops.difference(im, bg).convert('L').point(lambda v: 255 if v > 10 else 0)
    b = d.getbbox()
    return im.crop(b) if b else im


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--photo', required=True)
    ap.add_argument('--plate', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--fill-photo', action='store_true',
                    help='照片铺满上带（会裁掉上下），默认不裁剪')
    a = ap.parse_args()
    paper = (250, 247, 242)
    canvas = Image.new('RGB', (W, H), paper)
    _ph = Image.open(a.photo).convert('RGB')
    ph = cover(_ph, W, TOP) if a.fill_photo else fit(_ph, W, TOP)
    canvas.paste(ph, ((W - ph.width) // 2, max(0, (TOP - ph.height) // 2)))
    pl = trim(Image.open(a.plate).convert('RGB'))
    pl = fit(pl, int(W * 0.98), int((H - TOP) * 0.98))
    canvas.paste(pl, ((W - pl.width) // 2, TOP + max(0, (H - TOP - pl.height) // 2)))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    canvas.save(a.out)
    print('saved:', a.out, canvas.size)


if __name__ == '__main__':
    sys.exit(main())
