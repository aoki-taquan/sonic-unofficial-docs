# bfd-session Phase F — 副次 DB 書込スキャンノート

対象: CONFIG_DB `BFD_SESSION` を起点とする副次 DB 書込。
主購読者: `sonic-swss/orchagent/bfdorch.cpp` (`BfdOrch`)。`bgpcfgd` `BfdMgr` は STATE_DB
`SOFTWARE_BFD_SESSION_TABLE` を**読出**側で、書込起点は `bfdorch` 側に閉じている。

## grep 戦略

`bfdorch.cpp` に対して以下を grep:

- DB 名: `STATE_DB`, `APPL_DB`, `COUNTERS_DB`, `ASIC_DB`, `FLEX_COUNTER_DB`
- Table クラス参照: `m_stateBfdSessionTable`, `m_stateSoftBfdSessionTable`, `m_stateDbConnector`
- 書込メソッド: `.set(`, `.hset(`, `.del(`, `Producer`, `Notification`

## 検出結果一覧

| L | 文 | 対象 DB | 対象テーブル | 操作 | キー / 値 |
|---|---|---|---|---|---|
| 67 | `m_stateDbConnector = std::make_unique<swss::DBConnector>("STATE_DB", 0);` | STATE_DB | (接続) | open | — |
| 68 | `m_stateSoftBfdSessionTable = std::make_unique<swss::Table>(..., STATE_BFD_SOFTWARE_SESSION_TABLE_NAME);` | STATE_DB | `SOFTWARE_BFD_SESSION_TABLE` | bind | — |
| 78 | `m_stateBfdSessionTable.del(alias);` | STATE_DB | `BFD_SESSION_TABLE` | DEL | 全 stale エントリ (起動 cleanup) |
| 84 | `m_stateSoftBfdSessionTable->del(alias);` | STATE_DB | `SOFTWARE_BFD_SESSION_TABLE` | DEL | 全 stale エントリ (起動 cleanup) |
| 136 | `m_stateSoftBfdSessionTable->set(createStateDBKey(key), data);` | STATE_DB | `SOFTWARE_BFD_SESSION_TABLE` | SET | software BFD 経路で CONFIG_DB 内容を転記 |
| 185 | `m_stateSoftBfdSessionTable->del(createStateDBKey(key));` | STATE_DB | `SOFTWARE_BFD_SESSION_TABLE` | DEL | software BFD 経路で削除転記 |
| 252 | `m_stateBfdSessionTable.hset(key, "state", session_state_lookup.at(state));` | STATE_DB | `BFD_SESSION_TABLE` | HSET | SAI notify ハンドラから state 更新 |
| 565 | `m_stateBfdSessionTable.set(state_db_key, fvVector);` | STATE_DB | `BFD_SESSION_TABLE` | SET | hardware 経路の SAI create 成功直後に初期エントリを起こす |
| 629 | `m_stateBfdSessionTable.del(...);` | STATE_DB | `BFD_SESSION_TABLE` | DEL | hardware 経路の SAI remove 直後に削除 |
| 708 | `m_stateSoftBfdSessionTable->set(createStateDBKey(key), data);` | STATE_DB | `SOFTWARE_BFD_SESSION_TABLE` | SET | `createSoftwareBfdSession()` から (L136 と等価) |
| 714 | `m_stateSoftBfdSessionTable->del(createStateDBKey(key));` | STATE_DB | `SOFTWARE_BFD_SESSION_TABLE` | DEL | `removeSoftwareBfdSession()` から (L185 と等価) |

## DB 別サマリ

### STATE_DB

- `BFD_SESSION_TABLE` (`STATE_BFD_SESSION_TABLE_NAME`)
  - **hardware 経路**で `BfdOrch` が直接書く。create 成功時 SET (`bfdorch.cpp:565`)、remove 時 DEL (`bfdorch.cpp:629`)、SAI notify 受信時 `state` フィールドのみ HSET (`bfdorch.cpp:252`)。
  - キー形式: `<vrf>|<alias>|<peer_ip>` (`get_state_db_key()` `bfdorch.cpp:636-639`)。区切り文字は `state_db_key_delimiter`。
  - 値: CONFIG_DB から流入した `fvVector` (`local_addr`, `tx_interval`, `rx_interval`, `multiplier`, `multihop`, `type`, `tos`, `dst_mac`, …) + 後追いの `state` (`Down`/`Init`/`Up`/`Admin_Down`)。
- `SOFTWARE_BFD_SESSION_TABLE` (`STATE_BFD_SOFTWARE_SESSION_TABLE_NAME`)
  - **software 経路**で `BfdOrch::createSoftwareBfdSession()` / `removeSoftwareBfdSession()` が SET/DEL する (`bfdorch.cpp:706-716`)。`use_software_bfd=true` または SAI offload capability なしのとき経路がこちらへ振られる (`bfdorch.cpp:116-138, 178-185`)。
  - キー形式: `createStateDBKey()` で生成 (vrf/interface/peer を `state_db_key_delimiter` で連結)。値: doTask が受け取った CONFIG_DB の fvVector を**そのまま**転記 (`bfdorch.cpp:136, 708`)。`state` フィールドは bfdorch では書かない (FRR bfdd → `bgpcfgd` `BfdMgr` 側で polling 反映する設計、本リポでは未追跡)。

### APPL_DB

- `BfdOrch` は **APPL_DB を書かない**。`BFD_SESSION_TABLE` を `subscribe` 側として受信するのみ。
  別経路で `staticroutebfd` (`sonic-buildimage/dockers/docker-fpm-frr/staticroutebfd/`) が APPL_DB に書くケースはあるが、本ページのスコープ外。

### COUNTERS_DB / FLEX_COUNTER_DB

- `bfdorch.cpp` 全体で `COUNTERS_DB`・`FLEX_COUNTER_DB` への参照は **0 件** (`grep -nE "COUNTERS|FlexCounter|m_counters" bfdorch.cpp` で no match)。
- BFD セッションには SAI カウンタ enum (`SAI_BFD_SESSION_STAT_*`) が存在するが、`bfdorch` には FlexCounterManager 登録呼出が無く、`COUNTERS_DB` への `BFD:` キーは現状の master では生成されない。

### ASIC_DB

- 間接的に SAI BFD オブジェクト生成 (`sai_bfd_api->create_bfd_session`) 経由で syncd が `ASIC_DB` を更新するが、`bfdorch` は ASIC_DB を直接書かない。スコープ外。

### その他 (LOGLEVEL_DB / CHASSIS_APP_DB / DPU_APP_DB)

- 参照なし (grep 0 件)。

## 結論

副次 DB 書込は **STATE_DB の 2 テーブル** に閉じる:

1. `STATE_DB:BFD_SESSION_TABLE` (hardware 経路、SAI create/remove に同期 + state 通知)
2. `STATE_DB:SOFTWARE_BFD_SESSION_TABLE` (software 経路、CONFIG_DB 転記のみ)

COUNTERS_DB / APPL_DB への書込は `bfdorch` 起点では存在しない。
