#!/usr/bin/env python3
"""把霞鹜文楷（LXGW WenKai）下载到 assets/fonts/，或从本地文件复制。

字体不进仓库（18MB，占跟踪体积约 3/4），首次使用前跑一次就行：

    python3 scripts/fetch_font.py                 # 从 GitHub Releases 下最新的 Regular
    python3 scripts/fetch_font.py --from ~/Downloads/LXGWWenKai-Regular.ttf
    python3 scripts/fetch_font.py --check          # 只看现在能不能找到字体

下载失败也不要紧：`structure_plate.py` 的字体候选里还有 Songti / 文泉驿 / 微软雅黑等
系统字体，只是标题的楷体味道会变成宋体。
"""
import argparse
import json
import os
import shutil
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEST = os.path.join(ROOT, 'assets', 'fonts', 'LXGWWenKai-Regular.ttf')
API = 'https://api.github.com/repos/lxgw/LxgwWenKai/releases/latest'
# 接口挂了就试这几个固定 tag（asset 名一致）
PINNED = [
    'https://github.com/lxgw/LxgwWenKai/releases/download/v1.520/LXGWWenKai-Regular.ttf',
    'https://github.com/lxgw/LxgwWenKai/releases/download/v1.510/LXGWWenKai-Regular.ttf',
    'https://github.com/lxgw/LxgwWenKai/releases/download/v1.500/LXGWWenKai-Regular.ttf',
]
ASSET = 'LXGWWenKai-Regular.ttf'


def cache_dir():
    return os.path.join(os.path.expanduser('~'), '.cache', 'march-aa')


def find_existing():
    for p in (DEST, os.path.join(cache_dir(), ASSET)):
        if os.path.exists(p) and os.path.getsize(p) > 1_000_000:
            return p
    return None


def download(url, dest, label=''):
    print('↓ %s' % (label or url))
    req = urllib.request.Request(url, headers={'User-Agent': 'march-aa/fetch_font'})
    tmp = dest + '.part'
    with urllib.request.urlopen(req, timeout=120) as r, open(tmp, 'wb') as f:
        shutil.copyfileobj(r, f, 1 << 20)
    if os.path.getsize(tmp) < 1_000_000:
        os.remove(tmp)
        raise RuntimeError('下载内容过小，可能不是字体文件')
    os.replace(tmp, dest)
    print('  → %s (%.1f MB)' % (dest, os.path.getsize(dest) / 1048576))


def from_release_api(dest):
    with urllib.request.urlopen(API, timeout=30) as r:
        meta = json.load(r)
    for a in meta.get('assets', []):
        if a.get('name') == ASSET:
            download(a['browser_download_url'], dest, meta.get('tag_name', ''))
            return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--from', dest='src', help='本地已有的 ttf 路径（离线安装）')
    ap.add_argument('--check', action='store_true', help='只检查，不下载')
    ap.add_argument('--force', action='store_true', help='已有也重下')
    a = ap.parse_args()

    found = find_existing()
    if a.check:
        print('字体：', found or '未找到（会退回系统字体）')
        return 0 if found else 1
    if found and not a.force and not a.src:
        print('已存在：', found)
        return 0

    os.makedirs(os.path.dirname(DEST), exist_ok=True)
    if a.src:
        src = os.path.expanduser(a.src)
        if not os.path.exists(src):
            print('找不到：', src)
            return 2
        shutil.copyfile(src, DEST)
        print('已复制 →', DEST)
        return 0

    try:
        if from_release_api(DEST):
            return 0
    except Exception as e:
        print('  接口方式失败：%s' % e)
    for url in PINNED:
        try:
            download(url, DEST)
            return 0
        except Exception as e:
            print('  失败：%s' % e)
    print('\n没下成。可以手动下载后跑：python3 scripts/fetch_font.py --from <路径.ttf>')
    print('发布页：https://github.com/lxgw/LxgwWenKai/releases')
    return 2


if __name__ == '__main__':
    sys.exit(main())
