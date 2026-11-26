# job.json 结构

```json
{
  "family": "ting",
  "ratio": "3:4",
  "title": "重檐攒尖亭",
  "subtitle": "· 构造关系轴测",
  "desc": ["第一行说明", "第二行说明"],
  "photo": "/abs/path/to/source.jpg",
  "params": { }
}
```

- `family`（必填）：`ting` / `lang` / `dian` / `lou` / `ta` / `men` / `qiao`
- `ratio`：`3:4`（默认）/ `4:3` / `1:1` / `9:16`；命令行 `--ratio` 覆盖
- `title` / `subtitle` / `desc`：标题、副题、说明（各 ≤ 2 行，说明每行 ≤ 26 字为宜）
- `photo`：可选，右上照片卡；不存在时自动跳过
- `params`：按家族见下表

## params

**ting**：`plan`(`square`/`hex`/`oct`)、`side`(面阔 m)、`eaves`(1|2)、`col_per_side`、
`brackets`(bool)、`finial`(bool)、`lattice`(bool)

**lang**：`bays`(间)、`bay`(开间 m)、`depth`(进深 m)

**dian**：`style`(`xieshan`/`wudian`/`yingshan`)、`bays`、`bay`、`depth_bays`、`bayd`、`brackets`

**lou**：`side`、`floors`、`col_per_side`、`brackets`

**ta**：`style`(`louge`/`miyan`)、`storeys`、`radius`(底层外接半径 m)

**men**：`style`(`chenglou`/`pailou`)

**qiao**：`span`(净跨 m)、`rise`(拱高 m)、`width`(桥宽 m)、`arches`

所有字段都有默认值，缺省即「常规做法」。
