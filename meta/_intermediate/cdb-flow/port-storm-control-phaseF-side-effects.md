# PORT_STORM_CONTROL — Phase F 副次 DB 書込

調査日: 2026-05-16
ソース: `sonic-swss/orchagent/policerorch.cpp` (PolicerOrch::handlePortStormControlTable)
対象ページ: `docs/reference/config-db/port-storm-control.md`

---

## 概要

`PORT_STORM_CONTROL` エントリが CONFIG_DB に書き込まれると、`PolicerOrch` が直接 SAI API を呼び出し
ASIC_DB (syncd 経由) へ SAI policer オブジェクトおよびポート属性を書き込む。
APPL_DB / STATE_DB / COUNTERS_DB への副次書込は発生しない。

---

## 1. ASIC_DB — SAI policer 書込 (syncd 経由)

`sai_policer_api->create_policer()` / `set_policer_attribute()` が syncd を介して ASIC_DB に変換される。

### SAI 書込関数と条件

| 操作 | SAI 関数 | 条件 | ソース行 |
|------|---------|------|---------|
| 新規作成 (SET, 未存在) | `sai_policer_api->create_policer(&policer_id, gSwitchId, attrs)` | `m_syncdPolicers` に未登録 | `policerorch.cpp:226-238` |
| 更新 (SET, 既存) | `sai_policer_api->set_policer_attribute(policer_id, &attr)` | `m_syncdPolicers` に登録済み、CIR のみ更新 | `policerorch.cpp:257-268` |
| 削除 (DEL) | `sai_policer_api->remove_policer(policer_id)` | DEL コマンド受信 | `policerorch.cpp:355-365` |

### SAI policer 属性 (新規作成時に設定される固定属性)

| SAI 属性 | 値 | 備考 |
|---|---|---|
| `SAI_POLICER_ATTR_METER_TYPE` | `SAI_METER_TYPE_BYTES` | ハードコード |
| `SAI_POLICER_ATTR_MODE` | `SAI_POLICER_MODE_STORM_CONTROL` | ハードコード |
| `SAI_POLICER_ATTR_RED_PACKET_ACTION` | `SAI_PACKET_ACTION_DROP` | ハードコード |
| `SAI_POLICER_ATTR_CIR` | `kbps * 1000 / 8` (bytes/s、整数切捨て) | CONFIG_DB.kbps から変換 |

---

## 2. ASIC_DB — SAI ポート属性書込 (syncd 経由)

SAI policer 作成後に `sai_port_api->set_port_attribute()` で対象ポートの storm control policer を attach する。

### storm_type → SAI ポート属性マッピング

| storm_type | SAI ポート属性 | ソース行 |
|---|---|---|
| `broadcast` | `SAI_PORT_ATTR_BROADCAST_STORM_CONTROL_POLICER_ID` | `policerorch.cpp:208-210` |
| `unknown-unicast` | `SAI_PORT_ATTR_FLOOD_STORM_CONTROL_POLICER_ID` | `policerorch.cpp:212-214` |
| `unknown-multicast` | `SAI_PORT_ATTR_MULTICAST_STORM_CONTROL_POLICER_ID` | `policerorch.cpp:216-218` |

### update 時の remove-then-reapply

既存エントリ更新時は以下の 2 ステップで `set_port_attribute()` を 2 回呼び出す:

1. `port_attr.value.oid = SAI_NULL_OBJECT_ID` → ポートから storm control を一時解除 (`policerorch.cpp:278`)
2. `port_attr.value.oid = policer_id` → 新 policer を再 attach (`policerorch.cpp:291`)

この間、ポートで storm control が解除される短いウィンドウが存在する。

### DEL 時

`sai_port_api->set_port_attribute(SAI_NULL_OBJECT_ID)` でポートの storm control を解除後、
`sai_policer_api->remove_policer()` で policer オブジェクトを削除する。(`policerorch.cpp:344-365`)

---

## 3. APPL_DB / STATE_DB / COUNTERS_DB — 書込なし

`PolicerOrch::handlePortStormControlTable()` は APPL_DB / STATE_DB / COUNTERS_DB に一切書き込まない。
CRM カウンタの更新も行わない。

---

## 書込タイミングまとめ

```
PORT_STORM_CONTROL SET (CONFIG_DB)
  └─ PolicerOrch::handlePortStormControlTable()
       ├─ [新規] sai_policer_api->create_policer(...) → syncd → ASIC_DB (SAI_OBJECT_TYPE_POLICER)
       │     └─ m_syncdPolicers[storm_policer_name] = policer_id  (内部キャッシュ)
       ├─ [更新] sai_policer_api->set_policer_attribute(CIR のみ) → syncd → ASIC_DB
       │     └─ sai_port_api->set_port_attribute(SAI_NULL_OBJECT_ID) → syncd → ASIC_DB (一時解除)
       └─ sai_port_api->set_port_attribute(SAI_PORT_ATTR_*_STORM_CONTROL_POLICER_ID = policer_id)
              → syncd → ASIC_DB (PORT 属性)

PORT_STORM_CONTROL DEL (CONFIG_DB)
  └─ PolicerOrch::handlePortStormControlTable()
       ├─ sai_port_api->set_port_attribute(SAI_NULL_OBJECT_ID) → syncd → ASIC_DB (ポート解除)
       └─ sai_policer_api->remove_policer(policer_id) → syncd → ASIC_DB (policer 削除)
```

---

## 証跡サマリ

| 書込先 | オブジェクト/テーブル | 操作 | evidence |
|-------|-------------------|------|---------|
| ASIC_DB (SAI_OBJECT_TYPE_POLICER) | SAI policer | create/set_attribute/remove | `policerorch.cpp:226, 257, 355` |
| ASIC_DB (SAI PORT 属性) | `SAI_PORT_ATTR_*_STORM_CONTROL_POLICER_ID` | set_port_attribute | `policerorch.cpp:278, 291, 344` |
| APPL_DB | — | — | 書込なし |
| STATE_DB | — | — | 書込なし |
| COUNTERS_DB | — | — | 書込なし |
