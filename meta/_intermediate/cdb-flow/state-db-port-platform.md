# STATE_DB PORT_TABLE — Phase H プラットフォーム差異調査

調査日: 2026-05-19
ソース: sonic-swss/orchagent/portsorch.cpp, sonic-swss/portsyncd/linksync.cpp

## switchType 分岐

### gMySwitchType == "dpu"

`portsorch.cpp:6449` の `postPortInit()` 内:

```cpp
if (gMySwitchType != "dpu")
{
    initializePortBufferMaximumParameters(p);
}
```

DPU (Data Processing Unit) 環境では buffer 最大値パラメータの初期化をスキップ。

`portsorch.cpp:6589`:

```cpp
if (gMySwitchType != "dpu")
{
    initializePriorityGroupsBulk(ports);
    initializeQueuesBulk(ports);
    initializeSchedulerGroupsBulk(ports);
}
```

DPU では Priority Group / Queue / Scheduler Group の一括初期化もスキップ。

→ DPU 環境でも `initPortSupportedSpeeds` / `initPortSupportedFecModes` は実行される (portsorch.cpp:6460-6461)。
  ただし `supported_speeds` / `supported_fecs` の有無は SAI 実装依存。

### gMySwitchType == "voq" (VoQ シャーシ)

`portsorch.cpp:1496`:

```cpp
if (gMySwitchType == "voq") {
    removeDefaultVlanMembers();
    removeDefaultBridgePorts();
}
```

VoQ 環境ではポート作成後に追加の VLAN メンバー / bridge port クリーンアップが入る。

STATE_DB PORT_TABLE への書き込み内容自体は VoQ / 非 VoQ で差異なし（同一フィールド・同一経路）。
ただし VoQ 環境の PHY ポートは `updateSystemPort()` (portsorch.cpp:11033) で SYSTEM_PORT テーブルとの
連携処理が行われる。

## SAI Capability 依存フィールド

### supported_speeds (initPortSupportedSpeeds, portsorch.cpp:3159)

SAI `get_port_attribute(SAI_PORT_ATTR_SUPPORTED_SPEED)` が失敗した場合:
- `getPortSupportedSpeeds` 内で SWSS_LOG_WARN を出力しつつ空のセットを返す
- `supported_speeds` フィールドは空文字列 `""` または不在

ベンダー SAI が `SAI_PORT_ATTR_SUPPORTED_SPEED` を実装していないプラットフォームでは
`supported_speeds` フィールドが STATE_DB に存在しない場合がある (portsorch.cpp:3144-3146)。

### supported_fecs (initPortSupportedFecModes, portsorch.cpp:3265)

`getPortSupportedFecModes` が SAI_STATUS_SUCCESS 以外を返した場合:
- `supported_fecs` フィールドを STATE_DB に書き込まない (portsorch.cpp:3279-3284)
- ログ: "No supported_fecs exposed to STATE_DB for port %s since fetching supported FEC modes is not supported by the vendor"

ベンダー SAI が `SAI_PORT_ATTR_SUPPORTED_FEC_MODE` を未実装のプラットフォームでは
`supported_fecs` が存在しない。(portsorch.cpp:3249-3251)

### fec (updateDbPortOperFec)

`oper_fec_sup` が false の場合（`SAI_PORT_ATTR_OPER_PORT_FEC_MODE` 未実装）:
- FEC oper 値取得をスキップ → `fec` フィールドは `"N/A"` に固定 (portsorch.cpp:987-1011)
- `fec_override_sup` も DPU 以外でのみクエリされる

### host_tx_ready

CMIS サポート (`m_cmisModuleAsicSyncSupported`) に依存:
- `false` の場合: orchagent が `host_tx_ready` を直接制御 → admin UP/DOWN で "true"/"false" を書く
- `true` の場合: SAI コールバック `on_port_host_tx_ready` (portsorch.cpp:977) が代わりに
  書き込みを担当するため、orchagent は直接制御しない
- 100G ZR 等の光トランシーバ対応プラットフォームで `m_cmisModuleAsicSyncSupported = true` になる

## Mellanox プラットフォーム固有

`isMlnxPlatform()` (portsorch.cpp:689) を使った分岐:

```cpp
if (isMlnxPlatform() &&
    isPortStatSupported(SAI_PORT_STAT_TRIM_PACKETS) && ...)
{
    portStatPlugins += "," + nvdaPortTrimSha;   // Nvidia trim stat plugin 追加
}
```

これは FLEX_COUNTER_DB の plugin 設定であり STATE_DB PORT_TABLE フィールドには直接影響しない。

## 結論: プラットフォーム差異サマリ

| フィールド | 差異 |
|------------|------|
| `supported_speeds` | SAI 未実装プラットフォームでは不在またはフィールドなし |
| `supported_fecs` | SAI 未実装プラットフォームでは不在 |
| `fec` | SAI `SAI_PORT_ATTR_OPER_PORT_FEC_MODE` 未実装では常時 `"N/A"` |
| `host_tx_ready` | CMIS 非対応プラットフォームでは orchagent が制御、CMIS 対応では SAI コールバックが制御 |
| DPU | buffer PG / queue / scheduler 初期化スキップ（PORT_TABLE フィールド自体は同一） |
| VoQ シャーシ | PORT_TABLE フィールドの書き込み内容は非 VoQ と同一、ただし SYSTEM_PORT 連携あり |
