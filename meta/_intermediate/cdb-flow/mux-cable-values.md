# 値依存挙動分析: MUX_CABLE

## Phase 1: YANG フィールド全列挙

- `ifname` (leafref PORT.name, key)
- `cable_type` (enum): `active-active`/`active-standby`, default `active-standby`
- `prober_type` (enum): `hardware`/`software`, default `software`
- `neighbor_mode` (enum): `prefix-route`/`host-route`, default `host-route`
- `server_ipv4` (ipv4-prefix)
- `server_ipv6` (ipv6-prefix)
- `soc_ipv4` (ipv4-prefix)
- `soc_ipv6` (ipv6-prefix)
- `state` (enum): `auto`/`manual`/`detach`/`active`/`standby`, default `auto`

## Phase 2: per-value explicit grep

- `sonic-linkmgrd/src/DbInterface.cpp`: `mMuxState = {"active", "standby", "unknown", "Error"}`
- `sonic-linkmgrd/src/DbInterface.cpp`: `portCableType` default = `"active-standby"` when not found
- `sonic-linkmgrd/src/MuxManager.cpp`: `cableType == "active-standby"` → `active-standby` SM 選択
- `sonic-linkmgrd/src/MuxManager.cpp`: `cableType == "active-active"` → `active-active` SM 選択
- `sonic-linkmgrd/src/MuxPort.cpp`: `detach mode is only supported for acitve-active cable type` (WARN)
- `sonic-swss/orchagent/muxorch.cpp`: `neighbor_mode = "prefix-route"` → prefix-based NbrHandler 選択

## Phase 3: 専用ファイル確認

- `sonic-linkmgrd/src/MuxManager.cpp`: 未知の cable_type → active-standby にフォールバック (WARN ログ)
- `muxorch.cpp`: neighbor_mode 変更は動的には不可 (初期設定のみ有効)

## Phase 5: 値依存挙動マトリクス

| フィールド | 値 | 挙動 |
|-----------|-----|------|
| `state` | `auto` (default) | ICMP prober の判断で active/standby を自動決定。フェイルオーバも自動 |
| `state` | `active` | 当該 ToR を強制 active。linkmgrd が MUX を active 側に固定 |
| `state` | `standby` | 当該 ToR を強制 standby。トラフィックをピア ToR 経由に迂回 |
| `state` | `manual` | 自動フェイルオーバ無効。現在の active/standby 状態を維持 |
| `state` | `detach` | active-active 専用。NIC から ToR を論理的に切り離し。active-standby では WARN + 無視 |
| `cable_type` | `active-standby` (default) | ActiveStandby ステートマシン選択。ICMP prober で片系のみ active |
| `cable_type` | `active-active` | ActiveActive ステートマシン選択。両 ToR が active。SoC IP 必須 |
| `prober_type` | `software` (default) | linkmgrd が ICMP パケットをソフトウェアで生成 |
| `prober_type` | `hardware` | xcvrd 経由でハードウェア MUX に probe を委譲 |
| `neighbor_mode` | `host-route` (default) | サーバ IP を /32 (/128) host route として処理 |
| `neighbor_mode` | `prefix-route` | サーバ IP を prefix-based route として処理。SoC IP は prefix_route 扱い |

neighbor_mode の動的変更は muxorch.cpp で検出し WARN ログ (再起動が必要)。
