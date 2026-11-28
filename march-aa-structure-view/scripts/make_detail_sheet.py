#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""单个构件的详图页：一件一张，轴测 + 正视 + 分件编号说明。

用法:
  python3 scripts/make_detail_sheet.py --part dougong --out out/detail_dougong.png
  python3 scripts/make_detail_sheet.py --part chiwen  --out out/detail_chiwen.png

与 make_component_sheet.py 的区别：那个是「一页塞六个缩略」，这里是「一件占一页、
留出分件编号与做法说明」，用于讲清一件东西是怎么搭起来的。
"""
import argparse
import math
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import structure_plate as SP  # noqa: E402

W, H = 2400, 3200
PAPER, INK, INK3, INK4, ACCENT = SP.PAPER, SP.INK, SP.INK3, SP.INK4, SP.ACCENT


# ── 构件几何（局部坐标，单位 m，原点在构件底面中心）──────────────────
def _group(name, build):
    """在指定构件名下产面/线：SP.part 决定随后 _F 的 part 归属。"""
    prev = SP._PART[0]
    SP.part(name)
    faces, lines = build()
    SP._PART[0] = prev
    return faces, lines


def _b(x0, y0, z0, x1, y1, z1, kind='body'):
    return SP.box(x0, y0, z0, x1, y1, z1, kind)


def _ln(p, q, col=None, w=1.0, key=True):
    return ((p, q), col or INK, w, key)


def wrap(cv, text, font, maxw):
    """自由折行（不限行数），中文逐字量宽。maxw 用画布单位。"""
    lines, cur = [], ''
    for ch in text:
        if cv.dr.textlength(cur + ch, font=font) / SP.S <= maxw:
            cur += ch
        else:
            lines.append(cur)
            cur = ch
    if cur:
        lines.append(cur)
    return lines


def _prism_yz(quad_yz, x0, x1, kind='body'):
    """在 y-z 平面上给一个四边形轮廓，沿 x 挤出（用于下昂这类斜向长木）。"""
    out = []
    out.append(SP._F(tuple((x0, y, z) for y, z in quad_yz), kind))
    out.append(SP._F(tuple((x1, y, z) for y, z in reversed(quad_yz)), kind))
    n = len(quad_yz)
    for i in range(n):
        a, b = quad_yz[i], quad_yz[(i + 1) % n]
        out.append(SP._F(((x0, a[0], a[1]), (x1, a[0], a[1]),
                          (x1, b[0], b[1]), (x0, b[0], b[1])), kind))
    return out


def _swap_xy(model):
    """x/y 互换 → 用正视投影画出来就是「侧立面」。"""
    def sp(p):
        return (p[1], p[0], p[2])
    faces = []
    for f in model['faces']:
        quad, kind, meta = f[0], f[1], (f[2] if len(f) > 2 else {})
        faces.append((tuple(sp(q) for q in quad), kind, meta))
    lines = []
    for e in model['lines']:
        seg, col, w, key = SP._line_parts(e)
        lines.append((tuple(sp(q) for q in seg), col, w, key))
    return dict(faces=faces, lines=lines, callouts=[], chain=[])


def _shift(faces, dz):
    out = []
    for f in faces:
        quad, kind, meta = f[0], f[1], (f[2] if len(f) > 2 else {})
        out.append((tuple((p[0], p[1], p[2] + dz) for p in quad), kind, meta))
    return out


def _shift_lines(lines, dz):
    out = []
    for e in lines:
        seg, col, w, key = SP._line_parts(e)
        out.append((tuple((p[0], p[1], p[2] + dz) for p in seg), col, w, key))
    return out


def dougong(scale=1.0, explode=None):
    """金代柱头铺作。explode=None → 装配态；给 dict{part: 层序} → 按层序竖向拉开。

    层级：栌斗 → 泥道栱/华栱 → 下昂/斜拱 → 令栱 → 散斗 → 耍头。
    尺寸按辽金官式大致的层级比例（m），示意外形与分件关系，非测绘。
    """
    s = scale
    groups = []          # [(part, dz_index, faces, lines)]
    B = lambda *a: _b(*[v * s for v in a])

    def put(part, idx, fn):
        prev = SP._PART[0]
        SP.part(part)
        faces, lines = fn()
        SP._PART[0] = prev
        groups.append((part, idx, faces, lines))

    put('栌斗', 0, lambda: (B(-0.20, -0.20, 0.00, 0.20, 0.20, 0.12)
                           + B(-0.26, -0.26, 0.12, 0.26, 0.26, 0.26), []))
    put('泥道栱', 1, lambda: (B(-0.54, -0.085, 0.26, 0.54, 0.085, 0.40), []))
    put('散斗', 2, lambda: (B(-0.58, -0.10, 0.40, -0.38, 0.10, 0.50)
                           + B(0.38, -0.10, 0.40, 0.58, 0.10, 0.50), []))
    put('华栱', 3, lambda: (B(-0.085, -0.50, 0.26, 0.085, 0.46, 0.40), []))

    def ang():
        out = []
        for (y0, y1, zt, zb) in ((0.24, 0.94, 0.54, 0.34), (0.24, 1.06, 0.66, 0.46)):
            q = [(y0, zt), (y1, zb + 0.17), (y1, zb + 0.03), (y0, zt - 0.14)]
            q = [(y * s, z * s) for y, z in q]
            out += _prism_yz(q, -0.085 * s, 0.085 * s)
        return out, []
    put('下昂', 4, ang)

    def xie():
        out = []
        for sgn in (-1.0, 1.0):
            a = math.radians(30.0)
            ux, uy = math.cos(a) * sgn, math.sin(a)
            nx, ny = -uy, ux
            t0, t1, hw = -0.05 * s, 0.76 * s, 0.075 * s
            base = [(ux * t0 + nx * hw, uy * t0 + ny * hw),
                    (ux * t0 - nx * hw, uy * t0 - ny * hw),
                    (ux * t1 - nx * hw, uy * t1 - ny * hw),
                    (ux * t1 + nx * hw, uy * t1 + ny * hw)]
            out += SP.extrude([(x * s, y * s) for x, y in base], 0.44 * s, 0.56 * s)
        return out, []
    put('斜拱', 5, xie)

    put('令栱', 6, lambda: (B(-0.54, 0.66, 0.56, 0.54, 0.82, 0.68), []))
    put('散斗', 7, lambda: (B(-0.58, 0.68, 0.68, -0.42, 0.80, 0.78)
                           + B(-0.08, 0.68, 0.68, 0.08, 0.80, 0.78)
                           + B(0.42, 0.68, 0.68, 0.58, 0.80, 0.78), []))
    put('耍头', 8, lambda: (B(-0.10, 0.82, 0.78, 0.10, 1.14, 0.90), []))

    faces, lines, moved = [], [], []
    for part, idx, ff, ll in groups:
        dz = 0.0 if explode is None else idx * 0.42 * s
        sf = _shift(ff, dz)
        faces += sf
        lines += _shift_lines(ll, dz)
        moved.append((part, idx, sf, []))
    return dict(faces=faces, lines=lines, callouts=[], chain=[], _groups=moved)


def chiwen(scale=1.0, explode=None):
    """宋式鸱吻：兽头吞脊、尾上卷。侧视一条 S 形轮廓，沿 x 挤出成「片」。"""
    s = scale
    f, L = [], []
    prof = [(0.00, 0.00), (0.30, 0.00), (0.40, 0.12), (0.22, 0.10), (0.24, 0.02),
            (0.36, 0.24), (0.44, 0.46), (0.40, 0.70), (0.46, 0.92), (0.38, 1.06),
            (0.22, 1.10), (0.10, 0.98), (0.14, 0.84), (0.02, 0.92), (-0.06, 0.78),
            (-0.14, 0.56), (-0.10, 0.32), (-0.14, 0.10)]
    th, zh = 0.26 * s, 1.42 * s
    pts = [(y * s, z * zh) for y, z in prof]

    def body():
        out, ls = [], []
        out.append(SP._F(tuple((-th / 2, py, pz) for py, pz in pts), 'body'))
        out.append(SP._F(tuple((th / 2, py, pz) for py, pz in reversed(pts)), 'body'))
        for i in range(len(pts)):
            a2, b2 = pts[i], pts[(i + 1) % len(pts)]
            out.append(SP._F(((-th / 2, a2[0], a2[1]), (th / 2, a2[0], a2[1]),
                              (th / 2, b2[0], b2[1]), (-th / 2, b2[0], b2[1])), 'body'))
            ls.append(_ln((-th / 2, a2[0], a2[1]), (th / 2, a2[0], a2[1]), INK, 0.9, True))
        return out, ls
    ff, ll = _group('吻身', body)
    f += ff
    L += ll

    ff, ll = _group('背兽', lambda: (
        _b(-0.09 * s, 0.30 * s, 1.02 * zh, 0.09 * s, 0.46 * s, 1.16 * zh), []))
    f += ff
    L += ll

    ff, ll = _group('脊座', lambda: (
        _b(-0.17 * s, -0.26 * s, -0.20 * s, 0.17 * s, 0.10 * s, 0.02 * s, 'mass'), []))
    f += ff
    L += ll
    # 分层爆炸：吻身 0、背兽 1、脊座 -1
    dz_body = 0.20 * s if explode is not None else 0.0
    out = []
    for q, kind, meta in f:
        part = meta.get('part')
        dz = dz_body if part == '吻身' else (dz_body + 0.42 * s if part == '背兽' else 0.0)
        out.append((tuple((p[0], p[1], p[2] + dz) for p in q), kind, meta))
    return dict(faces=out, lines=L, callouts=[], chain=[], _groups=[])


def _mapper(x0, y0, w, h, xr, zr):
    k = min(w / max(1e-6, xr[1] - xr[0]), h / max(1e-6, zr[1] - zr[0]))
    ox = x0 + (w - (xr[1] - xr[0]) * k) / 2.0
    oy = y0 + h - ((h - (zr[1] - zr[0]) * k) / 2.0)

    def M(x, z):
        return (ox + (x - xr[0]) * k, oy - (z - zr[0]) * k)
    return M, k


def side_dougong(cv, x0, y0, w, h, ts, F):
    M, k = _mapper(x0, y0 - int(30 * ts), w, h, (-0.62, 1.30), (-0.10, 1.08))

    def poly(pts, fill=WOOD, lw=1.3):
        cv.poly([M(*p) for p in pts], fill, INK, lw)

    # 柱头（一小截柱子，说明它是坐在柱头上的）
    poly([(-0.20, -0.10), (0.20, -0.10), (0.20, 0.00), (-0.20, 0.00)], WOOD2, 1.0)
    # 栌斗
    poly([(-0.20, 0.00), (0.20, 0.00), (0.26, 0.12), (-0.26, 0.12)], WOOD)
    poly([(-0.26, 0.12), (0.26, 0.12), (0.26, 0.26), (-0.26, 0.26)], WOOD)
    # 华栱（前后贯通，出跳）
    poly([(-0.50, 0.26), (0.46, 0.26), (0.46, 0.40), (-0.50, 0.40)], WOOD)
    # 两下昂（斜面向下）
    poly([(0.24, 0.52), (0.94, 0.41), (0.94, 0.34), (0.24, 0.37)], WOOD)
    poly([(0.24, 0.62), (1.06, 0.51), (1.06, 0.44), (0.24, 0.47)], WOOD)
    # 令栱 + 散斗 + 耍头
    poly([(0.66, 0.56), (0.82, 0.56), (0.82, 0.68), (0.66, 0.68)], WOOD)
    poly([(0.68, 0.68), (0.80, 0.68), (0.80, 0.78), (0.68, 0.78)], WOOD)
    poly([(0.82, 0.78), (1.14, 0.78), (1.14, 0.90), (0.82, 0.90)], WOOD)

    # 出跳标注
    yb = M(0, -0.02)[1] + int(46 * ts)
    cv.line([M(0, 0.0)[0:1] + (yb,), M(1.14, 0.0)[0:1] + (yb,)], INK3, 1.0)
    for xx in (0.0, 1.14):
        cv.line([(M(xx, 0.0)[0], yb - int(8 * ts)), (M(xx, 0.0)[0], yb + int(8 * ts))], INK3, 1.0)
    cv.text((M(0, 0)[0] + M(1.14, 0)[0]) / 2, yb - int(24 * ts), '出跳 1.14 m',
            SP.font('hei', F(26)), INK3, anchor='mm')


def side_chiwen(cv, x0, y0, w, h, ts, F):
    M, k = _mapper(x0, y0 - int(30 * ts), w, h, (-0.55, 0.62), (-0.34, 1.62))
    prof = [(0.00, 0.00), (0.30, 0.00), (0.40, 0.12), (0.22, 0.10), (0.24, 0.02),
            (0.36, 0.24), (0.44, 0.46), (0.40, 0.70), (0.46, 0.92), (0.38, 1.06),
            (0.22, 1.10), (0.10, 0.98), (0.14, 0.84), (0.02, 0.92), (-0.06, 0.78),
            (-0.14, 0.56), (-0.10, 0.32), (-0.14, 0.10)]
    pts = [(y, z * 1.42) for y, z in prof]
    cv.poly([M(*p) for p in pts], WOOD, INK, 1.4)
    # 正脊（说明「吞脊」：脊从吞口里穿过去）
    cv.poly([M(-0.52, -0.22), M(0.30, -0.22), M(0.30, 0.02), M(-0.52, 0.02)], WOOD2, INK, 1.2)
    cv.text(M(-0.10, -0.10)[0], M(-0.10, -0.10)[1] + int(40 * ts), '正脊',
            SP.font('hei', F(26)), INK3, anchor='mm')
    # 背兽
    cv.poly([M(0.30, 1.45), M(0.46, 1.45), M(0.46, 1.62), M(0.30, 1.62)], WOOD, INK, 1.2)


PARTS = {
    'dougong': dict(
        model=dougong, title='柱头铺作 · 斜拱', era='善化寺三圣殿 · 金',
        lead='檐下那一圈「木头的花」，就是斗拱：斗上叠栱、栱上再叠斗，一层层往外挑。',
        rows=[
            ('01', '栌斗', '大斗，坐在柱头上，全朵的基座。'),
            ('02', '泥道栱', '横向那一根，把相邻两朵连成一线。'),
            ('03', '华栱', '垂直于檐面出跳，一跳不到半米。'),
            ('04', '下昂', '斜向下伸出的长木，用斜面把出檐「挑」得更远。'),
            ('05', '斜拱', '60° 斜出的两拱，三圣殿最显眼的记号，远看像花瓣。'),
            ('06', '令栱 · 散斗', '最外一跳承托檐檩的小横栱与小斗。'),
            ('07', '耍头', '最上层水平出头，压住整朵、也收口。'),
        ],
        note='出跳越多、层数越高，等级越高。斗拱把屋面荷载一层层收拢，最后交给柱子——'
             '所以它是「传力的关节」，不只是装饰。',
        num_of={'栌斗': '01', '泥道栱': '02', '华栱': '03', '下昂': '04',
                '斜拱': '05', '令栱': '06', '散斗': '06', '耍头': '07'},
        view_zoom=0.95, side2d=side_dougong, side_label='侧立面 · 昂的斜面把出檐挑远'),
    'chiwen': dict(
        model=chiwen, title='鸱吻 · 正脊两端', era='善化寺三圣殿 · 金',
        lead='屋脊两头那个张着嘴咬住脊的兽，就是鸱吻；宋代还是「兽头吞脊」，尾比明清短。',
        rows=[
            ('01', '吻身', '整片侧视为 S 形，厚度只有 26cm，是「片」不是「块」。'),
            ('02', '吞口', '下沿开口，把正脊咬进去——所以叫「吞脊」。'),
            ('03', '尾', '向上收、略微外卷；比明清的龙尾短得多。'),
            ('04', '背兽', '吻背上一只小兽，宋元常见，明清换成剑把。'),
            ('05', '脊座', '压在正脊上的底座，把吻与脊身连成一体。'),
        ],
        note='吻压在脊的两端，是屋面收头的位置：它加重了脊端、压住瓦垄，'
             '也让整条正脊在视觉上「有始有终」。',
        num_of={'吻身': '01', '背兽': '04', '脊座': '05'},
        view_zoom=0.86, side2d=side_chiwen, two_d=True, side_label='侧立面 · 吞脊口与上卷的尾'),
}


# ── 右侧的 2D 侧立面（直接画，不走 3D：昂的斜面与吞脊口这样最清楚）──────
WOOD = (231, 222, 207)
WOOD2 = (243, 237, 226)


def front_chiwen(cv, x0, y0, w, h, ts, F):
    """正立面：吻在正脊上就是一「片」——薄板 + 上下两条收分线 + 背兽。"""
    M, k = _mapper(x0, y0, w, h, (-0.30, 0.30), (-0.34, 1.62))
    th = 0.26

    def poly(pts, fill=WOOD, lw=1.3):
        cv.poly([M(*p) for p in pts], fill, INK, lw)

    # 正脊
    poly([(-0.30, -0.22), (0.30, -0.22), (0.30, 0.02), (-0.30, 0.02)], WOOD2, 1.1)
    # 吻身（下宽上窄，顶上一只背兽）
    poly([(-0.13, 0.02), (0.13, 0.02), (0.115, 0.62), (0.085, 1.02),
          (0.02, 1.10), (-0.085, 1.02), (-0.115, 0.62)], WOOD, 1.4)
    # 背兽
    poly([(-0.045, 1.10), (0.045, 1.10), (0.045, 1.26), (-0.045, 1.26)], WOOD, 1.2)
    # 厚度标注：这一片只有 26cm
    cv.line([M(-0.13, 0.06), M(-0.13, -0.06)], INK3, 1.0)
    cv.line([M(0.13, 0.06), M(0.13, -0.06)], INK3, 1.0)
    cv.text(M(0.0, -0.10)[0], M(0.0, -0.10)[1] + int(34 * ts), '厚 26 cm',
            SP.font('hei', F(26)), INK3, anchor='mm')


# ── 版式 ─────────────────────────────────────────────────────────
def _fit(model, box_w, box_h, *, front=False, zoom=0.95):
    c, s = (1.0, 0.0) if front else (0.866, 0.5)
    zk = 1.0 if front else zoom
    us, vs = [], []
    for fac in model['faces']:
        for q in SP._fs(fac)[0]:
            u, v = SP._uv(q, zk, c, s)
            us.append(u)
            vs.append(v)
    u0, u1, v0, v1 = min(us), max(us), min(vs), max(vs)
    k = min(box_w / max(1e-6, u1 - u0), box_h / max(1e-6, v1 - v0))
    return dict(k=k, u0=u0, v0=v0, bw=u1 - u0, bh=v1 - v0, c=c, s=s, zk=zk)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--part', required=True, choices=sorted(PARTS))
    ap.add_argument('--out', required=True)
    ap.add_argument('--scale', type=float, default=1.0)
    a = ap.parse_args()
    spec = PARTS[a.part]
    model = spec['model'](a.scale)

    # 单件详图用更实的木色：整片图里那些近乎白的面，放到构件特写上会读不出体块
    SP.BODY_TOP = (247, 241, 229)
    SP.BODY_BOT = (206, 196, 180)
    SP.BODY_SIDE = (230, 221, 206)
    SP.BODY_SIDE2 = (219, 209, 192)
    SP.FILL_BODY = 130

    cv = SP.Canvas(W, H)
    ts = SP._ts(W, H)
    F = lambda s: max(11, int(round(s * ts)))
    mx = int(150 * ts)

    # 标题
    cv.text(mx, int(150 * ts), spec['title'], SP.font('kai', F(110)), INK, anchor='lm')
    cv.text(mx, int(250 * ts), spec['era'], SP.font('hei', F(44)), ACCENT, anchor='lm')
    cv.line([(mx, int(318 * ts)), (W - mx, int(318 * ts))], INK4, 1.2)
    lead = spec['lead']
    y = int(390 * ts)
    for seg in wrap(cv, lead, SP.font('hei', F(40)), W - 2 * mx):
        cv.text(mx, y, seg, SP.font('hei', F(40)), INK3, anchor='lm')
        y += int(64 * ts)

    # 主图：左 = 分件爆炸轴测（看清层级），右 = 侧立面示意（看清昂的斜面）
    main_top = int(740 * ts)
    main_bot = int(1900 * ts)
    left_w = int(W * 0.56) - mx
    rx = mx + left_w + int(80 * ts)
    right_w = W - mx - rx

    exp = None
    if spec.get('two_d'):
        # 吻是「片」不是「块」，3D 轴测只会糊成一团；直接给两个立面
        spec['side2d'](cv, mx + int(40 * ts), main_top - int(30 * ts),
                       left_w - int(80 * ts), (main_bot - main_top) + int(60 * ts), ts, F)
        cv.text(mx, main_bot + int(26 * ts), '侧立面 · 吞脊口、上卷的尾',
                SP.font('hei', F(34)), INK3, anchor='la')
        front_chiwen(cv, rx, main_top - int(30 * ts), right_w, (main_bot - main_top) + int(60 * ts), ts, F)
        cv.text(rx, main_bot + int(26 * ts), '正立面 · 一片薄板',
                SP.font('hei', F(34)), INK3, anchor='la')

    exp = None if spec.get('two_d') else spec['model'](a.scale, explode={i: i for i in range(9)})
    if exp is None:
        fit = None
    if exp is not None:
        fit = _fit(exp, left_w * 0.96, (main_bot - main_top) * 0.94, zoom=spec['view_zoom'])
    if exp is not None:
        ox = mx + (left_w - fit['bw'] * fit['k']) / 2 - fit['u0'] * fit['k']
        oy = main_top + ((main_bot - main_top) - fit['bh'] * fit['k']) / 2 - fit['v0'] * fit['k']
        ax = SP.Axo(k=fit['k'], zk=fit['zk'], ox=ox, oy=oy, c=fit['c'], s=fit['s'])
        SP.draw_model(cv, exp, ax)
        # 分件编号：每件取包围盒中心，避开彼此
        nos = {}
        placed = []
        for part, idx, ff, ll in exp.get('_groups', []):
            if not ff:
                continue
            ps = [ax.pt(q) for f in ff for q in SP._fs(f)[0]]
            cx = sum(p[0] for p in ps) / len(ps)
            cy = sum(p[1] for p in ps) / len(ps)
            num = spec['num_of'].get(part)
            if num is None:
                continue
            for _ in range(8):
                if all(abs(cx - qx) > int(46 * ts) or abs(cy - qy) > int(46 * ts)
                       for qx, qy in placed):
                    break
                cy -= int(26 * ts)
            placed.append((cx, cy))
            r = int(23 * ts)
            cv.ellipse(cx, cy, r, r, fill=PAPER, outline=ACCENT, lw=1.4)
            cv.text(cx, cy, num, SP.font('num', F(24)), ACCENT, anchor='mm')
        cv.text(mx, main_bot + int(26 * ts), '分件爆炸 · 装配顺序自上而下',
                SP.font('hei', F(34)), INK3, anchor='la')

    # 右：侧立面（y-z 平面直接画，不再走 3D）；two_d 版已经在上面画过了
    if spec.get('side2d') and not spec.get('two_d'):
        spec['side2d'](cv, rx, main_top, right_w, main_bot - main_top, ts, F)
        cv.text(rx, main_bot + int(26 * ts), spec['side_label'],
                SP.font('hei', F(34)), INK3, anchor='la')

    # 分件编号说明（两栏）
    y0 = int(2060 * ts)
    col_w = (W - 2 * mx) // 2 - int(40 * ts)
    for i, (no, name, desc) in enumerate(spec['rows']):
        col, row = (0, i) if i < 4 else (1, i - 4)
        cx = mx + col * (col_w + int(80 * ts))
        cy = y0 + row * int(150 * ts)
        r = int(24 * ts)
        cv.ellipse(cx + r, cy, r, r, fill=PAPER, outline=ACCENT, lw=1.4)
        cv.text(cx + r, cy, no, SP.font('num', F(24)), ACCENT, anchor='mm')
        cv.text(cx + r * 2 + int(18 * ts), cy, name, SP.font('hei', F(42)), INK, anchor='lm')
        cv.text(cx + r * 2 + int(18 * ts), cy + int(48 * ts), desc,
                SP.font('hei', F(31)), INK3, anchor='lm')

    # 结语 + 免责
    ny = int(2780 * ts)
    cv.line([(mx, ny - int(40 * ts)), (mx + int(10 * ts), ny - int(40 * ts))], ACCENT, 3.0)
    for seg in wrap(cv, spec['note'], SP.font('hei', F(36)), W - 2 * mx):
        cv.text(mx, ny, seg, SP.font('hei', F(36)), INK3, anchor='lm')
        ny += int(58 * ts)
    cv.text(mx, int(3010 * ts), '示意外形与分件关系，非测绘数据 · march-aa structure view',
            SP.font('hei', F(28)), INK4, anchor='lm')

    cv.img.convert('RGB').save(a.out, quality=95)
    print('saved:', a.out, '(%d×%d)' % cv.img.size)


if __name__ == '__main__':
    main()
