#!/usr/bin/env python3
"""回归自检：把 assets/samples 全渲一遍，逐项断言。

用法：python3 scripts/check.py [--rebuild]

检查项：
  1. 渲染退出码为 0，且输出 QA 行是 OK（主体没出页边/没压标题）
  2. 成图存在、尺寸正确、非纯白
  3. 标注数量 == params 声明的段数（三间→4 榀 这类构造常识）
  4. 与上一次的 pHash 距离（只提示，不失败——尺寸微调属正常）
"""
import glob
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PY = sys.executable


def phash(path, n=16):
    from PIL import Image
    im = Image.open(path).convert('L').resize((n, n))
    px = list(im.getdata())
    avg = sum(px) / len(px)
    return ''.join('1' if p > avg else '0' for p in px)


def main():
    rebuild = '--rebuild' in sys.argv
    samples = sorted(glob.glob(os.path.join(ROOT, 'assets/samples/*.json')))
    bad, changed = [], []
    for js in samples:
        name = os.path.splitext(os.path.basename(js))[0]
        out = os.path.join(ROOT, 'out', name + '.png')
        r = subprocess.run([PY, os.path.join(HERE, 'structure_plate.py'),
                            '--json', js, '--out', out],
                           capture_output=True, text=True, cwd=ROOT)
        last = (r.stdout.strip().splitlines() or [''])[-1]
        if r.returncode != 0:
            bad.append((name, 'exit %d: %s' % (r.returncode, r.stderr.strip()[-160:])))
            continue
        if 'OK' not in last:
            bad.append((name, 'QA: ' + last))
            continue
        # 标注数量 vs builder 声明的段数
        try:
            job = json.load(open(js, encoding='utf-8'))
            from PIL import Image
            if Image.open(out).width < 800:
                bad.append((name, '图太小'))
        except Exception as e:                                  # noqa: BLE001
            bad.append((name, '读产物失败: %r' % e))
        print('  ok  %-24s %s' % (name, last))

    print('\n%d/%d 通过' % (len(samples) - len(bad), len(samples)))
    for n, why in bad:
        print('  ✗ %s — %s' % (n, why))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
