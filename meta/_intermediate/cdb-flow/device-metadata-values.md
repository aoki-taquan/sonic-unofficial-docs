# DEVICE_METADATA フィールド値分析

## enum フィールド

### `default_bgp_status` (enum up/down)
- `up` (デフォルト) → bgpcfgd 起動時に BGP daemon を auto-start 状態にする
- `down` → BGP daemon を shutdown 状態で起動（メンテ用）

### `docker_routing_config_mode` (pattern: separated/unified/split/split-unified)
- `separated` → minigraph デフォルト。bgp docker で frr.conf を独立管理、FRR + bgpcfgd が bgp テンプレを生成
- `unified` → frrcfgd (sonic-frr-mgmt-framework) が起動時に全 BGP テーブルをリプレイしてから CONFIG_DB 変更を監視
- `split` / `split-unified` → hybrid。frrcfgd が `config_mode = "separated"` として動作（コード: frrcfgd.py:2170）
- 未設定 → frrcfgd が `"separated"` とみなす（frrcfgd.py:2170）

### `default_pfcwd_status` (enum disable/enable)
- `enable` → `config load` / `config reload` 後に `pfcwd start_default` が自動実行される（config/main.py:2434）
- `disable` (デフォルト) → pfcwd は自動起動しない
- MgmtToRRouter / MgmtTsToR / BmcMgmtToRRouter / EPMS の type では pfcwd 呼び出し自体がスキップ

### `synchronous_mode` (enum enable/disable)
- `enable` (デフォルト) → orchagent.sh が `-s` フラグを付与して orchagent を synchronous mode で起動（SAI 操作がブロッキング）
- `disable` → orchestrator は非同期 SAI; switch_type=dpu のとき enable でも zmq_sync モードが優先（orchagent.sh:39-41）

### `suppress-fib-pending` (enum enabled/disabled)
- `enabled` → bgpcfgd/managers_bgp.py:502 で `bgp suppress-fib-pending` を FRR に適用
- `disabled` (デフォルト) → suppress-fib-pending なし
- YANG must: `enabled` のとき `synchronous_mode = enable` が必須（違反は YANG validate で reject）

### `yang_config_validation` (enum enable/disable)
- `enable` → sonic-cfggen が config_db.json 直接ロード時に YANG スキーマ検証を実施
- `disable` (デフォルト) → スキーマ検証なし（高速ロード）

### `async_swss_rec` (enum enabled/disabled)
- `enabled` → orchagent の swss.rec 書き込みを非同期化（高トラフィック時の遅延軽減）
- `disabled` (デフォルト) → 同期書き込み

### `nexthop_group` (enum enabled/disabled)
- `enabled` → boot 時のみ orchagent が Nexthop Group 機能を有効化（SAI nexthop group API 使用）
- `disabled` (デフォルト) → 従来 ECMP 方式

### `zebra_nexthop` (enum enabled/disabled)
- `enabled` (デフォルト) → boot 時のみ FRR/Zebra が next-hop group を使用
- `disabled` → next-hop group 無効

### `buffer_model` (pattern: dynamic/traditional)
- `dynamic` → buffermgr.cpp:393-394 で `dynamic_buffer_model = true` → BUFFER_POOL/PROFILE テーブル変更を buffermgr が無視し、dynamic buffer mgr (Mellanox 等) が SAI 直接更新
- `traditional` (またはその他) → `dynamic_buffer_model = false` → buffermgr が CONFIG_DB の BUFFER_POOL/PROFILE を APPL_DB に転写

### `frr_mgmt_framework_config` (boolean: true/false)
- `true` → sonic-frr-mgmt-framework (frrcfgd) が FRR 設定を担当。BGP_NEIGHBOR 等の汎用テーブルを frrcfgd が受け付ける
- `false` (デフォルト) → bgpcfgd が J2 テンプレを展開して frr.conf を生成

### `switch_type` (pattern: chassis-packet/fabric/npu/voq/dpu/dummy-sup)
- `voq` → orchestagent が VOQ モードで起動、switch_id を SAI に渡す（VoQ チャーシス用）
- `fabric` → orchagent が SAI_SWITCH_TYPE_FABRIC として作成、switch_id 必須（未設定で exit）
- `dpu` → orchagent.sh が zmq_sync + bulk limit 65536 で起動
- `npu` / 未設定 / 不正値 → 通常スイッチとして扱う（main.cpp:262-264）

### `subtype` (pattern: DualToR/SmartSwitch/Supervisor/UpstreamLC/DownstreamLC)
- `DualToR` → dual ToR トポロジ用。peer_switch 指定が運用上必要
- `SmartSwitch` → SmartSwitch トポロジ
- `Supervisor` / `UpstreamLC` / `DownstreamLC` → VoQ chassis 用

## boolean フィールド

### `bgp_adv_lo_prefix_as_128`
- `true` → Loopback0 の IPv6 /128 アドレスをそのまま BGP 広告
- `false` / 未設定 → /64 に丸めて広告（デフォルト動作）

### `ring_thread_enabled`
- `true` → OrchDaemon の gRingMode 有効化
- `false` (デフォルト) → 通常スレッドモード

## cross-cutting
- `switch_type = voq` のとき `asic_name` と `switch_id` が必須（VoQ key 修飾子）
- `suppress-fib-pending = enabled` には `synchronous_mode = enable` が必須（YANG must constraint）
- `buffer_model = dynamic` は Mellanox 等プラットフォーム専用。他プラットフォームで設定すると BUFFER_POOL が二重管理になる恐れ
