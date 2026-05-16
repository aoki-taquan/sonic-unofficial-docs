# appl-fdb — Phase H プラットフォーム差調査ノート

対象ソース: `sonic-swss/orchagent/fdborch.cpp` (全 1802 行) と関連ヘッダ。

## 1. SAI capability に依存する分岐

### 1.1 `SAI_FDB_ENTRY_ATTR_ALLOW_MAC_MOVE` の付与

- `addFdbEntry()` の attr 構築で **VXLAN_ADVERTIZED / MCLAG_ADVERTIZED かつ `type == "dynamic"`** のときのみ `SAI_FDB_ENTRY_ATTR_ALLOW_MAC_MOVE = true` を付ける（`fdborch.cpp:1441-1448`）。
- AGE/MOVE 通知ハンドラ側でも MCLAG remote entry を再投入する際に同 attr を `true` で付与する（`fdborch.cpp:507-509`, `583-585`）。
- origin 切替 (VXLAN → local 等) の `macUpdate` パスでは `ALLOW_MAC_MOVE = false` へ落とす（`fdborch.cpp:1487-1497`）。
- **プラットフォーム差**: 一部 SAI 実装 (vendor SAI) は `SAI_FDB_ENTRY_ATTR_ALLOW_MAC_MOVE` を未サポート / 部分サポート。コード上は capability query を行わず**無条件に attr を渡している**ため、サポートしない ASIC では `create_fdb_entry` が `SAI_STATUS_NOT_SUPPORTED` を返し `handleSaiCreateStatus()` で task_failed 経路に入る。

### 1.2 FDB aging の扱い

- aging time そのものは `SwitchOrch` 側で `SAI_SWITCH_ATTR_FDB_AGING_TIME` として一元管理されている。FdbOrch は **aging 通知 (`SAI_FDB_EVENT_AGED`) の受信側**として動作する（`fdborch.cpp:421-545`）。
- MCLAG remote (`dynamic_local`) は意図的に `SAI_FDB_ENTRY_TYPE_DYNAMIC` で登録されており、これは **「aging を有効化するため」**とコメントされている（`fdborch.cpp:1552-1556`、`fdborch.cpp:88` 周辺コメント `aging enabled`）。`dynamic_local` 化された MAC はピア由来でも、ローカルで一定時間トラフィックが無ければ ASIC 側の aging が動いて消える設計。
- **プラットフォーム差**: ASIC によっては aging 通知が**個別 MAC 単位で発行されない**（バルク flush でのみ通知）、または `dynamic` 属性でも内部的に aging 対象外として扱う実装がある。コードはこれを capability query せず、aging 通知を前提に書かれている。

### 1.3 `SAI_FDB_FLUSH_ATTR_*` の前提

- `flushFDBEntries()` / `flushFdbByPortVlan()` / `flushFdbByVlan()` は `SAI_FDB_FLUSH_ATTR_BRIDGE_PORT_ID` / `SAI_FDB_FLUSH_ATTR_BV_ID` / `SAI_FDB_FLUSH_ATTR_ENTRY_TYPE = DYNAMIC` の 3 attr の組合せで `sai_fdb_api->flush_fdb_entries` を呼ぶ（`fdborch.cpp:949-1170`）。
- **プラットフォーム差**: SAI 仕様上、3 attr 全てを同時指定する flush をサポートしない vendor SDK がある（attr の組合せ制約）。コードは capability チェックをしない。

## 2. MCLAG 連動（Mlag / MclagOrch 依存）

- `gMlagOrch->isMlagInterface(p.m_alias)` で MCLAG メンバーポートかを判定し、**oper-down 時の自動 FDB flush をスキップ**する（`fdborch.cpp:1209-1213`）。MCLAG ピア経由でトラフィックが回るため、ローカル port down で flush すると BUM/unknown unicast の冗長が一時的に崩れる。
- MCLAG remote MAC (`FDB_ORIGIN_MCLAG_ADVERTIZED`) は STATE_DB の `MCLAG_FDB_TABLE` にも書き戻され、`mclagsyncd` がピアへの再 advertise に使う（`fdborch.cpp:872-878`, `901-908`, `1595-1612`）。
- **プラットフォーム差**: MCLAG を**サポートしない / mclagsyncd を起動しない**プラットフォームでは `gMlagOrch` 自体は常に生成されるが `isMlagInterface()` は常に false を返すだけで、機能的な分岐は no-op。MCLAG 関連 SAI attr (`ALLOW_MAC_MOVE`) を発行する条件 (origin == MCLAG_ADVERTIZED) もそもそも成立しないので、MCLAG 非対応 ASIC でも問題なく動作する。

## 3. multi-asic / chassis (VOQ) との関係

- `fdborch.cpp` 内では `gMySwitchType` / `chassis` / `VOQ` / namespace といったキーワードへの直接分岐は**存在しない**（grep 結果: 0 hit）。
- FdbOrch は ASIC ごとに 1 つ orchagent プロセスで動くため、multi-asic プラットフォーム (`asic0`, `asic1`, ...) では同じ FdbOrch ロジックが asic 単位で独立に動作する。FDB の asic 間共有は行われない（VOQ chassis の場合は system-FDB を別経路で扱うが、それは `sonic-swss` の別 Orch ではなく `fpmsyncd` / `system-MAC` 系で処理される）。
- **プラットフォーム差**: multi-asic / VOQ chassis でも fdborch.cpp 自体に差はない。ASIC 横断 MAC 同期は本テーブルのスコープ外。

## 4. まとめ — ドキュメントに書くべき差

| 観点 | 差の内容 | コード根拠 |
|------|---------|-----------|
| `ALLOW_MAC_MOVE` attr | VXLAN/MCLAG origin の dynamic MAC 専用。capability チェック無しで attr 投入 | `fdborch.cpp:1441-1448, 507-509, 583-585` |
| FDB aging | `dynamic_local` 化で aging を**意図的に有効化**。aging time は SwitchOrch 管理 | `fdborch.cpp:1552-1556` |
| MCLAG port oper-down | 自動 flush を**スキップ** | `fdborch.cpp:1209-1213` |
| MCLAG state 書き戻し | `MCLAG_FDB_TABLE` (STATE_DB) に追記 / 削除 | `fdborch.cpp:872-878, 901-908, 1595-1612` |
| multi-asic / VOQ | fdborch.cpp に分岐**なし**。asic 単位独立、横断同期なし | grep: `gMySwitchType` / `namespace` / `VOQ` 0 hit |

Phase H 完了。
