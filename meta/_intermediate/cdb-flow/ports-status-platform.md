# ports-status — Phase H platform スキャンノート

## 調査対象

- `sonic-swss/portsyncd/linksync.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/orchagent/portsorch.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)

## 1. switch_type == "dpu" の影響

### linksync.cpp の DPU 分岐 (linksync.cpp:74-78)

```cpp
if (g_switchType == "dpu")
{
    return;
}
```

DPU SONiC では、カーネル netdev は syncd サービス起動時（ドライバロード時）に早期に作成され、ドライバがロードされている間ずっと存在し続ける。標準の `m_ifindexOldNameMap` による「旧インタフェース」比較ロジックは不要なため、起動時に即 `return` する。結果として DPU 環境でも linksync の RTM_NEWLINK/DELLINK ハンドリングは正常に動作し、STATE_DB `PORT_TABLE` への `state`, `admin_status`, `netdev_oper_status`, `mtu` 書き込みは発生する。

### portsorch.cpp の DPU 分岐

`gMySwitchType != "dpu"` ガードにより、DPU では以下の初期化が**スキップ**される:
- `initializePortBufferMaximumParameters()` (`portsorch.cpp:6449`) — バッファ最大値の初期化
- `initializePriorityGroupsBulk()`, `initializeQueuesBulk()`, `initializeSchedulerGroupsBulk()` (`portsorch.cpp:6589`) — PG / queue / scheduler の一括初期化
- `getSystemPorts()`, `removeDefaultVlanMembers()`, `removeDefaultBridgePorts()` (`portsorch.cpp:1043-1066`) — システムポート処理

これらのスキップは STATE_DB `PORT_TABLE` のフィールド (`speed`, `fec`, `supported_speeds`, `supported_fecs`, `host_tx_ready`, `link_training_status`, `rmt_adv_speeds`, `phy_ctrl_unreliable_los`) 書き込みロジック自体には直接影響しない。ただし `m_queue_ids` が DPU では初期化されないため、`p.m_host_tx_queue_configured && p.m_queue_ids.size() > p.m_host_tx_queue` の条件が false になり queue 関連の flex counter 設定は抑制される (`portsorch.cpp:6454`)。

## 2. Mellanox (NVIDIA Spectrum) 固有分岐

### isMlnxPlatform() とポート trim stat (portsorch.cpp:858-864)

```cpp
if (isMlnxPlatform() &&
    isPortStatSupported(SAI_PORT_STAT_TRIM_PACKETS) &&
    isPortStatSupported(SAI_PORT_STAT_TX_TRIM_PACKETS) &&
    !isPortStatSupported(SAI_PORT_STAT_DROPPED_TRIM_PACKETS))
{
    portStatPlugins += "," + nvdaPortTrimSha;
}
```

NVIDIA Spectrum 専用の trim drop Lua カウンタプラグインを flex counter グループに追加する。この分岐は STATE_DB `PORT_TABLE` のフィールドには影響しない。

### Mellanox LAG メンバー追加制限 (portsorch.cpp:6362-6379)

```
// is not supported on Mellanox platform
```

LAG 関連処理に Mellanox 制限コメントが存在するが、STATE_DB `PORT_TABLE` 書き込みパスには影響しない。

## 3. fec_override_sup / oper_fec_sup — SAI capability による platform 差異

`gMySwitchType != "dpu"` ガード内で SAI capability クエリを実行する:

```cpp
// portsorch.cpp:988-1010
if (sai_query_attribute_capability(...SAI_PORT_ATTR_AUTO_NEG_FEC_MODE_OVERRIDE...) &&
    attr_cap.set_implemented && attr_cap.create_implemented)
{
    fec_override_sup = true;
}

if (sai_query_attribute_capability(...SAI_PORT_ATTR_OPER_PORT_FEC_MODE...) &&
    oper_fec_cap.get_implemented)
{
    oper_fec_sup = true;
}
```

**`supported_fecs` への影響**: `fec_override_sup == true` の場合のみ `PORT_FEC_AUTO` が `fecModeList` に追加される (`portsorch.cpp:3310`)。`fec_override_sup == false`（非対応プラットフォーム）では `supported_fecs` から `"auto"` が除外される。

**`fec` フィールドへの影響**: `oper_fec_sup == false`（SAI oper FEC 取得非対応プラットフォーム）では `getPortOperFec()` を呼ばず、無条件に `updateDbPortOperFec(port, "N/A")` を書く (`portsorch.cpp:9693`)。対応プラットフォームでは実際の oper FEC モード文字列が書き込まれる。

## 4. Gearbox (External PHY) 対応プラットフォームの影響

`host_tx_ready` の書き込み条件が Gearbox の有無で変わる (`portsorch.cpp:2245-2256`):

```cpp
bool gbstatus = setGearboxPortsAttr(port, SAI_PORT_ATTR_ADMIN_STATE, &state);
if (gbstatus != true && !m_cmisModuleAsicSyncSupported)
{
    setHostTxReady(port, "false");  // Gearbox 操作失敗 → "false"
}
if (state && (gbstatus == true) && ... && !m_cmisModuleAsicSyncSupported)
{
    setHostTxReady(port, "true");   // admin UP + Gearbox 成功 → "true"
}
```

Gearbox 非対応プラットフォーム（`setGearboxPortsAttr()` が常に `false` を返す）では、admin UP 設定時に `gbstatus == false` となり `host_tx_ready = "false"` が書かれ続ける可能性がある。ただし `m_cmisModuleAsicSyncSupported == true` のプラットフォームでは CMIS 側が `host_tx_ready` を管理するため、この分岐は完全にスキップされる。

## 5. CMIS モジュール非同期対応 (m_cmisModuleAsicSyncSupported)

SAI が `SAI_PORT_ATTR_HOST_TX_SIGNAL_ENABLE` と `SAI_SWITCH_ATTR_PORT_HOST_TX_READY_NOTIFY` の両方をサポートする場合に `m_cmisModuleAsicSyncSupported = true` となる (`portsorch.cpp:968-972`)。

対応プラットフォームでは:
- `host_tx_ready` の admin UP/DOWN 時の明示的書き込みをすべてスキップ
- CMIS シーケンス完了後に `on_port_host_tx_ready` コールバック経由で更新
- `initializePortHostTxReadyBulk()` が初期一括設定を担当 (`portsorch.cpp:6597`)

非対応プラットフォームでは `initHostTxReadyState()` の `"false"` 初期値書き込み + admin_status 変更時の都度更新方式を使う。

## 6. VoQ (Voice over Queue) スイッチの影響

`gMySwitchType == "voq"` 分岐は LAG 処理・System Port 処理に影響するが、STATE_DB `PORT_TABLE` の物理ポートフィールド (`speed`, `fec`, `host_tx_ready` 等) への書き込みパスには直接影響しない。VoQ システム (Cisco 8000 等) でも `updateDbPortOperSpeed()`, `setHostTxReady()` 等は同じコードパスを通る。

## 7. link_training_status / supported_speeds / rmt_adv_speeds の platform 差異なし

コードスキャン結果、`refreshPortStateLinkTraining()`, `initPortSupportedSpeeds()`, `updatePortStateAutoNeg()` の各関数に `platform` 環境変数参照・`gMySwitchType` 分岐は存在しない。フィールドの書き込みロジック自体はプラットフォーム非依存。ただし SAI 実装の capability に依存するため、SAI が `SAI_PORT_ATTR_SUPPORTED_SPEED` / `SAI_PORT_ATTR_AUTO_NEG_ADVERTISED_SPEED` 等の `get` を非サポートの場合は `"N/A"` または空文字列フォールバックに落ちる。

## 結論サマリ

| フィールド | platform 差異の有無 | 差異の内容 |
|-----------|-------------------|-----------|
| `state`, `admin_status`, `netdev_oper_status`, `mtu` | なし | linksync は DPU/VoQ/Gearbox 非依存で動作 |
| `host_tx_ready` | あり | CMIS 対応プラットフォームでは CMIS コールバック管理。Gearbox 結果に依存 |
| `fec` | あり | `oper_fec_sup = false`（SAI 非対応プラットフォーム）では常に `"N/A"` |
| `supported_fecs` | あり | `fec_override_sup = false` プラットフォームでは `"auto"` が含まれない |
| `supported_speeds`, `link_training_status`, `rmt_adv_speeds` | なし | SAI capability 依存だが platform 分岐コードなし |
| `phy_ctrl_unreliable_los` | なし | platform 分岐なし |
