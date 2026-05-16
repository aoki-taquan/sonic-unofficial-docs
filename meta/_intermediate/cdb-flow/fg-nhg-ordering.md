# FG_NHG — Phase B 書込み順依存スキャンノート

対象テーブル: `FG_NHG` / `FG_NHG_PREFIX` / `FG_NHG_MEMBER`
Consumer: `FgNhgOrch::doTaskFgNhg()` / `doTaskFgNhgPrefix()` / `doTaskFgNhgMember()` (`sonic-swss/orchagent/fgnhgorch.cpp`)
スキャン範囲: L146–213 (calculateBankHashBucketStartIndices), L257–314 (createFineGrainedNextHopGroup), L568–820 (setActiveBankHashBucketChanges), L1036–1198 (setNewNhgMembers / sprayBankNhgMembers), L1673–1744 (doTaskFgNhg), L1969–2030 (doTaskFgNhgMember) 精読

---

## 検出した順序依存・タイミング依存

### 1. FG_NHG が先行必須（FG_NHG_MEMBER の待機）

- `doTaskFgNhgMember()` L1996–2003: `m_fgNhgNexthops.find(fg_nhg_name)` で親 FG_NHG エントリが未登録の場合、`return false` を返す。
- `return false` は Consumer キューにエントリを残したまま終了するため、**次のイベントループで自動的に再試行**される。
- 親 FG_NHG が SET されて `doTaskFgNhg()` が処理完了するまで、`FG_NHG_MEMBER` の SET は毎イベントループで retry される（無限ポーリング）。
- 順序依存: `FG_NHG|<name>` の SET が FgNhgOrch に処理済みであること（SAI NHG OID 割り当て不要、内部マップ登録だけで十分）。
- evidence: `fgnhgorch.cpp:1996–2003`

### 2. FG_NHG が先行必須（FG_NHG_PREFIX の依存）

- `doTaskFgNhgPrefix()`: `m_fgNhgPrefixes` / `m_fgNhgGroups` で FG_NHG グループ名を検索する。
- グループが未登録の場合は `SWSS_LOG_ERROR` + `return true`（破棄、再試行なし）。
- **再試行なし**なので `FG_NHG_PREFIX` の SET は `FG_NHG` の処理完了後に発行する必要がある。
- 順序依存: `FG_NHG|<name>` → `FG_NHG_PREFIX|<prefix>` の順序が必須（逆順は PREFIX 破棄）。
- evidence: `fgnhgorch.cpp:doTaskFgNhgPrefix()` (m_fgNhgGroups lookup)

### 3. NEXTHOP 解決順序（NeighOrch 依存）

- `validNextHopInNextHopGroup()` L380–487 / `invalidNextHopInNextHopGroup()` L490–560: NeighOrch から NextHop の OID を取得し、解決済みの NH だけを `nhopgroup_members_set` に格納する。
- NH が NeighOrch に未登録の場合は `m_neighOrch->getNextHopId(nexthop)` が `SAI_NULL_OBJECT_ID` → SAI NHG member 作成スキップ（NH がアクティブになった時点で `validNextHopInNextHopGroup` が呼ばれ遅延追加）。
- **Fine-Grained ECMP の SAI エントリ作成は NH ごとに行われる**。全 NH が未解決でも FG_NHG 自体は SAI で作成され、NH が解決されるたびにバケット割り当てが行われる。
- 順序依存: NH 解決は遅延追加で自動調停されるが、`bucket_size` と実際の active NH 数の差が大きいほど一時的なトラフィック分散の偏りが発生する。
- evidence: `fgnhgorch.cpp:L380–487`

### 4. バンク割り当て順序（calculateBankHashBucketStartIndices）

- `calculateBankHashBucketStartIndices()` L154–213: バンクへのバケット割り当ては **バンク番号 0 から昇順**に行われる。
- `prefix-based` モード: 強制的に単一バンク（bank 0）のみ。`max_next_hops` 個の NH を均等分配。
- それ以外: `FG_NHG_MEMBER` の `bank` フィールド値 0 始まりで連番バンクを生成。バンク間バケット数は NH 比例配分（端数は低バンクから順に 1 ずつ加算）。
- **バンク番号に連番の欠番があると欠番分のバンクが空バンクとして確保**される（memb_per_bank に 0 が挿入される）。
- evidence: `fgnhgorch.cpp:L154–213`

### 5. SAI NHG member 作成順序（sprayBankNhgMembers）

- `sprayBankNhgMembers()` L1113–1198: バンクに割り当てられたバケット範囲（`hash_idx_range.start_index` 〜 `hash_idx_range.end_index`）を**昇順**にスキャンし、SAI `create_next_hop_group_member` を呼ぶ。
- 各バケットへの NH 割り当てはラウンドロビン: `bucket_idx % nhs_to_add.size()` で NH を選択。
- SAI 属性付与順序（create 時固定）:
  1. `SAI_NEXT_HOP_GROUP_MEMBER_ATTR_NEXT_HOP_GROUP_ID` (グループ OID)
  2. `SAI_NEXT_HOP_GROUP_MEMBER_ATTR_NEXT_HOP_ID` (NH OID)
  3. `SAI_NEXT_HOP_GROUP_MEMBER_ATTR_INDEX` (バケットインデックス)
- evidence: `fgnhgorch.cpp:L1133–1166`

### 6. バケット再配分順序（NH 追加・削除時）

- `setActiveBankHashBucketChanges()` L568–820: **単純ラウンドロビンは使わず、各 NH のバケット数を均等化するアルゴリズム**を採用。
- NH 削除時: 削除 NH のバケットを残存 NH に均等配布。各 NH の目標バケット数 = `num_buckets_in_bank / active_nhs`、余剰は先頭 NH から 1 ずつ加算。
- NH 追加時: 既存 NH からバケットを奪取して新規 NH に均等分配。奪取元 NH も均等化される。
- **バンク単位で独立処理**（他バンクには影響なし）。
- evidence: `fgnhgorch.cpp:L619–706` (del path), `fgnhgorch.cpp:L709–820` (add path)

### 7. warm-reboot 時の状態復元順序

- `sprayBankNhgMembers()` L1125–1146: `m_recoveryMap` に warm-reboot 前の prefix → bucket → NH マッピングが存在する場合は、そのマッピングを**そのまま復元**する（ラウンドロビン割り当ては行わない）。
- 復元時に NH が別バンクにいる場合（バンク全断の代替）: `inactive_to_active_map` に記録し、バンク間フォールバックを設定する。
- 順序依存: `m_recoveryMap` は orchagent 起動時に WARM_RESTART DB から読み込まれるため、warm-reboot 後は通常の SET イベント処理より前に復元が完了している。
- evidence: `fgnhgorch.cpp:L1125–1146`

### 8. FG_NHG_MEMBER を prefix-based グループに投入する禁止順序

- `doTaskFgNhgMember()`: `match_mode == PREFIX_BASED` のグループに `FG_NHG_MEMBER` を SET すると `SWSS_LOG_ERROR` + `return true`（破棄、再試行なし）。
- **prefix-based グループでは FG_NHG_MEMBER は一切受け付けない**。SET 後に match_mode を変更しても既投入エントリは復活しない。
- 順序依存: `match_mode` 確認なしに `FG_NHG_MEMBER` を投入すると silent discard。
- evidence: `fgnhgorch.cpp:doTaskFgNhgMember()` (prefix-based guard)

### 9. DEL 順序（グループ削除時）

- `FG_NHG` DEL 前に `FG_NHG_MEMBER` / `FG_NHG_PREFIX` を先に DEL しないと、グループ参照が残りリソースリークが生じる可能性がある。
- 推奨 DEL 順序: `FG_NHG_MEMBER` → `FG_NHG_PREFIX` → `FG_NHG`
- 逆順で DEL すると `FG_NHG_MEMBER` / `FG_NHG_PREFIX` の DEL 時に親グループが未存在となり `SWSS_LOG_INFO` で no-op（CONFIG_DB 上は消えるが内部マップ整合性は維持）。
- evidence: `fgnhgorch.cpp:doTaskFgNhgPrefix() DEL path`, `doTaskFgNhgMember() DEL path`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | FG_NHG SET → FG_NHG_MEMBER SET | 強制先行（自動 retry あり） | Consumer キュー残留で自動再試行 |
| 2 | FG_NHG SET → FG_NHG_PREFIX SET | 強制先行（再試行なし） | PREFIX を先に書くと破棄される |
| 3 | NeighOrch NH 解決 → SAI バケット割り当て | 遅延追加で自動調停 | validNextHopInNextHopGroup で随時追加 |
| 4 | バンク番号昇順（0 始まり連番推奨） | 欠番は空バンクとして確保 | 欠番回避のため bank 値は 0 始まり連番を推奨 |
| 5 | SAI NHG member 属性: GROUP_ID → NH_ID → INDEX | create 時固定順 | アプリ側は意識不要（FgNhgOrch が構築） |
| 6 | NH 追加/削除時のバケット均等化 | バンク単位独立、自動 | ラウンドロビン非採用（均等化アルゴリズム） |
| 7 | warm-reboot 復元（recoveryMap 優先） | 復元マップが通常割り当てより優先 | orchagent 起動前に recoveryMap ロード完了 |
| 8 | prefix-based グループへの FG_NHG_MEMBER 投入禁止 | 破棄（再試行なし） | match_mode 確認後に MEMBER 投入 |
| 9 | DEL 順序: MEMBER → PREFIX → FG_NHG | 推奨（逆順は no-op だが CONFIG_DB 残留） | 逆順は内部整合性維持されるが推奨しない |
