#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第三张图：剖看一榀 · 主要构件图说。

一张竖版 4:3（1800×2400）：画面是房子的一部分（当心间一榀 + 前檐转角，剖开近端墙体），
台基、柱础、柱、额枋、斗拱、补间、梁架、檩椽、屋面、正脊同屏可见；
右栏逐条给「名称 / 类型 / 特点」三行说明，并从条目向左拉虚线引线到对应构件。

用法:
  python3 scripts/make_section_sheet.py --json assets/samples/hall_tang.json --out out/x.png
可选:
  --no-cut       不剖切（默认隐藏近端墙体，露出内部）
  --list a,b,c   只列指定 part（默认按 family 清单）
"""
import argparse
import json
import math
import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import structure_plate as SP  # noqa: E402

W, H = 1800, 2400
PAPER = SP.PAPER
INK, INK3, INK4, ACCENT = SP.INK, SP.INK3, SP.INK4, SP.ACCENT


# ── 构件清单：part / 名称 / 类型 / 特点 ───────────────────────────────
DIAN_LIST = [
    ('台基', '台基 · 踏道', '素台基 · 5 级踏道', '石作基础。把建筑抬离地面，收住全部竖向荷载，也划出建筑的边界。'),
    ('柱础', '柱础', '覆盆式', '圆盆倒扣护住柱脚：隔潮、找平，把柱子的压力摊到台基上。'),
    ('柱身', '柱身', '梭柱（唐）', '上细下粗、卷杀收分。柱径与柱高之比，是判断年代的第一眼。'),
    ('门窗', '门窗', '直棂窗 · 板门', '墙身开洞：当心间设板门、两梢间开直棂窗。门窗只作围护，不参与承重。'),
    ('额枋', '额枋', '阑额（唐）', '柱头的横向联系，把一圈柱子连成整体，也是斗拱的落脚处。'),
    ('斗拱', '斗拱', '偷心造 · 柱头铺作', '斗上叠拱、逐层出跳。出跳越多、层数越高，等级越高；荷载在这里被收拢。'),
    ('补间', '补间铺作', '一朵（唐）', '两柱之间的一朵，唐构补间少而雄大，与柱头铺作共同承檐。'),
    ('梁架', '梁架', '四椽栿 · 蜀柱', '明栿露明、不加天花。每缝一榀，四缝就是四榀，把屋面重量分到各柱。'),
    ('檩椽', '檩 · 椽', '圆檩 · 方椽', '檩承椽、椽承瓦。出檐深远靠椽头挑出，檐口才有那样一道长长的影子。'),
    ('屋面', '屋面', '四阿顶 · 板瓦筒瓦', '瓦垄顺坡而下，四坡交于正脊与垂脊；屋面是整栋最重的一层。'),
    ('正脊', '正脊 · 鸱尾', '唐式鱼尾内卷', '压脊收头。鸱尾鱼尾内卷、无兽头，是唐构屋顶最醒目的记号。'),
]

TING_LIST = [
    ('台基', '台基 · 踏道', '素台基', '把亭子抬离地面，收住四根柱子的荷载。'),
    ('柱础', '柱础', '覆盆式', '护住柱脚，隔潮找平。'),
    ('柱身', '柱身', '圆柱', '柱头直接承檩，省去斗拱这一档。'),
    ('额枋', '额枋', '阑额', '柱间横向联系，形成一圈框。'),
    ('斗拱', '斗拱', '一斗三升', '简单的斗拱，只做承托与过渡。'),
    ('屋面', '屋面', '攒尖顶', '四坡交于一点，上收宝顶。'),
    ('翼角', '翼角起翘', '起翘 · 出翘', '角梁向上翘起，檐口在角部扬起来。'),
    ('宝顶', '宝顶', '收头', '压在攒尖之交，是整个屋顶的结束。'),
]

LISTS = {'dian': DIAN_LIST, 'ting': TING_LIST}


def build_model(job):
    fam = job['family']
    if fam not in SP.BUILDERS:
        raise SystemExit('family 未实现：%s' % fam)
    return SP.BUILDERS[fam](job.get('params', {}))


def anchors(p, model):
    """每个 part 的一个取景锚点（模型坐标）。"""
    bays = int(p.get('bays', 5))
    bay = float(p.get('bay', 3.6))
    dbays = int(p.get('depth_bays', 3))
    bayd = float(p.get('bayd', 3.1))
    hw, hd = bays * bay / 2.0, dbays * bayd / 2.0
    ph = float(p.get('plat_h', 0.55))
    colh = float(p.get('col_h', 4.10))
    zt = ph + colh
    eh = float(p.get('efang_h', 0.32))
    bh = float(p.get('bracket_h', 1.20))
    z1 = zt + eh + (bh if p.get('brackets', True) else 0.0)
    pitch = float(p.get('pitch', 0.52 if p.get('style') == 'wudian' else 0.40))
    ridge = z1 + hd * pitch
    xs = [-hw + 2 * hw * i / bays for i in range(bays + 1)]
    x_in = xs[max(1, bays // 2)]
    return {
        '台基': (xs[len(xs)//2], hd * 0.75, ph * 0.55),
        '柱础': (x_in, hd, ph + 0.10),
        '柱身': (x_in, hd, ph + colh * 0.55),
        '门窗': (x_in, -hd, ph + colh * 0.42),
        '额枋': (x_in, hd, zt + eh * 0.5),
        '斗拱': (x_in, hd, zt + eh + bh * 0.55),
        '补间': (x_in + bay * 0.5, hd, zt + eh + bh * 0.55),
        '梁架': (0.0, 0.0, zt + eh + bh + 0.5),
        '檩椽': (0.0, hd * 0.55, z1 + 0.30),
        '屋面': (0.0, hd * 0.62, z1 + (ridge - z1) * 0.42),
        '正脊': (0.0, 0.0, ridge + 0.10),
    }


def hide_near(model, hd, ph, z1):
    """剖切：去掉近端（y 大）的墙体与门窗，露出内部。屋面不动（它是玻璃罩）。"""
    keep_f, keep_l = [], []
    for fac in model['faces']:
        quad, kind, meta = SP._fs(fac)
        ys = [q[1] for q in quad]
        zs = [q[2] for q in quad]
        near = min(ys) > hd * 0.25
        wallish = (max(zs) <= z1 + 0.01) and (min(zs) >= ph - 0.01)
        if near and wallish and kind in ('mass', 'screen', 'body'):
            continue
        keep_f.append(fac)
    for e in model.get('lines', []):
        seg = SP._line_parts(e)[0]
        ys = [q[1] for q in seg]
        zs = [q[2] for q in seg]
        if min(ys) > hd * 0.25 and max(zs) <= z1 + 0.01 and min(zs) >= ph - 0.01:
            continue
        keep_l.append(e)
    m = dict(model)
    m['faces'] = keep_f
    m['lines'] = keep_l
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--json', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--no-cut', action='store_true')
    ap.add_argument('--list', default='')
    a = ap.parse_args()

    job = json.load(open(a.json, encoding='utf-8'))
    p = job.get('params', {})
    fam = job.get('family')
    model = build_model(job)

    bays = int(p.get('bays', 5))
    bay = float(p.get('bay', 3.6))
    dbays = int(p.get('depth_bays', 3))
    bayd = float(p.get('bayd', 3.1))
    hw, hd = bays * bay / 2.0, dbays * bayd / 2.0
    ph = float(p.get('plat_h', 0.55))
    colh = float(p.get('col_h', 4.10))
    eh = float(p.get('efang_h', 0.32))
    bh = float(p.get('bracket_h', 1.20)) if p.get('brackets', True) else 0.0
    z1 = ph + colh + eh + bh

    if not a.no_cut:
        model = hide_near(model, hd, ph, z1)

    cv = SP.Canvas(W, H)
    ts = SP._ts(W, H)
    F = lambda s: max(11, int(round(s * ts)))

    # ── 取景：上半幅放「当心间一榀 + 前檐转角」
    _pitch = float(p.get('pitch', 0.52 if p.get('style') == 'wudian' else 0.40))
    _ridge = z1 + hd * _pitch
    us, vs = [], []
    for fac in model['faces']:
        quad = SP._fs(fac)[0]
        if max(q[2] for q in quad) > _ridge + 0.55:
            continue
        for q in quad:
            u, v = SP._uv(q)
            us.append(u); vs.append(v)
    u0, u1 = min(us), max(us)
    v0, v1 = min(vs), max(vs)
    x0, x1 = int(56 * ts), W - int(56 * ts)
    y0, y1 = int(196 * ts), int(H * 0.565)
    bw, bh_ = max(1e-6, u1 - u0), max(1e-6, v1 - v0)
    k = min((x1 - x0) / bw, (y1 - y0) / bh_)
    ox = x0 + ((x1 - x0) - bw * k) / 2.0 - u0 * k
    oy = y0 + ((y1 - y0) - bh_ * k) / 2.0 - v0 * k
    ax = SP.Axo(k=k, zk=0.95, ox=ox, oy=oy, c=0.866, s=0.5)

    SP.draw_model(cv, model, ax)

    # ── 标题
    f_t = SP.font('kai', F(88))
    f_s = SP.font('hei', F(34))
    cv.text(x0, int(92 * ts), job.get('title', '主要构件图说'), f_t, INK, anchor='lm')
    cv.text(x0, int(158 * ts), '剖看一榀 · 台基到正脊，十件逐件指认', f_s, ACCENT, anchor='lm')

    # ── 构件清单（下半幅双栏）
    lst = LISTS['ting' if fam == 'ting' else 'dian']
    want = [x.strip() for x in a.list.split(',') if x.strip()]
    if want:
        lst = [it for it in lst if it[0] in want]
    amap = anchors(p, model)

    f_no = SP.font('num', F(32))
    f_nm = SP.font('hei', F(46))
    f_ty = SP.font('hei', F(31))
    f_ft = SP.font('hei', F(29))

    # 锚点编号徽标（相互避让）
    placed = []
    for idx, (key, name, typ, feat) in enumerate(lst):
        at = amap.get(key)
        if not at:
            continue
        px, py = ax.pt(at)
        r = int(26 * ts)
        for _ in range(6):
            if all(abs(px - qx) > 2.2 * r or abs(py - qy) > 2.2 * r for qx, qy in placed):
                break
            py -= int(50 * ts)
        placed.append((px, py))
        cv.poly([(px - r, py - r), (px + r, py - r), (px + r, py + r), (px - r, py + r)],
                fill=(250, 247, 242), outline=ACCENT, lw=1.4)
        cv.text(px, py, '%02d' % (idx + 1), SP.font('num', F(30)), ACCENT, anchor='mm')

    # 双栏文字
    col_w = (W - 2 * int(56 * ts) - int(60 * ts)) // 2
    top = int(H * 0.595)
    rows = (len(lst) + 1) // 2
    step = (H - int(96 * ts) - top) / float(rows)
    for idx, (key, name, typ, feat) in enumerate(lst):
        col, row = idx // rows, idx % rows
        cx = int(56 * ts) + col * (col_w + int(60 * ts))
        cy = top + step * (row + 0.5)
        cv.text(cx, cy - int(34 * ts), '%02d' % (idx + 1), f_no, ACCENT, anchor='lm')
        cv.text(cx + int(44 * ts), cy - int(34 * ts), name, f_nm, INK, anchor='lm')
        cv.text(cx + int(44 * ts), cy + int(4 * ts), '类型：' + typ, f_ty, INK3, anchor='lm')
        for j, ln_ in enumerate(SP._wrap(cv, '特点：' + feat, f_ft, col_w - int(50 * ts))[:2]):
            cv.text(cx + int(44 * ts), cy + int(42 * ts) + j * int(32 * ts), ln_,
                    f_ft, INK3, anchor='lm')

    # ── 页脚 logo（右下，与右栏右边界对齐）
    mk_path = os.path.join(ROOT, 'assets', 'brand', 'mark.png')
    seal = int(96 * ts)
    R = W - int(56 * ts)
    if os.path.exists(mk_path):
        mk = Image.open(mk_path).convert('RGB')
        S = cv.img.width / float(cv.w)
        mk = mk.resize((int(seal * S), int(seal * S)), Image.LANCZOS)
        _lg = (int((R - seal) * S), int((H - int(70 * ts) - seal) * S))
        cv.img.paste(mk.convert('RGB'), _lg)
    f_sig = SP.font('num', F(30))
    f_sig2 = SP.font('hei', F(22))
    cy = H - int(70 * ts) - seal // 2
    cv.text(R - seal - int(22 * ts), cy - int(14 * ts), 'march-aa', f_sig, INK, anchor='rm')
    cv.text(R - seal - int(22 * ts), cy + int(22 * ts),
            '古建构造关系轴测 · structure view', f_sig2, INK3, anchor='rm')

    out = a.out
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    cv.img.resize((W, H), Image.LANCZOS).save(out)
    print('saved: %s (%dx%d) | items: %d' % (out, W, H, len(lst)))


if __name__ == '__main__':
    main()
