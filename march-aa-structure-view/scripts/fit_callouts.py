"""按「实际绘制顺序的可见像素」反算 callout 坐标，输出可直接写进 samples/*.json 的 callout_xy。

用法：python scripts/fit_callouts.py assets/samples/qiao5.json
原理见 references/callouts.md：录 Canvas.poly → 栅格化（像素=绘制序号）→ 顶点签名匹配回 part
→ 每个构件取「离该 part 像素质心最近、且确实露在最前」的点。
"""
import json
import sys
from collections import defaultdict

from PIL import Image, ImageDraw

import structure_plate as SP


def main(job_path):
    job = json.load(open(job_path, encoding='utf-8'))
    rec, cap = [], {}

    orig_poly = SP.Canvas.poly

    def spy(self, pts, fill=None, outline=None, lw=1.0, alpha=None):
        if fill is not None:
            rec.append(list(pts))
        return orig_poly(self, pts, fill=fill, outline=outline, lw=lw, alpha=alpha)

    SP.Canvas.poly = spy
    orig_dc = SP.draw_callouts

    def spy_dc(cv, model, ax, *a, **k):
        cap.update(cv=cv, model=model, ax=ax)

    SP.draw_callouts = spy_dc
    SP.render(job)
    SP.Canvas.poly, SP.draw_callouts = orig_poly, orig_dc

    cv, model, ax = cap['cv'], cap['model'], cap['ax']
    W, H, S = cv.w, cv.h, SP.S

    sig = {}
    for f in model['faces']:
        quad, kind, meta = SP._fs(f)
        p2 = [(round(x, 1), round(y, 1)) for x, y in (ax.pt(q) for q in quad)]
        part = meta.get('part')
        if not part:
            continue
        sig[tuple(p2)] = part
        sig[tuple(reversed(p2))] = part

    im = Image.new('I', (W * S, H * S), 0)
    d = ImageDraw.Draw(im)
    pm = {}
    for n, pts in enumerate(rec, 1):
        part = sig.get(tuple((round(x, 1), round(y, 1)) for x, y in pts))
        if part:
            pm[n] = part
            d.polygon([(x * S, y * S) for x, y in pts], fill=n)
    px = im.load()

    byp = defaultdict(list)
    for y in range(0, H * S, 3):
        for x in range(0, W * S, 3):
            p = pm.get(px[x, y])
            if p:
                byp[p].append((x / float(W * S), y / float(H * S)))

    out = {}
    for c in model['callouts']:
        part = SP._part_of(c.get('label'))
        pool = byp.get(part) or []
        # 构件可见像素太少（大半被墙/屋面遮住）时，最近点法会落到旁边的墙上，
        # 改用锚点投影更稳。
        if len(pool) < 1200:
            ax0, ay0 = ax.pt(c['at'])
            out[c['label']] = [round(ax0 / W, 3), round(ay0 / H, 3)]
            print('ANCHOR %-8s part=%-5s px=%5d 锚点' % (c['label'], part, len(pool)))
            continue
        if not pool:
            # 该构件整片被遮住（桥台、塔刹、被墙挡住的台基）：退回到「锚点投影」，
            # 保证徽标仍落在构件所在的方位，而不是消失。
            ax0, ay0 = ax.pt(c['at'])
            out[c['label']] = [round(ax0 / W, 3), round(ay0 / H, 3)]
            print('FALLBK %-8s part=%s 用锚点 %.3f,%.3f' % (c['label'], part,
                                                           ax0 / W, ay0 / H))
            continue
        ax0, ay0 = ax.pt(c['at'])
        fx, fy = ax0 / W, ay0 / H
        # 底部构件（柱础/金柱/翼角）取「横向最近、且尽量靠下」的那一点：
        # 只按欧氏最近会落到旁边的墙面或远角上。
        if part in ('柱础', '金柱', '翼角'):
            # 这三类整片贴在地面/檐角，像素池里混着墙与台基面，最近点会跑偏；
            # 直接用锚点（构件几何中心）投影，落点一定在构件上。
            out[c['label']] = [round(fx, 3), round(fy, 3)]
            print('ANCHOR %-8s part=%-5s px=%5d 锚点' % (c['label'], part, len(pool)))
            continue
        else:
            best = min(pool, key=lambda t: (t[0] - fx) ** 2 + (t[1] - fy) ** 2)
        # 兜底：最近点若离锚点太远（>0.10 归一化），说明池子里混进了别的构件，
        # 退回到锚点投影，宁可压在构件中心，也不要飘到旁边的墙上。
        if abs(best[0] - fx) + abs(best[1] - fy) > 0.06:
            out[c['label']] = [round(fx, 3), round(fy, 3)]
            print('GUARD  %-8s part=%-5s px=%6d 离锚点过远->锚点' % (c['label'], part, len(pool)))
            continue
        out[c['label']] = [round(best[0], 3), round(best[1], 3)]
        print('%-8s part=%-5s px=%6d  ->  [%.3f, %.3f]' % (c['label'], part, len(pool), best[0], best[1]))

    if out:
        job['callout_xy'] = out
        json.dump(job, open(job_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        print('\n已写入', job_path, '的 callout_xy')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'assets/samples/hall_tang.json')
