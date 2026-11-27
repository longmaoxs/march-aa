#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
march-aa-structure-view — 古建构造关系图（透明轴测）

同一套参数化建模，画法从「分层爆炸 + 白模填色」换成「整栋透明 + 被遮线降级」：
  · 面：极浅纸色填充（多重叠加自然加深），保留体量感
  · 线：可见段实线、被遮段浅灰虚线（逐段做深度可见性判定，不是"全画上去"）
  · 朱红：只给传力路径与关键节点
不生成位图、不写 AI 文字。
"""

import math
import os
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# ------------------------------------------------------------------ 基本常量

S = 2                                   # 超采样倍数
PAPER = (250, 249, 246)

INK = (38, 42, 46)
INK2 = (88, 97, 103)
INK3 = (152, 157, 160)
INK4 = (188, 192, 194)
WIRE = (146, 151, 155)

BODY_TOP = (253, 253, 252)
BODY_SIDE = (250, 250, 248)
BODY_SIDE2 = (247, 247, 245)
BODY_BOT = (237, 237, 235)
SCREEN = (246, 244, 238)
MASS = (229, 228, 224)

ACCENT = (174, 52, 47)
ACCENT_DEEP = (146, 38, 34)
ACCENT_MID = (188, 100, 94)
ACCENT_SOFT = (203, 128, 122)

FILL_BODY = 30                          # 面的基础透明度（叠加后自然加深）
FILL_ACC = 30

VIEW = (0.57735, 0.57735, 0.57735)

_KIND_W = {'body': 1.0, 'screen': 0.8, 'accent': 1.2}


# ------------------------------------------------------------------ 字体

FONT_CANDIDATES = {
    'kai': ['assets/fonts/LXGWWenKai-Regular.ttf',
            '/System/Library/Fonts/Supplemental/Songti.ttc',
            '/usr/share/fonts/truetype/arphic/ukai.ttc'],
    'hei': ['/System/Library/Fonts/STHeiti Medium.ttc',
            '/System/Library/Fonts/Supplemental/Arial Unicode.ttf',
            '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
            '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
            'C:/Windows/Fonts/msyh.ttc'],
    'num': ['/System/Library/Fonts/HelveticaNeue.ttc',
            '/Library/Fonts/Arial.ttf',
            'C:/Windows/Fonts/arial.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'],
}
_FONTS = {}
_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _pick_font(kind):
    if kind in _FONTS:
        return _FONTS[kind]
    for path in FONT_CANDIDATES.get(kind, []):
        cand = path if os.path.isabs(path) else os.path.join(_HERE, path)
        if os.path.exists(cand):
            _FONTS[kind] = cand
            return cand
    _FONTS[kind] = None
    return None


def font(kind, size):
    path = _pick_font(kind) or _pick_font('hei') or _pick_font('num')
    if path:
        try:
            return ImageFont.truetype(path, size * S)
        except Exception:
            pass
    return ImageFont.load_default()


# ------------------------------------------------------------------ 画布

class Canvas(object):
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.img = Image.new('RGB', (w * S, h * S), PAPER)
        self.dr = ImageDraw.Draw(self.img, 'RGBA')

    def poly(self, pts, fill=None, outline=None, lw=1.0, alpha=None):
        p = [(x * S, y * S) for x, y in pts]
        if fill is None and outline is None:
            return
        f = None
        if fill is not None:
            a = 255 if alpha is None else int(alpha)
            f = tuple(fill) + (a,)
        o = None
        if outline is not None and lw:
            width = max(1, int(round(lw * S)))
            if width <= 1:
                o = tuple(outline) + (255,)
            else:
                self.dr.line(p + [p[0]], fill=tuple(outline) + (255,), width=width, joint='curve')
        self.dr.polygon(p, fill=f)
        if o is not None:
            self.dr.line(p + [p[0]], fill=o, width=1)

    def line(self, pts, color, lw=1.0, alpha=255):
        p = [(x * S, y * S) for x, y in pts]
        self.dr.line(p, fill=tuple(color) + (int(alpha),),
                     width=max(1, int(round(lw * S))), joint='curve')

    def dash(self, pts, color, lw=1.0, on=5.0, off=4.0, alpha=255):
        p = [(x * S, y * S) for x, y in pts]
        on *= S
        off *= S
        for i in range(len(p) - 1):
            x0, y0 = p[i]
            x1, y1 = p[i + 1]
            L = math.hypot(x1 - x0, y1 - y0)
            if L < 0.01:
                continue
            ux, uy = (x1 - x0) / L, (y1 - y0) / L
            t = 0.0
            while t < L:
                t2 = min(L, t + on)
                self.dr.line([(x0 + ux * t, y0 + uy * t), (x0 + ux * t2, y0 + uy * t2)],
                             fill=tuple(color) + (int(alpha),),
                             width=max(1, int(round(lw * S))))
                t = t2 + off

    def ellipse(self, cx, cy, rx, ry, outline=None, fill=None, lw=1.0, alpha=None):
        box = [(cx - rx) * S, (cy - ry) * S, (cx + rx) * S, (cy + ry) * S]
        f = None
        if fill is not None:
            f = tuple(fill) + (255 if alpha is None else int(alpha),)
        o = None
        if outline is not None:
            o = tuple(outline) + (255,)
        self.dr.ellipse(box, fill=f, outline=o, width=max(1, int(round(lw * S))))

    def text(self, x, y, s, fnt, color, anchor='la', alpha=255):
        self.dr.text((x * S, y * S), s, font=fnt, fill=tuple(color) + (int(alpha),), anchor=anchor)

    def finish(self, noise=3):
        out = self.img.resize((self.w, self.h), Image.LANCZOS)
        a = np.asarray(out).astype(np.int16)
        rng = np.random.default_rng(7)
        n = rng.integers(-noise, noise + 1, size=(self.h, self.w, 1))
        a = np.clip(a + n, 0, 255).astype(np.uint8)
        return Image.fromarray(a)


# ------------------------------------------------------------------ 三维 → 屏幕

class Axo(object):
    def __init__(self, k=100.0, zk=0.95, ox=1200.0, oy=1600.0, c=0.866, s=0.5):
        self.k, self.zk, self.ox, self.oy, self.c, self.s = k, zk, ox, oy, c, s

    def pt(self, p):
        x, y, z = p
        return (self.ox + (x - y) * self.c * self.k,
                self.oy + ((x + y) * self.s - z * self.zk) * self.k)

    def at(self, k=None, ox=None, oy=None):
        return Axo(self.k if k is None else k, self.zk,
                   self.ox if ox is None else ox, self.oy if oy is None else oy)


def _norm(a, b, c):
    ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
    nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    L = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
    return (nx / L, ny / L, nz / L)


def _shade(n):
    if n[2] > 0.55:
        return BODY_TOP
    if n[2] < -0.55:
        return BODY_BOT
    return BODY_SIDE if (n[0] + n[1]) >= 0 else BODY_SIDE2


_PART = [None]
_PART_TARGET = [None]


def part(name):
    """设定当前正在生成的构件名，随后 _F 生成的面都会带上它。"""
    _PART[0] = name
    return name


def _F(quad, kind='body', **kw):
    meta = dict(n=_norm(quad[0], quad[1], quad[2]) if len(quad) >= 3 else (0, 0, 1))
    meta.update(kw)
    if _PART[0] and 'part' not in meta:
        meta['part'] = _PART[0]
    return (tuple(quad), kind, meta)


def _fs(fac):
    if len(fac) == 3 and isinstance(fac[2], dict):
        return fac[0], fac[1], fac[2]
    if len(fac) == 2:
        return fac[0], fac[1], {}
    return fac, 'body', {}


def _plane_tag(quad):
    cen = sum(p[0] + p[1] + p[2] for p in quad) / len(quad)
    n = _norm(quad[0], quad[1], quad[2])
    if n[0] + n[1] + n[2] < 0:
        n = (-n[0], -n[1], -n[2])
    return {'n': n, 'plane': cen}


# ------------------------------------------------------------------ 基础体

def box(x0, y0, z0, x1, y1, z1, kind='body'):
    x0, x1 = min(x0, x1), max(x0, x1)
    y0, y1 = min(y0, y1), max(y0, y1)
    z0, z1 = min(z0, z1), max(z0, z1)
    q = [
        ((x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)),
        ((x0, y0, z0), (x0, y1, z0), (x1, y1, z0), (x1, y0, z0)),
        ((x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)),
        ((x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)),
        ((x1, y1, z0), (x0, y1, z0), (x0, y1, z1), (x1, y1, z1)),
        ((x0, y1, z0), (x0, y0, z0), (x0, y0, z1), (x0, y1, z1)),
    ]
    return [_F(t, kind) for t in q]


def extrude(pts2d, z0, z1, kind='body'):
    out = [[(p[0], p[1], z1) for p in pts2d],
           [(p[0], p[1], z0) for p in reversed(pts2d)]]
    n = len(pts2d)
    for i in range(n):
        a, b = pts2d[i], pts2d[(i + 1) % n]
        out.append([(a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1), (a[0], a[1], z1)])
    return [_F(tuple(q), kind) for q in out]


def prism(cx, cy, r, z0, z1, n=12, rot=math.pi / 12, kind='body', r_top=None, slim=False):
    _prev = _PART[0]
    rt = r if r_top is None else r_top
    pts = [(cx + r * math.cos(rot + 2 * math.pi * i / n),
            cy + r * math.sin(rot + 2 * math.pi * i / n)) for i in range(n)]
    top = [(cx + rt * math.cos(rot + 2 * math.pi * i / n),
            cy + rt * math.sin(rot + 2 * math.pi * i / n)) for i in range(n)]
    out = [_F(tuple((p[0], p[1], z1) for p in top), kind),
           _F(tuple((p[0], p[1], z0) for p in reversed(pts)), kind)]
    for i in range(n):
        j = (i + 1) % n
        q = ((pts[i][0], pts[i][1], z0), (pts[j][0], pts[j][1], z0),
             (top[j][0], top[j][1], z1), (top[i][0], top[i][1], z1))
        out.append(_F(q, kind, edge=0.0 if slim else None))
    _PART[0] = _prev
    return out


def column(cx, cy, z0, z1, r=0.13, base=True, kind='body', base_type='fupen',
           shaft='round'):
    """柱 + 柱础。base_type 见 components.md；shaft: round|octagon|square|suo"""
    _prev = _PART[0]; part('柱身')
    if shaft == 'octagon':
        out = prism(cx, cy, r * 1.06, z0, z1, n=8, kind=kind, slim=True)
    elif shaft == 'square':
        out = prism(cx, cy, r * 1.18, z0, z1, n=4, kind=kind, slim=True)
    elif shaft == 'suo':          # 梭柱：下粗上细，中段略鼓
        zb = z0 + (z1 - z0) * 0.42
        out = prism(cx, cy, r * 1.07, z0, zb, n=12, kind=kind, slim=True)
        out += prism(cx, cy, r * 0.99, zb, z1, n=12, kind=kind, slim=True)
    else:
        out = prism(cx, cy, r, z0, z1, n=12, kind=kind, slim=True)
    if not base:
        _PART[0] = _prev
        return out
    part('柱础')
    if base_type == 'plain':
        out += box(cx - r * 0.95, cy - r * 0.95, z0, cx + r * 0.95, cy + r * 0.95,
                   z0 + 0.09, kind)
    elif base_type == 'drum':
        out += prism(cx, cy, r * 1.32, z0, z0 + 0.15, n=12, kind=kind, slim=True)
        out += box(cx - r * 1.38, cy - r * 1.38, z0 - 0.02, cx + r * 1.38,
                   cy + r * 1.38, z0 + 0.03, kind)
    elif base_type == 'xumizuo':
        out += box(cx - r * 1.55, cy - r * 1.55, z0, cx + r * 1.55, cy + r * 1.55,
                   z0 + 0.09, kind)
        out += prism(cx, cy, r * 1.18, z0 + 0.09, z0 + 0.19, n=12, kind=kind, slim=True)
        out += box(cx - r * 1.45, cy - r * 1.45, z0 + 0.19, cx + r * 1.45,
                   cy + r * 1.45, z0 + 0.26, kind)
    else:  # fupen / lianban：倒扣的浅盆（下宽上窄）
        prof = [(r * 1.52, z0), (r * 1.44, z0 + 0.05), (r * 1.20, z0 + 0.11),
                (r * 1.02, z0 + 0.15)]
        for i in range(len(prof) - 1):
            r0, zz0 = prof[i]
            r1, zz1 = prof[i + 1]
            out += prism(cx, cy, (r0 + r1) * 0.5, zz0, zz1, n=12, kind=kind, slim=True)
        if base_type == 'lianban':
            for k in range(12):
                a = 2 * math.pi * k / 12.0
                px, py = cx + math.cos(a) * r * 1.28, cy + math.sin(a) * r * 1.28
                out += _plank(px, py, math.cos(a), math.sin(a), 0.10, 0.05,
                              z0 + 0.03, z0 + 0.13, kind)
    _PART[0] = _prev
    return out


def _plank(cx, cy, ux, uy, length, width, z0, z1, kind='body'):
    n = math.hypot(ux, uy) or 1.0
    ux, uy = ux / n, uy / n
    px, py = -uy * width * 0.5, ux * width * 0.5
    ax, ay = cx - ux * length * 0.5, cy - uy * length * 0.5
    bx, by = cx + ux * length * 0.5, cy + uy * length * 0.5
    quad = [(ax + px, ay + py), (bx + px, by + py), (bx - px, by - py), (ax - px, ay - py)]
    return extrude(quad, z0, z1, kind)


def _beam3(a, b, w=0.16, kind='body'):
    dx, dy, dz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    px, py = -dy, dx
    n = math.hypot(px, py) or 1.0
    px, py = px / n * w * 0.5, py / n * w * 0.5
    h = w * 0.5
    ca = [(a[0] + px, a[1] + py, a[2] + h), (a[0] + px, a[1] + py, a[2] - h),
          (a[0] - px, a[1] - py, a[2] - h), (a[0] - px, a[1] - py, a[2] + h)]
    cb = [(b[0] + px, b[1] + py, b[2] + h), (b[0] + px, b[1] + py, b[2] - h),
          (b[0] - px, b[1] - py, b[2] - h), (b[0] - px, b[1] - py, b[2] + h)]
    quads = [tuple(cb[::-1]), tuple(ca)]
    for i in range(4):
        j = (i + 1) % 4
        quads.append((ca[i], ca[j], cb[j], cb[i]))
    return [_F(q, kind) for q in quads]


def _square(cx, cy, r):
    return [(cx - r, cy - r), (cx + r, cy - r), (cx + r, cy + r), (cx - r, cy + r)]


def _perimeter(half, cps=2):
    """正方形周长上的柱子点：按「下→右→上→左」顺序环行，保证相邻点是一条边。
    （旧写法把四个边按 t 交错输出，连起来是横跨平面的锯齿，梁与棂条会画成对角线）"""
    cps = max(2, cps)
    out = []
    for i in range(cps):                                   # 下边：左 → 右
        out.append((-half + 2 * half * i / (cps - 1), -half))
    for i in range(1, cps):                                # 右边：下 → 上
        out.append((half, -half + 2 * half * i / (cps - 1)))
    for i in range(cps - 2, -1, -1):                       # 上边：右 → 左
        out.append((-half + 2 * half * i / (cps - 1), half))
    for i in range(cps - 2, 0, -1):                        # 左边：上 → 下
        out.append((-half, -half + 2 * half * i / (cps - 1)))
    return out


def platform(cx, cy, hx, hy, h=0.45, steps=3, kind='mass', front='+y',
             step_style='chuídai'):
    """台基：一块方台 + 正面中点的踏跺（front 指定朝 +x / +y）。"""
    _prev = _PART[0]; part('台基')
    out = box(cx - hx, cy - hy, 0.0, cx + hx, cy + hy, h, kind)
    sw = min((hx if front == '+y' else hy) * 0.62, 1.35)
    for i in range(steps):
        zz = h - h * (i + 1) / float(steps)
        t0 = 0.15 + 0.34 * i
        if front == '+y':
            wdt = sw - i * (0.10 if step_style == 'chuídai' else 0.16)
            out += box(cx - wdt, cy + hy + t0, 0.0, cx + wdt, cy + hy + t0 + 0.34,
                       zz + 0.02, kind)
            if step_style == 'yulu':      # 御路：中间一整条斜石
                out += box(cx - 0.62, cy + hy + t0, zz + 0.02,
                           cx + 0.62, cy + hy + t0 + 0.34, zz + 0.10, kind)
        else:
            out += box(cx + hx + t0, cy - sw + i * 0.10, 0.0,
                       cx + hx + t0 + 0.34, cy + sw - i * 0.10, zz + 0.02, kind)
    _PART[0] = _prev
    return out


def efang_set(pts2d, zt, eh, style='lan_e_pupai', kind='body'):
    """额枋体系。style: lan_e(只阑额)|lan_e_pupai(阑额+普拍枋)|e_fang(额枋+由额)|di_fu(加地栿)"""
    _prev = _PART[0]; part('额枋')
    out = beam_ring(pts2d, zt, zt + eh, 0.12, kind)
    if style == 'lan_e_pupai':
        out += beam_ring(pts2d, zt + eh, zt + eh + 0.10, 0.17, kind)   # 普拍枋：更宽更扁
    elif style == 'e_fang':
        out += beam_ring(pts2d, zt - 0.30, zt - 0.12, 0.10, kind)     # 由额
        out += beam_ring(pts2d, zt + eh, zt + eh + 0.09, 0.15, kind)
    if style == 'di_fu':
        out += beam_ring(pts2d, zt - 0.55, zt - 0.45, 0.09, kind)     # 地栿
    _PART[0] = _prev
    return out


def railing(pts2d, z0, h=0.75, n=None, kind='body'):
    _prev = _PART[0]; part('栏杆')
    out = []
    for i in range(len(pts2d)):
        a, b = pts2d[i], pts2d[(i + 1) % len(pts2d)]
        L = ((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5
        if L < 0.2:
            continue
        m = n or max(2, int(L / 1.6) + 1)
        for k in range(m + 1):
            t = k / float(m)
            x, y = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
            out += box(x - 0.10, y - 0.10, z0, x + 0.10, y + 0.10, z0 + h, kind)
        out += box(min(a[0], b[0]) - 0.06, min(a[1], b[1]) - 0.06, z0 + h * 0.92,
                   max(a[0], b[0]) + 0.06, max(a[1], b[1]) + 0.06, z0 + h, kind)
        out += box(min(a[0], b[0]) - 0.06, min(a[1], b[1]) - 0.06, z0 + 0.10,
                   max(a[0], b[0]) + 0.06, max(a[1], b[1]) + 0.06, z0 + h * 0.26, kind)
    _PART[0] = _prev
    return out


def beam_ring(pts2d, z0, z1, w=0.09, kind='body'):
    """沿多边形顶点依次连梁（额枋）。"""
    _prev = _PART[0]; part('额枋')
    out = []
    m = len(pts2d)
    for i in range(m):
        a, b = pts2d[i], pts2d[(i + 1) % m]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy)
        if L < 1e-6:
            continue
        nx, ny = -dy / L * w, dx / L * w
        quad = [(a[0] + nx, a[1] + ny, z0), (a[0] - nx, a[1] - ny, z0),
                (b[0] - nx, b[1] - ny, z0), (b[0] + nx, b[1] + ny, z0)]
        out += extrude(quad, z0, z1, kind)
    _PART[0] = _prev
    return out


def lattice_panel(pts2d, z0, z1, step=0.22, kind='body'):
    """槛窗 / 楣子：薄板 + 竖棂 + 一道横披。"""
    faces, lines = [], []
    m = len(pts2d)
    for i in range(m):
        a, b = pts2d[i], pts2d[(i + 1) % m]
        if math.hypot(b[0] - a[0], b[1] - a[1]) < 1e-6:
            continue
        n_out = _norm((a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1))
        quad = [(a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1), (a[0], a[1], z1)]
        faces.append(_F(tuple(quad), 'screen', n=n_out))
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        plane = sum(q[0] + q[1] + q[2] for q in quad) / 4.0
        tag = {'n': n_out, 'plane': plane}
        cnt = max(2, int(L / step))
        for j in range(1, cnt):
            u = j / cnt
            x = a[0] + (b[0] - a[0]) * u
            y = a[1] + (b[1] - a[1]) * u
            lines.append((((x, y, z0 + 0.02), (x, y, z1 - 0.02), INK3, 0.9), tag))
        zr = z0 + (z1 - z0) * 0.62
        lines.append((((a[0], a[1], zr), (b[0], b[1], zr), INK3, 1.0), tag))
    return faces, lines


def wall_ring(pts2d, z0, z1, sill=0.55, step=0.24, kind='body'):
    """墙体环：下段实墙 + 上段槛窗棂花。"""
    _prev = _PART[0]; part('墙体')
    faces, lines = [], []
    m = len(pts2d)
    for i in range(m):
        a, b = pts2d[i], pts2d[(i + 1) % m]
        if math.hypot(b[0] - a[0], b[1] - a[1]) < 1e-6:
            continue
        zm = z0 + (z1 - z0) * sill
        faces.append(_F(((a[0], a[1], z0), (b[0], b[1], z0),
                         (b[0], b[1], zm), (a[0], a[1], zm)), kind))
        pf, pl = lattice_panel([a, b], zm, z1, step=step, kind=kind)
        faces += pf
        lines += pl
    return faces, lines


# ------------------------------------------------------------------ 屋面 / 砖纹 / 斗拱（重建段）

BRICK = (152, 160, 164)
BRICK_DEEP = (120, 128, 133)


def _uv(p, zk=0.95):
    x, y, z = p
    return ((x - y) * 0.866, (x + y) * 0.5 - z * zk)


def _uv_bbox(model, zk=0.95):
    us, vs = [], []
    for fac in model['faces']:
        for p in _fs(fac)[0]:
            u, v = _uv(p, zk)
            us.append(u); vs.append(v)
    for e in model.get('lines', []):
        seg = _line_parts(e)[0]
        for p in seg:
            u, v = _uv(p, zk)
            us.append(u); vs.append(v)
    for c in model.get('callouts', []):
        u, v = _uv(c['at'], zk)
        us.append(u); vs.append(v)
    if not us:
        return (0.0, 0.0, 1.0, 1.0)
    return (min(us), min(vs), max(us), max(vs))


def brick_quad(p0, u, v, nu, nv, color=BRICK, w=0.62, stagger=True):
    """一块矩形面上的青灰砖缝：水平通缝 + 错缝竖缝。返回线表。"""
    _prev = _PART[0]; part('砖石')
    lu = math.sqrt(u[0] ** 2 + u[1] ** 2 + u[2] ** 2) or 1.0
    lv = math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2) or 1.0
    u = (u[0] / lu, u[1] / lu, u[2] / lu)
    v = (v[0] / lv, v[1] / lv, v[2] / lv)

    def P(a, b):
        return (p0[0] + u[0] * a + v[0] * b,
                p0[1] + u[1] * a + v[1] * b,
                p0[2] + u[2] * a + v[2] * b)
    cen = P(0.5, 0.5)
    n = _norm(p0, P(1.0, 0.0), P(0.0, 1.0))
    if n[0] + n[1] + n[2] < 0:
        n = (-n[0], -n[1], -n[2])
    tag = {'n': n, 'plane': cen[0] + cen[1] + cen[2]}
    out = []
    nc = max(2, int(round(nv / 0.20)))
    for i in range(1, nc):
        b = nv * i / nc
        out.append(((P(0, b), P(nu, b), color, 0.5), tag))
    nr = max(1, int(round(nu / w)))
    for i in range(nc):
        b0, b1 = nv * i / nc, nv * (i + 1) / nc
        off = (w * 0.5) if (stagger and i % 2) else 0.0
        for j in range(nr + 1):
            a = off + nu * j / nr
            if a <= 0.02 or a >= nu - 0.02:
                continue
            out.append(((P(a, b0), P(a, b1), color, 0.42), tag))
    _PART[0] = _prev
    return out


def brick_box_sides(x0, y0, x1, y1, z0, z1, color=BRICK):
    """方体四个侧面贴砖缝。"""
    out = []
    out += brick_quad((x0, y0, z0), (1, 0, 0), (0, 0, 1), x1 - x0, z1 - z0, color)
    out += brick_quad((x1, y0, z0), (0, 1, 0), (0, 0, 1), y1 - y0, z1 - z0, color)
    out += brick_quad((x0, y1, z0), (1, 0, 0), (0, 0, 1), x1 - x0, z1 - z0, color)
    out += brick_quad((x0, y0, z0), (0, 1, 0), (0, 0, 1), y1 - y0, z1 - z0, color)
    return out


def brick_tri(gx, ys, shz, ridge_z, course=0.24, color=BRICK):
    """山花的砖缝：逐皮收窄的水平线。"""
    out = []
    H = ridge_z - shz
    if H <= 0:
        return out
    n = max(2, int(H / course))
    for i in range(1, n):
        z = shz + H * i / n
        w = ys * (1 - i / float(n))
        if w < 0.08:
            continue
        out.append((((gx, -w, z), (gx, w, z), color, 0.5), {'n': (1, 0, 0), 'plane': gx}))
    return out


def bracket_set(pts, z0, z1, proj=0.32, kind='body', style='jixin'):
    """斗拱。style: jixin(计心造,每跳加横栱) | touxin(偷心造,只出华栱) | yidou3sheng(一斗三升)"""
    _prev = _PART[0]; part('斗拱')
    if style == 'xiegong':                 # 斜拱：45° 斜出的两跳
        import math as _m
        base = [(p[0], p[1], z0) for p in pts]
        out += prism(cx, cy, 0.26, z0, z0 + 0.20, n=8, kind=kind)
        for k in range(2):
            zz = z0 + 0.24 + k * 0.26
            ln2 = 0.42 - k * 0.08
            for s in (-1.0, 1.0):
                dx, dy = _m.cos(_m.pi / 4) * s * ln2, _m.sin(_m.pi / 4) * s * ln2
                out += box(cx + dx - 0.07, cy + dy - 0.07, zz, cx + dx + 0.07, cy + dy + 0.07, zz + 0.10, kind)
        return out
    if style == 'yidou3sheng':
        out = []
        h = z1 - z0
        cx = sum(p[0] for p in pts) / float(len(pts))
        cy = sum(p[1] for p in pts) / float(len(pts))
        for (x, y) in pts:
            out += box(x - 0.17, y - 0.17, z0, x + 0.17, y + 0.17, z0 + h * 0.62, kind)
            vx, vy = x - cx, y - cy
            L = math.hypot(vx, vy) or 1.0
            vx, vy = vx / L, vy / L
            tx, ty = -vy, vx
            for d in (-0.34, 0.0, 0.34):
                out += _plank(x + tx * d, y + ty * d, tx, ty, 0.26, 0.13,
                              z0 + h * 0.62, z0 + h * 0.95, kind)
        return out
    out = []
    h = (z1 - z0)
    dz = h / 4.6
    cx = sum(p[0] for p in pts) / float(len(pts))
    cy = sum(p[1] for p in pts) / float(len(pts))
    for (x, y) in pts:
        vx, vy = x - cx, y - cy
        L = math.hypot(vx, vy) or 1.0
        vx, vy = vx / L, vy / L
        tx, ty = -vy, vx
        out += box(x - 0.16, y - 0.16, z0, x + 0.16, y + 0.16, z0 + dz * 1.4, kind)
        for i in range(3):
            zz = z0 + dz * (1.4 + i * 1.0)
            reach = proj * (0.42 + 0.29 * i)
            out += _plank(x + vx * reach * 0.45, y + vy * reach * 0.45, vx, vy,
                          reach * 1.1, 0.17, zz, zz + dz * 0.55, kind)
            if style != 'touxin':          # 计心造才有跳头横栱
                out += _plank(x, y, tx, ty, 0.60, 0.15, zz, zz + dz * 0.5, kind)
    _PART[0] = _prev
    return out


BASE_NAME = {'plain': '素平', 'fupen': '覆盆式', 'lianban': '宝装莲瓣', 'drum': '鼓镜', 'xumizuo': '须弥座'}
BRACKET_NAME = {'jixin': '三跳计心造', 'touxin': '偷心造', 'yidou3sheng': '一斗三升',
                'xiegong': '斜拱'}
RIDGE_NAME = {'chiwei': '鸱尾（唐式）', 'chiwen': '鸱吻（宋式）', 'zhengwen': '正吻（明清式）', 'none': ''}


def _ral(nx, ny):
    """坡面浓淡：按外法向与视线的夹角连续取值（40…56）。"""
    t = max(0.0, min(1.0, (nx + ny) / 1.414))
    return int(round(40 + 16 * t))


def roof_pyramid(pts, eave_z, apex_z, apex=(0.0, 0.0), lift=0.62, bands=3, seg=8,
                 chu=0.34, kind='accent'):
    """任意边数攒尖：檐口中段平直、只在外端 48% 起翘。"""
    _prev = _PART[0]; part('屋面')
    n = len(pts)
    ring, normals = [], []
    for i in range(n):
        a = pts[i]
        b = pts[(i + 1) % n]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy) or 1.0
        nx, ny = dy / L, -dx / L
        if (nx * (a[0] + b[0]) + ny * (a[1] + b[1])) < 0:
            nx, ny = -nx, -ny
        normals.append((nx, ny))
        row = []
        for j in range(seg + 1):
            u = j / seg
            k = abs(2 * u - 1)
            kk = max(0.0, (k - 0.52) / 0.48)
            e = kk ** 1.9
            out = chu * e
            row.append((a[0] + dx * u + nx * out, a[1] + dy * u + ny * out,
                        eave_z + lift * e))
        ring.append(row)

    def pt_at(i, j, t):
        x, y, z = ring[i][j]
        ax_, ay_ = apex
        return (x + (ax_ - x) * t, y + (ay_ - y) * t, z + (apex_z - z) * (t ** 1.15))

    faces, lines = [], []
    for i in range(n):
        nx, ny = normals[i]
        al = _ral(nx, ny)
        for j in range(seg):
            for bi in range(bands):
                t0, t1 = bi / bands, (bi + 1) / bands
                q = (pt_at(i, j, t0), pt_at(i, j + 1, t0), pt_at(i, j + 1, t1), pt_at(i, j, t1))
                faces.append(_F(q, kind, alpha=al))
            for bi in range(1, bands):
                t = bi / bands
                lines.append(((pt_at(i, j, t), pt_at(i, j + 1, t)), ACCENT_SOFT, 0.6, None))
        for j in range(1, seg):
            lines.append(((ring[i][j], pt_at(i, j, 1.0)), ACCENT_SOFT, 0.55, None))
        # 戗脊
        hip = [ring[i][0]] + [pt_at(i, 0, t) for t in (0.25, 0.5, 0.75)] + [pt_at(i, 0, 1.0)]
        hx, hy = ring[i][0][0] - apex[0], ring[i][0][1] - apex[1]
        far = (hx + hy) < 0
        hc, hw = (ACCENT_SOFT, 0.9) if far else (ACCENT, 1.5)
        for k in range(len(hip) - 1):
            lines.append(((hip[k], hip[k + 1]),
                          hc if k < 1 else (ACCENT_SOFT if far else ACCENT_MID),
                          hw if k < 1 else (0.8 if far else 1.1), None))
        # 檐口封边
        dep = 0.17
        for j in range(seg):
            x0, y0, z0 = ring[i][j]
            x1, y1, z1 = ring[i][j + 1]
            faces.append(_F(((x0, y0, z0 - dep), (x1, y1, z1 - dep), (x1, y1, z1), (x0, y0, z0)),
                            kind, alpha=60))
        eave_top = list(ring[i])
        eave_bot = [(p[0], p[1], p[2] - dep) for p in ring[i]]
        for k in range(len(eave_top) - 1):
            lines.append(((eave_top[k], eave_top[k + 1]), ACCENT, 1.5, None))
            lines.append(((eave_bot[k], eave_bot[k + 1]), ACCENT, 1.0, None))
        # 套兽
        cx, cy, cz = ring[i][0]
        vx, vy = cx - apex[0], cy - apex[1]
        vd = math.hypot(vx, vy) or 1.0
        vx, vy = vx / vd, vy / vd
        bx, by, bz = cx - vx * 0.05, cy - vy * 0.05, cz + 0.02
        faces.append(_F(((bx - 0.075, by - 0.075, bz), (bx + 0.075, by - 0.075, bz),
                         (bx + 0.075, by + 0.075, bz), (bx - 0.075, by + 0.075, bz)),
                        'accent', alpha=180, edge=0.9, edge_color=ACCENT_DEEP))
        faces.append(_F(((bx - 0.06, by - 0.06, bz), (bx + 0.06, by - 0.06, bz),
                         (bx + 0.06, by + 0.06, bz + 0.13), (bx - 0.06, by + 0.06, bz + 0.13)),
                        'accent', alpha=180, edge=0.9, edge_color=ACCENT_DEEP))
    return faces, lines


def roof_hip(x0, x1, yh, eave_z, tx0, tx1, ty, tz, bands=5, kind='accent', curve=1.65):
    """庑殿屋面（重写版）。

    几何用「等参数矩形」描述：t=0 是檐口矩形 [x0,x1]×[-yh,yh]，t=1 收到脊（ty=0 即一条线）。
    任意 t 处的水平截面是矩形 [x0t,x1t]×[-yt,yt]，四坡各由自家方向的边拼成，
    因此带与带之间天然连续；举折用 z = eave + (tz-eave)*t**curve（凹曲）。
    """
    _prev = _PART[0]; part('屋面')
    faces, lines = [], []

    def L(a, b, t):
        return a + (b - a) * t

    def zt_(t):
        return eave_z + (tz - eave_z) * (t ** curve)

    def XL(t):
        return L(x0, tx0, t)

    def XR(t):
        return L(x1, tx1, t)

    def Y(t):
        return L(yh, ty, t)

    rows = [i / float(bands) for i in range(bands + 1)]
    al_f = int(_ral(0, -1) * 0.86)      # 前排坡（朝观察者）最重
    al_b = int(_ral(0, 1) * 0.50)
    al_e = int(_ral(-1, 0) * 0.66)

    for i in range(bands):
        t0, t1 = rows[i], rows[i + 1]
        z0, z1 = zt_(t0), zt_(t1)
        xa0, xb0, ya0 = XL(t0), XR(t0), Y(t0)
        xa1, xb1, ya1 = XL(t1), XR(t1), Y(t1)

        # 前坡（y 负侧）
        faces.append(_F(((xa0, -ya0, z0), (xb0, -ya0, z0),
                         (xb1, -ya1, z1), (xa1, -ya1, z1)), kind, alpha=al_f))
        # 后坡（y 正侧）
        faces.append(_F(((xa0, ya0, z0), (xa1, ya1, z1),
                         (xb1, ya1, z1), (xb0, ya0, z0)), kind, alpha=al_b))
        # 左山面（x = xa(t)）
        faces.append(_F(((xa0, -ya0, z0), (xa1, -ya1, z1),
                         (xa1, ya1, z1), (xa0, ya0, z0)), kind, alpha=al_e))
        # 右山面
        faces.append(_F(((xb0, ya0, z0), (xb1, ya1, z1),
                         (xb1, -ya1, z1), (xb0, -ya0, z0)), kind, alpha=al_e))

    # 瓦垄：沿坡向的曲线，前坡/后坡各画一套
    nt = max(6, int((x1 - x0) / 0.26))
    for j in range(1, nt):
        u = float(j) / nt
        xe = L(x0, x1, u)
        xr = min(max(xe, tx0), tx1)                 # 到了脊段就收到脊，否则收到山面
        pts_f, pts_b = [], []
        for k in range(9):
            t = k / 8.0
            xx = L(xe, xr, t)
            yy = Y(t)
            zz = zt_(t) + 0.01
            pts_f.append((xx, -yy, zz))
            pts_b.append((xx, yy, zz))
        lines.append(((pts_f[0], pts_f[-1]), ACCENT_SOFT, 0.5, None))
        lines.append(((pts_b[0], pts_b[-1]), ACCENT_SOFT, 0.5, None))
        # 用折线补齐曲面（三点以上拆段画）
        for pts in (pts_f, pts_b):
            for k in range(len(pts) - 1):
                lines.append(((pts[k], pts[k + 1]), ACCENT_SOFT, 0.5, None))

    # 檐口封边：一圈 0.20 深的竖面带（唐构檐口是一条厚带）
    corners = [(XL(0), -Y(0), zt_(0)), (XR(0), -Y(0), zt_(0)),
               (XR(0), Y(0), zt_(0)), (XL(0), Y(0), zt_(0))]
    for i in range(4):
        p_, q_ = corners[i], corners[(i + 1) % 4]
        faces.append(_F(((p_[0], p_[1], p_[2] - 0.16), (q_[0], q_[1], q_[2] - 0.16),
                         (q_[0], q_[1], q_[2] + 0.02), (p_[0], p_[1], p_[2] + 0.02)),
                        kind, alpha=62))
        lines.append(((p_, q_), ACCENT, 1.6, None))

    # 戗脊：四条，从檐角沿角弧收向脊端
    for sgn, xe_init, x_ridge in ((1, XL, tx0), (-1, XR, tx1)):
        for ys in (-1, 1):
            hip = []
            for k in range(9):
                t = k / 8.0
                hip.append((xe_init(t), ys * Y(t), zt_(t) + 0.015))
            for k in range(len(hip) - 1):
                lines.append(((hip[k], hip[k + 1]), ACCENT, 1.4 if k < 4 else 1.0, None))

    # 正脊
    lines.append((((tx0, ty, tz), (tx1, ty, tz)), INK, 1.7, True))
    return faces, lines


def roof_xieshan(x0, x1, yh, eave_z, rx0, rx1, ridge_z, sh=0.48, bands=3, kind='accent'):
    """歇山：下半庑殿收到肩部，上半两坡夹山花（0.20 厚薄板）。"""
    _prev = _PART[0]; part('屋面')
    ys = yh * 0.48
    shz = eave_z + (ridge_z - eave_z) * sh
    faces, lines = roof_hip(x0, x1, yh, eave_z, rx0, rx1, ys, shz, bands=bands, kind=kind)
    for sgn in (-1, 1):
        y0 = ys * sgn
        faces.append(_F(((rx0, y0, shz), (rx1, y0, shz), (rx1, 0, ridge_z), (rx0, 0, ridge_z)),
                        kind, alpha=_ral(0, sgn)))
        nt = max(2, int((rx1 - rx0) / 0.36))
        for j in range(1, nt):
            xa = rx0 + (rx1 - rx0) * j / nt
            lines.append((((xa, y0, shz + 0.004), (xa, 0, ridge_z)), ACCENT_SOFT, 0.5, None))
    for gx2 in (rx0, rx1):
        gA, gB = gx2 - 0.10, gx2 + 0.10
        faces.append(_F(((gB, -ys, shz), (gB, ys, shz), (gB, 0, ridge_z)), 'mass', alpha=158))
        faces.append(_F(((gA, -ys, shz), (gA, ys, shz), (gA, 0, ridge_z)), 'mass', alpha=96))
        faces.append(_F(((gA, -ys, shz), (gB, -ys, shz), (gB, 0, ridge_z), (gA, 0, ridge_z)),
                        'mass', alpha=120))
        faces.append(_F(((gA, ys, shz), (gB, ys, shz), (gB, 0, ridge_z), (gA, 0, ridge_z)),
                        'mass', alpha=120))
        lines += brick_tri(gA - 0.01, ys, shz, ridge_z)
        lines.append((((gB, -ys, shz), (gB, 0, ridge_z)), INK, 1.2, True))
        lines.append((((gB, ys, shz), (gB, 0, ridge_z)), INK, 1.2, True))
        lines.append((((gB, -ys, shz), (gB, ys, shz)), INK, 1.0, True))
        # 博风板 + 悬鱼
        t = 0.20
        faces.append(_F(((gA, -ys, shz), (gB, -ys, shz), (gB, 0, ridge_z), (gA, 0, ridge_z)),
                        'body', alpha=210))
        lines.append((((gA, -ys, shz), (gA, 0, ridge_z)), ACCENT_DEEP, 2.6, True))
        lines.append((((gA, ys, shz), (gA, 0, ridge_z)), ACCENT_DEEP, 2.6, True))
        faces.append(_F(((gA - 0.02, -0.16, shz + 0.42), (gA - 0.02, 0.16, shz + 0.42),
                         (gA - 0.02, 0.0, shz + 0.10)), 'mass', alpha=210))
    lines.append((((rx0, 0, ridge_z), (rx1, 0, ridge_z)), INK, 1.5, True))
    return faces, lines


def roof_gable(x0, x1, yh, eave_z, ridge_z, bands=3, kind='accent'):
    """两坡顶（硬山/悬山共用）。"""
    _prev = _PART[0]; part('屋面')
    faces, lines = [], []
    rows = [i / bands for i in range(bands + 1)]
    for i in range(bands):
        t0, t1 = rows[i], rows[i + 1]
        y0, y1 = -yh * (1 - t0), -yh * (1 - t1)
        z0 = eave_z + (ridge_z - eave_z) * (t0 ** 1.12)
        z1 = eave_z + (ridge_z - eave_z) * (t1 ** 1.12)
        faces.append(_F(((x0, y0, z0), (x1, y0, z0), (x1, y1, z1), (x0, y1, z1)),
                        kind, alpha=_ral(0, 1)))
        faces.append(_F(((x0, -y0, z0), (x1, -y0, z0), (x1, -y1, z1), (x0, -y1, z1)),
                        kind, alpha=_ral(0, -1)))
        nt = max(2, int((x1 - x0) / 0.36))
        for j in range(1, nt):
            xa = x0 + (x1 - x0) * j / nt
            lines.append((((xa, -y0, z0 + 0.004), (xa, -y1, z1 + 0.004)), ACCENT_SOFT, 0.5, None))
            lines.append((((xa, y0, z0 + 0.004), (xa, y1, z1 + 0.004)), ACCENT_SOFT, 0.5, None))
    for gx in (x0, x1):
        faces.append(_F(((gx, -yh, eave_z), (gx, yh, eave_z), (gx, 0, ridge_z)), 'body'))
        lines.append((((gx, -yh, eave_z), (gx, 0, ridge_z)), INK, 1.0, True))
        lines.append((((gx, yh, eave_z), (gx, 0, ridge_z)), INK, 1.0, True))
    lines.append((((x0, 0, ridge_z), (x1, 0, ridge_z)), INK, 1.5, True))
    for cy in (-yh, yh):
        lines.append((((x0, cy, eave_z), (x1, cy, eave_z)), ACCENT, 1.4, None))
    return faces, lines


def roof_barrel(x0, x1, half, eave_z, rise, seg=8, kind='accent'):
    """卷棚：筒瓦两坡（无正脊）。"""
    _prev = _PART[0]; part('屋面')
    faces, lines = [], []
    for i in range(seg):
        t0, t1 = i / seg, (i + 1) / seg
        a0, a1 = -half + 2 * half * t0, -half + 2 * half * t1
        z0 = eave_z + rise * (1 - (abs(a0) / half) ** 2)
        z1 = eave_z + rise * (1 - (abs(a1) / half) ** 2)
        faces.append(_F(((x0, a0, z0), (x1, a0, z0), (x1, a1, z1), (x0, a1, z1)),
                        kind, alpha=_ral(0, 1 if a0 < 0 else -1)))
        nt = max(2, int((x1 - x0) / 0.36))
        for j in range(1, nt):
            xa = x0 + (x1 - x0) * j / nt
            lines.append((((xa, a0, z0 + 0.004), (xa, a1, z1 + 0.004)), ACCENT_SOFT, 0.55, None))
    for xx in (x0, x1):
        prof = [(xx, -half + 2 * half * i / seg,
                 eave_z + rise * (1 - (abs(-half + 2 * half * i / seg) / half) ** 2))
                for i in range(seg + 1)]
        for i in range(seg):
            lines.append(((prof[i], prof[i + 1]), ACCENT, 1.3, None))
    return faces, lines


def ridge_box(x0, x1, z, h=0.30, chiwen=True, kind='body', orn=None):
    """正脊 + 脊饰。orn: none|chiwei(唐,鱼尾内卷)|chiwen(宋,兽头吞脊)|zhengwen(明清,带剑把)"""
    _prev = _PART[0]; part('正脊')
    if orn is None:
        orn = 'chiwei' if chiwen else 'none'
    out = box(x0, -0.11, z, x1, 0.11, z + h, kind)
    if orn == 'none':
        return out
    H = h * 3.1 if orn != 'zhengwen' else h * 2.6
    for rx, sgn in ((x0, -1.0), (x1, 1.0)):
        if orn == 'chiwei':      # 唐：鱼尾形，尾尖向内卷，无兽头
            prof = [(0.00, 0.00), (0.30, 0.14), (0.46, 0.46), (0.44, 0.80),
                    (0.26, 1.00), (0.04, 0.94), (-0.10, 0.72), (-0.12, 0.34)]
        elif orn == 'chiwen':    # 宋元：兽头张口吞脊，尾仍上卷、比头短
            prof = [(0.00, 0.00), (0.05, 0.30), (0.02, 0.48), (0.16, 0.52),
                    (0.34, 0.44), (0.44, 0.62), (0.36, 0.84), (0.16, 0.92),
                    (-0.02, 0.76), (-0.08, 0.40)]
        else:                    # 明清：龙形正吻，尾外卷、背上剑把
            prof = [(0.00, 0.00), (0.18, 0.10), (0.34, 0.26), (0.40, 0.52),
                    (0.34, 0.74), (0.20, 0.86), (0.04, 0.80), (-0.06, 0.56),
                    (-0.04, 0.24)]
        xa, xb = rx - 0.065, rx + 0.065
        pts = [(sgn * yy, z + h * 0.30 + zz * H) for yy, zz in prof]
        out.append(_F(tuple((xa, py, pz) for py, pz in pts), kind))
        out.append(_F(tuple((xb, py, pz) for py, pz in reversed(pts)), kind))
        for i in range(len(pts)):
            a2, b2 = pts[i], pts[(i + 1) % len(pts)]
            out.append(_F(((xa, a2[0], a2[1]), (xb, a2[0], a2[1]),
                           (xb, b2[0], b2[1]), (xa, b2[0], b2[1])), kind))
        if orn == 'zhengwen':    # 剑把
            out += box(rx - 0.03, sgn * 0.02 - 0.02, z + h * 0.30 + H * 0.66,
                       rx + 0.03, sgn * 0.02 + 0.02, z + h * 0.30 + H * 1.06, kind)
    _PART[0] = _prev
    return out


def finial(cx, cy, z, scale=1.0, kind='body'):
    """宝顶：座 + 钵 + 相轮 + 宝珠。"""
    _prev = _PART[0]; part('宝顶')
    s = scale
    out = box(cx - 0.30 * s, cy - 0.30 * s, z, cx + 0.30 * s, cy + 0.30 * s, z + 0.18 * s, kind)
    out += prism(cx, cy, 0.26 * s, z + 0.18 * s, z + 0.52 * s, n=14, r_top=0.13 * s, kind=kind)
    out += prism(cx, cy, 0.10 * s, z + 0.52 * s, z + 0.92 * s, n=12, kind=kind)
    out += prism(cx, cy, 0.13 * s, z + 0.92 * s, z + 1.06 * s, n=12, r_top=0.02 * s, kind=kind)
    _PART[0] = _prev
    return out


# ------------------------------------------------------------------ 透明绘制

def _tri_fill(buf, a, b, c):
    """按重心坐标插值深度，写入半分辨率 z-buffer（大 = 近）。"""
    bh, bw = buf.shape
    minx = max(0, int(min(a[0], b[0], c[0])))
    maxx = min(bw - 1, int(max(a[0], b[0], c[0])) + 1)
    miny = max(0, int(min(a[1], b[1], c[1])))
    maxy = min(bh - 1, int(max(a[1], b[1], c[1])) + 1)
    if minx > maxx or miny > maxy:
        return
    (x1, y1, d1), (x2, y2, d2), (x3, y3, d3) = a, b, c
    den = (y2 - y3) * (x1 - x3) + (x3 - x2) * (y1 - y3)
    if abs(den) < 1e-9:
        return
    ys = np.arange(miny, maxy + 1)
    xs = np.arange(minx, maxx + 1)
    px, py = np.meshgrid(xs, ys)
    w1 = ((y2 - y3) * (px - x3) + (x3 - x2) * (py - y3)) / den
    w2 = ((y3 - y1) * (px - x3) + (x1 - x3) * (py - y3)) / den
    w3 = 1.0 - w1 - w2
    m = (w1 >= -1e-6) & (w2 >= -1e-6) & (w3 >= -1e-6)
    if not m.any():
        return
    d = w1 * d1 + w2 * d2 + w3 * d3
    sub = buf[miny:maxy + 1, minx:maxx + 1]
    np.maximum(sub, np.where(m, d, -1e9), out=sub)


def _zbuffer(faces, ax, bw, bh, sc):
    """半分辨率 z-buffer：逐三角形按顶点真实深度插值（大 = 近）。"""
    buf = np.full((bh, bw), -1e9, dtype=np.float32)
    for fac in faces:
        quad, kind, meta = _fs(fac)
        if kind == 'accent':
            continue                       # 屋面是玻璃罩，不参与遮挡
        pts2 = [ax.pt(p) for p in quad]
        pts3 = [(p[0] + p[1] + p[2]) for p in quad]
        n = len(pts2)
        trip = [[0, 1, 2]] if n == 3 else [[0, i, i + 1] for i in range(1, n - 1)]
        for t in trip:
            v = [(pts2[i][0] / sc, pts2[i][1] / sc, pts3[i]) for i in t]
            _tri_fill(buf, v[0], v[1], v[2])
    return buf


def _runs(a, b, ax, buf, sc, n=12, tol=0.10):
    """把三维线段切成可见/被遮连续段。"""
    pa, pb = a, b
    out, cur, state = [], [pa], None
    for i in range(1, n + 1):
        t = i / float(n)
        p = (pa[0] + (pb[0] - pa[0]) * t, pa[1] + (pb[1] - pa[1]) * t, pa[2] + (pb[2] - pa[2]) * t)
        sx, sy = ax.pt(p)
        d = p[0] + p[1] + p[2]
        ix, iy = int(sx / sc), int(sy / sc)
        bh, bw = buf.shape
        vis = True
        if 0 <= ix < bw and 0 <= iy < bh:
            vis = buf[iy, ix] <= d + tol
        if state is None:
            state = vis
        if vis != state:
            out.append((cur + [p], state))
            cur = [p]
            state = vis
        else:
            cur.append(p)
    out.append((cur, state))
    return out


def draw_model(cv, model, ax):
    """面 + 线同一条深度序列（远→近），线做逐段可见性判定。"""
    faces = model.get('faces', [])
    lines = model.get('lines', [])
    sc = 2.0
    bw, bh = max(16, cv.w // 2), max(16, cv.h // 2)
    buf = _zbuffer(faces, ax, bw, bh, sc)

    items = []
    for fac in faces:
        quad, kind, meta = _fs(fac)
        pts2 = [ax.pt(p) for p in quad]
        area = 0.0
        for i in range(len(pts2)):
            x0, y0 = pts2[i]
            x1, y1 = pts2[(i + 1) % len(pts2)]
            area += x0 * y1 - x1 * y0
        if abs(area * 0.5) < 0.8:
            continue
        depth = sum(p[0] + p[1] + p[2] for p in quad) / float(len(quad))
        items.append((depth, pts2, kind, meta))
        if meta.get('edge', 1) != 0.0:                 # 棱边（slim 柱身不描内缝）
            # 按面角色给默认线重：骨（body）/ 皮（mass、screen）/ 饰（accent）
            _dw = {'body': 1.30, 'mass': 0.88, 'screen': 0.80,
                   'accent': 0.70, 'fill': 0.70}.get(kind, 0.95)
            ew_ = meta.get('edge') or _dw
            for i2 in range(len(quad)):
                a3 = quad[i2]
                b3 = quad[(i2 + 1) % len(quad)]
                items.append((depth + 0.05, (a3, b3), 'line',
                              {'col': meta.get('edge_color', INK), 'w': ew_, 'key': None}))
    for e in lines:
        seg, col, w, key = _line_parts(e)
        depth = sum(p[0] + p[1] + p[2] for p in seg) / float(len(seg))
        items.append((depth + 0.06, seg, 'line', {'col': col, 'w': w, 'key': key}))
    items.sort(key=lambda t: t[0])

    for depth, pts2, kind, meta in items:
        if kind == 'line':
            _draw_seg(cv, pts2, ax, buf, sc, meta['col'], meta['w'], meta['key'])
            continue
        n = meta.get('n') or (0, 0, 1)
        if kind == 'body' and n[0] * VIEW[0] + n[1] * VIEW[1] + n[2] * VIEW[2] < -0.02:
            continue                        # 只对实心体做背面剔除；屋面/砖石/板片是玻璃罩，两面都画
        if kind == 'accent':
            col = ACCENT
            cv.poly(pts2, col, None, 0, meta.get('alpha', FILL_ACC))
        else:
            base = meta.get('fill') or {"body": _shade(n), "screen": SCREEN,
                                        "mass": MASS}.get(kind, BODY_SIDE)
            _al = meta.get('alpha', 150 if kind == 'mass' else FILL_BODY)   # 砖石要比木构实
            cv.poly(pts2, base, None, 0, _al)
        # 轮廓线：法向接近垂直视线 → 描边（柱身/体量侧面靠它成形）
        if abs(n[0] * VIEW[0] + n[1] * VIEW[1] + n[2] * VIEW[2]) < 0.26:
            cv.poly(pts2, None, INK, 0.95)


def _line_parts(e):
    """统一三种线写法：
       ((p0, p1, color, w), tag)        —— 贴面线（带平面 tag）
       ((p0, p1), color, w[, key])      —— 普通线
       (p0, p1, color, w[, key])        —— 扁平写法
    """
    if len(e) == 2 and isinstance(e[1], dict):
        seg = e[0]
        return (seg[0], seg[1]), seg[2], seg[3], None
    if isinstance(e[0], (tuple, list)) and len(e[0]) == 2 \
            and isinstance(e[0][0], (tuple, list)) and len(e[0][0]) == 3:
        return (e[0][0], e[0][1]), e[1], e[2], (e[3] if len(e) > 3 else None)
    return (e[0], e[1]), e[2], e[3], (e[4] if len(e) > 4 else None)


# 三档线重：骨（柱梁斗拱）/ 皮（墙面门窗台基）/ 饰（瓦垄脊饰门钉天花）
_TIER = ((1.20, 1.30), (0.95, 1.00), (0.75, 0.85), (0.60, 0.65), (0.0, 0.50))


def _tier_w(w):
    for lo, nw in _TIER:
        if w >= lo:
            return nw
    return w


def _draw_seg(cv, seg, ax, buf, sc, col, w, key):
    if key:
        cv.line([ax.pt(seg[0]), ax.pt(seg[1])], col, w)
        return
    w = _tier_w(w)
    for pts, vis in _runs(seg[0], seg[1], ax, buf, sc):
        if len(pts) < 2:
            continue
        p2 = [ax.pt(p) for p in pts]
        if vis:
            cv.line(p2, col, w)
        else:
            cv.dash(p2, INK4, max(0.6, w * 0.85), 3.4, 3.2, 128)


def draw_chain(cv, model, ax, f_small):
    """传力链：朱红粗线 + 节点圆 + 箭头。"""
    chain = list(model.get('chain') or [])
    axis = model.get('chainAxis')
    if axis:
        chain = [(axis[0], axis[1], q[2]) for q in chain]
    if len(chain) < 2:
        return
    pts = [ax.pt(p) for p in chain]
    cv.line(pts, ACCENT, 2.3, alpha=200)
    for (x, y) in pts:
        cv.ellipse(x, y, 6.0, 6.0, fill=PAPER)
        cv.ellipse(x, y, 4.2, 4.2, fill=ACCENT)
    (x0, y0), (x1, y1) = pts[-2], pts[-1]
    ang = math.atan2(y1 - y0, x1 - x0)
    for sgn in (-0.42, 0.42):
        cv.line([(x1, y1), (x1 - 15 * math.cos(ang - sgn), y1 - 15 * math.sin(ang - sgn))],
                ACCENT, 2.0)


def draw_callouts(cv, model, ax, f_name, f_num, x_col=118, row_h=52, top=None,
                  r_leg=21, r_mark=26, ts=1.0, marks_only=False):
    """图上编号标记（图例由 _legend_strip 画）。"""
    cals = list(model.get('callouts', []))
    for c in cals:
        pn = _part_of(c.get('label'))
        if pn:
            hit, vis = _vis_anchor(model, ax, cv.w, cv.h, pn, c['at'])
            if hit:
                c['_pxy'] = hit
            else:
                c['lead'] = True          # 该构件被完全遮住：标记外移 + 引线
    def _pp(c):
        if c.get('xy'):
            return [c['xy'][0] * cv.w, c['xy'][1] * cv.h]
        if c.get('_pxy'):
            return list(c['_pxy'])
        return list(ax.pt(c['at']))
    num_of = {id(c): i for i, c in enumerate(cals)}   # 编号按 callout 原始顺序，与图例一致
    cals.sort(key=lambda c: -_pp(c)[1])
    placed = [_pp(c) for c in cals]
    # 带引线的构件：把标记先拖到构件上方，再说避让
    for i, c in enumerate(cals):
        if c.get('lead'):
            px0, py0 = placed[i]
            cx0, cy0 = cv.w * 0.5, cv.h * 0.46
            dx, dy = px0 - cx0, py0 - cy0
            n = math.hypot(dx, dy) or 1.0
            placed[i][0] = px0 + dx / n * r_mark * 2.4
            placed[i][1] = py0 + dy / n * r_mark * 2.4
    rr = r_mark * 1.25      # 只做轻微避让：宁可挤一点，也不能离开构件
    for _ in range(60):
        moved = False
        for i in range(len(placed)):
            for j in range(i + 1, len(placed)):
                dx = placed[j][0] - placed[i][0]
                dy = placed[j][1] - placed[i][1]
                d = math.hypot(dx, dy)
                if d < rr:
                    if d < 1e-3:
                        dx, dy, d = 0.0, rr, rr
                    push = (rr - d) * 0.30
                    ux, uy = dx / d, dy / d
                    placed[j][0] += ux * push
                    placed[j][1] += uy * push
                    placed[i][0] -= ux * push
                    placed[i][1] -= uy * push
                    moved = True
        if not moved:
            break
    for idx, c in enumerate(cals, 1):
        sx, sy = placed[idx - 1]
        if c.get('_lead_to'):
            anchor = [c['_lead_to'][0] * cv.w, c['_lead_to'][1] * cv.h]
        elif c.get('xy'):
            anchor = [sx, sy]            # 人工指定坐标：徽标就压在构件上，不画引线
        else:
            anchor = list(c['_pxy']) if c.get('_pxy') else list(ax.pt(c['at']))
        if math.hypot(anchor[0]-sx, anchor[1]-sy) > r_mark * 1.15:   # 被避让挤开 → 画引线指回去
            ex, ey = anchor
            d = math.hypot(ex - sx, ey - sy)
            if d > 1e-3:
                ux, uy = (ex - sx) / d, (ey - sy) / d
                # 虚线引到构件，末端点一个小红点
                seg = 9
                n = int(max(1, (d - r_mark) / (seg * 1.7)))
                for k in range(n):
                    a = r_mark + k * seg * 1.7
                    b = min(d - 2, a + seg)
                    cv.line([(sx + ux * a, sy + uy * a), (sx + ux * b, sy + uy * b)], INK3, 0.9)
                cv.ellipse(ex, ey, 3.4, 3.4, fill=ACCENT)
        cv.ellipse(sx, sy, r_mark, r_mark, fill=PAPER, outline=ACCENT, lw=1.7, alpha=238)
        cv.text(sx, sy + 2, '%02d' % (num_of[id(c)] + 1), f_num, ACCENT_DEEP, anchor='mm')
    return None





_PART_KEYS = (('桥面', '桥面'), ('栏板', '栏板望柱'), ('望柱', '栏板望柱'), ('桥台', '桥台'),
              ('台基', '台基'), ('踏跺', '台基'), ('踏道', '台基'), ('柱础', '柱础'),
              ('直棂窗', '门窗'), ('槛窗', '门窗'), ('支摘窗', '门窗'), ('漏窗', '门窗'),
              ('窗', '门窗'), ('板门', '门窗'), ('门', '门窗'),
              ('额枋', '额枋'), ('阑额', '额枋'), ('平板枋', '额枋'),
              ('斗拱', '斗拱'), ('铺作', '斗拱'),
              ('墙', '墙体'), ('金柱', '柱身'), ('角柱', '柱身'), ('檐柱', '柱身'), ('柱', '柱身'),
              ('屋面', '屋面'), ('四坡', '屋面'), ('翼角', '屋面'), ('正脊', '正脊'),
              ('鸱尾', '正脊'), ('梁架', '梁架'), ('檩', '梁架'), ('椽', '梁架'),
              ('宝顶', '宝顶'), ('栏杆', '栏杆'), ('拱券', '拱券'))


def _part_of(label):
    for k, v in _PART_KEYS:
        if k in (label or ''):
            return v
    return None


def _anchor_for(model, at):
    """把标注点落到该构件自身「最近且朝向相机的一个面」的形心。"""
    import math as _m
    best, bd = None, 1e9
    for fac in model.get('faces', []):
        quad, kind, meta = _fs(fac)
        pn = meta.get('part')
        if not pn:
            continue
        if pn not in (_PART_TARGET[0],):
            continue
        n = meta.get('n') or _norm(quad[0], quad[1], quad[2])
        if (n[0] + n[1] + n[2]) <= 0.10:      # 背对相机
            continue
        cx_ = sum(q[0] for q in quad) / len(quad)
        cy_ = sum(q[1] for q in quad) / len(quad)
        cz_ = sum(q[2] for q in quad) / len(quad)
        d = _m.dist((cx_, cy_, cz_), at)
        if d < bd:
            bd, best = d, (cx_, cy_, cz_)
    return best




def _id_map(model, ax, W, H, sc=0.3, include_accent=False):
    """按画家顺序把每个面画进 id 图：像素值 = 面序号+1，最终留下的是真正可见的面。"""
    from PIL import Image as _I, ImageDraw as _D
    w, h = max(32, int(W * sc)), max(32, int(H * sc))
    im = _I.new('I', (w, h), 0)
    dr = _D.Draw(im)
    order = []
    for idx, fac in enumerate(model.get('faces', [])):
        quad, kind, meta = _fs(fac)
        pts2 = [ax.pt(q) for q in quad]
        area = 0.0
        for i2 in range(len(pts2)):
            x0, y0 = pts2[i2]
            x1, y1 = pts2[(i2 + 1) % len(pts2)]
            area += x0 * y1 - x1 * y0
        if abs(area * 0.5) < 0.8:
            continue
        if kind == 'accent' and not include_accent:
            continue
        depth = sum(q[0] + q[1] + q[2] for q in quad) / float(len(quad))
        order.append((depth, idx, pts2, kind, meta))
    order.sort(key=lambda t: t[0])
    for depth, idx, pts2, kind, meta in order:
        n = meta.get('n')
        if kind == 'body' and n and (n[0] * VIEW[0] + n[1] * VIEW[1] + n[2] * VIEW[2]) < -0.02:
            continue
        dr.polygon([(x * sc, y * sc) for x, y in pts2], fill=idx + 1)
    return im, sc



def _vis_anchor(model, ax, W, H, part_name, at):
    """在该构件的面里找「确实露在最前」的位置：面内多点取样，取首个可见点。
    返回 ((x, y), visible)。"""
    im, sc = _id_map(model, ax, W, H, include_accent=True)
    px = im.load()
    w, h = im.size
    best, bd = None, 1e9
    for idx, fac in enumerate(model.get('faces', [])):
        quad, kind, meta = _fs(fac)
        if meta.get('part') != part_name:
            continue
        cx_ = sum(q[0] for q in quad) / len(quad)
        cy_ = sum(q[1] for q in quad) / len(quad)
        cz_ = sum(q[2] for q in quad) / len(quad)
        # 面内取样：中心 + 朝每个顶点收 45%
        pts = [(cx_, cy_, cz_)]
        for q in quad:
            pts.append((cx_ + (q[0] - cx_) * 0.45,
                        cy_ + (q[1] - cy_) * 0.45,
                        cz_ + (q[2] - cz_) * 0.45))
        for cand in pts:
            sx, sy = ax.pt(cand)
            ix, iy = int(sx * sc), int(sy * sc)
            if not (0 <= ix < w and 0 <= iy < h):
                continue
            if px[ix, iy] != idx + 1:      # 该点看到的是别的面 → 被挡
                continue
            d = math.dist(cand, at)
            if d < bd:
                bd, best = d, (sx, sy)
    if best is None:
        return None, False
    # 该构件露出的面积太小（基本被遮住）→ 也算「看不见」，改为外移标记
    cnt = 0
    ids = set()
    for i2, fac in enumerate(model.get('faces', [])):
        if _fs(fac)[2].get('part') == part_name:
            ids.add(i2 + 1)
    if ids:
        for yy in range(h):
            for xx in range(w):
                if px[xx, yy] in ids:
                    cnt += 1
                    if cnt >= 500:
                        break
            if cnt >= 500:
                break
    return (best, True) if cnt >= 500 else (None, False)

def _part_anchor(model, ax, W, H, part_name):
    """该构件在画面上真正可见像素的重心（逻辑坐标）；完全被挡则返回 None。"""
    im, sc = _id_map(model, ax, W, H)
    want = set()
    for idx, fac in enumerate(model.get('faces', [])):
        if _fs(fac)[2].get('part') == part_name:
            want.add(idx + 1)
    if not want:
        return None
    px = im.load()
    w, h = im.size
    xs = ys = n = 0
    for y in range(h):
        row = [px[x, y] for x in range(w)]
        for x, v in enumerate(row):
            if v in want:
                xs += x
                ys += y
                n += 1
    if n < 12:
        return None
    return (xs / float(n) / sc, ys / float(n) / sc, n)


def _snap_visible(model, p, reach=3.2):
    """把标记点吸附到「最近的、朝向相机的面」的形心，保证标在看得见的一面。"""
    import math as _m
    view = (1.0, 1.0, 1.0)
    best, bd = None, 1e9
    for fac in model.get('faces', []):
        quad = _fs(fac)[0]
        if len(quad) < 3:
            continue
        # 面法向（取前三点）
        ax_, ay_, az_ = quad[0]
        bx_, by_, bz_ = quad[1]
        cx_, cy_, cz_ = quad[2]
        u1 = (bx_ - ax_, by_ - ay_, bz_ - az_)
        u2 = (cx_ - ax_, cy_ - ay_, cz_ - az_)
        nx = u1[1] * u2[2] - u1[2] * u2[1]
        ny = u1[2] * u2[0] - u1[0] * u2[2]
        nz = u1[0] * u2[1] - u1[1] * u2[0]
        nl = _m.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
        if (nx + ny + nz) / nl <= 0.12:      # 背对相机
            continue
        cxm = sum(q[0] for q in quad) / len(quad)
        cym = sum(q[1] for q in quad) / len(quad)
        czm = sum(q[2] for q in quad) / len(quad)
        d = _m.dist((cxm, cym, czm), p)
        if d < bd:
            bd, best = d, (cxm, cym, czm)
    if best is not None and bd <= reach:
        return best
    return p

def truss_frame(xs, yh, z0, ridge_z, bw=0.15, kind='body', apex_of=None):
    """屋架：下弦 + 两斜撑 + 脊瓜柱（任意 x 位置的排架）。

    apex_of(x) 给该榀的脊高：庑殿两山面那两榀不到脊，要收到撒头面上；
    不给就一律到 ridge_z。
    """
    _prev = _PART[0]; part('梁架')
    out = []
    for x in xs:
        zt = ridge_z if apex_of is None else apex_of(x)
        out += _beam3((x, -yh, z0), (x, yh, z0), bw, kind)          # 下弦
        out += _beam3((x, -yh, z0), (x, 0, zt), bw, kind)            # 南斜撑
        out += _beam3((x, yh, z0), (x, 0, zt), bw, kind)             # 北斜撑
        out += _beam3((x, 0, z0), (x, 0, zt), bw * 0.8, kind)        # 脊瓜柱
    _PART[0] = _prev
    return out


def _edge_cols(pts, cps=2):
    """沿多边形每条边均布柱子（含两端，去重）。"""
    out = []
    n = len(pts)
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        m = max(1, cps - 1)
        for j in range(m):
            t = j / float(m)
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    seen, uniq = set(), []
    for q in out:
        key = (round(q[0], 3), round(q[1], 3))
        if key not in seen:
            seen.add(key)
            uniq.append(q)
    return uniq


def _poly_platform(pts, k=0.0, h=0.45, n=3):
    """多边形台基：外扩 k 的棱柱 + 每面砖缝。"""
    import math as _m
    npts = []
    cx = sum(q[0] for q in pts) / len(pts)
    cy = sum(q[1] for q in pts) / len(pts)
    for q in pts:
        dx, dy = q[0] - cx, q[1] - cy
        d = _m.hypot(dx, dy) or 1.0
        npts.append((q[0] + dx / d * k, q[1] + dy / d * k))
    f = extrude(npts, 0.0, h, 'mass')
    ln = []
    for i in range(len(npts)):
        a, b = npts[i], npts[(i + 1) % len(npts)]
        L = _m.hypot(b[0] - a[0], b[1] - a[1])
        ln += brick_quad((a[0], a[1], 0.0), (b[0] - a[0], b[1] - a[1], 0.0), (0.0, 0.0, h),
                         max(1, int(L / 0.62)), max(1, int(h / 0.20)))
    return f, ln


def build_ting(p):
    side = float(p.get('side', 4.2))
    n = int(p.get('sides', 4))
    eaves = int(p.get('eaves', 2))
    cps = int(p.get('col_per_side', 2))
    br = bool(p.get('brackets', True))
    fin = bool(p.get('finial', True))
    lat = bool(p.get('lattice', True))

    if n <= 4:
        half = side / 2.0
        ring = lambda r: _square(0, 0, r)
        eave_r = half + 0.96
    else:
        half = side / (2.0 * math.sin(math.pi / n))          # 外接圆半径
        ring = lambda r: poly_ring(r, n, rot=math.pi / 2)
        eave_r = half + 0.72

    f, ln, cal = [], [], []
    if n <= 4:
        f += platform(0, 0, half + 0.70, half + 0.70, 0.45, 3)
        ln += brick_box_sides(-half - 0.70, -half - 0.70, half + 0.70, half + 0.70, 0.0, 0.45)
    else:
        pf, pl = _poly_platform(ring(half + 0.70), 0.0, 0.45, 3)
        f += pf
        ln += pl
    cal.append({'at': (half + 0.95, -0.7, 0.34), 'label': '台基踏跺'})
    cal.append({'at': (0.9, -(half + 0.70), 0.26), 'label': '台明'})

    zt = 0.45 + (2.60 if eaves > 1 else 2.75)
    pts = _edge_cols(ring(half), cps)
    for (x, y) in pts:
        f += column(x, y, 0.45, zt)
    f += beam_ring(pts, zt, zt + 0.26, 0.10)
    cal.append({'at': (-half * 0.42, -half, zt + 0.13), 'label': '额枋'})
    if lat:
        pf, pl = lattice_panel(ring(half), zt - 0.30, zt, 0.24)
        f += pf
        ln += pl
        cal.append({'at': (half * 0.46, -half, zt - 0.16), 'label': '挂落'})

    z1 = zt + 0.26
    if br:
        f += bracket_set(_edge_cols(ring(half + 0.16), cps), z1, z1 + 0.44, proj=0.34)
        cal.append({'at': (-half * 0.52, -half - 0.16, z1 + 0.22), 'label': '斗拱'})
        z1 += 0.44
    z1 += 0.12                                                # 檩：屋面从斗拱顶之上起坡

    if eaves > 1:
        h2 = half * 0.60
        rf, rl = roof_ring(ring(eave_r), z1, ring(h2 + 0.20), z1 + 0.92, alpha=24)
        f += rf
        ln += rl
        cal.append({'at': (0, -eave_r * 0.92, z1 + 0.34), 'label': '下檐屋面'})
        zb = z1 + 0.92
        f += extrude(ring(h2 + 0.12), zb - 0.16, zb, 'body')          # 平坐楼板
        zc = zb + 2.05
        p2 = _edge_cols(ring(h2), cps)
        for (x, y) in p2:
            f += column(x, y, zb, zc)
        pf, pl = lattice_panel(ring(h2 - 0.06), zb + 0.30, zc - 0.16, 0.22)
        f += pf
        ln += pl
        f += beam_ring(p2, zc - 0.16, zc, 0.09)
        cal.append({'at': (-h2 * 0.5, -h2, zb + 1.0), 'label': '上层柱窗'})
        cal.append({'at': (0, -(h2 + 0.12), zb - 0.08), 'label': '平坐'})
        z1 = zc
        if br:
            f += bracket_set(_edge_cols(ring(h2 + 0.16), cps), z1, z1 + 0.42, proj=0.30)
            z1 += 0.42
        z1 += 0.10
        ur = h2 + 0.80
        apex = z1 + max(1.86, 0.82 * ur)
        rf, rl = roof_pyramid(ring(ur), z1, apex, lift=0.17 * ur, chu=0.07 * ur)
        f += rf
        ln += rl
        cal.append({'at': (-h2 * 0.4, -ur, z1 + 0.30), 'label': '上檐屋面'})
        top = apex
    else:
        apex = z1 + max(2.05, 0.78 * eave_r)
        rf, rl = roof_pyramid(ring(eave_r), z1, apex, lift=0.135 * eave_r, chu=0.060 * eave_r)
        f += rf
        ln += rl
        cal.append({'at': (0, -eave_r, z1 + 0.14), 'label': '屋面'})
        top = apex

    eh = eave_r if eaves == 1 else half * 0.60 + 0.80
    cal.append({'at': (-eh * 0.55, -eh, z1 + 0.34), 'label': '翼角起翘'})
    if fin:
        f += finial(0, 0, top - 0.05, 1.0)
        cal.append({'at': (0, 0, top + 0.30), 'label': '宝顶'})

    chain = [(0, 0, top + 0.55), (0, 0, top), (0, 0, z1), (0, 0, zt), (0, 0, 0.45), (0, 0, 0.0)]
    meta = {'span': eave_r * 2, 'height': top + 0.55, 'axis': (0.0, 0.0)}
    return {'faces': f, 'lines': ln, 'callouts': cal, 'chain': chain, 'chainAxis': (0.0, 0.0),
            'chainLabel': '荷载自上而下', 'meta': meta, 'chainAxis': (0.0, 0.0)}


# ------------------------------------------------------------------ 二、廊

def build_lang(p):
    bays = int(p.get('bays', 3))
    bay = float(p.get('bay', 2.6))
    depth = float(p.get('depth', 2.2))
    gap = float(p.get('gap', 0.0))
    hy = depth / 2.0
    L = bays * bay + (bays - 1) * 0 + (bays) * 0.0

    f, ln, cal = [], [], []
    x_end = bays * bay
    f += extrude([(-0.1, -hy - 0.55), (x_end + 0.1, -hy - 0.55),
                  (x_end + 0.1, hy + 0.55), (-0.1, hy + 0.55)], 0.0, 0.45)
    zt = 0.45 + 2.45
    xs = [i * bay for i in range(bays + 1)]
    for x in xs:
        for y in (-hy, hy):
            f += column(x, y, 0.45, zt)
    for y in (-hy, hy):
        f += beam_ring([(x, y) for x in xs], zt, zt + 0.24, 0.10)
    for x in (xs[0], xs[-1]):
        f += beam_ring([(x, -hy), (x, hy)], zt, zt + 0.24, 0.10)
    for x in xs[1:-1]:
        f += _plank(x, 0, 0, 1, hy * 2, 0.10, zt, zt + 0.24)     # 横枋
    # 坐凳楣子 / 倒挂楣子
    for i in range(bays):
        x0, x1 = xs[i], xs[i + 1]
        for y in (-hy, hy):
            pf, pl = lattice_panel([(x0, y), (x1, y)], 0.88, 1.24, 0.30)
            f += pf
            ln += pl
            pf2, pl2 = lattice_panel([(x0, y), (x1, y)], zt - 0.52, zt - 0.06, 0.30)
            f += pf2
            ln += pl2
    cal.append({'at': (0, -hy, 1.06), 'label': '坐凳楣子'})
    cal.append({'at': (0, -hy, zt - 0.30), 'label': '倒挂楣子'})
    cal.append({'at': (bay * 0.5, hy, 1.4), 'label': '柱列'})
    rf, rl = roof_barrel(-0.55, x_end + 0.55, hy + 0.50, zt + 0.24, 0.72, seg=10)
    f += rf
    ln += rl
    cal.append({'at': (bay * 1.2, 0, zt + 0.24 + 0.72), 'label': '卷棚顶'})
    cal.append({'at': (0, 0, 0.30), 'label': '台基'})
    chain = [(x_end * 0.5, 0, zt + 0.98), (x_end * 0.5, 0, zt), (x_end * 0.5, 0, 0.45), (x_end * 0.5, 0, 0.0)]
    meta = {'span': x_end + 1.1, 'height': zt + 1.1}
    return {'faces': f, 'lines': ln, 'callouts': cal, 'chain': chain, 'chainAxis': (0.0, 0.0),
            'chainLabel': '逐间传递', 'meta': meta}


def extrude_y(pts_xz, y0, y1, kind='body'):
    out = [[(p[0], y1, p[1]) for p in pts_xz],
           [(p[0], y0, p[1]) for p in reversed(pts_xz)]]
    n = len(pts_xz)
    for i in range(n):
        a, b = pts_xz[i], pts_xz[(i + 1) % n]
        out.append([(a[0], y0, a[1]), (b[0], y0, b[1]), (b[0], y1, b[1]), (a[0], y1, a[1])])
    return [_F(tuple(q), kind) for q in out]


def arch_ring(cx, cz, R, t, a0, y0, y1, segs=18, alpha=74, kind='accent'):
    """券脸石环：按券石分块做成一个个四边形（PIL 填不了带洞的多边形，
    旧写法 `extrude_y(outer+reversed(inner))` 的端面会被填成实心圆盘，把券洞糊住）。"""
    _prev = _PART[0]; part('拱券')
    faces, lines = [], []
    ang = [-a0 + 2.0 * a0 * j / segs for j in range(segs + 1)]
    def P(a, r, y):
        return (cx + r * math.sin(a), y, cz + r * math.cos(a))
    for j in range(segs):
        a1, a2 = ang[j], ang[j + 1]
        for yy in (y0, y1):
            faces.append(_F((P(a1, R, yy), P(a2, R, yy), P(a2, R + t, yy), P(a1, R + t, yy)),
                            kind, alpha=alpha, edge=1.1, edge_color=ACCENT))
        faces.append(_F((P(a1, R + t, y0), P(a2, R + t, y0), P(a2, R + t, y1), P(a1, R + t, y1)),
                        kind, alpha=int(alpha * 0.7)))
        faces.append(_F((P(a1, R, y0), P(a2, R, y0), P(a2, R, y1), P(a1, R, y1)),
                        kind, alpha=int(alpha * 0.55)))
        for yy in (y0, y1):
            lines.append(((P(a1, R, yy), P(a1, R + t, yy)), ACCENT, 1.0, True))
    for yy in (y0, y1):
        for rr in (R, R + t):
            pts = [P(a, rr, yy) for a in ang]
            for j in range(len(pts) - 1):
                lines.append(((pts[j], pts[j + 1]), ACCENT, 1.5 if rr == R else 1.2, True))
    return faces, lines


def poly_ring(r, n=8, cx=0.0, cy=0.0, rot=math.pi / 8):
    return [(cx + r * math.cos(rot + 2 * math.pi * i / n),
             cy + r * math.sin(rot + 2 * math.pi * i / n)) for i in range(n)]


def roof_ring(outer, z_out, inner, z_in, kind='accent', alpha=34):
    """腰檐：外圈檐口 → 内圈（收进并抬高）的环状坡。"""
    _prev = _PART[0]; part('屋面')
    faces, lines = [], []
    n = len(outer)
    for i in range(n):
        j = (i + 1) % n
        q = ((outer[i][0], outer[i][1], z_out), (outer[j][0], outer[j][1], z_out),
             (inner[j][0], inner[j][1], z_in), (inner[i][0], inner[i][1], z_in))
        ex_, ey_ = outer[j][0] - outer[i][0], outer[j][1] - outer[i][1]
        el_ = math.hypot(ex_, ey_) or 1.0
        faces.append(_F(q, kind, alpha=_ral(ey_ / el_, -ex_ / el_)))
        lines.append((((outer[i][0], outer[i][1], z_out), (outer[j][0], outer[j][1], z_out)),
                      ACCENT, 1.4, None))
        faces.append(_F(((outer[i][0], outer[i][1], z_out - 0.15),
                         (outer[j][0], outer[j][1], z_out - 0.15),
                         (outer[j][0], outer[j][1], z_out),
                         (outer[i][0], outer[i][1], z_out)), kind, alpha=52,
                        edge=0.6, edge_color=ACCENT_SOFT))
        lines.append((((outer[i][0], outer[i][1], z_out - 0.15),
                       (outer[j][0], outer[j][1], z_out - 0.15)), ACCENT, 1.3, None))

        # 瓦垄：沿檐口方向分条，从外檐口拉到内圈
        seg_len = math.hypot(outer[j][0] - outer[i][0], outer[j][1] - outer[i][1])
        nt = max(2, int(round(seg_len / 0.36)))
        for t in range(1, nt):
            u = t / nt
            p0 = (outer[i][0] + (outer[j][0] - outer[i][0]) * u,
                  outer[i][1] + (outer[j][1] - outer[i][1]) * u, z_out + 0.004)
            p1 = (inner[i][0] + (inner[j][0] - inner[i][0]) * u,
                  inner[i][1] + (inner[j][1] - inner[i][1]) * u, z_in + 0.004)
            lines.append(((p0, p1), ACCENT_MID, 0.6, None))
        # 板瓦横缝
        for fr in (0.62,):
            q0 = (outer[i][0] + (inner[i][0] - outer[i][0]) * fr,
                  outer[i][1] + (inner[i][1] - outer[i][1]) * fr, z_out + (z_in - z_out) * fr + 0.004)
            q1 = (outer[j][0] + (inner[j][0] - outer[j][0]) * fr,
                  outer[j][1] + (inner[j][1] - outer[j][1]) * fr, z_out + (z_in - z_out) * fr + 0.004)
            lines.append(((q0, q1), ACCENT_MID, 0.5, None))
    return faces, lines


# ------------------------------------------------------------------ 三、殿堂

def build_dian(p):
    style = p.get('style', 'xieshan')
    cb = str(p.get('components', {}).get('column_base', 'fupen'))
    bk = str(p.get('components', {}).get('bracket', 'jixin'))
    ro = str(p.get('components', {}).get('ridge_orn', 'chiwei'))
    sh = str(p.get('components', {}).get('column_shaft', 'round'))
    ab = str(p.get('components', {}).get('arch_beam', 'lan_e_pupai'))
    ss = str(p.get('components', {}).get('steps', 'chuídai'))
    win = str(p.get('components', {}).get('window', 'zhiling'))
    pb = str(p.get('components', {}).get('platform_base', 'plain'))
    rl = str(p.get('components', {}).get('railing', 'none'))
    bays = int(p.get('bays', 5))
    bay = float(p.get('bay', 3.6))
    dbays = int(p.get('depth_bays', 3))
    bayd = float(p.get('bayd', 3.1))
    br = bool(p.get('brackets', True))

    hw, hd = bays * bay / 2.0, dbays * bayd / 2.0
    xs = [-hw + 2 * hw * i / bays for i in range(bays + 1)]
    f, ln, cal = [], [], []
    ph = float(p.get('plat_h', 0.55))
    _po = float(p.get('plat_out', 0.75))
    if pb == 'xumizuo':
        b = ph / 5.0
        f += box(-(hw + _po), -(hd + _po), 0.0, hw + _po, hd + _po, b, 'mass')
        f += box(-(hw + _po) + 0.12, -(hd + _po) + 0.12, b, hw + _po - 0.12, hd + _po - 0.12, b * 2, 'mass')
        f += box(-(hw + _po) + 0.36, -(hd + _po) + 0.36, b * 2, hw + _po - 0.36, hd + _po - 0.36, b * 3, 'mass')
        f += box(-(hw + _po) + 0.12, -(hd + _po) + 0.12, b * 3, hw + _po - 0.12, hd + _po - 0.12, b * 4, 'mass')
        f += box(-(hw + _po), -(hd + _po), b * 4, hw + _po, hd + _po, ph, 'mass')
    else:
        f += platform(0, 0, hw + _po, hd + _po, ph, 5, step_style=ss)
    ln += brick_box_sides(-hw - _po, -hd - _po, hw + _po, hd + _po, 0.0, ph)
    cal.append({'at': (hw + 0.9, -1.0, ph * 0.6), 'label': '台基踏跺'})
    cal.append({'at': (xs[1], hd, ph + 0.14), 'label': '柱础（' + BASE_NAME.get(cb, '覆盆式') + '）', 'lead': True})

    colh = float(p.get('col_h', 4.10))
    zt = ph + colh
    xs = [-hw + 2 * hw * i / bays for i in range(bays + 1)]
    ring = [(-hw, -hd), (hw, -hd), (hw, hd), (-hw, hd)]
    for x in xs:
        for y in (-hd, hd):
            f += column(x, y, ph, zt, 0.16, base_type=cb, shaft=sh)
    for y in (-hd, hd):
        f += column(-hw, y, ph, zt, 0.16, base_type=cb, shaft=sh)
        f += column(hw, y, ph, zt, 0.16, base_type=cb, shaft=sh)
    _eh = float(p.get('efang_h', 0.32))
    f += efang_set(ring, zt, _eh, ab)
    wf, wl = wall_ring(ring, ph, zt, sill=0.52, step=0.30)
    f += wf
    ln += wl
    cal.append({'at': (0, hd, zt + 0.16), 'label': '额枋'})
    cal.append({'at': (-hw * 0.55, -hd, ph + 1.4),
                    'label': '墙体' + {'zhiling': '直棂窗', 'jian': '槛窗',
                                     'zhizhai': '支摘窗', 'lou': '漏窗'}.get(win, '槛窗')})

    # 当心间板门、两梢间直棂窗（正面 y=-hd 外贴一层）
    yf = hd + 0.03          # 相机在 (+x,+y) 侧，门要开在朝观察者的长边上
    ci = bays // 2
    dx0, dx1 = xs[ci] + 0.30, xs[ci + 1] - 0.30
    dz0, dz1 = ph + 0.10, zt - 0.45
    f.append(_F(((dx0, yf, dz0), (dx1, yf, dz0), (dx1, yf, dz1), (dx0, yf, dz1)),
                'mass', alpha=232, edge=1.2, edge_color=INK, fill=(126, 112, 104)))
    if str((p.get('components') or {}).get('door', 'plain')) == 'studs':
        for i in range(5):
            for j in range(5):
                sx = dx0 + (dx1 - dx0) * (0.16 + 0.17 * i)
                sz = dz0 + (dz1 - dz0) * (0.60 + 0.09 * j)
                ln.append((((sx - 0.045, yf + 0.02, sz), (sx + 0.045, yf + 0.02, sz)), INK3, 1.5, None))
                ln.append((((sx, yf + 0.02, sz - 0.045), (sx, yf + 0.02, sz + 0.045)), INK3, 1.5, None))
        cxd = (dx0 + dx1) / 2.0
        for rr2 in (0.10, 0.16):
            for k in range(13):
                ang = 3.14159 * 2 * k / 12.0
                ax1 = cxd + rr2 * __import__('math').cos(ang)
                az1 = (dz0 + dz1) / 2.0 + rr2 * __import__('math').sin(ang)
                if k == 0:
                    px, pz = ax1, az1
                    continue
                ln.append((((px, yf + 0.03, pz), (ax1, yf + 0.03, az1)), ACCENT_SOFT, 1.2, None))
                px, pz = ax1, az1
    part('门窗')
    for bx in (ci - 1, ci + 1):
        if 0 <= bx < bays:
            wx0, wx1 = xs[bx] + 0.45, xs[bx + 1] - 0.45
            wz0, wz1 = ph + 1.20, zt - 0.70
            f.append(_F(((wx0, yf, wz0), (wx1, yf, wz0), (wx1, yf, wz1), (wx0, yf, wz1)),
                        'mass', alpha=200, edge=0.9, edge_color=INK3, fill=(214, 208, 196)))
            if win == 'jian':
                zz = wz0 + (wz1 - wz0) * 0.35
                ln.append((((wx0, yf, zz), (wx1, yf, zz)), INK3, 1.1, None))
                ln.append((((wx0, yf, zz + (wz1 - zz) * 0.5), (wx1, yf, zz + (wz1 - zz) * 0.5)), INK3, 0.8, None))
                for k in range(1, 5):
                    xx = wx0 + (wx1 - wx0) * k / 5.0
                    ln.append((((xx, yf, zz), (xx, yf, wz1)), INK3, 0.8, None))
                    ln.append((((xx, yf, wz0), (xx, yf, zz)), INK3, 0.6, None))
            elif win == 'lou':
                for i in range(4):
                    for j in range(5):
                        x0 = wx0 + (wx1 - wx0) * i / 4.0
                        x1 = wx0 + (wx1 - wx0) * (i + 1) / 4.0
                        z0 = wz0 + (wz1 - wz0) * j / 5.0
                        z1b = wz0 + (wz1 - wz0) * (j + 1) / 5.0
                        cx0, cz0 = (x0 + x1) / 2.0, (z0 + z1b) / 2.0
                        for pa, pb in (((x0, z0), (cx0, z1b)), ((cx0, z1b), (x1, z0)),
                                       ((x0, z1b), (cx0, z0)), ((cx0, z0), (x1, z1b))):
                            ln.append((((pa[0], yf, pa[1]), (pb[0], yf, pb[1])), INK3, 0.7, None))
            elif win == 'zhizhai':
                zz = wz0 + (wz1 - wz0) * 0.55
                ln.append((((wx0, yf, zz), (wx1, yf, zz)), INK3, 1.3, None))
                for k in range(1, 4):
                    xx = wx0 + (wx1 - wx0) * k / 4.0
                    ln.append((((xx, yf, zz), (xx, yf, wz1)), INK3, 0.9, None))
                    ln.append((((xx, yf, wz0), (xx, yf, zz)), INK3, 0.6, None))
            else:
                for k in range(1, 9):
                    xx = wx0 + (wx1 - wx0) * k / 9.0
                    ln.append((((xx, yf, wz0 + 0.05), (xx, yf, wz1 - 0.05)), INK3, 0.8, None))

    if rl != 'none':
        f += railing([(-hw - _po + 0.18, -hd - _po + 0.18), (hw + _po - 0.18, -hd - _po + 0.18),
                      (hw + _po - 0.18, hd + _po - 0.18), (-hw - _po + 0.18, hd + _po - 0.18)],
                     ph, 0.78)
    z1 = zt + _eh
    ceil = str((p.get('components') or {}).get('ceiling', 'none'))
    if ceil != 'none':
        cz = zt - 0.28
        if ceil == 'jingkou':
            for i in range(bays + 1):
                xx = xs[0] + (xs[-1] - xs[0]) * i / float(bays)
                ln.append((((xx, -hd + 0.10, cz), (xx, hd - 0.10, cz)), INK3, 0.7, None))
            for j in range(4):
                yy = -hd + 0.10 + (2 * hd - 0.20) * (j + 0.5) / 4.0
                ln.append((((-hw + 0.10, yy, cz), (hw - 0.10, yy, cz)), INK3, 0.7, None))
            cal.append({'at': (0, -hd * 0.4, cz), 'label': '井口天花'})
        else:
            for k in range(4):
                rr3 = min(hw, hd) * (0.62 - 0.14 * k)
                pts = _square(0, 0, rr3)
                pts.append(pts[0])
                ln.append(([(x, y, cz + 0.06 * k) for x, y in pts], INK3, 0.7, None))
            cal.append({'at': (0, 0, cz + 0.30), 'label': '藻井'})
    if br:
        _ox = hw + _po + 0.30
        _oy = hd + _po + 0.30
        f += beam_ring([(-_ox, -_oy), (_ox, -_oy), (_ox, _oy), (-_ox, _oy)],
                       z1 - 0.34, z1 - 0.18, 0.11)
        mid = [(xs[i] + xs[i + 1]) / 2.0 for i in range(bays)]
        bpts = ([(x, -hd) for x in xs] + [(x, hd) for x in xs]
                + [(x, -hd) for x in mid] + [(x, hd) for x in mid]
                + [(-hw, 0), (hw, 0)])
        bh = float(p.get('bracket_h', 0.42)) * colh      # 唐式斗拱：柱高的 3-4 成
        f += bracket_set(bpts, z1, z1 + bh, proj=float(p.get('bracket_proj', 0.55)))
        cal.append({'at': (bay * 0.5, -hd, z1 + bh * 0.5), 'label': '斗拱（' + BRACKET_NAME.get(bk, '计心造') + '）'})
        z1 += bh

    # 金柱与梁架
    ihw, ihd = hw - bay, hd - bayd * 0.5
    ip = [(-ihw, -ihd), (ihw, -ihd), (ihw, ihd), (-ihw, ihd)]
    for (x, y) in ip:
        f += column(x, y, ph, z1, 0.17, base_type=cb, shaft=sh)
    cal.append({'at': (xs[1], hd, ph + colh * 0.55), 'label': '金柱'})

    ey = hd + float(p.get('eave_out', 0.18)) * bays * bay
    if style == 'barrel':                       # 卷棚：无正脊的圆脊
        ridge = z1 + hd * float(p.get('pitch', 0.52))
        rf, rl = roof_barrel(-hw - 0.55, hw + 0.55, ey, z1, ridge - z1, seg=10)
        f += rf
        ln += rl
        cal.append({'at': (hw * 0.3, -ey * 0.5, z1 + 0.45), 'label': '卷棚屋面'})
        rr = ridge
    elif style == 'luding':                     # 盝顶：四坡收到一圈，顶上平
        ridge = z1 + ey * float(p.get('pitch', 0.40))
        _rr = float(p.get('ridge_ratio', 0.30))
        rf, rl = roof_hip(-hw - 0.55, hw + 0.55, ey, z1, -hw * _rr, hw * _rr, 0.0, ridge, bands=3)
        f += rf
        ln += rl
        f += box(-hw * _rr, -hw * _rr * 0.42, ridge, hw * _rr, hw * _rr * 0.42, ridge + 0.10, 'accent')
        cal.append({'at': (hw * 0.3, -ey * 0.55, z1 + 0.5), 'label': '盝顶屋面'})
        cal.append({'at': (0, 0, ridge + 0.30), 'label': '平顶'})
        rr = ridge + 0.10
    elif style == 'yingshan':
        ridge = z1 + hd * float(p.get('pitch', 0.62))
        rf, rl = roof_gable(-hw, hw, ey, z1, ridge, bands=4)
        f += rf
        ln += rl
        f += ridge_box(-hw, hw, ridge, 0.26, orn=ro if p.get('chiwen', True) else 'none')
        cal.append({'at': (hw * 0.35, -ey * 0.5, z1 + 0.5), 'label': '两坡屋面'})
        cal.append({'at': (-hw, 0, ridge + 0.8), 'label': '正脊' + RIDGE_NAME.get(ro, '鸱尾')})
        # 博风板（沿山面两坡的斜边）+ 悬鱼（脊端小三角），悬山最典型的收头
        for sgn in (-1.0, 1.0):
            gx = sgn * hw
            for sgn2 in (-1.0, 1.0):
                ln.append((((gx, sgn2 * ey, z1), (gx, 0.0, ridge)), ACCENT, 2.0, True))
            tri = ((gx, -0.55, ridge - 0.55), (gx, 0.55, ridge - 0.55), (gx, 0.0, ridge - 0.12))
            f.append(_F(tri, 'accent', alpha=150))
        cal.append({'at': (hw, 0, ridge - 0.5), 'label': '博风板 · 悬鱼'})
        rr = ridge
    elif style == 'wudian':
        ridge = z1 + ey * float(p.get('pitch', 0.34))
        _rr = float(p.get('ridge_ratio', 0.55))
        rf, rl = roof_hip(-hw - 0.55, hw + 0.55, ey, z1, -hw * _rr, hw * _rr, 0.0, ridge, bands=4)
        f += rf
        ln += rl
        f += ridge_box(-hw * _rr, hw * _rr, ridge, float(p.get('ridge_h', 0.26)), orn=ro if p.get('chiwen', True) else 'none')
        cal.append({'at': (hw * 0.3, -ey * 0.55, z1 + 0.6), 'label': '四坡屋面'})
        cal.append({'at': (-hw, -ey, z1), 'label': '翼角'})
        cal.append({'at': (-hw * 0.92, 0, ridge + 0.42), 'label': '正脊' + RIDGE_NAME.get(ro, '鸱尾')})
        rr = ridge
    else:
        ridge = z1 + ey * float(p.get('pitch', 0.56))
        _ss = float(p.get('shoushan', 1.75))
        rf, rl = roof_xieshan(-hw - 0.55, hw + 0.55, ey, z1, -hw + _ss, hw - _ss, ridge, bands=3)
        f += rf
        ln += rl
        f += ridge_box(-hw + _ss, hw - _ss, ridge, float(p.get('ridge_h', 0.26)), orn=ro if p.get('chiwen', True) else 'none')
        cal.append({'at': (hw * 0.32, -ey * 0.5, z1 + 0.55), 'label': '歇山屋面'})
        cal.append({'at': (hw - 1.75, 0, z1 + 1.4), 'label': '山花'})
        rr = ridge

    if int(p.get('eaves', 1)) >= 2:             # 重檐：檐下再挑一圈腰檐
        zw = ph + (zt - ph) * 0.62
        rf2, rl2 = roof_ring(_square(0, 0, hw + _po + 0.55), zw,
                             _square(0, 0, hw + _po - 0.10), zw + 0.55, alpha=40)
        f += rf2
        ln += rl2
        cal.append({'at': (hw + _po + 0.30, -hd * 0.5, zw), 'label': '腰檐'})

    # 屋架
    _tx = hw * 0.55
    _ey = ey

    def _apex(x):
        u = min(1.0, abs(x) / max(_tx, 1e-6))          # 0 在脊、1 在檐
        return rr - (rr - (z1 + _ey * 0.0)) * (u ** 1.65) * 0.0 - (rr - z1) * (u ** 1.65)
    if str(p.get('truss', 'tailiang')) == 'chuandou':
        for x in xs:
            f += column(x, 0.0, ph, rr - 0.15, 0.13, base_type='plain', shaft='round')
        for zz in (z1 + 0.35, rr - 0.55):
            f += beam_ring([(xs[0], -hd * 0.55), (xs[-1], -hd * 0.55)], zz, zz + 0.13, 0.10)
            f += beam_ring([(xs[0], hd * 0.55), (xs[-1], hd * 0.55)], zz, zz + 0.13, 0.10)
    else:
        f += truss_frame(xs, hd * 0.90, z1 - 1.05, rr, bw=0.15, apex_of=_apex)
    cal.append({'at': (xs[1] + (xs[2]-xs[1])*0.5, -hd * 0.42, z1 - 1.35), 'label': '梁架'})

    chain = [(0, 0, rr + 0.38), (0, 0, z1), (0, 0, zt + 0.16), (0, 0, 2.2), (0, 0, 0.55), (0, 0, 0.0)]
    meta = {'span': hw * 2 + 1.1, 'height': rr + 0.5}
    return {'faces': f, 'lines': ln, 'callouts': cal, 'chain': chain, 'chainAxis': (0.0, 0.0),
            'chainLabel': '屋架→斗拱→额枋→柱', 'meta': meta}


# ------------------------------------------------------------------ 四、楼阁

def build_lou(p):
    side = float(p.get('side', 7.0))
    floors = int(p.get('floors', 2))
    br = bool(p.get('brackets', True))
    half = side / 2.0

    f, ln, cal = [], [], []
    f += platform(0, 0, half + 0.85, half + 0.85, 0.55, 3)
    ln += brick_box_sides(-half - 0.85, -half - 0.85, half + 0.85, half + 0.85, 0.0, 0.55)
    cal.append({'at': (half + 1.0, -1.2, 0.35), 'label': '台基踏跺'})

    z = 0.55
    r = half
    for i in range(floors):
        zt = z + 2.55
        pts = _perimeter(r, max(2, int(p.get('col_per_side', 3))))
        for (x, y) in pts:
            f += column(x, y, z, zt, 0.15)
        f += beam_ring(pts, zt, zt + 0.28, 0.11)
        pf, pl = lattice_panel(pts, z + 0.55, zt - 0.10, 0.26)
        f += pf
        ln += pl
        if i == 0:
            cal.append({'at': (r, -r * 0.5, z + 1.5), 'label': '首层柱窗'})
        z1 = zt + 0.28
        if br:
            f += bracket_set(_perimeter(r + 0.26, max(2, int(p.get('col_per_side', 3)))),
                             z1, z1 + 0.44, proj=0.34)
            z1 += 0.44
        if i < floors - 1:
            # 腰檐 + 平坐
            out = _perimeter(r + 0.72, max(2, int(p.get('col_per_side', 3))))
            inn = _perimeter(r * 0.86, max(2, int(p.get('col_per_side', 3))))
            rf, rl = roof_ring(out, z1, inn, z1 + 0.62)
            f += rf
            ln += rl
            zp = z1 + 0.62
            f += box(-r * 0.86, -r * 0.86, zp - 0.20, r * 0.86, r * 0.86, zp)
            f += beam_ring(inn, zp, zp + 0.16, 0.10)
            if i == 0:
                cal.append({'at': (r + 0.5, -r * 0.4, z1 + 0.3), 'label': '腰檐'})
                cal.append({'at': (r * 0.9, r * 0.9, zp - 0.10), 'label': '平坐'})
            z = zp + 0.16
            r *= 0.82
        else:
            apex = z1 + 2.10
            rf, rl = roof_pyramid(_square(0, 0, r + 0.60), z1, apex, lift=0.30, chu=0.20)
            f += rf
            ln += rl
            f += finial(0, 0, apex - 0.05, 0.95)
            cal.append({'at': (r + 0.55, 0, z1 + 0.12), 'label': '顶檐屋面'})
            cal.append({'at': (0, 0, apex + 0.28), 'label': '宝顶'})
            top = apex
    chain = [(0, 0, top + 0.5), (0, 0, z1), (0, 0, z1 - 0.9), (0, 0, 0.55), (0, 0, 0.0)]
    meta = {'span': half * 2 + 1.9, 'height': top + 0.6}
    return {'faces': f, 'lines': ln, 'callouts': cal, 'chain': chain, 'chainAxis': (0.0, 0.0),
            'chainLabel': '层层上传', 'meta': meta}


# ------------------------------------------------------------------ 五、塔

def build_ta(p):
    style = p.get('style', 'louge')
    n = 8
    storeys = int(p.get('storeys', 5))
    r0 = float(p.get('radius', 4.2))

    f, ln, cal = [], [], []
    f += prism(0, 0, r0 * 1.22, 0.0, 0.85, n=n, kind='body')
    cal.append({'at': (r0 * 1.2, -r0 * 0.5, 0.4), 'label': '台基'})

    z = 0.85
    r = r0
    hstep = 2.35 if style == 'louge' else 1.30
    for i in range(storeys):
        zt = z + hstep
        body = prism(0, 0, r * 0.80, z, zt, n=n, kind='body')
        f += body
        pts = poly_ring(r * 0.80, n)
        part('门窗')
    # 门窗：每面一个内凹的板（门在下层、窗在上层），塔身才不是光筒
        rr = r * 0.80
        for j in range(n):
            a1 = math.pi / 8 + 2 * math.pi * j / n
            a2 = a1 + 2 * math.pi / n
            m1 = a1 + (a2 - a1) * 0.30
            m2 = a1 + (a2 - a1) * 0.70
            hz0, hz1 = z + hstep * 0.12, z + hstep * 0.78
            q = ((rr * math.cos(m1), rr * math.sin(m1), hz0),
                 (rr * math.cos(m2), rr * math.sin(m2), hz0),
                 (rr * math.cos(m2), rr * math.sin(m2), hz1),
                 (rr * math.cos(m1), rr * math.sin(m1), hz1))
            f.append(_F(q, 'screen', alpha=168))
            ln.append((((rr * math.cos(m1), rr * math.sin(m1), hz0),
                        (rr * math.cos(m2), rr * math.sin(m2), hz0)), INK3, 0.9, None))
            ln.append((((rr * math.cos(m1), rr * math.sin(m1), hz1),
                        (rr * math.cos(m2), rr * math.sin(m2), hz1)), INK3, 0.9, None))
            ln.append((((rr * math.cos(m1), rr * math.sin(m1), hz0),
                        (rr * math.cos(m1), rr * math.sin(m1), hz1)), INK3, 0.9, None))
            ln.append((((rr * math.cos(m2), rr * math.sin(m2), hz0),
                        (rr * math.cos(m2), rr * math.sin(m2), hz1)), INK3, 0.9, None))
        if style == 'louge':
            f += bracket_set(poly_ring(r * 0.80 + 0.02, n), zt - 0.02, zt + 0.20, proj=0.17)
            cal0 = zt + 0.30
        else:
            cal0 = zt
        # 腰檐：内圈贴塔身顶，外圈向外、向下垂 —— 檐是「挂」在塔身上的
        out = poly_ring(r * 0.80 + 0.66, n)
        inn = poly_ring(r * 0.80 + 0.02, n)
        drop = 0.78 if style == 'louge' else 0.50
        rf, rl = roof_ring(out, cal0 - drop, inn, cal0, alpha=40)
        f += rf
        ln += rl
        # 檐口封边
        zf = cal0 - drop
        for (x, y) in out:
            pass
        for i2 in range(n):
            a2, b2 = out[i2], out[(i2 + 1) % n]
            f.append(_F(((a2[0], a2[1], zf - 0.14), (b2[0], b2[1], zf - 0.14),
                         (b2[0], b2[1], zf), (a2[0], a2[1], zf)), 'accent', alpha=52,
                        edge=0.6, edge_color=ACCENT_SOFT))
        if i == 0:
            cal.append({'at': (r * 0.8, -r * 0.8, z + 1.2), 'label': '塔身'})
            cal.append({'at': (r * 0.8 + 0.55, -r * 0.30, zf + 0.20),
                        'label': '斗拱挑檐' if style == 'louge' else '密檐叠出'})
        z = cal0
        r *= 0.90 if style == 'louge' else 0.955

    # 塔刹
    f += prism(0, 0, r * 0.62, z, z + 0.28, n=n, kind='body')
    f += finial(0, 0, z + 0.24, 1.5)
    cal.append({'at': (0, 0, z + 1.1), 'label': '塔刹'})
    for (x, y) in poly_ring(r + 0.6, n):
        ln.append((((x, y, z), (0, 0, z + 1.0)), ACCENT_MID, 0.8, None))

    chain = [(0, 0, z + 1.4), (0, 0, z), (0, 0, z * 0.55), (0, 0, 0.85), (0, 0, 0.0)]
    meta = {'span': (r0 + 1.2) * 2, 'height': z + 1.6}
    return {'faces': f, 'lines': ln, 'callouts': cal, 'chain': chain, 'chainAxis': (0.0, 0.0),
            'chainLabel': '塔刹→塔身→台基', 'meta': meta}


# ------------------------------------------------------------------ 六、门

def build_men(p):
    style = p.get('style', 'chenglou')
    f, ln, cal = [], [], []

    if style == 'pailou':
        bays = int(p.get('bays', 3))
        bay = float(p.get('bay', 3.0))
        h = float(p.get('height', 6.2))
        xs = [(-bays / 2.0 + i) * bay for i in range(bays + 1)]
        f += extrude([(xs[0] - 0.7, -0.9), (xs[-1] + 0.7, -0.9),
                      (xs[-1] + 0.7, 0.9), (xs[0] - 0.7, 0.9)], 0.0, 0.40)
        for x in xs:
            f += column(x, 0, 0.40, h, 0.19, base=False)
            f += box(x - 0.32, -0.5, 0.40, x + 0.32, 0.5, 0.95)
            for y in (-0.34, 0.34):
                f += column(x, y, 2.9, 3.5, 0.09, base=False)
        for i in range(bays):
            x0, x1 = xs[i], xs[i + 1]
            f += _plank((x0 + x1) / 2, 0, 1, 0, abs(x1 - x0), 0.16, 3.55, 3.85)
            f += _plank((x0 + x1) / 2, 0, 1, 0, abs(x1 - x0), 0.14, 4.55, 4.80)
            rf, rl = roof_gable(x0 - 0.18, x1 + 0.18, 1.15, 4.95, 5.55, bands=2)
            f += rf
            ln += rl
        mid = (xs[bays // 2] + xs[bays // 2 + 1]) / 2
        rf, rl = roof_gable(xs[bays // 2] - 0.22, xs[bays // 2 + 1] + 0.22, 1.3, 5.62, 6.55, bands=2)
        f += rf
        ln += rl
        cal.append({'at': (xs[-1], 0, h - 0.4), 'label': '柱头'})
        cal.append({'at': (mid, 0.6, 3.7), 'label': '额枋'})
        cal.append({'at': (mid, 0.8, 6.1), 'label': '主楼屋帽'})
        cal.append({'at': (0, 0, 0.2), 'label': '夹杆石台基'})
        chain = [(mid, 0, 6.6), (mid, 0, 3.7), (mid, 0, 0.4), (mid, 0, 0.0)]
        meta = {'span': abs(xs[-1] - xs[0]) + 2.0, 'height': 7.0}
        return {'faces': f, 'lines': ln, 'callouts': cal, 'chain': chain, 'chainAxis': (0.0, 0.0),
                'chainLabel': '额枋→夹杆石', 'meta': meta}

    # 城门楼：城台 + 拱门 + 城楼
    HW, HD, H = 16.0, 7.0, 8.2
    ow = 3.0
    f += box(-HW, -HD, 0.0, -ow, HD, H, 'mass')
    f += box(ow, -HD, 0.0, HW, HD, H, 'mass')
    f += box(-ow, -HD, 6.0, ow, HD, H, 'mass')
    # 城台贴青灰砖缝：券门两侧各一整片，端头两面，门券以上一条
    wL = HW - ow
    nvT = int(round(H / 0.20))
    for yy in (-HD, HD):
        ln += brick_quad((-HW, yy, 0.0), (wL, 0.0, 0.0), (0.0, 0.0, H), wL, H)
        ln += brick_quad((ow, yy, 0.0), (wL, 0.0, 0.0), (0.0, 0.0, H), wL, H)
        ln += brick_quad((-ow, yy, 6.0), (2 * ow, 0.0, 0.0), (0.0, 0.0, H - 6.0),
                         2 * ow, H - 6.0)
    for xx in (-HW, HW):
        ln += brick_quad((xx, -HD, 0.0), (0.0, 2 * HD, 0.0), (0.0, 0.0, H), 2 * HD, H)
    for yy in (-HD, HD):
        R, t = ow, 0.55
        arc = []
        for k in range(19):
            a = math.pi * k / 18
            arc.append((R * math.cos(a), 5.35 + R * math.sin(a)))
        outer = [((R + t) * math.cos(math.pi * k / 18), 5.35 + (R + t) * math.sin(math.pi * k / 18))
                 for k in range(19)]
        af, al = arch_ring(0.0, 5.35, R, 0.55, math.pi / 2.0, yy - 0.18, yy + 0.18,
                           segs=18, alpha=78)
        f += af
        ln += al
        ln.append(((( -R, yy, 5.35), (R, yy, 5.35)), ACCENT, 1.6, None))
    cal.append({'at': (HW - 1.0, -HD, 4.0), 'label': '城台'})
    cal.append({'at': (ow + 0.1, -HD, 5.0), 'label': '券门'})

    # 城楼（五间歇山）
    z0 = H
    hw2, hd2 = 9.0, 4.4
    f += box(-hw2 - 0.6, -hd2 - 0.6, z0, hw2 + 0.6, hd2 + 0.6, z0 + 0.22)
    xs = [-hw2 + 2 * hw2 * i / 5 for i in range(6)]
    zt = z0 + 3.0
    for x in xs:
        for y in (-hd2, hd2):
            f += column(x, y, z0 + 0.22, zt, 0.15)
    f += beam_ring([(-hw2, -hd2), (hw2, -hd2), (hw2, hd2), (-hw2, hd2)], zt, zt + 0.28, 0.11)
    f += bracket_set([(x, -hd2) for x in xs] + [(x, hd2) for x in xs], zt + 0.28, zt + 0.66, proj=0.34)
    cal.append({'at': (0, -hd2, zt + 0.20), 'label': '城楼斗拱'})
    ridge = zt + 0.66 + hd2 * 1.20
    rf, rl = roof_xieshan(-hw2 - 0.5, hw2 + 0.5, hd2 + 0.62, zt + 0.66,
                          -hw2 + 1.5, hw2 - 1.5, ridge, bands=3)
    f += rf
    ln += rl
    f += ridge_box(-hw2 + 1.55, hw2 - 1.55, ridge, 0.24, chiwen=True)
    cal.append({'at': (0, -hd2 - 0.6, zt + 1.0), 'label': '城楼屋面'})

    chain = [(0, 0, ridge + 0.4), (0, 0, zt), (0, 0, z0), (0, 0, 3.0), (0, 0, 0.0)]
    meta = {'span': HW * 2 + 1.0, 'height': ridge + 0.6}
    return {'faces': f, 'lines': ln, 'callouts': cal, 'chain': chain, 'chainAxis': (0.0, 0.0),
            'chainLabel': '屋面→城楼→城台', 'meta': meta}


# ------------------------------------------------------------------ 七、桥

def build_qiao(p):
    span = float(p.get('span', 14.0))
    rise = float(p.get('rise', 1.15))
    width = float(p.get('width', 4.6))
    n = int(p.get('arches', 1))
    f, ln, cal = [], [], []

    W = width / 2.0
    segs = 16
    deck = []
    for i in range(segs + 1):
        x = -span / 2 + span * i / segs
        u = 2 * x / span
        deck.append((x, (rise + 1.20) * (1 - u * u) ** 1.0))

    f += box(-span / 2 - 1.2, -W - 0.4, 0.0, span / 2 + 1.2, W + 0.4, 0.55, 'mass')   # 桥台

    # 券洞参数先算出来：侧墙要按「拱背」留洞，否则会糊住券洞
    base = 0.55
    arches = []
    for k in range(n):
        cx = -span / 2 + span * (k + 0.5) / n
        hspan = span / (2.0 * n)
        R = (hspan ** 2 + rise ** 2) / (2.0 * rise)
        cz = base + rise - R
        arches.append((cx, hspan, R, cz))

    def _wall_bottom(x):
        for (cx, hspan, R, cz) in arches:
            dx = x - cx
            if abs(dx) <= hspan:
                rz = (R + 0.46) ** 2 - dx ** 2
                return cz + math.sqrt(max(0.0, rz))
        return base

    for i in range(segs):
        x0, z0 = deck[i]
        x1, z1 = deck[i + 1]
        f.append(_F(((x0, -W, z0), (x1, -W, z1), (x1, W, z1), (x0, W, z0)), 'mass', alpha=126))
        for yy in (-W, W):
            f.append(_F(((x0, yy, _wall_bottom(x0)), (x1, yy, _wall_bottom(x1)),
                         (x1, yy, z1 - 0.38), (x0, yy, z0 - 0.38)), 'mass'))
        f.append(_F(((x0, -W, z0 - 0.42), (x0, W, z0 - 0.42), (x1, W, z1 - 0.42), (x1, -W, z1 - 0.42)), 'body'))
        for yy in (-W, W):
            f.append(_F(((x0, yy, z0 - 0.42), (x1, yy, z1 - 0.42), (x1, yy, z1), (x0, yy, z0)), 'body'))

    # 拱券：弓形券，起拱点落在两端桥台上，券顶贴着桥面底
    for k in range(n):
        cx, hspan, R, cz = arches[k]
        a0 = math.asin(min(1.0, hspan / R))
        outer, inner = [], []
        for j in range(21):
            a = -a0 + 2.0 * a0 * j / 20.0
            outer.append((cx + (R + 0.46) * math.sin(a), cz + (R + 0.46) * math.cos(a)))
            inner.append((cx + R * math.sin(a), cz + R * math.cos(a)))
        af, al = arch_ring(cx, cz, R, 0.46, a0, -W, W, segs=18, alpha=72)
        f += af
        ln += al
        for yy in (-W, W):
            ln.append((((cx - hspan, yy, base), (cx + hspan, yy, base)), ACCENT, 1.4, None))
            for j in range(0, 21, 2):                 # 券石：径向缝，从内弧拉到外弧
                a = -a0 + 2.0 * a0 * j / 20.0
                pi = (cx + R * math.sin(a), cz + R * math.cos(a))
                po = (cx + (R + 0.46) * math.sin(a), cz + (R + 0.46) * math.cos(a))
                ln.append((((pi[0], yy, pi[1]), (po[0], yy, po[1])), ACCENT, 1.0, None))
        for j in range(21):
            a = -a0 + 2.0 * a0 * j / 20.0
            px = cx + R * math.sin(a)
            pz = cz + R * math.cos(a)
            ln.append((((px, -W, pz), (px, W, pz)), ACCENT_SOFT, 0.7, None))
        # 券边线（沿弧）
        for j in range(20):
            a1 = -a0 + 2.0 * a0 * j / 20.0
            a2 = -a0 + 2.0 * a0 * (j + 1) / 20.0
            for yy in (-W, W):
                ln.append((((cx + R * math.sin(a1), yy, cz + R * math.cos(a1)),
                            (cx + R * math.sin(a2), yy, cz + R * math.cos(a2))), ACCENT, 1.4, None))

    # 栏板 + 望柱
    _pv = _PART[0]; part('栏板望柱')
    for yy in (-W, W):
        for i in range(segs):
            x0, z0 = deck[i]
            x1, z1 = deck[i + 1]
            f.append(_F(((x0, yy - 0.08, z0), (x1, yy - 0.08, z1),
                         (x1, yy + 0.08, z1), (x0, yy + 0.08, z0)), 'screen'))
            f.append(_F(((x0, yy - 0.08, z0 + 0.55), (x1, yy - 0.08, z1 + 0.55),
                         (x1, yy + 0.08, z1 + 0.55), (x0, yy + 0.08, z0 + 0.55)), 'screen'))
        for i in range(0, segs + 1, 2):
            x, z = deck[i]
            f += box(x - 0.10, yy - 0.11, z, x + 0.10, yy + 0.11, z + 0.78)

    cal.append({'at': (0, -W, rise + 0.35), 'label': '桥面'})
    cal.append({'at': (0, -W, 0.9), 'label': '拱券'})
    cal.append({'at': (span / 2 - 1.2, W, rise * 0.3), 'label': '栏板望柱'})
    cal.append({'at': (-span / 2 - 0.9, -W * 0.6, 0.3), 'label': '桥台'})
    chain = [(0, 0, rise + 0.6), (0, 0, 1.2), (0, 0, 0.4), (0, 0, 0.0)]
    meta = {'span': span + 2.4, 'height': rise + 1.4}
    return {'faces': f, 'lines': ln, 'callouts': cal, 'chain': chain, 'chainAxis': (0.0, 0.0),
            'chainLabel': '桥面→拱券→桥台', 'meta': meta}


def build_qiao5(p):
    """多孔石拱桥（默认五孔：一中孔 + 每侧两小孔，驼峰桥面）。"""
    L = float(p.get('span', 40.0))       # 全长
    width = float(p.get('width', 6.0))
    W = width / 2.0
    base = 0.0
    spr = 0.60                            # 起拱线高度
    ops = p.get('openings') or [[0.0, 0.33, 0.42], [0.235, 0.105, 0.50],
                                [-0.235, 0.105, 0.50], [0.390, 0.090, 0.46],
                                [-0.390, 0.090, 0.46]]
    arches = []
    for (cf, sf, hr) in ops:
        cx = cf * L
        s = sf * L
        h = hr * s
        R = ((s / 2.0) ** 2 + h ** 2) / (2.0 * h)
        cz = spr + h - R
        arches.append((cx, s / 2.0, R, cz, h))
    f, ln, cal = [], [], []

    # 驼峰桥面：贴着各孔拱背走（拱顶 +0.42），在墩上做「闭运算」保持连续
    N = 96
    xs = [-L / 2.0 + L * i / N for i in range(N + 1)]
    env = []
    for x in xs:
        e = 0.0
        for (cx, hspan, R, cz, h) in arches:
            dx = x - cx
            if abs(dx) <= hspan + 0.15:
                e = max(e, cz + math.sqrt(max(0.0, R * R - dx * dx)) + 0.78)
        env.append(e)
    win = max(4, N // 9)
    deck = []
    for i, x in enumerate(xs):
        lo, hi = max(0, i - win), min(N, i + win)
        deck.append((x, max(1.05, max(env[lo:hi + 1]))))
    # 收头：两端落到 1.05
    for i in range(N + 1):
        x, d = deck[i]
        edge = max(0.0, (abs(x) - 0.40 * L) / (0.08 * L))
        deck[i] = (x, d + (1.05 - d) * min(1.0, edge))

    def wall_bottom(x):
        for (cx, hspan, R, cz, h) in arches:
            dx = x - cx
            if abs(dx) <= hspan:
                return cz + math.sqrt(max(0.0, R * R - dx * dx))
        return spr

    # 桥台：两端实体，顶面与桥面收头齐平
    _pv = _PART[0]; part('桥台')
    f += box(-L / 2.0 - 2.2, -W - 1.3, base - 0.8, -L / 2.0 + 1.0, W + 1.3, 1.05, 'mass')
    f += box(L / 2.0 - 1.0, -W - 1.3, base - 0.8, L / 2.0 + 2.2, W + 1.3, 1.05, 'mass')
    _PART[0] = _pv

    # 侧墙（拱背以上到桥面），挨着每个开孔留洞
    segs = len(deck) - 1
    for i in range(segs):
        x0, d0 = deck[i]
        x1, d1 = deck[i + 1]
        for yy in (-W, W):
            b0, b1 = wall_bottom(x0), wall_bottom(x1)
            t0 = max(d0 - 0.34, b0 + 0.26)   # 拱顶附近保证墙身有厚度，避免四边形反转出缺口
            t1 = max(d1 - 0.34, b1 + 0.26)
            f.append(_F(((x0, yy, b0), (x1, yy, b1), (x1, yy, t1), (x0, yy, t0)), 'mass'))
        # 桥面板 + 檐口
        _pv = _PART[0]; part('桥面')
        f.append(_F(((x0, -W, d0 - 0.34), (x1, -W, d1 - 0.34),
                     (x1, W, d1 - 0.34), (x0, W, d0 - 0.34)), 'body'))
        for yy in (-W, W):
            f.append(_F(((x0, yy, d0 - 0.34), (x0, yy, d0), (x1, yy, d1), (x1, yy, d1 - 0.34)), 'body'))
        _PART[0] = _pv

    # 拱券（券脸石环 + 券石缝）
    for (cx, hspan, R, cz, h) in arches:
        a0 = math.asin(min(1.0, hspan / R))
        af, al = arch_ring(cx, cz, R, 0.42, a0, -W, W, segs=16, alpha=76)
        f += af
        ln += al
        for yy in (-W, W):
            for j in range(0, 17, 2):
                a = -a0 + 2.0 * a0 * j / 16.0
                pi = (cx + R * math.sin(a), yy, cz + R * math.cos(a))
                po = (cx + (R + 0.42) * math.sin(a), yy, cz + (R + 0.42) * math.cos(a))
                ln.append(((pi, po), ACCENT, 1.0, None))
            for j in range(16):
                a1 = -a0 + 2.0 * a0 * j / 16.0
                a2 = -a0 + 2.0 * a0 * (j + 1) / 16.0
                ln.append((((cx + (R + 0.42) * math.sin(a1), yy, cz + (R + 0.42) * math.cos(a1)),
                            (cx + (R + 0.42) * math.sin(a2), yy, cz + (R + 0.42) * math.cos(a2))),
                           ACCENT, 1.3, None))
        for j in range(0, 17, 2):
            a = -a0 + 2.0 * a0 * j / 16.0
            px = cx + R * math.sin(a)
            pz = cz + R * math.cos(a)
            ln.append((((px, -W, pz), (px, W, pz)), ACCENT_SOFT, 0.7, None))

    # 桥墩分水尖（迎水面做尖）
    pier_x = []
    for i in range(len(arches) - 1):
        pier_x.append((arches[i][0] + arches[i + 1][0]) / 2.0)
    for px in pier_x:
        for yy in (-W, W):
            ln.append((((px, yy, spr), (px, yy, spr - 0.5)), ACCENT_SOFT, 0.8, None))

    # 栏板 + 望柱
    for yy in (-W, W):
        for i in range(segs):
            x0, d0 = deck[i]
            x1, d1 = deck[i + 1]
            f.append(_F(((x0, yy - 0.07, d0), (x1, yy - 0.07, d1),
                         (x1, yy + 0.07, d1), (x0, yy + 0.07, d0)), 'screen'))
            f.append(_F(((x0, yy - 0.07, d0 + 0.62), (x1, yy - 0.07, d1 + 0.62),
                         (x1, yy + 0.07, d1 + 0.62), (x0, yy + 0.07, d0 + 0.62)), 'screen'))
        for i in range(0, segs + 1, 3):
            x, d = deck[i]
            f += box(x - 0.09, yy - 0.10, d, x + 0.09, yy + 0.10, d + 0.86)
    _PART[0] = _pv

    zc = max(d for _, d in deck)
    cal.append({'at': (0, -W, zc + 0.2), 'label': '桥面'})
    cal.append({'at': (0, -W, spr + 1.2), 'label': '拱券'})
    _i33 = min(len(deck) - 1, int((0.33 * L + L / 2.0) / L * N))
    cal.append({'at': (deck[_i33][0], W, deck[_i33][1] + 0.5), 'label': '栏板望柱'})
    cal.append({'at': (-L / 2.0 - 1.4, W * 0.5, spr * 0.6), 'label': '桥台'})
    chain = [(0, 0, zc + 0.3), (0, 0, spr + 1.0), (0, 0, spr - 0.3), (0, 0, base)]
    meta = {'span': L + 4.0, 'height': zc + 1.6}
    return {'faces': f, 'lines': ln, 'callouts': cal, 'chain': chain,
            'chainAxis': (0.0, 0.0), 'chainLabel': '桥面→拱券→桥台', 'meta': meta}


BUILDERS = {'ting': build_ting, 'lang': build_lang, 'dian': build_dian,
            'lou': build_lou, 'ta': build_ta, 'men': build_men, 'qiao': build_qiao, 'qiao5': build_qiao5}


# ------------------------------------------------------------------ 版式

RATIOS = {'3:4': (2400, 3200), '4:3': (2400, 1800), '1:1': (2400, 2400), '9:16': (2160, 3840)}


def _wrap(cv, text, font, maxw):
    """按像素宽度折行（中文无空格，逐字量）。最多两行，超出加省略号。"""
    lines, cur = [], ''
    for ch in text:
        if cv.dr.textlength(cur + ch, font=font) / S <= maxw:
            cur += ch
        else:
            lines.append(cur)
            cur = ch
            if len(lines) == 2:
                break
    if cur and len(lines) < 2:
        lines.append(cur)
    used = ''.join(lines)
    if len(used) < len(text) and lines:
        while lines and cv.dr.textlength(lines[-1] + '…', font=font) / S > maxw:
            lines[-1] = lines[-1][:-1]
        lines[-1] += '…'
    return lines


def _rect(cv, x0, y0, x1, y1, fill=None, alpha=255, outline=None, lw=1.0):
    cv.poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], fill, outline, lw, alpha)


def _photo_ar(path, lo=0.60, hi=2.00):
    """原图宽高比（横图保持横、竖图保持竖），只做温和夹紧，不裁切。"""
    try:
        im = Image.open(path)
        ar = im.width / float(im.height)
    except Exception:
        return 1.0
    return min(hi, max(lo, ar))


def _photo_card(cv, path, x1, y1, h):
    try:
        im = Image.open(path).convert('RGB')
    except Exception:
        return None
    ar = _photo_ar(path)
    w = int(h * ar)
    im = im.resize((int(w * S), int(h * S)), Image.LANCZOS)
    cv.img.paste(im, (int((x1 - w) * S), int((y1 - h) * S)))
    _rect(cv, x1 - w, y1 - h, x1, y1, None, 255, INK4, 1.0)
    return (x1 - w, y1 - h, x1, y1)


def _ts(W, H):
    """排版缩放：横向按宽、竖向按高，取几何平均，保证四种画幅比例一致。"""
    return max(0.62, ((W / 2400.0) ** 0.5) * ((H / 3200.0) ** 0.5))


ROLE_HINT = {'台基': '承重', '台明': '承重', '台基踏跺': '出入', '踏跺': '出入',
             '额枋': '联系', '斗拱': '传力', '柱': '承重', '金柱': '承重', '檐柱': '承重',
             '挂落': '装饰', '坐凳': '使用', '倒挂': '装饰', '墙面': '围护', '墙': '围护',
             '槛窗': '围护', '柱网': '承重', '梁架': '承重', '屋架': '承重', '平坐': '楼层',
             '腰檐': '屋面', '屋面': '屋面', '顶檐': '屋面', '棚顶': '屋面', '卷棚': '屋面',
             '塔身': '承重', '塔刹': '收头', '宝顶': '收头', '山花': '围护', '博风': '围护',
             '正脊': '收头', '吻兽': '收头', '城台': '承重', '券门': '出入', '拱券': '承重',
             '桥面': '通行', '桥台': '承重', '栏板': '围护', '望柱': '围护'}


def _role(label):
    for kk, vv in ROLE_HINT.items():
        if kk in label:
            return vv
    return ''


def _legend_strip(cv, cals, f_name, f_num, x0, y0, maxw, row_h, r_leg, ts, top=None,
                  f_hint=None):
    """横向图例：① 台基 ② 金柱 …… 一行排不下就换行。返回 (底边 y, 每项中心点)。"""
    gap = int(26 * ts)
    x, y = x0, y0
    centers = []
    for idx, c in enumerate(cals, 1):
        tw = cv.dr.textlength(c['label'], font=f_name) / S
        rl_ = _role(c['label'])
        if rl_ and f_hint is not None:
            tw += cv.dr.textlength(rl_, font=f_hint) / S + int(8 * ts)
        w = r_leg * 2 + int(10 * ts) + tw
        if x + w > x0 + maxw and x > x0:
            x = x0
            y += row_h
        cv.ellipse(x + r_leg, y, r_leg, r_leg, fill=PAPER, outline=ACCENT_MID, lw=1.4, alpha=255)
        cv.text(x + r_leg, y + 2, '%02d' % idx, f_num, ACCENT_DEEP, anchor='mm')
        cv.text(x + r_leg * 2 + int(10 * ts), y, c['label'], f_name, INK, anchor='lm')
        rl = _role(c['label'])
        if rl:
            lw_ = cv.dr.textlength(c['label'], font=f_name) / S
            cv.text(x + r_leg * 2 + int(10 * ts) + lw_ + int(8 * ts), y + int(2 * ts), rl,
                    f_hint or f_name, INK4, anchor='lm')
        centers.append((x + r_leg, y))
        x += w + gap
    return y + row_h * 0.5, centers


def _uv_bbox_focus(model, focus=None, zk=0.95):
    us, vs = [], []
    def keep(p):
        if not focus:
            return True
        for ax_, lo, hi in (('x', None, None),):
            pass
        if 'x' in focus and not (focus['x'][0] <= p[0] <= focus['x'][1]):
            return False
        if 'y' in focus and not (focus['y'][0] <= p[1] <= focus['y'][1]):
            return False
        if 'z' in focus and not (focus['z'][0] <= p[2] <= focus['z'][1]):
            return False
        return True
    for fac in model['faces']:
        for p in _fs(fac)[0]:
            if keep(p):
                u, v = _uv(p, zk)
                us.append(u); vs.append(v)
    for e in model.get('lines', []):
        for p in _line_parts(e)[0]:
            if keep(p):
                u, v = _uv(p, zk)
                us.append(u); vs.append(v)
    if not us:
        return _uv_bbox(model, zk)
    return (min(us), min(vs), max(us), max(vs))


def _dim_line(fam, p):
    """一句话尺寸注记（右下角）。"""
    try:
        if fam == 'ting':
            nn = int(p.get('sides', 4))
            name = {4: '方', 6: '六角', 8: '八角'}.get(nn, '%d 角' % nn)
            return '%s亭 边长 %g m' % (name, float(p.get('side', 4.2)))
        if fam == 'lang':
            return '%d 间 × %g m · 进深 %g m' % (int(p.get('bays', 3)),
                                                float(p.get('bay', 2.6)), float(p.get('depth', 2.2)))
        if fam == 'dian':
            return '面阔 %d 间 × %g m · 进深 %d 间 × %g m' % (
                int(p.get('bays', 5)), float(p.get('bay', 3.6)),
                int(p.get('depth_bays', 3)), float(p.get('bayd', 3.1)))
        if fam == 'lou':
            return '方 %g m · %d 层' % (float(p.get('side', 7.0)), int(p.get('floors', 2)))
        if fam == 'ta':
            return '八角 径 %g m · %d 层' % (float(p.get('radius', 4.2)) * 2,
                                          int(p.get('storeys', 5)))
        if fam == 'qiao':
            return '净跨 %g m · 矢高 %g m' % (float(p.get('span', 14)), float(p.get('rise', 1.15)))
        if fam == 'men':
            return '城台 %g × %g m' % (float(p.get('hw', 16)) * 2, float(p.get('hd', 7)) * 2)
    except Exception:
        pass
    return ''



def render_subject(job, W=2400, H=1800):
    """只画主体：无标题/图例/页脚。用于「照片在上、主体在下」的 4:3 版式。"""
    fam = job['family']
    par = job.get('params', {})
    model = BUILDERS[fam](par)
    cv = Canvas(W, H)
    ts = _ts(W, H)
    F = lambda sz: max(11, int(round(sz * ts)))
    f_num = font('num', F(30))
    mx = mr = int(60 * ts)
    my = int(52 * ts)
    x0, x1 = mx, W - mr
    y0, y1 = my, H - my
    umin, vmin, umax, vmax = _uv_bbox(model)
    bw, bh = max(1e-6, umax - umin), max(1e-6, vmax - vmin)
    k = min((x1 - x0) / bw, (y1 - y0) / bh)
    ox = x0 - k * umin + ((x1 - x0) - k * bw) * 0.5
    oy = y0 - k * vmin + ((y1 - y0) - k * bh) * 0.5 - max(0.0, ((y1 - y0) - k * bh) * 0.30)
    if job.get('view', 'axo') == 'front':
        ax = Axo(k=k, zk=1.0, ox=ox, oy=oy, c=1.0, s=0.0)
    else:
        ax = Axo(k=k, zk=float(job.get('z_ratio', 0.95)), ox=ox, oy=oy)
    draw_model(cv, model, ax)
    return cv


def _apply_xy(job, model):
    """人工指定的标注坐标（分数，0..1）优先于自动锚点。"""
    m = job.get('callout_xy') or {}
    for c in model.get('callouts', []):
        v = m.get(c.get('label'))
        if v:
            c['xy'] = (float(v[0]), float(v[1]))
            if len(v) >= 4:                 # 可选：再给一个「引线指到」的坐标
                c['_lead_to'] = (float(v[2]), float(v[3]))
            c.pop('lead', None)
            c.pop('_pxy', None)
    return model


def render(job):
    fam = job['family']
    if fam not in BUILDERS:
        raise SystemExit('family 未实现：%s（支持 %s）' % (fam, '/'.join(sorted(BUILDERS))))
    par = job.get('params', {})
    model = _apply_xy(job, BUILDERS[fam](par))
    W, H = RATIOS.get(job.get('ratio', '3:4'), RATIOS['3:4'])
    cv = Canvas(W, H)
    ts = _ts(W, H)

    F = lambda sz: max(11, int(round(sz * ts)))
    f_title = font('kai', F(124))
    f_sub = font('hei', F(62))
    f_desc = font('kai', F(48))
    f_name = font('hei', F(50))
    f_num = font('num', F(35))
    f_seal = font('kai', F(54))
    f_sig = font('num', F(32))
    f_note = font('hei', F(31))
    f_note_cn = font('hei', F(35))
    f_hint = font('hei', F(30))

    mx = int(128 * ts)
    mr = int(128 * ts)
    top = int(120 * ts)

    # ── 标题块几何（先算，再画模型，最后画字）────────────────
    desc_n = min(3, len(job.get('desc', [])))
    desc_bottom = top + int(168 * ts) + desc_n * int(62 * ts) - int(24 * ts)
    ph = int(min(max(H * 0.132, 250), 460))
    _par = _photo_ar(job['photo']) if job.get('photo') else 0.80
    pw = int(ph * _par)
    # 不压标题：按标题实际排字宽度收窄，等比缩高
    _ttw = cv.dr.textlength(job.get('title', ''), font=font('kai', F(124))) / S
    _stw = cv.dr.textlength(job.get('subtitle', ''), font=font('hei', F(62))) / S
    _title_right = mx + _ttw + int(26 * ts) + _stw + int(56 * ts)
    _pw_max = max(int(W * 0.16), W - mr - _title_right)
    if pw > _pw_max:
        pw = _pw_max
        ph = int(pw / _par)
    photo = None
    if job.get('photo'):
        py1 = top + int(6 * ts) + ph
        photo = (W - mr - pw, top + int(6 * ts), W - mr, py1)
        desc_bottom = max(desc_bottom, py1)
    rule_y = desc_bottom + int(30 * ts)

    # ── 画法图例（实线/虚线/朱红）：位置先算，擦完家具再画 ────
    conv_y = None
    conv_items = ((INK, 1.0, False, '可见轮廓'), (INK3, 0.9, True, '被遮构件'),
                  (ACCENT_MID, 0.7, False, '瓦垄/棂条'))
    rule_y = rule_y + int(10 * ts)

    # ── 横向图例 ─────────────────────────────────────────
    cals = list(model.get('callouts', []))
    maxlab = 0
    for c in cals:
        maxlab = max(maxlab, cv.dr.textlength(c['label'], font=f_name) / S)
    r_leg = int(24 * ts)
    row_h = int(78 * ts)
    # 图例改到图的下方：先只占位，等版心算完再画
    clabel = None
    leg_top_y = None

    # ── 版心：横向基本用满页宽 ────────────────────────────
    x0, x1 = mx, W - mr
    y0 = rule_y + int(30 * ts)
    sig = H - int(150 * ts)
    y1 = sig - int(470 * ts)
    leg_top_y = y1 + int(150 * ts)
    conv_y = leg_top_y + 2 * row_h + int(26 * ts)
    leg_bottom = leg_top_y + 2 * row_h
    chain_y = leg_bottom + int(30 * ts)
    if y1 - y0 < 400 * ts:
        y1 = H - int(200 * ts)

    # ── 取景：focus 框决定 k（可以不画全）──────────────────
    focus = job.get('zoom')
    umin, vmin, umax, vmax = _uv_bbox(model)
    bw_all, bh_all = max(1e-6, umax - umin), max(1e-6, vmax - vmin)
    bmin, bmin2, bmax, bmax2 = _uv_bbox_focus(model, focus)
    bw = max(1e-6, bmax - bmin)
    bh = max(1e-6, bmax2 - bmin2)
    k = min((x1 - x0) / bw, (y1 - y0) / bh)
    # 允许横向溢出（主体跑出页边），但不超过整幅宽度的 1.35 倍
    k = min(k, (W * 1.34) / bw_all, (y1 - y0) / bh * (1.0 if bh > 1e-3 else 1.0))
    ox = x0 - k * bmin + ((x1 - x0) - k * bw) * 0.5
    oy = y0 - k * bmin2 + ((y1 - y0) - k * bh) * 0.5 - max(0.0, ((y1 - y0) - k * bh) * 0.30)
    # 竖向不许跑出去：把整幅上下压回版心
    if k * bh_all <= (y1 - y0):
        pass
    else:
        oy = y0 - k * vmin + ((y1 - y0) - k * bh_all) * 0.5 - max(0.0, ((y1 - y0) - k * bh_all) * 0.30)
    vw = job.get('view', 'axo')
    if vw == 'front':
        _zk, _vc, _vs = 1.0, 1.0, 0.0
    else:
        _zk, _vc, _vs = float(job.get('z_ratio', 0.95)), 0.866, 0.5
    if vw == 'front':                      # 正立面：X=x、Y=−z，y 只参与深度排序
        ax = Axo(k=k, zk=1.0, ox=ox, oy=oy, c=1.0, s=0.0)
    else:
        ax = Axo(k=k, zk=float(job.get('z_ratio', 0.95)), ox=ox, oy=oy)

    # ── 模型先画（可以溢到页边），再擦掉家具区 ─────────────
    draw_model(cv, model, ax)
    _rect(cv, 0, 0, W, rule_y + 2, PAPER)
    _rect(cv, 0, sig - int(64 * ts), W, H, PAPER)

    # ── 标题块 ───────────────────────────────────────────
    _rect(cv, mx, top, mx + int(16 * ts), top + int(150 * ts), ACCENT)
    tx = mx + int(52 * ts)
    cv.text(tx, top + int(10 * ts), job.get('title', ''), f_title, INK)
    tw = cv.dr.textlength(job.get('title', ''), font=f_title) / S
    cv.text(tx + tw + int(16 * ts), top + int(64 * ts),
            job.get('subtitle', '· 构造关系轴测'), f_sub, INK2)
    yy = top + int(168 * ts)
    # 可用宽度：有照片卡时让到它的左边，避免文字压上去被裁
    avail = W - mr - tx
    if job.get('photo'):
        avail = (W - mr - int(ph * 0.8)) - tx - int(36 * ts)
    _comp = (job.get('params') or {}).get('components') or {}
    _w = str(_comp.get('window', 'zhiling'))
    _dlist = list(job.get('desc', [])[:3])
    if _w == 'jian':
        _dlist = [l.replace('直棂窗', '槛窗') for l in _dlist]
    elif _w == 'zhizhai':
        _dlist = [l.replace('直棂窗', '支摘窗') for l in _dlist]
    for raw in _dlist:
        for line in _wrap(cv, raw, f_desc, avail):
            cv.text(tx, yy, line, f_desc, INK2)
            yy += int(62 * ts)
    if job.get('photo'):
        _photo_card(cv, job['photo'], W - mr, top + int(6 * ts) + ph, ph)
    cv.line([(mx, rule_y), (W - mr, rule_y)], WIRE, 1.0)

    xx = mx
    for col, lw_, dash, label in conv_items:
        if dash:
            for seg in range(3):
                xa = xx + seg * int(20 * ts)
                cv.line([(xa, conv_y), (xa + int(11 * ts), conv_y)], col, lw_)
            xx += int(66 * ts)
        else:
            cv.line([(xx, conv_y), (xx + int(46 * ts), conv_y)], col, lw_)
            xx += int(56 * ts)
        cv.text(xx, conv_y, label, f_hint, INK3, anchor='lm')
        xx += cv.dr.textlength(label, font=f_hint) / S + int(34 * ts)

    # ── 图例与传力路径说明 ────────────────────────────────
    _legend_strip(cv, cals, f_name, f_num, mx, leg_top_y, W - mx - mr, row_h, r_leg, ts, f_hint=f_hint)
    if clabel:
        cv.line([(mx + int(11 * ts), chain_y - int(20 * ts)),
                 (mx + int(11 * ts), chain_y + int(34 * ts))], ACCENT, 2.2)
        cv.ellipse(mx + int(11 * ts), chain_y + int(34 * ts), int(4.6 * ts), int(4.6 * ts), fill=ACCENT)
        cv.text(mx + int(30 * ts), chain_y - int(30 * ts), '传力路径', f_name, ACCENT_DEEP)
        cv.text(mx + int(30 * ts), chain_y + int(20 * ts),
                clabel.replace('→', ' · '), f_note_cn, INK2)
        tr = job.get('trust') or {}
        if tr:
            meas = sum(1 for v in tr.values() if isinstance(v, dict) and v.get('source') == 'measured')
            est = len(tr) - meas
            note = '比例：%d 项实测 · %d 项按常规' % (meas, est)
            worst = max((v for v in tr.values() if isinstance(v, dict) and v.get('range')),
                        key=lambda v: (v['range'][1] / max(1e-6, v['value'])),
                        default=None)
            if worst:
                note += '（误差最大 %s，区间 %.2f–%.2f）' % (
                    [k for k, v in tr.items() if v is worst][0],
                    worst['range'][0], worst['range'][1])
            cv.text(mx + int(30 * ts), chain_y + int(58 * ts), note, f_note_cn, INK4)

    # ── 图上编号 ─────────────────────────────────────────
    if cals:
        draw_callouts(cv, model, ax, f_name, f_num, x_col=mx, top=leg_top_y,
                      r_leg=r_leg, r_mark=int(30 * ts), row_h=row_h, ts=ts,
                      marks_only=True)

    # ── 比例尺 / 方印 / 注记 ──────────────────────────────
    bl = min(int(540 * ts), (x1 - x0) * 0.32)
    nseg = 4
    bx, by = mx, sig + int(78 * ts)
    bh_ = max(6, int(8 * ts))
    for i in range(nseg):
        xx = bx + bl * i / nseg
        if i % 2 == 0:
            _rect(cv, xx, by, xx + bl / nseg, by + bh_, ACCENT)
        else:
            _rect(cv, xx, by, xx + bl / nseg, by + bh_, None, 255, ACCENT, 1.0)
    cv.text(bx, by + bh_ + int(10 * ts), '0', f_num, INK3)
    cv.text(bx + bl, by + bh_ + int(10 * ts), '2 m', f_num, INK3, anchor='ra')

    # 左下角：换成 march-aa 的「亭」标识（assets/brand/mark.png），字也随之放大
    seal = int(84 * ts)
    sy = sig + int(4 * ts)
    try:
        from PIL import Image as _Img
        _mk = _Img.open(str(__import__('pathlib').Path(__file__).resolve().parent.parent
                            / 'assets/brand/mark.png')).convert('RGBA')
        _mk = _mk.resize((seal, seal), _Img.LANCZOS)
        _S = cv.img.width / float(cv.w)
        _mk2 = _mk.resize((int(seal * _S), int(seal * _S)), _Img.LANCZOS)
        cv.img.paste(_mk2, (int((W - mr - seal) * _S), int(sy * _S)), _mk2)
    except Exception:
        _rect(cv, mx, sy, mx + seal, sy + seal, ACCENT)
        cv.text(mx + seal / 2, sy + seal / 2 - int(3 * ts),
                (job.get('sign') or '构')[0], f_seal, PAPER, anchor='mm')
    # 右下角：logo 组右对齐（图标在最右，两行文字在其左侧）
    f_brand = font('num', F(46))
    _R = W - mr
    _Rx = _R if not _dim_line(fam, par) else _R
    cv.text(_Rx - seal - int(20 * ts), sy + seal * 0.34,
            'march-aa', f_brand, INK, anchor='rm')
    cv.text(_Rx - seal - int(20 * ts), sy + seal * 0.76,
            '古建构造关系轴测 · structure view', font('hei', F(26)), INK3, anchor='rm')
    _dl = _dim_line(fam, par)
    _ty = sig + int(12 * ts)
    if _dl:
        cv.text(mx, _ty, _dl, f_note, INK3, anchor='lm')
        _ty += int(34 * ts)
    cv.text(mx, _ty, '东南向轴测 · 被遮构件降为浅虚线', f_note, INK4, anchor='lm')

    info = _qa(dict(x0=x0, y0=y0, x1=x1, y1=y1), (umin, vmin, umax, vmax),
               k, ox, oy, model, W, H, rule_y, photo, mx, maxlab, cv, f_name,
               focus_box=(bmin, bmin2, bmax, bmax2))
    return cv.finish(), info


def _qa(view, bbox, k, ox, oy, model, W, H, title_bottom, photo, lab_x, maxlab, cv, f_name,
        focus_box=None, zk=0.95, vc=0.866, vs=0.5):
    """几何判据：主体出界 / 撞标题 / 撞照片 / 构件名拥挤。"""
    warn = []
    ax = Axo(k=k, zk=zk, ox=ox, oy=oy, c=vc, s=vs)
    xs, ys = [], []
    for fac in model['faces']:
        for p in _fs(fac)[0]:
            sx, sy = ax.pt(p)
            xs.append(sx)
            ys.append(sy)
    left, right, top, bot = min(xs), max(xs), min(ys), max(ys)
    # 取景框（可以让整幅跑出页边，但取景框本身要落在版心内）
    if focus_box:
        fu0, fv0, fu1, fv1 = focus_box
        fx0, fy0 = ax.pt((0, 0, 0))
        pb = [(ox + k * fu0, oy + k * fv0), (ox + k * fu1, oy + k * fv1)]
        if pb[0][0] < 60 or pb[1][0] > W - 60:
            warn.append('取景框超出页边')
        if pb[0][1] < 60 or pb[1][1] > H - 60:
            warn.append('取景框超出页边')
    else:
        if left < 96 or right > W - 96 or top < 96 or bot > H - 96:
            warn.append('主体触及页边')
    if top < title_bottom - 6:
        warn.append('主体上缘压到标题块')
    if photo and left < photo[2] and right > photo[0] and top < photo[3] and bot > photo[1]:
        warn.append('主体与照片卡重叠')
    n_cal = len(model.get('callouts', []))
    if 330 + n_cal * 52 > H - 210:
        warn.append('图例超出下边界')
    state = 'OK' if not warn else 'WARN ' + ' / '.join(sorted(set(warn)))
    return '主体 %d–%d × %d–%d  %s' % (int(left), int(right), int(top), int(bot), state)


def main(argv=None):
    import argparse
    import json
    ap = argparse.ArgumentParser(description='古建构造关系轴测图（透明画法）')
    ap.add_argument('--json', required=True, help='形制 JSON')
    ap.add_argument('--out', required=True, help='输出 PNG')
    ap.add_argument('--subject', action='store_true',
                    help='只画主体（4:3，无标题/图例/页脚），用于照片+成图版式')
    ap.add_argument('--ratio', default=None, choices=sorted(RATIOS))
    args = ap.parse_args(argv)
    with open(args.json, encoding='utf-8') as fh:
        job = json.load(fh)
    if args.ratio:
        job['ratio'] = args.ratio
    if getattr(args, 'subject', False):
        cv = render_subject(job, 2400, 1800)
        cv.img.resize((2400, 1800), __import__('PIL.Image').Image.LANCZOS).save(args.out)
        print('saved: %s (2400×1800)  只画主体' % args.out)
        return
    img, info = render(job)
    img.save(args.out)
    print('saved: %s (%d×%d)  %s' % (args.out, img.size[0], img.size[1], info))


if __name__ == '__main__':
    main()
