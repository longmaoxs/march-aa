#!/usr/bin/env python3
"""输出「主要构件拆解」竖版 4:3 图：每个构件单独画一遍 + 名称/说明。

用法：
    python3 scripts/make_component_sheet.py --json assets/samples/hall_tang.json \
        --out out/hall_tang_components.png
"""
import argparse, json, sys
from pathlib import Path
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parent))
import structure_plate as SP

W, H = 1800, 2400          # 竖版：高宽比 4:3

_SC = lambda cv: cv.img.width / float(cv.w)


def zc(pts):
    return sum(p[2] for p in pts) / float(len(pts))


def bbox(pts):
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]; zs = [p[2] for p in pts]
    return min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)


def fit(im, bw, bh):
    r = min(bw / im.width, bh / im.height)
    return im.resize((max(1, int(im.width * r)), max(1, int(im.height * r))), Image.LANCZOS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--json', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--cols', type=int, default=2)
    a = ap.parse_args()
    job = json.load(open(a.json, encoding='utf-8'))
    p = job.get('params', {})
    model = SP.BUILDERS[job['family']](p)

    # ── 参考高度 ────────────────────────────────────────────────
    zs_all = [zc(f[0]) for f in model['faces']]
    zmax = max(zs_all)
    plat_h = float(p.get('plat_h', 0.55))
    col_h = float(p.get('col_h', 4.6))
    brk_h = float(p.get('bracket_h', 1.4))
    z_eave = plat_h + col_h + brk_h          # 檐口高度
    z_brk = plat_h + col_h                   # 柱头

    def kind_of(pts, is_line=False):
        x0, x1, y0, y1, z0, z1 = bbox(pts)
        dz, dx, dy = z1 - z0, x1 - x0, y1 - y0
        if z1 <= plat_h + 0.06:
            return 0                                    # 台基 · 踏道
        if z0 >= z_eave - 0.06:
            return 5                                    # 屋面 · 脊饰
        if dz > 0.7 and max(dx, dy) > 1.2 and z1 > z_brk:
            return 4                                    # 屋架（斜梁、瓜柱）
        if z0 >= z_brk - 0.55 and max(dz, dx, dy) > 0.2:
            return 3                                    # 斗拱 · 额枋
        if dz > 1.0 and max(dx, dy) < 0.8:
            return 1                                    # 柱
        return 2                                        # 墙体 · 门窗

    groups = ([], [], [], [], [], [])
    for f in model['faces']:
        groups[kind_of(f[0])].append(f)
    lgroups = ([], [], [], [], [], [])
    for ln in model['lines']:
        seg, col, w, key = SP._line_parts(ln)
        if not key:                            # 被遮线跟着面走，避免单独成卡
            continue
        lgroups[kind_of(seg, True)].append(ln)

    base = [('台基 · 踏道', (0,), ['石作基础：把建筑抬离地面。',
                                   '台明收住全部竖向荷载，也划出建筑边界。']),
            ('柱网 · 墙体', (1, 2), ['柱是骨架、墙只围护；直棂窗开在当心间。',
                                     '柱础（覆盆式）＋梭柱，柱间以额枋相连。']),
            ('斗拱 · 额枋', (3,), ['柱头上叠斗、逐跳出跳，托住上面的檩。',
                                   '出跳越多等级越高；荷载在此收拢，交给柱子。']),
            ('屋面 · 屋架', (4, 5), ['椽上铺瓦、瓦垄顺坡而下，四坡交于正脊。',
                                     '脊下是梁架与瓜柱，把屋面的重量分到各缝。'])]

    cards, gsel = [], []
    for nm, idxs, ds in base:
        gf = [f for k in idxs for f in groups[k]]
        gl = [ln for k in idxs for ln in lgroups[k]]
        if gf or gl:
            cards.append((nm, ds))
            gsel.append((gf, gl))

    # ── 画布与标题 ──────────────────────────────────────────────
    cv = SP.Canvas(W, H)
    ts = SP._ts(W, H)
    F = lambda s: max(11, int(round(s * ts)))
    f_era = SP.font('kai', F(74))
    f_sub = SP.font('hei', F(30))
    f_no = SP.font('num', F(30))
    f_hd = SP.font('hei', F(40))
    f_ds = SP.font('hei', F(28))
    f_sig = SP.font('num', F(34))
    f_sig2 = SP.font('hei', F(24))

    mx = int(96 * ts)
    y = int(96 * ts)
    cv.text(mx, y, job.get('title', '主要构件拆解'), f_era, SP.INK, anchor='lm')
    y += int(66 * ts)
    sub = '把一栋建筑拆成能说清楚的几个部件，每个部件单独看一遍'
    cv.text(mx, y, sub, f_sub, SP.INK3, anchor='lm')
    y += int(52 * ts)
    cv.line([(mx, y), (W - mx, y)], SP.INK4, 1.4)
    y += int(40 * ts)

    # ── 卡片网格 ────────────────────────────────────────────────
    cols = max(1, min(a.cols, len(cards)))
    rows = (len(cards) + cols - 1) // cols
    gx0, gy0 = mx, y
    gw = W - 2 * mx
    gh = H - int(150 * ts) - gy0
    cw, ch = gw / cols, gh / rows

    for idx, ((nm, ds), (gf, gl)) in enumerate(zip(cards, gsel)):
        r, c = divmod(idx, cols)
        cxx = gx0 + c * cw
        cyy = gy0 + r * ch
        # 构件单独渲染到小画布
        sub_model = dict(model, faces=gf, lines=gl, callouts=[], chain=[])
        iw, ih = int(cw - 30 * ts), int(ch - int(150 * ts))
        mini = SP.Canvas(iw, ih)
        umin, vmin, umax, vmax = SP._uv_bbox(sub_model, zk=float(job.get('z_ratio', 0.95)))
        bw_, bh_ = max(1e-6, umax - umin), max(1e-6, vmax - vmin)
        pad = int(14 * ts)
        k = min((iw - 2 * pad) / bw_, (ih - 2 * pad) / bh_)
        ox = pad - k * umin + ((iw - 2 * pad) - k * bw_) * 0.5
        oy = pad - k * vmin + ((ih - 2 * pad) - k * bh_) * 0.5
        SP.draw_model(mini, sub_model, SP.Axo(k=k, zk=float(job.get('z_ratio', 0.95)), ox=ox, oy=oy))
        S = _SC(cv)
        cv.img.paste(Image.new('RGB', (max(1, int((iw + 12 * ts) * S)), max(1, int((ih + 12 * ts) * S))),
                              (238, 234, 226)),
                     (int((cxx - 6 * ts) * S), int((cyy - 6 * ts) * S)))
        thumb = mini.img.convert('RGB').resize((int(iw * S), int(ih * S)), Image.LANCZOS)
        cv.img.paste(thumb, (int(cxx * S), int(cyy * S)))

        ty = cyy + ih + int(46 * ts)
        cv.text(cxx + int(4 * ts), ty - int(14 * ts), '%02d' % (idx + 1), f_no, SP.ACCENT, anchor='lm')
        cv.text(cxx + int(56 * ts), ty - int(16 * ts), nm, f_hd, SP.INK, anchor='lm')
        ty += int(46 * ts)
        for d in ds:
            for line in SP._wrap(cv, d, f_ds, int(cw - 24 * ts)):
                cv.text(cxx + int(56 * ts), ty, line, f_ds, SP.INK3, anchor='lm')
                ty += int(34 * ts)
        if idx % cols == cols - 1 or idx == len(cards) - 1:
            pass

    # ── 页脚 logo（右对齐）─────────────────────────────────────
    try:
        mk = Image.open(Path(__file__).resolve().parent.parent / 'assets/brand/mark.png').convert('RGBA')
        seal = int(104 * ts)
        R = W - mx
        ly = H - int(120 * ts)
        S = _SC(cv)
        mk = mk.resize((int(seal * S), int(seal * S)), Image.LANCZOS)
        cv.img.paste(mk, (int((R - seal) * S), int(ly * S)), mk)
        _cy = ly + seal // 2
        cv.text(R - seal - int(26 * ts), _cy - int(16 * ts), 'march-aa', f_sig, SP.INK, anchor='rm')
        cv.text(R - seal - int(26 * ts), _cy + int(24 * ts),
                '古建构造关系轴测 · structure view', f_sig2, SP.INK3, anchor='rm')
    except Exception as e:
        print('logo skipped:', e)

    cv.img.resize((W, H), Image.LANCZOS).save(a.out)
    print('saved:', a.out, cv.img.size, '| cards:', len(cards), [c[0] for c in cards])


if __name__ == '__main__':
    main()
