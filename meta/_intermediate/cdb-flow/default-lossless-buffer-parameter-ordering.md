# DEFAULT_LOSSLESS_BUFFER_PARAMETER — Phase B 書込み順依存

slug: default-lossless-buffer-parameter
phase: B (ordering)
generated: 2026-05-18

## 検出した順序依存 (4件)

| # | 依存関係 | 方向 | 緩和策 | evidence |
|---|----------|------|--------|----------|
| 1 | `BUFFER_POOL\|ingress_lossless_pool` 登録済み → `DEFAULT_LOSSLESS_BUFFER_PARAMETER` SET 処理 | 強制先行 | pool 未登録時 task_need_retry | buffermgrdyn.cpp:1985-1988 |
| 2 | `default_dynamic_th` 設定 → lossless BUFFER_PROFILE 命名確定 | 強制先行 | 空状態で生成するとプロファイル名スキームが後から変わる | buffermgrdyn.cpp:494-496 |
| 3 | `over_subscribe_ratio` 非ゼロ + `m_portInitDone=true` → SAI SHP 有効化確認 | 強制先行 | SAI 反映前は task_need_retry | buffermgrdyn.cpp:2019-2025, 2035-2046 |
| 4 | DEL → `over_subscribe_ratio` 空リセット → refreshSharedHeadroomPool | 即時 (過去値破棄) | 再設定には再度 SET 必要 | buffermgrdyn.cpp:2005-2008 |

## 調査メモ

- handleDefaultLossLessBufferParam L1978-2046 全行読了
- isSharedHeadroomPoolEnabledInSai L2034-2050 全行読了
- buffermgrdyn.cpp L494-496 読了
- buffermgrdyn.h L14: INGRESS_LOSSLESS_PG_POOL_NAME = "ingress_lossless_pool"
