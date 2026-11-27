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
        if not pool:
            print('MISS  %-8s part=%s 无可见像素' % (c['label'], part))
            continue
        ax0, ay0 = ax.pt(c['at'])
        fx, fy = ax0 / W, ay0 / H
        best = min(pool, key=lambda t: (t[0] - fx) ** 2 + (t[1] - fy) ** 2)
        out[c['label']] = [round(best[0], 3), round(best[1], 3)]
        print('%-8s part=%-5s px=%6d  ->  [%.3f, %.3f]' % (c['label'], part, len(pool), best[0], best[1]))

    if out:
        job['callout_xy'] = out
        json.dump(job, open(job_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        print('\n已写入', job_path, '的 callout_xy')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'assets/samples/hall_tang.json')
