# 字体（不进仓库）

`LXGWWenKai-Regular.ttf`（霞鹜文楷）约 18 MB，占仓库跟踪体积的四分之三，所以**不入库**。
第一次出图前跑一次：

```bash
python3 scripts/fetch_font.py            # 从 GitHub Releases 下载
python3 scripts/fetch_font.py --check    # 只检查装没装
```

离线场景：自己下载 `LXGWWenKai-Regular.ttf` 后

```bash
python3 scripts/fetch_font.py --from ~/Downloads/LXGWWenKai-Regular.ttf
```

**不装也能跑。** `scripts/structure_plate.py` 的字体候选顺序是：

1. `assets/fonts/LXGWWenKai-Regular.ttf`（或 `~/.cache/march-aa/` 下的同名文件）
2. macOS：`Songti.ttc`；Linux：`ukai.ttc`
3. 黑体兜底：`STHeiti Medium.ttc` / `Noto Sans CJK` / `wqy-microhei` / `msyh.ttc`

楷体缺失时标题会退成宋体，版式不变、字宽略不同（个别长标题可能重排）。

## 许可

LXGW WenKai 以 **SIL Open Font License 1.1** 发布，Copyright (c) 2021 LXGW / 落霞孤鹜。
许可全文见 [LICENSE-LXGWWenKai.txt](LICENSE-LXGWWenKai.txt) 与
<https://scripts.sil.org/OFL>。字体只作为本工具的出图字体使用，不随工具再分发。
