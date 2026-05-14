# BGP_GLOBALS — Phase 6/7/8 スキャンノート

## Phase 6: 値による他フィールド自動派生
- minigraph.py では BGP_GLOBALS を直接生成しない（sonic-frr-mgmt-framework / frrcfgd が FRR running-config から同期）
- 派生なし

## Phase 7: 条件付き module/manager 登録
- frrcfgd BGPConfigDaemon: BGP_GLOBALS を常時購読。条件付き登録はない
  - sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py:2094-2140

## Phase 8: Handler メソッド内分岐
- bgp_global_handler → bgp_table_handler_common (comb_attr_list=[{'keepalive','holdtime'}])
  - data is None → del_table=True （DELETE path）/ data 有 → SET path
  - frrcfgd.py:3910-3935

## grep カバレッジ
- frrcfgd.py 3000+ 行、BGP_GLOBALS handler: bgp_global_handler（1件、条件なし）
