#!/usr/bin/env python3
"""输出「照片 + 爆炸轴测」4:3 双联图：上 32% 原照片，下 68% 分层爆炸的主体 + 右侧 01/02/03 说明。"""
import argparse, json, sys
from pathlib import Path
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parent))
import structure_plate as SP

W, H = 1800, 2400          # 竖版：高宽比 4:3
TOP = int(H * 0.35)
NOTE_W = int(W * 0.40)


_SC = lambda cv: cv.img.width / float(cv.w)


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

    notes_top_index = list(range(n))[::-1]   # 说明顺序：屋顶在上
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

    # ── 右栏：风格 + 形制 + 构件分条（大字号）+ 页脚 logo ──────
    f_era = SP.font('kai', F(66))
    f_sub = SP.font('hei', F(31))
    f_lab = SP.font('hei', F(29))
    f_val = SP.font('hei', F(31))
    f_no = SP.font('num', F(36))
    f_hd = SP.font('hei', F(42))
    f_note = SP.font('hei', F(29))
    f_sig = SP.font('num', F(38))
    f_sig2 = SP.font('hei', F(26))

    nx = W - NOTE_W + int(8 * ts)
    nw = NOTE_W - int(30 * ts)
    p_ = job.get('params', {})
    comp = p_.get('components') or {}
    roof_name = {'wudian': '庑殿（四阿）', 'xieshan': '歇山', 'yingshan': '悬山',
                 'barrel': '卷棚', 'luding': '盝顶'}.get(p_.get('style'), '厅堂')
    eaves = int(p_.get('eaves', 1))
    bays, bayw = int(p_.get('bays', 3)), float(p_.get('bay', 4.0))
    dbays, dbayw = int(p_.get('depth_bays', 3)), float(p_.get('bayd', 3.6))
    base_name = {'plain': '素台基', 'xumizuo': '须弥座'}.get(comp.get('platform_base'), '素台基')
    win_name = {'zhiling': '直棂窗', 'jian': '槛窗', 'zhizhai': '支摘窗',
                'lou': '漏窗'}.get(comp.get('window'), '直棂窗')
    brk_name = {'jixin': '计心造', 'touxin': '偷心造',
                'yidou3sheng': '一斗三升', 'xiegong': '斜拱'}.get(comp.get('bracket'), '计心造')
    col_base = {'fupen': '覆盆式', 'lianban': '莲瓣式', 'drum': '鼓镜式',
                'xumizuo': '须弥座式', 'plain': '素覆盆'}.get(comp.get('column_base'), '覆盆式')
    shaft = {'round': '圆柱', 'octagon': '八角柱', 'square': '方柱', 'suo': '梭柱'}.get(
        comp.get('column_shaft'), '圆柱')

    era = job.get('eraNote') or (job.get('title') or '').replace('·', '').strip()
    facts = [
        ('屋顶', '%s · %s檐' % (roof_name, '重' if eaves >= 2 else '单')),
        ('间架', '面阔 %d 间 × %.1f m　进深 %d 间 × %.1f m' % (bays, bayw, dbays, dbayw)),
        ('斗拱', '%s · 柱头 + 补间' % brk_name),
        ('柱·础', '%s · %s' % (shaft, col_base)),
        ('门窗', '%s · 板门' % win_name),
        ('台基', '%s · %d 级踏道' % (base_name, int(p_.get('plat_steps', 5)))),
    ]
    summary = job.get('styleNote') or (
        '斗拱雄大、出檐深远、屋面平缓；力由屋面逐层收到斗拱、额枋、柱，'
        '最后由台基收入地面。')

    seal = int(80 * ts)
    foot_y = H - int(52 * ts) - seal
    y = TOP + int(74 * ts)
    # 标题
    cv.text(nx, y, era or '构造关系', f_era, SP.INK, anchor='lm')
    y += int(52 * ts)
    cv.text(nx, y, '%s · 唐式木构' % roof_name, f_sub, SP.ACCENT, anchor='lm')
    y += int(40 * ts)
    cv.line([(nx, y), (nx + nw, y)], SP.INK4, 1.4)
    y += int(34 * ts)
    # 形制六行
    for lab, val in facts:
        cv.text(nx, y, lab, f_lab, SP.ACCENT, anchor='lm')
        cv.text(nx + int(78 * ts), y, val, f_val, SP.INK, anchor='lm')
        y += int(40 * ts)
    y += int(14 * ts)
    cv.line([(nx, y), (nx + nw, y)], SP.INK4, 1.0)
    y += int(36 * ts)
    # 构件分条（小图示 + 大字）
    notes = job.get('explodeNotes') or [
        ('01', '屋顶 · 屋面', '坡面铺瓦成垄，压在梁架与斗拱上。'),
        ('02', '斗拱 · 额枋', '层层出跳，把屋面的荷载收拢到柱头。'),
        ('03', '柱网 · 墙体', '柱承重、墙只围护，木构与砖石各司其职。'),
        ('04', '台基 · 踏道', '把整栋建筑抬离地面，收住全部竖向荷载。'),
    ][:n]
    notes_top_index = list(range(n))[::-1]
    slot = max(int(150 * ts), (foot_y - int(70 * ts) - y) / float(len(notes)))
    th = min(int(slot * 0.72), int(150 * ts))
    tw = int(th * 1.40)
    for i, (no, hd, txt) in enumerate(notes):
        by = y + i * slot
        cy = by + slot * 0.42
        m1 = dict(model, faces=bands[notes_top_index[i]], lines=lbands[notes_top_index[i]],
                  callouts=[], chain=[])
        u0, v0, u1, v1 = SP._uv_bbox(m1)
        w_, h_ = max(1e-6, u1 - u0), max(1e-6, v1 - v0)
        k2 = min(tw / w_, th / h_)
        ax2 = SP.Axo(k=k2, zk=float(job.get('z_ratio', 0.95)),
                     ox=-k2 * u0 + (tw - k2 * w_) * 0.5,
                     oy=-k2 * v0 + (th - k2 * h_) * 0.5)
        mini = SP.Canvas(tw, th)
        SP.draw_model(mini, m1, ax2)
        thumb = mini.img.resize((tw, th), Image.LANCZOS).convert('RGB')
        cv.img.paste(thumb, (int(nx * _SC(cv)), int((cy - th * 0.5) * _SC(cv))))
        tx = nx + tw + int(20 * ts)
        cv.text(tx, cy - th * 0.30, no, f_no, SP.ACCENT, anchor='lm')
        cv.text(tx + int(46 * ts), cy - th * 0.30, hd, f_hd, SP.INK, anchor='lm')
        yy = cy - th * 0.30 + int(44 * ts)
        for line in (SP._wrap(cv, txt, f_note, nw - tw - int(20 * ts)) or [txt])[:2]:
            cv.text(tx + int(46 * ts), yy, line, f_note, SP.INK3, anchor='lm')
            yy += int(34 * ts)

    # 页脚：总结 + logo
    yb = foot_y - int(86 * ts)
    for line in (SP._wrap(cv, summary, f_note, nw) or [summary])[:3]:
        cv.text(nx, yb, line, f_note, SP.INK3, anchor='lm')
        yb += int(34 * ts)
    try:
        mk = Image.open(str(Path(__file__).resolve().parent.parent /
                            'assets/brand/mark.png')).convert('RGBA')
        mk = mk.resize((seal, seal), Image.LANCZOS)
        cv.img.paste(mk, (int(nx * _SC(cv)), int(foot_y * _SC(cv))), mk)
        cv.text(nx + seal + int(20 * ts), foot_y + int(seal * 0.32), 'march-aa',
                f_sig, SP.INK, anchor='lm')
        cv.text(nx + seal + int(20 * ts), foot_y + int(seal * 0.74),
                '古建构造关系轴测 · structure view', f_sig2, SP.INK3, anchor='lm')
    except Exception as e:
        print('logo skipped:', e)

    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    cv.img.resize((W, H), Image.LANCZOS).save(a.out)
    print('saved:', a.out, (W, H))


if __name__ == '__main__':
    main()
