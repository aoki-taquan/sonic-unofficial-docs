# WARM_RESTART — 値依存挙動メモ

## module: bgp / teamd / swss / system
- bgp → bgp_eoiu, bgp_timer が有効。bgpcfgd が vtysh の graceful-restart 設定に変換
- teamd → teamsyncd_timer が有効。teamd が LAG 再収束タイムアウトとして使用
- swss → neighsyncd_timer が有効。neighsyncd が ARP/route reconciliation 待ちに使用
- system → システム全体の warm-restart 有効/無効制御。個別タイマなし
- その他の値 → YANG バリデーションで reject

## bgp_eoiu: true / false
- true → BGP End-of-Initial-Update シグナルを待つ（再収束完了の判定に使用）
- false → EOIU なしで再収束完了と判定
- must "module = 'bgp'" (YANG)

## bgp_timer: 1..3600 (秒)
- bgpcfgd が graceful-restart restart-time <val> として vtysh に設定
- must "module = 'bgp'" (YANG)
- 典型値: 300

## teamsyncd_timer: 1..3600 (秒)
- teamd が LAG 再収束タイムアウトとして使用
- must "module = 'teamd'" (YANG)

## neighsyncd_timer: 1..9999 (秒)
- neighsyncd が ARP/NDP reconciliation 待ちに使用
- must "module = 'swss'" (YANG)
- 典型値: 110

## enable フィールドについて
- CONFIG_DB の WARM_RESTART テーブルには enable フィールドはない
- enable/disable は STATE_DB の WARM_RESTART_ENABLE_TABLE および `config warm_restart enable` コマンドで扱う
- 各 mgr/daemon は起動時に CONFIG_DB からタイマ値を読み込む

Sources:
- sonic-buildimage/src/sonic-yang-models/yang-models/sonic-warm-restart.yang
- sonic-swss-common/common/warm_restart.cpp
- sonic-swss/doc/swss-schema.md
