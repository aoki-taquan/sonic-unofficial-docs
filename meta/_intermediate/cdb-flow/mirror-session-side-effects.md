# MIRROR_SESSION — 副次 DB 書込 分析 (Phase F)

ソース: `sonic-swss/orchagent/mirrororch.cpp`, `sonic-swss-common/common/schema.h`

## MirrorOrch (orchagent/mirrororch.cpp)

CONFIG_DB の `MIRROR_SESSION` を直接購読し、`doTask()` → `createEntry()` / `deleteEntry()` で処理する。cfgmgr 中間層はない。APP_DB / APPL_STATE_DB への書き込みは行わない (orchagent → SAI の直接経路)。

---

## STATE_DB 書込み

### MIRROR_SESSION_TABLE

テーブル名定数: `STATE_MIRROR_SESSION_TABLE_NAME` = `"MIRROR_SESSION_TABLE"` (`sonic-swss-common/common/schema.h:433`)

`setSessionState()` (`mirrororch.cpp:574-638`) が `m_mirrorTable.set()` を呼び出し書き込む。`removeSessionState()` (`mirrororch.cpp:640-645`) は `m_mirrorTable.del()` でエントリ全体を削除する。

| タイミング | キー | フィールド | 値 | evidence |
|---|---|---|---|---|
| `activateSession()` 成功 | `MIRROR_SESSION_TABLE\|<name>` | `status` | `"active"` | `mirrororch.cpp:1093, 583-586` |
| `deactivateSession()` 成功 | `MIRROR_SESSION_TABLE\|<name>` | `status` | `"inactive"` | `mirrororch.cpp:1144-1146` |
| `activateSession()` 成功 (ERSPAN) | `MIRROR_SESSION_TABLE\|<name>` | `monitor_port` | nexthop 解決後の出力ポート alias | `mirrororch.cpp:589-605` |
| `activateSession()` 成功 (VoQ ERSPAN) | `MIRROR_SESSION_TABLE\|<name>` | `monitor_port` | recirc ポート alias | `mirrororch.cpp:592-599` |
| `activateSession()` 成功 (ERSPAN) | `MIRROR_SESSION_TABLE\|<name>` | `dst_mac` | nexthop の MAC アドレス | `mirrororch.cpp:607-616` |
| `activateSession()` 成功 (ERSPAN) | `MIRROR_SESSION_TABLE\|<name>` | `route_prefix` | nexthop プレフィックス文字列 | `mirrororch.cpp:619-623` |
| `activateSession()` 成功 (ERSPAN VLAN 経由) | `MIRROR_SESSION_TABLE\|<name>` | `vlan_id` | VLAN ID (十進文字列) | `mirrororch.cpp:625-629` |
| `activateSession()` 成功 (ERSPAN) | `MIRROR_SESSION_TABLE\|<name>` | `next_hop_ip` | nexthop IP アドレス文字列 | `mirrororch.cpp:631-635` |
| `removeSessionState()` (セッション削除時) | `MIRROR_SESSION_TABLE\|<name>` | — | エントリ全体削除 | `mirrororch.cpp:644` |
| MirrorOrch 起動時 (既存エントリ読み込み) | `MIRROR_SESSION_TABLE\|<name>` | (全フィールド) | STATE_DB から既存セッション状態を復元 | `mirrororch.cpp:118-152` |

### SPAN と ERSPAN の書込み差異

| フィールド | ERSPAN | SPAN |
|---|---|---|
| `status` | 書込み (active/inactive) | 書込み (active/inactive) |
| `monitor_port` | nexthop 解決後の出力ポート | `dst_port` の alias |
| `dst_mac` | nexthop MAC | 書込みなし |
| `route_prefix` | nexthop prefix | 書込みなし |
| `vlan_id` | VLAN 経由時のみ | 書込みなし |
| `next_hop_ip` | nexthop IP | 書込みなし |

```bash
# 確認コマンド
sonic-db-cli STATE_DB hgetall 'MIRROR_SESSION_TABLE|everflow0'
```

---

## ASIC_DB 書込み (SAI 経由)

MirrorOrch は `sai_mirror_api` を直接呼び出す。syncd が SAI 操作を ASIC_DB に記録する。

| タイミング | SAI API | ASIC_DB への反映 |
|---|---|---|
| `activateSession()` 成功 | `sai_mirror_api->create_mirror_session(&session.sessionId, gSwitchId, ...)` | `ASIC_DB:ASIC_STATE:SAI_OBJECT_TYPE_MIRROR_SESSION:<oid>` 生成 |
| src_port ミラー設定 (`configurePortMirrorSession()`) | `sai_port_api->set_port_attribute(SAI_PORT_ATTR_INGRESS_MIRROR_SESSION / EGRESS_MIRROR_SESSION)` | 対応ポート OID の mirror session 属性更新 |
| `deactivateSession()` 成功 | `sai_mirror_api->remove_mirror_session(session.sessionId)` | `ASIC_DB:ASIC_STATE:SAI_OBJECT_TYPE_MIRROR_SESSION:<oid>` 削除 |
| policer 指定時 | create_mirror_session attrs に `SAI_MIRROR_SESSION_ATTR_POLICER` を含む | mirror session OID に policer OID が関連付けられる |

証跡: `mirrororch.cpp:1066-1067` (`create_mirror_session`), `mirrororch.cpp:1123` (`remove_mirror_session`), `mirrororch.cpp:813-877` (`configurePortMirrorSession`)

---

## COUNTERS_DB 書込み

MirrorOrch は COUNTERS_DB に直接書き込まない。`mirrororch.cpp` 内に `CrmOrch` / `flex_counter` 呼び出しが存在しないことをコード全体でグレップ確認済み。

---

## APPL_STATE_DB 書込み

MirrorOrch は APP_DB / APPL_STATE_DB への書き込みを行わない。CONFIG_DB → MirrorOrch → `sai_mirror_api` → syncd の直接経路のみ。

---

## Observer 通知 (SUBJECT_TYPE_MIRROR_SESSION_CHANGE)

セッション activate/deactivate 時に `notify(SUBJECT_TYPE_MIRROR_SESSION_CHANGE, ...)` を呼び出し、`AclOrch` 等の Observer に通知する。これにより ACL ルールのミラーアクション OID が即座に更新される。STATE_DB / ASIC_DB への直接書き込みではなくオブジェクト内 OID の更新のみ。

証跡: `mirrororch.cpp:1096` (activate 後), `mirrororch.cpp:1111` (deactivate 前)

---

## スキーマまとめ

| DB | テーブル名 | 定数 | 定義箇所 |
|---|---|---|---|
| STATE_DB | `MIRROR_SESSION_TABLE` | `STATE_MIRROR_SESSION_TABLE_NAME` | `sonic-swss-common/common/schema.h:433` |
| ASIC_DB | `ASIC_STATE:SAI_OBJECT_TYPE_MIRROR_SESSION` | (syncd 管理) | syncd |
| COUNTERS_DB | — | — | 書込みなし |
| APPL_STATE_DB | — | — | 書込みなし |
