# bfdorch (APPL_DB BFD_SESSION_TABLE) — Phase F: 副次 DB 書込スキャン中間ファイル

生成日: 2026-05-16 (Task F Phase F / cdb_q67_f)

## 調査対象

`docs/reference/config-db/bfd-orch.md` がカバーする主作用テーブルは **APPL_DB `BFD_SESSION_TABLE`** (bfdorch が `Orch` 基底クラスを通じて consumer として購読)。本ページの主体である `BfdOrch` が APPL_DB consume の主作用以外に、どの DB / テーブルへ副次的に書込みを行うかを `orchagent/bfdorch.cpp` で全数走査する。

ASIC への SAI BFD セッション作成・削除 (`sai_bfd_api->create_bfd_session()` / `remove_bfd_session()`) は主作用 (= SAI 経路) のため副次書込みとしては扱わない。

## 走査範囲

- `.cache/sonic-sources/sonic-swss/orchagent/bfdorch.cpp` (L1–L800)
- `.cache/sonic-sources/sonic-swss/orchagent/bfdorch.h`

## 走査コマンドと結果

### 1. DB ハンドル / Producer / Table の宣言

```bash
grep -nE "DBConnector|ProducerStateTable|NotificationProducer|swss::Table|Notification(Consumer|Producer)" bfdorch.cpp
```

検出されたヒット (代表):

- L59 `m_stateBfdSessionTable(stateDbBfdSessionTable.first, stateDbBfdSessionTable.second)` — STATE_DB `BFD_SESSION_TABLE` への書込ハンドル (`swss::Table` ベース)
- L63 `DBConnector *notificationsDb = new DBConnector("ASIC_DB", 0);`
- L64 `m_bfdStateNotificationConsumer = new swss::NotificationConsumer(notificationsDb, "NOTIFICATIONS");` — ASIC_DB `NOTIFICATIONS` の **consumer** (受信のみ、書込ではない)
- L67 `m_stateDbConnector = std::make_unique<swss::DBConnector>("STATE_DB", 0);`
- L68 `m_stateSoftBfdSessionTable = std::make_unique<swss::Table>(m_stateDbConnector.get(), STATE_BFD_SOFTWARE_SESSION_TABLE_NAME);` — STATE_DB `SOFTWARE_BFD_SESSION_TABLE` への書込ハンドル

→ **STATE_DB に対する書込ハンドルが 2 系統**存在することを確認 (`m_stateBfdSessionTable`, `m_stateSoftBfdSessionTable`)。`ProducerStateTable` / `NotificationProducer` の宣言は無し。

### 2. STATE_DB 書込操作の grep

```bash
grep -nE "m_stateBfdSessionTable|m_stateSoftBfdSessionTable" bfdorch.cpp
```

検出された書込操作 (代表):

- L78 `m_stateBfdSessionTable.del(alias);` — コンストラクタでの再起動時クリーンアップ
- L84 `m_stateSoftBfdSessionTable->del(alias);` — 同上 (software 側)
- L136 `m_stateSoftBfdSessionTable->set(createStateDBKey(key), data);` — `doTask()` 内で `use_software_bfd == true` 時、APPL_DB から受けた FV をそのまま STATE_DB に転記
- L185 `m_stateSoftBfdSessionTable->del(createStateDBKey(key));` — 同上 DEL 経路
- L252 `m_stateBfdSessionTable.hset(key, "state", session_state_lookup.at(state));` — ASIC_DB `NOTIFICATIONS` 経由の状態変化通知を受けて `state` フィールドを更新
- L565 `m_stateBfdSessionTable.set(state_db_key, fvVector);` — `create_bfd_session()` 成功時の初期 state 書込 (`state="Down"`)
- L629 `m_stateBfdSessionTable.del(bfd_session_lookup[bfd_session_id].peer);` — セッション削除時

→ **STATE_DB 2 テーブル (`BFD_SESSION_TABLE` / `SOFTWARE_BFD_SESSION_TABLE`) への書込が確認された**。

### 3. COUNTERS_DB / FLEX_COUNTER_DB の有無

```bash
grep -nE "COUNTERS|FLEX_COUNTER|FlexCounter" bfdorch.cpp
```

→ ヒット **0 件**。`BfdOrch` は COUNTERS_DB / FLEX_COUNTER_DB に一切書込まない。BFD は SAI counter 統計の対象外 (`bfdshow` / `show bfd peers` は STATE_DB / FRR から情報を取得する)。

### 4. APPL_DB / CONFIG_DB への書戻し有無

```bash
grep -nE "APPL_DB|APP_DB|CONFIG_DB|m_appDb|m_configDb|ProducerStateTable|NotificationProducer" bfdorch.cpp
```

→ ヒット **0 件**。`BfdOrch` は APPL_DB / CONFIG_DB に対しては consumer のみで書戻しは行わない。

### 5. その他の副次効果 (DB 書込以外)

- `notify(SUBJECT_TYPE_BFD_SESSION_STATE_CHANGE, ...)` (L260 / L572 / L680) — orchagent プロセス内の observer pattern (`Observer` 派生クラスへの通知)。DB 書込ではないため副次 DB 書込としては記録しない。subscriber は `NhgOrch` / `RouteOrch` 等 (BFD 連動 next-hop tracking)。
- `m_bfdStateNotificationConsumer` (L64) — ASIC_DB `NOTIFICATIONS` を **受信**するのみ。書込みではない。

### 6. 結論

| 副次 DB | テーブル / キー | 書込 API | トリガ |
|---------|---------------|---------|--------|
| STATE_DB | `BFD_SESSION_TABLE\|<vrf>:<ifname>:<peer_ip>` | `m_stateBfdSessionTable.set()` / `.hset()` / `.del()` | `create_bfd_session()` 成功時 (L565)、ASIC_DB NOTIFICATIONS 受信時の `state` 更新 (L252)、`remove_bfd_session()` 時 (L629)、コンストラクタ起動時 cleanup (L78) |
| STATE_DB | `SOFTWARE_BFD_SESSION_TABLE\|<vrf>:<ifname>:<peer_ip>` | `m_stateSoftBfdSessionTable->set()` / `->del()` | `use_software_bfd == true` 経路で APPL_DB SET 受信時に転記 (L136)、DEL 受信時 (L185)、コンストラクタ起動時 cleanup (L84) |

副次書込対象は **STATE_DB の 2 テーブルのみ**。COUNTERS_DB / FLEX_COUNTER_DB / ASIC_DB への直接書込み、APPL_DB / CONFIG_DB への書戻しは検出されなかった。

→ 本ページに `<!-- side-effects -->` ブロックを追加し、上記 2 系統を明記する。
