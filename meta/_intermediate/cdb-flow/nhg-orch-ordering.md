# nhg-orch — Phase B 書込み順依存スキャンノート

対象テーブル: `NEXTHOP_GROUP_TABLE` / `CLASS_BASED_NEXT_HOP_GROUP_TABLE` / `FC_TO_NHG_INDEX_MAP_TABLE`
Consumer: `NhgOrch` / `CbfNhgOrch` / `NhgMapOrch` (`sonic-swss/orchagent/nhgorch.cpp`)
スキャン範囲: `doTask()` / `sync()` / `syncMembers()` / `update()` / `removeMembers()` / `createNhgmAttrs()` 全行精読

---

## 検出した順序依存・タイミング依存

### 1. NEXTHOP 先行必須 — メンバー NH が未 sync の場合グループ作成失敗

- `syncMembers()` (nhgorch.cpp:906–986) では各 `nh_key` に対して `nhgm.getNhId()` が `SAI_NULL_OBJECT_ID` であれば `success = false` のまま継続し、最終的に `sync()` → `doTask()` が `success = false` を返してエントリを再試行キューに戻す。
- **順序依存**: `NEXTHOP_GROUP_TABLE` エントリを書き込む前に、対応するネクストホップ (IPv4/IPv6/MPLS/SRv6) が `NeighOrch` によってすでに解決・sync 済みであること。NH が未登録だと NHG 作成はスキップされ、次回 `doTask()` 呼び出しで再試行される。
- evidence: `nhgorch.cpp:936–944`

### 2. allPortsReady() — ポート初期化完了が先行必須

- `NhgOrch::doTask()` の先頭 (nhgorch.cpp:41–44) で `gPortsOrch->allPortsReady()` を確認し、`false` の場合は即座に `return` する。
- **順序依存**: システム起動直後にポート初期化が完了していない間は `NEXTHOP_GROUP_TABLE` への書き込みが完全に無視される（再試行なし）。PortsOrch の初期化完了通知を待つ必要がある。
- evidence: `nhgorch.cpp:41–44`

### 3. recursive NHG — メンバー NHG の先行 sync 必須

- `doTask()` 内の recursive NHG 処理 (nhgorch.cpp:118–158) では、`nhgv` の各メンバーが `m_syncdNextHopGroups` に存在するか確認する。未存在メンバーは `non_existent_member = true` フラグを立て、NHG キーから除外して部分的に処理する。
- recursive または temporary なメンバー NHG を持つ場合は `invalid_member = true` でエントリ破棄 (nhgorch.cpp:142–148)。
- **順序依存**: recursive NHG を作成する場合、参照するすべてのメンバー NHG (`nexthop_group` フィールド) が先に `NEXTHOP_GROUP_TABLE` へ書き込まれ、`NhgOrch` によって sync 済みである必要がある。未 sync メンバーは `nhgs` から除外されるため、意図したグループ構成にならない可能性がある。
- evidence: `nhgorch.cpp:128–153`

### 4. SAI nhg_member 作成順 — グループ本体を先に作成してからメンバーを追加

- `NextHopGroup::sync()` (nhgorch.cpp:735–812) は以下の順序で実行される:
  1. `sai_next_hop_group_api->create_next_hop_group()` でグループ本体を作成 (nhgorch.cpp:775–779)
  2. `gCrmOrch->incCrmResUsedCounter()` で CRM カウント増加 (nhgorch.cpp:795)
  3. `syncMembers(m_key.getNextHops())` でメンバーを一括追加 (nhgorch.cpp:803)
- **順序保証**: メンバーは常にグループ本体の SAI OID (`m_id`) が確定した後に `create_next_hop_group_member` が呼ばれる。グループ本体なしのメンバー追加は発生しない。
- メンバー属性 (`createNhgmAttrs`) の設定順: `SAI_NEXT_HOP_GROUP_MEMBER_ATTR_NEXT_HOP_GROUP_ID` → `SAI_NEXT_HOP_GROUP_MEMBER_ATTR_NEXT_HOP_ID` → (weight != 0 の場合) `SAI_NEXT_HOP_GROUP_MEMBER_ATTR_WEIGHT` (nhgorch.cpp:1103–1118)。
- evidence: `nhgorch.cpp:775–808`, `nhgorch.cpp:1099–1121`

### 5. メンバー追加は ObjectBulker でバッチ処理

- `syncMembers()` (nhgorch.cpp:913–964) は `ObjectBulker<sai_next_hop_group_api_t>` を使い、全メンバーの `create_entry()` をバッファリングしてから `flush()` で一括 SAI 呼び出しを行う。
- メンバーの追加順序は `std::set<NextHopKey> nh_keys` の反復順（辞書順）に従う。ASIC への適用は `flush()` 後に一括実行される。
- インタフェースが down のメンバー (`NHFLAGS_IFDOWN`) はスキップされる (nhgorch.cpp:947–951)。
- evidence: `nhgorch.cpp:913–964`

### 6. update() — 削除を先行、追加を後続（ASIC メンバー上限対策）

- `NextHopGroup::update()` (nhgorch.cpp:999–1087) は以下の順序で実行される:
  1. 旧メンバーのうち不要なものを `removeMembers()` で削除 (nhgorch.cpp:1057)
  2. 新規メンバーを `m_members` に追加 (nhgorch.cpp:1070–1073)
  3. `syncMembers()` で全未 sync メンバーを一括追加 (nhgorch.cpp:1080)
- コメントに明示: "We first remove the missing members to avoid cases where we reached the ASIC group members limit." (nhgorch.cpp:993–995)
- **順序依存**: メンバー削除後に追加する順序は ASIC のグループメンバー数上限回避のための設計上の制約。逆順（追加→削除）では上限超過エラーが発生しうる。
- evidence: `nhgorch.cpp:988–1087`

### 7. 1 メンバー非 recursive NHG — グループ作成スキップ

- `sync()` (nhgorch.cpp:741–760) にて、非 recursive かつメンバー数が 1 の場合はグループを SAI に作成せず、メンバー NH の OID を直接 `m_id` として使用する。
- **順序依存**: この最適化は NH が既に sync 済みであることを前提とする。NH OID が `SAI_NULL_OBJECT_ID` の場合は `sync()` が `false` を返し、後続の `ROUTE_TABLE` 等への適用も失敗する。
- evidence: `nhgorch.cpp:741–760`

### 8. Temp NHG — リソース枯渇時の先行ランダム選択

- `NhgOrch::createTempNhg()` (nhgorch.cpp:824–898) は NHG 数が上限 (`getMaxNhgCount()`) に達した際に呼ばれ、有効な NH のうち 1 つをランダム選択して 1 メンバーグループを作成する。
- SRv6 NHG は Temp NHG 非対応 (nhgorch.cpp:866–870)。
- Temp NHG が後で full NHG に昇格する際には `update()` を経由し、SAI ID が変更される。参照側はその都度 NhgOrch に再問い合わせが必要。
- evidence: `nhgorch.cpp:824–898`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | NeighOrch NH 解決 → NEXTHOP_GROUP_TABLE | 先行必須 | 未 sync NH はスキップ・再試行 |
| 2 | PortsOrch allPortsReady() → NhgOrch doTask() | 先行必須 | 初期化完了前は全エントリ無視 |
| 3 | メンバー NHG の sync → recursive NEXTHOP_GROUP_TABLE | 先行必須 | 未 sync メンバーは除外、部分適用 |
| 4 | create_next_hop_group → create_next_hop_group_member | 強制先行（同一 sync() 内） | SAI API 構造上グループ先行を保証 |
| 5 | nhg_member 属性: GROUP_ID → NH_ID → WEIGHT | 固定順序（createNhgmAttrs） | weight=0 の場合は WEIGHT 属性省略 |
| 6 | removeMembers → syncMembers (update 時) | 強制先行（ASIC 上限回避） | 削除先行で空きを確保してから追加 |
| 7 | NH sync → 1 メンバー NHG 直接 OID 使用 | 先行必須 | NH 未 sync なら sync() false |
| 8 | Temp NHG 昇格時 SAI ID 変更 | 参照側再問い合わせ必要 | update() 経由で自動昇格 |
