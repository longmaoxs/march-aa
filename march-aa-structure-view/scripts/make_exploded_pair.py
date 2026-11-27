#!/usr/bin/env python3
"""输出「照片 + 爆炸轴测」4:3 双联图：上 32% 原照片，下 68% 分层爆炸的主体 + 右侧 01/02/03 说明。"""
import argparse, json, sys
from pathlib import Path
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parent))
import structure_plate as SP

W, H = 1800, 2400          # 竖版：高宽比 4:3
TOP = int(H * 0.35)
NOTE_W = int(W * 0.34)


def zc(pts):
    return sum(p[2] for p in pts) / float(len(pts))


def shift_face(f, dz):
    quad, kind, meta = f[0], f[1], (f[2] if len(f) > 2 else {})
    return (tuple((p[0], p[1], p[2] + dz) for p in quad), kind, meta)


def shift_line(ln, dz):
    seg, col, w, key = SP._line_parts(ln)
    return (tuple((p[0], p[1], p[2] + dz) for p in seg), col, w, key)


def fit(im, bw, bh):
    r = min(bw / im.width, bh / im.height)
    return im.resize((max(1, int(im.width * r)), max(1, int(im.height * r))), Image.LANCZOS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--json', required=True)
    ap.add_argument('--photo', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--layers', type=int, default=4)
    ap.add_argument('--gap', type=float, default=0.0, help='层间抬升（模型单位）；0=自动')
    a = ap.parse_args()
    job = json.load(open(a.json, encoding='utf-8'))
    model = SP.BUILDERS[job['family']](job.get('params', {}))

    faces = [f for f in model['faces']]
    lines = list(model['lines'])
    zs = [zc(f[0]) for f in faces]
    zmin, zmax = min(zs), max(zs)
    n = max(2, a.layers)
    step = (zmax - zmin) / n
    gap = a.gap or step * 1.35

    bands = [[] for _ in range(n)]
    for f in faces:
        i = min(n - 1, int((zc(f[0]) - zmin) / step))
        bands[i].append(f)
    lbands = [[] for _ in range(n)]
    for ln in lines:
        seg, col, w, key = SP._line_parts(ln)
        i = min(n - 1, int((zc(seg) - zmin) / step))
        lbands[i].append(ln)

    ex_f, ex_l = [], []
    for i in range(n):
        dz = (i * gap) if True else 0
        ex_f += [shift_face(f, dz) for f in bands[i]]
        ex_l += [shift_line(ln, dz) for ln in lbands[i]]

    cv = SP.Canvas(W, H)
    ts = SP._ts(W, H)
    F = lambda s: max(11, int(round(s * ts)))
    # 上带照片
    _ph = Image.open(a.photo).convert('RGB')
    _r = max(W / _ph.width, TOP / _ph.height)
    _pc = _ph.resize((max(W, int(_ph.width * _r)), max(TOP, int(_ph.height * _r))), Image.LANCZOS)
    _x = (_pc.width - W) // 2
    _y = int((_pc.height - TOP) * 0.58)
    _band = _pc.crop((max(0, _x), max(0, _y), max(0, _x) + W, max(0, _y) + TOP)).convert('RGB')
    _S = cv.img.width / float(cv.w)
    cv.img.paste(_band.resize((int(W * _S), int(TOP * _S)), Image.LANCZOS), (0, 0))
    # 下带：爆炸主体
    model2 = dict(model, faces=ex_f, lines=ex_l, callouts=[], chain=[])
    mx, my = int(70 * ts), int(40 * ts)
    x0, x1 = mx, W - NOTE_W - int(30 * ts)
    y0, y1 = TOP + my, H - my
    umin, vmin, umax, vmax = SP._uv_bbox(model2)
    bw, bh = max(1e-6, umax - umin), max(1e-6, vmax - vmin)
    k = min((x1 - x0) / bw, (y1 - y0) / bh)
    ox = x0 - k * umin + ((x1 - x0) - k * bw) * 0.5
    oy = y0 - k * vmin + ((y1 - y0) - k * bh) * 0.5
    ax = SP.Axo(k=k, zk=float(job.get('z_ratio', 0.95)), ox=ox, oy=oy)
    SP.draw_model(cv, model2, ax)

    # 右侧说明
    f_no = SP.font('num', F(34))
    f_hd = SP.font('hei', F(38))
    f_note = SP.font('hei', F(25))
    nx = W - NOTE_W + int(4 * ts)
    notes = job.get('explodeNotes') or [
        ('01', '屋顶 · 屋面', '庑殿/歇山/攒尖的坡面与瓦垄，挂在梁架与斗拱之上。'),
        ('02', '斗拱 · 额枋', '把屋面的荷载层层收拢，再交给柱子。'),
        ('03', '柱网 · 墙体', '柱承重、墙只围护，是木构与砖石的分工。'),
        ('04', '台基 · 踏道', '把整栋建筑抬离地面，收住全部竖向荷载。'),
    ]
    yy = TOP + int(46 * ts)
    for i, (no, hd, txt) in enumerate(notes[:n][::-1]):
        cv.text(nx, yy, no, f_no, SP.ACCENT, anchor='lm')
        cv.text(nx + int(46 * ts), yy, hd, f_hd, SP.INK, anchor='lm')
        yy += int(44 * ts)
        for line in SP._wrap(cv, txt, f_note, NOTE_W - int(30 * ts)) or [txt]:
            cv.text(nx + int(46 * ts), yy, line, f_note, SP.INK3, anchor='lm')
            yy += int(30 * ts)
        yy += int(26 * ts)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    cv.img.resize((W, H), Image.LANCZOS).save(a.out)
    print('saved:', a.out, (W, H))


if __name__ == '__main__':
    main()
