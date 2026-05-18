# orchagent-state — Phase H プラットフォーム差調査メモ

対象テーブル: `WARM_RESTART_TABLE` / `PORT_TABLE` / `FDB_TABLE` / `VRF_OBJECT_TABLE` / `FIPS_MACSEC_POST_TABLE`
調査日: 2026-05-18
スキャン範囲: `orchagent/main.cpp`, `orchagent/orchdaemon.cpp`, `orchagent/portsorch.cpp`, `orchagent/fdborch.cpp`, `orchagent/vrforch.cpp`, `orchagent/macsecpost.cpp`, `common/warm_restart.cpp` 全行精読

---

## 1. WARM_RESTART_TABLE — プラットフォーム差なし

`WarmStart::setWarmStartState()` / `checkWarmStart()` は `sonic-swss-common/common/warm_restart.cpp` に実装され、
ASIC 種別・switch_type・multi-asic 構成に一切依存しない。`WARM_RESTART_TABLE` フィールド (`state` / `restore_count` /
`restore_check` / `shutdown_check`) の値・遷移は全プラットフォームで同一。

根拠: `warm_restart.cpp` に `platform` / `gMySwitchType` / `multi_asic` を参照するコードは存在しない。

---

## 2. PORT_TABLE — プラットフォーム差あり（フィールド有無 + 値）

### 2-1. `supported_fecs` — ベンダー SAI 非対応時は書かれない

`initPortCapFec()` (`portsorch.cpp:3240-3320`) は SAI の `get_port_attribute` で `SAI_PORT_ATTR_SUPPORTED_FEC_MODE`
を取得する。SAI が当該アトリビュートを非対応として `SAI_STATUS_NOT_SUPPORTED` / `SAI_STATUS_ATTR_NOT_SUPPORTED` を
返した場合、`supported_fecs` フィールドは STATE_DB に**書き込まれない**:

```cpp
// portsorch.cpp:3281-3283
SWSS_LOG_INFO("No supported_fecs exposed to STATE_DB for port %s since fetching supported FEC modes is not supported by the vendor",
               port.m_alias.c_str());
```

- **Mellanox (MLNX) ASIC**: `isMlnxPlatform()` によるパス分岐は `supported_fecs` 書込み経路には存在しない。
  ただし Mellanox SAI が FEC mode query に対応している場合は通常通り書かれる。
- **FEC auto オーバーライド**: `SAI_SWITCH_ATTR_SUPPORTED_EXTENDED_OBJECT_TYPES` でサポートを確認できる場合のみ
  `supported_fecs` 末尾に `"auto"` を付加する (`portsorch.cpp:3310-3318`)。この能力は ASIC 依存。

### 2-2. `host_tx_ready` — Gearbox 搭載 vs 非搭載

`initHostTxReadyState()` (`portsorch.cpp:2177-2205`) は全プラットフォームで実行されるが、
`setHostTxReady()` (`portsorch.cpp:2217-2275`) の内部では Gearbox が有効な場合
`SAI_PORT_ATTR_HOST_TX_READY_STATUS` を Gearbox PHY 経由で取得するパスが追加される:

```cpp
// portsorch.cpp:2240-2252 (gearbox path)
if (m_gearboxEnabled && m_gearboxPortOidMap.count(port_id))
{
    // Gearbox (PHY) 経由で host_tx_ready を取得
}
```

Gearbox 非搭載構成では SAI switch の `SAI_PORT_ATTR_HOST_TX_READY_STATUS` のみ参照。
**フィールド名・格納形式は変わらず、挙動（取得経路）のみが異なる**。

### 2-3. Mellanox プラットフォーム — flex counter trim stat プラグイン

`isMlnxPlatform()` チェック (`portsorch.cpp:858`) は STATE_DB `PORT_TABLE` の直接フィールドには影響しない。
これは NVIDIA TRIM パケット統計の Flex Counter プラグイン登録の可否判定にのみ使われる。

---

## 3. FDB_TABLE — プラットフォーム差なし

`FdbOrch::doTask()` / SAI FDB event handler は ASIC 種別・switch_type に依存しない。
フィールド (`port` / `type`) の書込み経路に `gMySwitchType` / `platform` 参照なし。

VXLAN FDB (`APP_VXLAN_FDB_TABLE_NAME`) と MCLAG FDB (`APP_MCLAG_FDB_TABLE_NAME`) の origin 判定は
STATE_DB 書込み有無に影響するが、これは機能フラグ（VXLAN / MCLAG が有効か）であり ASIC 種別ではない。

---

## 4. VRF_OBJECT_TABLE — プラットフォーム差なし

`vrforch.cpp` に `gMySwitchType` / `platform` / `isMlnxPlatform` 等の参照なし。
SAI `create_virtual_router` / `set_virtual_router_attribute` の成否に基づく `state="ok"` 書込みは全プラットフォーム共通。

---

## 5. FIPS_MACSEC_POST_TABLE — switch_type 依存（fabric では無効）

`main.cpp:773` に明示的な switch_type 条件:

```cpp
if (gMySwitchType != "fabric" && macsec_post_enabled)
{
    macsec_post_state = "switch-level-post-in-progress";
    // SAI_SWITCH_ATTR_MACSEC_ENABLE_POST を create_switch 属性に追加
}
else
{
    macsec_post_state = "disabled";
}
```

- **`switch_type = "fabric"` (FabricOrchDaemon)**: MACsec POST が有効であっても `post_state = "disabled"` で固定。`FIPS_MACSEC_POST_TABLE` は書かれるが `post_state = "disabled"` のみ。
- **`switch_type = "voq"` / `"chassis-packet"` / `"dpu"` / `"switch"`**: `macsec_post_enabled` (SAI capability による) が `true` の場合は POST フローが走る。
- **SAI MACsec POST 非対応 ASIC**: `SAI_SWITCH_ATTR_MACSEC_ENABLE_POST` が非対応の場合、SAI create_switch は失敗しないが MACsec POST コールバックが呼ばれないため `post_state` は `"disabled"` のまま変化しない (`main.cpp:791-793`)。

`macsec_post_enabled` フラグ自体は `SAI_SWITCH_ATTR_MACSEC_SUPPORTED` の取得結果 (`main.cpp:765-770`) および FIPS モード有効化フラグ（起動引数 `-z`）に依存する。

---

## 6. multi-asic / VOQ chassis 影響

| テーブル | multi-asic (is_multi_npu) | VOQ chassis (supervisor + linecards) |
|---------|--------------------------|--------------------------------------|
| WARM_RESTART_TABLE | 各 asic instance の orchagent が独立に書く。namespace 分離 | supervisor orchagent / linecard orchagent が独立に書く |
| PORT_TABLE | 各 asic instance 管理のポートのみ (`-i INST_ID` で分離) | linecard asic 管理ポートのみ。supervisor には front-panel PORT なし |
| FDB_TABLE | 各 asic instance の orchagent が独立に書く | linecard orchagent のみ FDB 操作。supervisor は FabricOrchDaemon |
| VRF_OBJECT_TABLE | 各 asic instance で VRF が独立に管理される | linecard asic で VRF 作成。supervisor (fabric) では VRF 操作なし |
| FIPS_MACSEC_POST_TABLE | 各 asic instance の orchagent で独立に POST 実行 | supervisor (fabric) は `switch_type="fabric"` のため `disabled` 固定 |

---

## 7. プラットフォーム差サマリ

| テーブル | プラットフォーム差 | 観点 |
|---------|----------------|------|
| WARM_RESTART_TABLE | **なし** | 全 switch_type / ASIC で共通 |
| PORT_TABLE `supported_fecs` | SAI 非対応 ASIC で**フィールド未書込み** | ベンダー SAI capability 依存 |
| PORT_TABLE `supported_fecs` 末尾 `"auto"` | SAI extended object types 対応 ASIC のみ付加 | ASIC SAI capability 依存 |
| PORT_TABLE `host_tx_ready` | Gearbox 搭載時のみ PHY 経由で取得 | **フィールド名・値は同一**、取得経路のみ異なる |
| FDB_TABLE | **なし** | ASIC 種別・switch_type に非依存 |
| VRF_OBJECT_TABLE | **なし** | ASIC 種別・switch_type に非依存 |
| FIPS_MACSEC_POST_TABLE | `switch_type="fabric"` で `post_state="disabled"` 固定 | switch_type 依存 |
| FIPS_MACSEC_POST_TABLE | SAI MACsec POST 非対応 ASIC で `post_state` が `"disabled"` 固定 | SAI capability 依存 |
