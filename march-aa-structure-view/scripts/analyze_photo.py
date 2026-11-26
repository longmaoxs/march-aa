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


def load_gray(path, maxw=900):
    im = Image.open(path).convert('L')
    if im.width > maxw:
        im = im.resize((maxw, int(im.height * maxw / im.width)), Image.LANCZOS)
    return np.asarray(im, dtype=np.float32) / 255.0


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--photo', required=True)
    ap.add_argument('--out', default=None)
    ap.add_argument('--family', default=None, help='已知家族就直接指定，脚本只量尺寸')
    a = ap.parse_args()

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
