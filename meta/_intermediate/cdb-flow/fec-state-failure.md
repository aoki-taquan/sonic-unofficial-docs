# FEC_STATE 失敗挙動調査メモ (Phase D)

調査日: 2026-05-19
対象: `PortsOrch` の FEC モード適用失敗 (`setPortFec` / `isFecModeSupported` / `getPortOperFec`) ならびに STATE_DB 書込み失敗経路
調査ファイル: `sonic-swss/orchagent/portsorch.cpp` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)

---

## FEC モード SET 時の失敗パターン (`doPortTask`)

`doPortTask()` (portsorch.cpp:5312–5379) における FEC 設定分岐の失敗経路:

| # | 失敗ケース | 発生箇所 | 挙動 | retry | STATE_DB 反映 |
|---|-----------|---------|------|-------|--------------|
| 1 | `fec_override_sup=false` かつ `fec=auto` (override_fec=false) | portsorch.cpp:5317-5321 | SWSS_LOG_ERROR → `erase(it)`（恒久スキップ） | なし | 書込なし |
| 2 | `isFecModeSupported()` が false（プラットフォーム未サポート FEC モード） | portsorch.cpp:5323-5331 | SWSS_LOG_ERROR → `erase(it)`（恒久スキップ） | なし | 書込なし |
| 3 | ポート admin UP 状態で `setPortAdminStatus(false)` 失敗 | portsorch.cpp:5342-5350 | SWSS_LOG_ERROR → `it++`（次サイクル再試行） | 無制限 | 書込なし |
| 4 | `setPortFec()` 内 SAI `set_port_attribute(FEC_MODE)` 失敗 | portsorch.cpp:2394-2401 | SWSS_LOG_ERROR → `handleSaiSetStatus` → `parseHandleSaiStatusFailure` → caller へ false 返却 | 条件次第 | 書込なし |
| 5 | `setPortFec()` 内 `setPortFecOverride()` 失敗 (SAI AUTO_NEG_FEC_MODE_OVERRIDE 失敗) | portsorch.cpp:2405-2408 | SWSS_LOG_ERROR → `handleSaiSetStatus` → false 返却 | 条件次第 | 書込なし |
| 6 | `setPortFec()` が false を返した → `doPortTask` 側で検出 | portsorch.cpp:5356-5363 | SWSS_LOG_ERROR → `it++`（次サイクル再試行） | 無制限 | 書込なし |

FEC 適用失敗時、**STATE_DB には何も書き込まれない**。`fec` / `supported_fecs` フィールドは以前の値のままとなる（初回なら不在）。

---

## `isFecModeSupported` — 空集合フォールバック

`isFecModeSupported()` (portsorch.cpp:3205-3222) は以下の特殊ケースを持つ:

- `obj.supported == false`: SAI が `NOT_SUPPORTED` / `NOT_IMPLEMENTED` → **true を返す**（バリデーションスキップ、設定を通す）
  (portsorch.cpp:3211-3213)
- `obj.data.empty()` (空集合): **false を返す**（全 FEC モード拒否）
  (portsorch.cpp:3216-3218)

「`supported=false`（クエリ非対応）」と「`data.empty()`（サポート FEC モード空集合）」は挙動が逆になる点に注意。前者は設定を通し、後者は設定を拒否する。

---

## `getPortOperFec` — SAI クエリ失敗経路

`getPortOperFec()` (portsorch.cpp:9994-10015):

- `port.m_type != Port::PHY`: 即 `return false` → `fec_str = "N/A"` (portsorch.cpp:9998-10000)
- SAI `get_port_attribute(SAI_PORT_ATTR_OPER_PORT_FEC_MODE)` 失敗: SWSS_LOG_NOTICE → `return false` → `fec_str = "N/A"` (portsorch.cpp:10007-10010)

いずれの失敗でも `updateDbPortOperFec(port, "N/A")` が呼ばれ STATE_DB に `"N/A"` が書き込まれる (portsorch.cpp:9692-9694)。

---

## `fecToStr` 変換失敗

`fecToStr()` が未知の SAI FEC mode を受け取った場合:
- SWSS_LOG_ERROR → `fec_str = "N/A"` (portsorch.cpp:9684-9688)
- その後 `updateDbPortOperFec(port, "N/A")` で STATE_DB に `"N/A"` 書込み

`fecToStr` 失敗でも orchagent はクラッシュしない。`"N/A"` フォールバックにより続行する。

---

## `getPortSupportedFecModes` — SAI クエリ失敗経路

`getPortSupportedFecModes()` (portsorch.cpp:3224-3263):

- `NOT_SUPPORTED` / `NOT_IMPLEMENTED` 系 SAI エラー: SWSS_LOG_NOTICE → `supported_fec_modes` に何も追加しない → `initPortSupportedFecModes` で `obj.supported=false` フラグセット → `STATE_DB supported_fecs` 書込みをスキップ
- その他 SAI エラー: SWSS_LOG_ERROR → 同様に空のまま

`obj.supported=false` (not_implemented) の場合、STATE_DB の `supported_fecs` フィールドは一切書き込まれない（フィールド不在）。
`obj.supported=true` かつ `obj.data.empty()` の場合、`"N/A"` が書き込まれる (portsorch.cpp:3290-3292)。

---

## STATE_DB 書込み自体の失敗

`updateDbPortOperFec()` は `m_portStateTable.set()` を呼ぶ（`swss::Table::set` は void、戻り値なし）。Redis I/O エラー時は `swss::RedisException` 例外として伝播し、orchagent プロセス abort → systemd 再起動という経路を取る。STATE_DB 書込みの部分的失敗（一部フィールドのみ書けない等）はアプリ層では観測できない。

---

## FEC 適用失敗後の `m_portList` / `m_fec_cfg` フラグ

- FEC SET 成功時のみ `p.m_fec_cfg = true` を設定し `m_portList` を更新 (portsorch.cpp:5366-5369)
- 失敗時は `m_fec_cfg=false` のまま → 次サイクルで再度 FEC 設定を試みる（`m_fec_cfg || m_fec_mode != pCfg.fec.value` による変更検出）

ただし `erase(it)` （恒久スキップ）パターン（#1, #2）では APPL_DB のエントリが消費されてしまうため、orchagent 側では永久に再試行されない（systemd 再起動 + CONFIG_DB 再投入が必要）。
