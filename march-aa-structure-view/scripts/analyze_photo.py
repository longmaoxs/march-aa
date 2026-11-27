#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""照片 → 形制草案（job.json）

做三件事：
1) 量：主体外框、天际线高度比、水平檐口线的条数、左右对称度；
2) 猜：family / style / eaves / plan（猜不准就写 unknown，绝不硬猜）；
3) 出：一份带 evidence 与 confidence 的 job.json 草案，交给人（或 agent）复核后改。

用法：
    python3 scripts/analyze_photo.py --photo a.jpg --out draft.json [--family ting]
"""
import argparse, json, math
import numpy as np
from PIL import Image


def load_gray(path, maxw=900, ret_box=False):
    im = Image.open(path).convert('L')
    if im.width > maxw:
        im = im.resize((maxw, int(im.height * maxw / im.width)), Image.LANCZOS)
    g = np.asarray(im, dtype=np.float32) / 255.0
    if ret_box:
        return g, {'x0': 0.0, 'x1': 1.0}
    return g


def edge_energy(g):
    gx = np.abs(np.diff(g, axis=1, prepend=g[:, :1]))
    gy = np.abs(np.diff(g, axis=0, prepend=g[:1, :]))
    return gx + gy


def subject_box(e):
    """用边缘能量找主体：列/行能量超过全图中位数的区域。"""
    col = e.sum(axis=0)
    row = e.sum(axis=1)
    def band(v, frac=0.35):
        thr = v.max() * frac
        idx = np.where(v >= thr)[0]
        return int(idx[0]), int(idx[-1])
    x0, x1 = band(col)
    y0, y1 = band(row, 0.45)
    return x0, y0, x1, y1


def hline_count(g, box, min_frac=0.75, gap_frac=0.05):
    """数「长横线」：檐口在照片里表现为又长又暗的水平条。"""
    x0, y0, x1, y1 = box
    sub = g[y0:y1, x0:x1]
    dark = (sub < sub.mean() - 0.10)
    width = sub.shape[1]
    counts, rows = [], []
    for yy in range(sub.shape[0]):
        c = int(dark[yy].sum())
        counts.append(c)
    counts = np.asarray(counts, dtype=np.float32)
    thr = counts.max() * min_frac
    # 找局部极大、且彼此至少隔 2% 图高
    peaks = []
    gap = max(4, int(sub.shape[0] * gap_frac))
    for i in range(1, len(counts) - 1):
        if counts[i] >= thr and counts[i] >= counts[i - 1] and counts[i] >= counts[i + 1]:
            if not peaks or i - peaks[-1] > gap:
                peaks.append(i)
    return len(peaks), [round((y0 + p) / g.shape[0], 3) for p in peaks]


def detect_bands(g, box, top_n=12, min_frac=0.35):
    """找主体里的水平结构线（台基上沿 / 额枋 / 檐口 / 正脊 / 鸱尾尖）。

    做法：只看主体中间 70% 宽（避开树、配楼），逐行统计「暗像素 + 竖直梯度」，
    取峰值并合并相邻 1.5% 图高的峰，返回 [(归一化 y, 强度)] 由强到弱。
    """
    x0, y0, x1, y1 = box
    w = x1 - x0
    cx0, cx1 = int(x0 + w * 0.15), int(x0 + w * 0.85)
    sub = g[y0:y1, cx0:cx1]
    dark = (sub < np.percentile(sub, 35)).astype(np.float32)
    grad = np.abs(np.diff(sub, axis=0, prepend=sub[:1, :]))
    score = dark.sum(axis=1) / max(1, sub.shape[1]) + grad.mean(axis=1) * 4.0
    # 平滑，避免瓦垄这种高频纹理把峰打散
    k = np.ones(5) / 5.0
    score = np.convolve(score, k, mode='same')
    thr = score.max() * min_frac
    peaks = []
    for i in range(1, len(score) - 1):
        if score[i] >= thr and score[i] >= score[i - 1] and score[i] > score[i + 1]:
            peaks.append((i, float(score[i])))
    peaks.sort(key=lambda t: -t[1])
    keep = []
    min_gap = max(4, int(sub.shape[0] * 0.015))
    for i, v in peaks:
        if all(abs(i - j) > min_gap for j, _ in keep):
            keep.append((i, v))
        if len(keep) >= top_n:
            break
    keep.sort(key=lambda t: t[0])
    return [((y0 + i) / g.shape[0], round(v / (score.max() or 1), 2)) for i, v in keep]


def draw_bands(src, box, bands, out):
    """把候选线画回照片，带序号 —— 人眼确认哪条是哪条。"""
    from PIL import ImageDraw
    im = Image.open(src).convert('RGB')
    d = ImageDraw.Draw(im)
    x0, y0b, x1, y1b = box
    for k, (yn, st) in enumerate(bands):
        y = int(yn * im.height)
        d.line([(0, y), (im.width, y)], fill=(200, 40, 40), width=max(1, im.width // 500))
        d.text((8, y - 14), str(k), fill=(200, 40, 40))
    d.rectangle([x0, y0b, x1, y1b], outline=(40, 120, 200), width=max(1, im.width // 500))
    im.save(out)


def symmetry(g, box):
    x0, y0, x1, y1 = box
    sub = g[y0:y1, x0:x1]
    w = sub.shape[1]
    half = w // 2
    left = sub[:, :half]
    right = sub[:, w - half:][:, ::-1]
    n = min(left.shape[1], right.shape[1])
    a = left[:, :n] - left[:, :n].mean()
    b = right[:, :n] - right[:, :n].mean()
    denom = math.sqrt(float((a * a).sum() * (b * b).sum())) or 1e-6
    return float((a * b).sum() / denom)



# —— 矫正（roll / 四点透视） ——————————————————————————————

def _line_angle(g, box, y0, y1, thr=0.02):
    """在 [y0,y1] 窗口里逐列找最强竖直梯度，拟合水平线倾角（度）。g 为 0..1 灰度。"""
    g = np.abs(np.diff(g, axis=0))
    H, W = g.shape
    x0, x1 = int(box['x0'] * W), int(box['x1'] * W)
    win = g[int(y0 * H):int(y1 * H), x0:x1]
    ys = []
    for c in range(win.shape[1]):
        col = win[:, c]
        if col.max() < thr:
            continue
        ys.append(int(y0 * H) + int(np.argmax(col)))
    if len(ys) < 20:
        return None, 0
    xs = np.arange(x0, x0 + len(ys))
    k, _ = np.polyfit(xs, ys, 1)
    return math.degrees(math.atan(k)), len(ys)


def estimate_roll(g, box):
    """取台基与檐口两条线倾角的中位数；返回 (角度, [(窗口, 角度)])。"""
    got = []
    for y0, y1 in ((0.66, 0.75), (0.46, 0.53)):
        a, n = _line_angle(g, box, y0, y1)
        if a is not None:
            got.append(round(a, 2))
    if not got:
        return 0.0, []
    return float(np.median(got)), got


def apply_roll(im, deg):
    """旋转拉平：deg 为检测到的倾角（y 随 x 增大而减小为正角），旋转方向取反。"""
    return im.rotate(deg, resample=Image.BICUBIC, expand=False, fillcolor=(255, 255, 255))


def homography(src, dst):
    """四点透视：解 8 个系数，供 PIL PERSPECTIVE 用。src/dst 为 4 个 (x,y)。"""
    A, b = [], []
    for (x, y), (u, v) in zip(src, dst):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); b.append(u)
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y]); b.append(v)
    h = np.linalg.solve(np.array(A, float), np.array(b, float))
    return tuple(h.tolist())


def apply_quad(im, quad, out_w=None, out_h=None):
    """quad = 4 个归一化点（TL,TR,BR,BL），把这块四边形拉成正矩形。

    纵向比值用不到真实长宽比：目标矩形取任意比例，等价于再乘一个各向异性缩放，
    竖直方向的**比例**不变。所以 out_w/out_h 只要形状合理即可。
    """
    W, H = im.size
    src = [(quad[i] * (W if i % 2 == 0 else H)) for i in range(8)]
    src = list(zip(src[0::2], src[1::2]))
    w = out_w or int((((src[1][0]-src[0][0])**2 + (src[1][1]-src[0][1])**2) ** .5 +
                      ((src[2][0]-src[3][0])**2 + (src[2][1]-src[3][1])**2) ** .5) / 2)
    h = out_h or int((((src[3][0]-src[0][0])**2 + (src[3][1]-src[0][1])**2) ** .5 +
                      ((src[2][0]-src[1][0])**2 + (src[2][1]-src[1][1])**2) ** .5) / 2)
    dst = [(0, 0), (w, 0), (w, h), (0, h)]
    coeffs = homography(src, dst)
    return im.transform((w, h), Image.PERSPECTIVE, coeffs, Image.BICUBIC)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--photo', required=True)
    ap.add_argument('--out', default=None)
    ap.add_argument('--family', default=None, help='已知家族就直接指定，脚本只量尺寸')
    ap.add_argument('--mark', default=None, help='把候选水平线画回照片，输出到这张图')
    ap.add_argument('--rectify', default='roll', choices=['none', 'roll', 'quad'],
                    help='取线前先矫正：roll=自动拉平（默认），quad=四点透视，none=不矫正')
    ap.add_argument('--quad', default=None,
                    help='--rectify quad 用的 4 个角（归一化，TL,TR,BR,BL），'
                         '如 0.10,0.70,0.90,0.70,0.90,0.75,0.10,0.75')
    ap.add_argument('--lines', default=None,
                    help='人工确认的 4 条线：可给候选序号（如 10,9,7,6），'
                         '也可直接给归一化 y（带小数，如 0.703,0.542,0.492,0.416），'
                         '顺序均为 台基上沿,柱顶,檐口,正脊')
    a = ap.parse_args()

    im_color = Image.open(a.photo).convert('RGB')
    rect_info = {'mode': a.rectify}
    if a.rectify != 'none':
        g0, box0 = load_gray(a.photo, ret_box=True)
        if a.rectify == 'roll':
            ang, got = estimate_roll(g0, box0)
            im_color = apply_roll(im_color, ang)
            rect_info.update({'angle_deg': round(ang, 2), 'lines_deg': got})
        else:
            if not a.quad:
                raise SystemExit('--rectify quad 需要 --quad（8 个归一化数）')
            q = [float(t) for t in a.quad.split(',')]
            if len(q) != 8:
                raise SystemExit('--quad 需要 8 个数（TL,TR,BR,BL 的 x,y）')
            im_color = apply_quad(im_color, q)
            rect_info.update({'quad': q, 'size': list(im_color.size)})
        tmp = '/tmp/_rectified.png'
        im_color.save(tmp)
        a.photo = tmp
    g = load_gray(a.photo)
    e = edge_energy(g)
    box = subject_box(e)
    H, W = g.shape
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    rows = g[y0:y1, x0:x1].mean(axis=1)
    # 天际线：主体框里亮度由「天空」变「建筑」的那一行
    sky = float(np.percentile(rows, 90))
    ground = float(np.percentile(rows, 10))
    n_line, line_pos = hline_count(g, box)
    sym = symmetry(g, box)
    bands = detect_bands(g, box)
    if a.mark:
        draw_bands(a.photo, box, bands, a.mark)

    report = {
        'photo': a.photo,
        'image': {'w': W, 'h': H},
        'subject': {'x0': round(x0 / W, 3), 'y0': round(y0 / H, 3),
                    'x1': round(x1 / W, 3), 'y1': round(y1 / H, 3),
                    'aspect': round(w / max(1, h), 2)},
        'measure': {
            'sky_luma': round(sky, 3), 'ground_luma': round(ground, 3),
            'candidate_eave_lines': n_line,        # 候选檐口线（含少量瓦垄/台基线，需人眼确认）
            'line_positions': line_pos,            # 归一化 y（0=顶, 1=底）
            'lr_symmetry': round(sym, 3),          # 只对正立面照有意义；3/4 视角偏低属正常
            'note': '檐数请人眼数「并排且等距」的那几条长线，不要直接用 candidate 数',
        },
        'guess': {},
        'todo': [
            '屋顶形式（攒尖/歇山/庑殿/硬山/卷棚/无顶）→ family + style',
            '檐数：数清几重檐（照片上「并排的水平檐口线」有几道）→ eaves',
            '平面形状：方/长方/六角/八角 → plan，若照片只给一个角，写 unknown',
            '面阔间数：数柱间（仅正面可见时写 at_least_n）',
            '有无斗拱、有无平坐、台基几级',
            '比例：先按「面阔 ≈ 3.6–4.2m、层高 ≈ 2.2–2.6m」占位，再用照片比例校',
        ],
        'confidence': {},
        'evidence': [],
    }
    report['measure']['rectified'] = rect_info
    report['measure']['bands'] = [{'i': i, 'y': y, 'strength': st}
                                  for i, (y, st) in enumerate(bands)]

    # —— 按照片量比例 ——
    # 四条线（y 向下增大）：台基上沿 / 柱顶（斗拱下）/ 檐口下沿 / 正脊
    if a.lines:
        toks = [t.strip() for t in a.lines.split(',') if t.strip()]
        if len(toks) != 4:
            raise SystemExit('--lines 需要 4 个值（台基上沿,柱顶,檐口,正脊）')
        if any('.' in t for t in toks):
            ybase, ycol, yeave, yridge = [float(t) for t in toks]
        else:
            idx = [int(t) for t in toks]
            if max(idx) >= len(bands):
                raise SystemExit('序号越界：只有 %d 条候选线' % len(bands))
            ybase, ycol, yeave, yridge = [bands[i][0] for i in idx]
        if not (yridge < yeave < ycol < ybase):
            raise SystemExit('顺序不对：需要 正脊 < 檐口 < 柱顶 < 台基上沿（y 向下增大）')
        tot = ybase - yridge          # 台基上沿 → 正脊（不含台基）
        col = ybase - ycol
        brk = ycol - yeave
        roof = yeave - yridge
        report['measure']['ratios'] = {
            'col_over_total': round(col / tot, 3),
            'bracket_over_total': round(brk / tot, 3),
            'roof_over_total': round(roof / tot, 3),
            'bracket_over_col': round(brk / col, 3),
            'roof_over_col': round(roof / col, 3),
            'span_px': round(tot, 4),
            'note': '占「台基上沿→正脊」的比例；bracket_over_col 可直接当 job 的 bracket_h',
        }

    fam = a.family
    if not fam:
        # 极保守的猜测：只用「横线数 + 对称 + 主体比例」，判不出来就 unknown
        if n_line >= 3 and 0.8 <= (w / max(1, h)) <= 1.8:
            fam = 'ting'
            report['guess']['family'] = 'ting'
            report['guess']['reason'] = '主体近方、长横线多（多层檐口）——先按亭试'
            report['confidence']['family'] = 0.4
        elif (w / max(1, h)) > 2.0:
            fam = 'dian'
            report['guess']['family'] = 'dian'
            report['guess']['reason'] = '主体明显横向拉长——先按殿堂/廊试'
            report['confidence']['family'] = 0.35
        else:
            report['guess']['family'] = 'unknown'
            report['confidence']['family'] = 0.0
            fam = 'ting'
        report['guess']['eaves'] = 'unknown'
        report['confidence']['eaves'] = 0.0
        report['evidence'].append('檐数未判：照片里瓦垄与檐口同向，必须人眼数并排等距的檐口线')

    job = {
        'family': fam,
        'ratio': '3:4',
        'photo': a.photo,
        'title': '待定 · 构造关系轴测',
        'subtitle': '· 构造关系轴测',
        'desc': ['（形制待复核）', '透明画法：屋面为玻璃罩，被遮构件降为浅虚线。'],
        'params': {},
        '_analyze': report,
    }
    if a.out:
        with open(a.out, 'w', encoding='utf-8') as f:
            json.dump(job, f, ensure_ascii=False, indent=1)

    print(json.dumps(report, ensure_ascii=False, indent=1))
    if a.out:
        print('\n草案已写入 %s —— 改完 family/params 再出图：' % a.out)
        print('  python3 scripts/structure_plate.py --json %s --out out/x.png' % a.out)


if __name__ == '__main__':
    main()
