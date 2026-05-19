# FEC_STATE プラットフォーム差調査メモ (Phase H)

調査日: 2026-05-19
対象: STATE_DB `PORT_TABLE` の FEC 関連フィールド（`fec`, `supported_fecs`）
調査ファイル: `sonic-swss/orchagent/portsorch.cpp`

---

## SAI Capability クエリと `oper_fec_sup` / `fec_override_sup` フラグ

PortsOrch コンストラクタ (portsorch.cpp:987-1010) は `gMySwitchType != "dpu"` のときのみ以下の SAI capability クエリを 1 回実行する。

### `fec_override_sup` — `SAI_PORT_ATTR_AUTO_NEG_FEC_MODE_OVERRIDE` 対応確認

```cpp
sai_attr_capability_t attr_cap;
if (sai_query_attribute_capability(gSwitchId, SAI_OBJECT_TYPE_PORT,
                                   SAI_PORT_ATTR_AUTO_NEG_FEC_MODE_OVERRIDE,
                                   &attr_cap) != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_NOTICE("Unable to query autoneg fec mode override");
}
else if (attr_cap.set_implemented && attr_cap.create_implemented)
{
    fec_override_sup = true;
}
```

`SAI_PORT_ATTR_AUTO_NEG_FEC_MODE_OVERRIDE` は autoneg が有効なポートで FEC モードを明示的に override するための SAI 属性。Broadcom SDK (OpenNSA) および Mellanox SDK (MLNX-SAI) が実装しているが、DPU 系やコスト優先 ASIC では未実装のことがある。

| プラットフォームカテゴリ | `fec_override_sup` | `supported_fecs` の `"auto"` 出現 | `fec=auto` 設定可否 |
|------------------------|-------------------|----------------------------------|-------------------|
| Broadcom Trident/Tomahawk (OpenNSA) | `true`（set+create 両実装） | `"...,auto"` が末尾に追加される | 可（autoneg=on 前提） |
| Mellanox/NVIDIA Spectrum (MLNX-SAI) | `true`（SAI 実装あり） | `"...,auto"` が末尾に追加される | 可 |
| DPU (`gMySwitchType == "dpu"`) | `false`（クエリ自体スキップ） | `"auto"` 追加なし | 不可 |
| SAI クエリ失敗 / 未実装 ASI | `false`（NOTICE ログ） | `"auto"` 追加なし | 不可 (`SWSS_LOG_ERROR` + erase) |

**影響**: `fec_override_sup=false` のプラットフォームで CONFIG_DB に `fec=auto` を設定すると、
`doPortTask` 内 (portsorch.cpp:5317-5321) で `SWSS_LOG_ERROR("Auto FEC mode is not supported")` となり
エントリが永久スキップ (`erase(it)`) される。STATE_DB には何も書き込まれない。

### `oper_fec_sup` — `SAI_PORT_ATTR_OPER_PORT_FEC_MODE` 取得対応確認

```cpp
sai_attr_capability_t oper_fec_cap;
if (sai_query_attribute_capability(gSwitchId, SAI_OBJECT_TYPE_PORT,
                                   SAI_PORT_ATTR_OPER_PORT_FEC_MODE, &oper_fec_cap)
                                   != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_NOTICE("Unable to query capability support for oper fec mode");
}
else if (oper_fec_cap.get_implemented)
{
    oper_fec_sup = true;
}
```

`SAI_PORT_ATTR_OPER_PORT_FEC_MODE` は起動中のポートで実際に使われている FEC モードを SAI から読み取る属性。

| プラットフォームカテゴリ | `oper_fec_sup` | `fec` フィールドの挙動 |
|------------------------|---------------|----------------------|
| Broadcom Trident4/Tomahawk4 等 (get 実装あり) | `true` | ポート UP 時に SAI 値から `none`/`rs`/`fc` が書き込まれる |
| Broadcom 旧世代 (Trident2 等、get 未実装) | `false`（NOTICE ログ） | 常に `"N/A"` |
| Mellanox/NVIDIA Spectrum (get 実装あり) | `true` | SAI 値から書き込まれる |
| DPU (`gMySwitchType == "dpu"`) | `false`（クエリ自体スキップ） | 常に `"N/A"` |

---

## Broadcom 固有: `SAI_PORT_ATTR_SUPPORTED_FEC_MODE` の扱い

Broadcom OpenNSA では `SAI_PORT_ATTR_SUPPORTED_FEC_MODE` は実装されていることが多いが、
返す FEC モード集合はポートの速度・レーン構成に依存する。例:

- 100GbE (4 lane): `none`, `rs` が返る → `supported_fecs = "none,rs,auto"`（override_sup=true 時）
- 25GbE: `none`, `fc` が返ることがある
- 400GbE: `rs` のみ

Broadcom 旧世代 (`broadcom-legacy`) では `SAI_PORT_ATTR_SUPPORTED_FEC_MODE` が NOT_IMPLEMENTED を返す場合があり、`supported_fecs` フィールドが STATE_DB に存在しない。

## Mellanox (NVIDIA Spectrum) 固有の挙動

Mellanox MLNX-SAI は `SAI_PORT_ATTR_OPER_PORT_FEC_MODE` および `SAI_PORT_ATTR_SUPPORTED_FEC_MODE` を実装しているため、`oper_fec_sup=true` / `fec_override_sup=true` となり、`fec` フィールドおよび `supported_fecs` の `"auto"` が正常に書き込まれる。

Mellanox 固有の分岐 `isMlnxPlatform()` (portsorch.cpp:689-700) は **FEC フィールド書込みには影響しない**。この関数は Trim 統計プラグイン追加 (portsorch.cpp:858) と LAG distribution/collection 順序制御 (portsorch.cpp:6362, 6379) のみに使われる。

## DPU (gMySwitchType == "dpu") の特別扱い

```cpp
if (gMySwitchType != "dpu")
{
    // SAI capability クエリ (oper_fec_sup / fec_override_sup 確定)
}
```

DPU (`gMySwitchType == "dpu"`) のとき上記ブロック全体がスキップされるため:
- `oper_fec_sup = false`（デフォルト値）
- `fec_override_sup = false`（デフォルト値）

→ `fec` フィールドは常に `"N/A"`
→ `supported_fecs` の `"auto"` は絶対に追加されない

`postPortInit()` (portsorch.cpp:6449) も `gMySwitchType != "dpu"` 条件で `initializePortBufferMaximumParameters()` のみをスキップするが、`initPortSupportedFecModes()` は DPU でも呼ばれる (portsorch.cpp:6461)。ただし SAI が `SAI_PORT_ATTR_SUPPORTED_FEC_MODE` を返さない DPU では `supported_fecs` フィールドが STATE_DB に存在しないことが多い。

---

## プラットフォーム別 STATE_DB 書込みサマリ

| プラットフォーム | `fec` フィールド | `supported_fecs` | `"auto"` 含む |
|----------------|----------------|-----------------|--------------|
| Broadcom (modern, Trident4+) | SAI oper FEC 値 (`none`/`rs`/`fc`) | SAI 対応モード CSV | ◎（override_sup=true 時） |
| Broadcom (旧世代, Trident2) | `"N/A"`（get 未実装） | フィールド不在（NOT_IMPLEMENTED） | ✗ |
| Mellanox/NVIDIA Spectrum | SAI oper FEC 値 | SAI 対応モード CSV | ◎ |
| DPU | `"N/A"`（クエリスキップ） | SAI 次第（多くは不在） | ✗ |
| VS (仮想スイッチ) | `"N/A"`（SAI stub が unimplemented） | フィールド不在 | ✗ |
