# 亭（攒尖）

- 家族键：`ting`；`params`：`side`、`eaves`(1|2)、`col_per_side`、`brackets`、`finial`、`lattice`
- 构件序：台基踏跺 → 柱网 → 额枋 + 挂落 → 斗拱 → 屋面 → 宝顶
- 重檐（`eaves=2`）：下檐是一圈裙檐，从檐口收到上层柱脚（`roof_ring`），上面接平坐楼板，再起上层柱窗、斗拱、上檐
- 出檐：`eave_half = side/2 + 0.96`；起翘 `lift≈0.26`，只让角部翘（指数 3.0）
- 画重点：戗脊（ACCENT 2.0）必须从角点收到宝顶；瓦垄是 ACCENT_SOFT 0.85，别抢戗脊
