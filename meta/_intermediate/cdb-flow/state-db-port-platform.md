# state-db-port Phase H — プラットフォーム差調査

調査日: 2026-05-19
対象ソース:
- `sonic-swss/portsyncd/linksync.cpp`
- `sonic-swss/orchagent/portsorch.cpp`
- `sonic-swss/orchagent/orchdaemon.cpp`

## portsyncd / linksync — プラットフォーム差なし

`linksync.cpp` に `getenv("platform")`、`gMySwitchType`、ASIC 種別参照が存在しない。
`PORT_TABLE` への `state`、`admin_status`、`mtu`、`netdev_oper_status` フィールド書き込みは
全プラットフォーム共通ロジック。

## PortsOrch — フィールド別プラットフォーム差

### isMlnxPlatform() — PORT_TABLE への影響なし

`portsorch.cpp:689` の `isMlnxPlatform()` は Flex Counter のトリムスタットプラグイン登録可否にのみ
使われ（portsorch.cpp:858）、STATE_DB PORT_TABLE フィールドの書き込みには関与しない。

### supported_fecs — ベンダー SAI 依存

`getPortSupportedFecModes()` が SAI_STATUS_SUCCESS 以外を返した場合（SAI が FEC モード取得を
未サポート）、`supported_fecs` フィールドは STATE_DB に書き込まれない（portsorch.cpp:3281-3283）。
つまり `supported_fecs` の有無はベンダー SAI 実装に依存する。

さらに `"auto"` エントリの付加は `fec_override_sup`（`SAI_PORT_ATTR_AUTO_NEG_FEC_MODE_OVERRIDE`
の set/create capability）が true の場合のみ（portsorch.cpp:3308-3310）。これもベンダー SAI 依存。

### host_tx_ready — Gearbox / CMIS 依存

- Gearbox なし・`m_cmisModuleAsicSyncSupported=false`: orchagent が admin UP/DOWN 変化時に直接
  `hset("host_tx_ready", "true"/"false")` を書き込む（portsorch.cpp:2253-2257, 2246-2249）。
- Gearbox 搭載（`m_gearboxEnabled=true`）: `setGearboxPortsAttr()` の結果次第で true/false が決まる。
  フィールド名・値は同一、取得経路のみ異なる。
- `m_cmisModuleAsicSyncSupported=true`（CMIS ZR 等の光トランシーバ対応 ASIC）: orchagent は
  `host_tx_ready` を直接書かない。SAI コールバック `on_port_host_tx_ready`（portsorch.cpp:977）
  が代わりに SET する。フィールド名・値は同一。

### gMySwitchType による差異

| switch_type | PORT_TABLE への影響 |
|-------------|-------------------|
| `"switch"` | 通常動作。全フィールドが適宜書き込まれる |
| `"voq"` | `PortsOrch` は VOQ chassis 上の linecard asic として動作。PORT_TABLE 書き込みロジックに変化なし。VOQ 固有処理（System Port、LAG ID）は PORT_TABLE とは別テーブル |
| `"dpu"` | 初期化時の System Port 取得・1Q ブリッジ削除・FDB 通知設定がスキップされる（portsorch.cpp:987-1056）が、その後の PORT_TABLE フィールド書き込みロジックに差異なし |
| `"fabric"` | `FabricOrchDaemon` では `PortsOrch` が起動しない。STATE_DB PORT_TABLE は portsyncd（linksync）のみが書く |

## multi-asic / VOQ chassis

multi-asic 構成では各 asic namespace に独立した `portsyncd` / `PortsOrch` が存在し、
それぞれの namespace 内 STATE_DB に書き込む。フィールド・値・書込みロジックに差異なし。

## 結論

PORT_TABLE のプラットフォーム差:
1. `supported_fecs`: ベンダー SAI が FEC モード取得をサポートしない場合はフィールド不在
2. `supported_fecs` の `"auto"` エントリ: SAI `fec_override_sup` capability 依存
3. `host_tx_ready` 書込み主体: CMIS 対応 ASIC では SAI コールバック経由（値は同一）
4. `fabric` switch_type: `PortsOrch` 不起動により orchagent 由来フィールド（speed、fec 等）が書かれない
