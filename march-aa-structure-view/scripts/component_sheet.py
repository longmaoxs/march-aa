"""单件详图：一个构件一页，正立面 + 侧立面 并排，带引线编号与尺寸。

用法：
    python scripts/component_sheet.py --part dougong --out out/detail_dougong.png
    python scripts/component_sheet.py --part chiwen  --out out/detail_chiwen.png

坐标一律 mm，原点在「柱心线 × 柱头顶面」。比例靠 Sheet.k（px/mm）统一，
两个视图共用同一 k 和同一基线，读者可以直接横向比尺寸。
"""
import argparse
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import archdraw as A

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZH = os.path.join(ROOT, 'assets', 'components')

WOOD = (244, 238, 227)      # 看得见的木面
WOOD2 = (238, 231, 218)     # 次一级的面（出跳件）
CUT = A.INK                  # 剖到的断面

MU = 15.0                    # 1 分 = 15mm，栌斗 32 分 = 480mm


def F(n):
    return n * MU


# ── 斗拱 ────────────────────────────────────────────────────────────────
def _dougong_core(P, R, sh, back=False):
    """斗拱的层叠骨架：栌斗 → 栱 → 散斗 → 昂 → 令栱 → 耍头。"""
    # 栌斗 32×20 分，斗欹内凹
    sh.poly([P(-10, 0), P(10, 0), P(16, 12), P(16, 20), P(-16, 20), P(-16, 12)], fill=WOOD)

    # 泥道栱：62 分长，两端各一散斗
    sh.poly(R(-31, 20, 31, 35), fill=WOOD)
    for x in (-31, 22):
        sh.poly(R(x, 35, x + 9, 45), fill=WOOD2)

    # 华栱：向外 30 分，端头交互斗
    sh.poly(R(-10, 20, 50, 35), fill=WOOD2)
    sh.poly(R(44, 35, 56, 45), fill=WOOD)

    # 双下昂：25°，每跳 30 分，压在交互斗上
    def ang(z0, x0, x1, drop):
        return [P(x0, z0), P(x1, z0 + drop), P(x1, z0 + drop - 6), P(x0, z0 - 6)]

    sh.poly(ang(45, 50, 86, 17), fill=WOOD)
    sh.poly(ang(60, 52, 96, 17), fill=WOOD)

    # 令栱（72 分）+ 三散斗 + 耍头
    sh.poly(R(78, 60, 94, 74), fill=WOOD2)
    for x in (76, 86, 96):
        sh.poly(R(x, 74, x + 9, 84), fill=WOOD)
    sh.poly(R(90, 84, 108, 94), fill=WOOD2)


def draw_dougong_front(sh, cx, base, s=0.055):
    """正立面：柱头 + 斗拱 + 斜拱（45° 斜插，三圣殿的记号）。"""
    def P(x, z):
        return (cx + F(x) * s, base - F(z) * s)

    def R(x0, z0, x1, z1):
        return [P(x0, z0), P(x1, z0), P(x1, z1), P(x0, z1)]

    sh.cut(R(-11, -20, 11, 0))                       # 柱身剖切
    # 斜拱先画（在后面）：两条 45° 短臂，从栌斗口斜出
    for sg in (-1, 1):
        sh.poly([P(sg * 8, 20), P(sg * 34, 46), P(sg * 46, 38), P(sg * 20, 14)],
                fill=(236, 229, 216))
    _dougong_core(P, R, sh)
    return dict(top=94, left=-31, right=108)


def draw_dougong_side(sh, cx, base, s=0.055):
    """侧立面：沿出跳方向剖开，看昂的斜面与层叠次序。"""
    def P(x, z):
        return (cx + F(x) * s, base - F(z) * s)

    def R(x0, z0, x1, z1):
        return [P(x0, z0), P(x1, z0), P(x1, z1), P(x0, z1)]

    sh.cut(R(-10, -20, 10, 0))
    sh.poly([P(-10, 0), P(10, 0), P(16, 12), P(16, 20), P(-16, 20), P(-16, 12)], fill=WOOD)
    sh.poly(R(-12, 20, 12, 35), fill=WOOD)           # 泥道栱截面
    sh.poly(R(-8, 35, 34, 47), fill=WOOD2)           # 华栱（侧看一段）
    for (z0, x0, x1, drop) in ((47, 34, 70, 17), (62, 34, 82, 17)):
        sh.poly([P(x0, z0), P(x1, z0 + drop), P(x1, z0 + drop - 6), P(x0, z0 - 6)], fill=WOOD)
    sh.poly(R(64, 64, 82, 78), fill=WOOD2)           # 令栱截面
    sh.poly(R(80, 78, 100, 88), fill=WOOD2)          # 耍头

    sh.line(P(34, 47), P(76, 47), w=A.LW_FINE, col=A.INK3, dash=(3, 1.6))
    sh.text(P(56, 49)[0], P(56, 49)[1], '25°', 'num', 2.8, A.INK3, anchor='mb')
    return dict(top=88, left=-16, right=100)


# ── 页面 ────────────────────────────────────────────────────────────────
def page(spec, out, draw_front, draw_side, k_mm=1.0):
    sh = A.Sheet(210, 280)
    L, R = 18.0, 192.0
    sh.text(L, 20, spec['title'], 'kai', 9.0, A.INK, 'lm')
    sh.text(L, 27.5, spec['subtitle'], 'hei', 3.4, A.INK3, 'lm')
    sh.line((L, 32), (R, 32), w=A.LW_FINE, col=A.GREY)

    lead = spec['lead']
    x, y = L, 38.0
    for ch in lead:
        pass
    # 简单折行：每行 ~52 个汉字宽（按 3.2pt 估）
    line, lines = '', []
    for ch in lead:
        line += ch
        if len(line) >= 50:
            lines.append(line)
            line = ''
    if line:
        lines.append(line)
    for i, ln in enumerate(lines):
        sh.text(L, y + i * 5.4, ln, 'hei', 3.2, A.INK2, 'lm')
    y += len(lines) * 5.4 + 6

    # 两个视图：共用基线、同一比例
    base = 128.0
    cxf, cxs = 60.0, 150.0
    draw_front(sh, cxf, base)
    draw_side(sh, cxs, base)
    sh.axis((cxf, base - 4), (cxf, base - 24 - 78))
    sh.axis((cxs, base - 4), (cxs, base - 24 - 70))

    sh.text(cxf, base + 12, '正立面 · 出跳与斜拱', 'hei', 3.0, A.INK3, 'mm')
    sh.text(cxs, base + 12, '侧立面 · 昂的斜面', 'hei', 3.0, A.INK3, 'mm')

    # 引线编号（正立面）
    SC = 0.055
    leaders = [((cxf, base - 8 * MU * SC), (28, base + 16)),
               ((cxf - 22 * MU * SC, base - 27 * MU * SC), (28, base - 8)),
               ((cxf + 6 * MU * SC, base - 40 * MU * SC), (100, base - 26)),
               ((cxf + 50 * MU * SC, base - 55 * MU * SC), (108, base - 4)),
               ((cxf - 38 * MU * SC, base - 40 * MU * SC), (20, base - 30)),
               ((cxf + 88 * MU * SC, base - 70 * MU * SC), (112, base - 34)),
               ((cxf + 106 * MU * SC, base - 89 * MU * SC), (112, base - 46))]
    for i, (pt, tgt) in enumerate(leaders):
        sh.leader(pt, '%02d' % (i + 1), tgt, side=1 if tgt[0] > cxf else -1, r=2.3, fs=3.0)

    # 说明两栏
    yy = 168.0
    for i, (no, name, desc) in enumerate(spec['parts']):
        col_x = L if i < 4 else 106.0
        row = yy + (i % 4) * 17.0
        sh.circle((col_x + 3, row), 2.6, fill=None, outline=A.ACCENT, w=A.LW_FINE)
        sh.text(col_x + 3, row, no, 'num', 2.8, A.ACCENT, 'mm')
        sh.text(col_x + 8, row - 1.2, name, 'hei', 3.6, A.INK, 'lm')
        sh.text(col_x + 8, row + 3.4, desc, 'hei', 2.8, A.INK2, 'lm')

    sh.text(L, 268, spec['note'], 'hei', 2.6, A.INK3, 'lm')
    sh.scalebar(R - 40, 264, 40, '40 mm')
    sh.save(out)
    sh.to_svg(out.rsplit('.', 1)[0] + '.svg')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--part', default='dougong', choices=['dougong', 'chiwen'])
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    spec = json.load(open(os.path.join(ZH, a.part + '.json'), encoding='utf-8'))
    if a.part == 'dougong':
        page(spec, a.out, draw_dougong_front, draw_dougong_side)
    else:
        from component_chiwen import draw_chiwen_front, draw_chiwen_side
        page(spec, a.out, draw_chiwen_front, draw_chiwen_side)
    print('saved', a.out)


if __name__ == '__main__':
    main()
