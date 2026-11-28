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
def _gong(P, sh, x0, x1, z0, z1, cut=3.0, fill=None):
    """一根栱：两端带卷杀（45° 切角），比直角块像木构件。"""
    zt, zb = z1, z0
    pts = [P(x0 + cut, zt), P(x1 - cut, zt), P(x1, zt - cut * 0.9),
           P(x1, zb + cut * 0.6), P(x1 - cut * 0.8, zb),
           P(x0 + cut * 0.8, zb), P(x0, zb + cut * 0.6), P(x0, zt - cut * 0.9)]
    sh.poly(pts, fill=fill or WOOD)


def _dou(P, sh, x, z, w=9.0, h=10.0):
    """一个小斗：上宽下窄，斗欹内凹。"""
    sh.poly([P(x + 1.2, z), P(x + w - 1.2, z), P(x + w, z + h * 0.35),
             P(x + w, z + h), P(x, z + h), P(x, z + h * 0.35)], fill=WOOD2)


def _dougong_core(P, R, sh):
    """宋式六铺作单杪双下昂的层叠骨架（材分制，1 分 = 15mm）。

    层序：栌斗 → 泥道栱/华栱 → 交互斗 → 双下昂（外端低、内尾高）→ 令栱 → 散斗 → 耍头。
    """
    # 栌斗 32 分宽、20 分高
    sh.poly([P(-10, 0), P(10, 0), P(16, 12), P(16, 20), P(-16, 20), P(-16, 12)], fill=WOOD)
    sh.line(P(-16, 13), P(16, 13), w=A.LW_FINE, col=A.INK2)

    # 泥道栱（横 62 分，带卷杀）+ 两端散斗
    _gong(P, sh, -31, 31, 20, 35)
    _dou(P, sh, -31, 35, 9, 10)
    _dou(P, sh, 22, 35, 9, 10)

    # 华栱（第一跳，向外 30 分）+ 交互斗
    _gong(P, sh, -10, 50, 20, 35, cut=4, fill=WOOD2)
    _dou(P, sh, 44, 35, 12, 11)

    # 双下昂：外端低、内尾高，斜度约 25°
    def ang(x_in, z_in, x_out, z_out, th=6.0):
        return [P(x_in, z_in), P(x_out, z_out),
                P(x_out, z_out - th), P(x_in, z_in - th)]

    sh.poly(ang(46, 60, 84, 45), fill=WOOD)      # 第一根昂：尖在 45 分高
    sh.poly(ang(48, 72, 92, 57), fill=WOOD)      # 第二根昂：压在上面

    # 令栱（承在第一根昂尖上）+ 三散斗 + 耍头
    _gong(P, sh, 74, 92, 45, 58, cut=3, fill=WOOD2)
    for x in (72, 82, 92):
        _dou(P, sh, x, 58, 9, 9)
    _gong(P, sh, 86, 104, 67, 77, cut=2.5, fill=WOOD2)


def draw_dougong_front(sh, cx, base, s=0.045):
    """正立面：柱头 + 斗拱 + 斜拱（45° 斜插，三圣殿的记号）。"""
    def P(x, z):
        return (cx + F(x) * s, base - F(z) * s)

    def R(x0, z0, x1, z1):
        return [P(x0, z0), P(x1, z0), P(x1, z1), P(x0, z1)]

    sh.cut(R(-11, -18, 11, 0))
    _dougong_core(P, R, sh)

    # 斜拱：45° 斜向「朝观者」出挑，正立面里是被透视压缩的短粗斜块，
    # 不是满长的斜杆——画长了会变成一个 X，把整朵都盖住。
    for sg in (-1, 1):
        sh.poly([P(sg * 9, 24), P(sg * 26, 42), P(sg * 33, 36), P(sg * 16, 18)],
                fill=(240, 234, 222))

    marks = [('01', P(0, 10)), ('02', P(-16, 27)), ('03', P(20, 27)),
             ('04', P(66, 54)), ('05', P(-30, 38)),
             ('06', P(84, 52)), ('07', P(100, 72))]
    return dict(top=94, left=-50, right=108, marks=marks)


def draw_dougong_side(sh, cx, base, s=0.045):
    """侧立面：沿出跳方向剖开，看昂的斜面与层叠次序。"""
    def P(x, z):
        return (cx + F(x) * s, base - F(z) * s)

    def R(x0, z0, x1, z1):
        return [P(x0, z0), P(x1, z0), P(x1, z1), P(x0, z1)]

    sh.cut(R(-10, -18, 10, 0))
    sh.poly([P(-10, 0), P(10, 0), P(16, 12), P(16, 20), P(-16, 20), P(-16, 12)], fill=WOOD)
    _gong(P, sh, -12, 12, 20, 35, cut=2)             # 泥道栱截面
    _gong(P, sh, -8, 34, 35, 47, cut=3, fill=WOOD2)  # 华栱（侧看一段）
    for (xi, zi, xo, zo) in ((34, 60, 68, 45), (36, 72, 76, 57)):
        sh.poly([P(xi, zi), P(xo, zo), P(xo, zo - 6), P(xi, zi - 6)], fill=WOOD)
    _gong(P, sh, 58, 76, 45, 58, cut=2.5, fill=WOOD2)   # 令栱截面
    _gong(P, sh, 70, 90, 67, 77, cut=2, fill=WOOD2)     # 耍头

    sh.line(P(30, 62), P(74, 62), w=A.LW_FINE, col=A.INK3, dash=(3, 1.6))
    sh.line(P(34, 60), P(68, 45), w=A.LW_FINE, col=A.INK3, dash=(2, 1.2))
    sh.text(P(52, 64)[0], P(52, 64)[1], '25°', 'num', 2.6, A.INK3, anchor='mb')
    return dict(top=88, left=-16, right=100, marks=[])


# ── 页面 ────────────────────────────────────────────────────────────────
def page(spec, out, draw_front, draw_side, k_mm=1.0):
    sh = A.Sheet(210, 280)
    L, R = 18.0, 192.0
    sh.text(L, 20, spec['title'], 'kai', 9.0, A.INK, 'lm')
    sh.text(L, 27.5, spec['subtitle'], 'hei', 3.4, A.INK3, 'lm')
    sh.line((L, 32), (R, 32), w=A.LW_FINE, col=A.GREY)

    lead = spec['lead']
    x, y = L, 38.0
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
    base = 160.0
    cxf, cxs = 42.0, 126.0
    mf = draw_front(sh, cxf, base)
    draw_side(sh, cxs, base)
    sh.axis((cxf, base - 4), (cxf, base - 24 - 78))
    sh.axis((cxs, base - 4), (cxs, base - 24 - 70))

    sh.text(cxf, base + 12, '正立面 · 出跳与斜拱', 'hei', 3.0, A.INK3, 'mm')
    sh.text(cxs, base + 12, '侧立面 · 昂的斜面', 'hei', 3.0, A.INK3, 'mm')

    # 引线编号（正立面）：左侧的号放左缘，右侧的号放两图之间/右缘
    # 编号统一排在两幅图的外侧栏，引线短、互不交叉
    lefts = [m for m in mf.get('marks', []) if m[1][0] <= cxf + 8]
    rights = [m for m in mf.get('marks', []) if m[1][0] > cxf + 8]
    for i, (no, pt) in enumerate(sorted(lefts, key=lambda m: -m[1][1])):
        sh.leader(pt, no, (14.0, base - 18 - i * 11.0), side=-1, r=2.2, fs=2.6)
    for i, (no, pt) in enumerate(sorted(rights, key=lambda m: -m[1][1])):
        sh.leader(pt, no, (112.0, base - 12 - i * 11.0), side=1, r=2.2, fs=2.6)

    # 说明两栏
    yy = 186.0
    for i, (no, name, desc) in enumerate(spec['parts']):
        col_x = L if i < 4 else 106.0
        row = yy + (i % 4) * 16.0
        sh.circle((col_x + 3, row), 2.6, fill=None, outline=A.ACCENT, w=A.LW_FINE)
        sh.text(col_x + 3, row, no, 'num', 2.8, A.ACCENT, 'mm')
        sh.text(col_x + 8, row - 1.2, name, 'hei', 3.6, A.INK, 'lm')
        sh.text(col_x + 8, row + 3.4, desc, 'hei', 2.8, A.INK2, 'lm')

    sh.text(L, 272, spec['note'], 'hei', 2.6, A.INK3, 'lm')
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
