# DPU / ENI / VDPU / REMOTE_DPU 副次 DB 書込調査メモ (Phase F)

調査日: 2026-05-18
対象: `DashEniFwdOrch` / `EniFwdCtxBase` / `EniAclRule`

## 調査対象ファイル

- `sonic-swss/orchagent/dash/dashenifwdorch.cpp` (createAclRule / deleteAclRule / addAclTable / deleteAclTable / lazyInit)
- `sonic-swss/orchagent/dash/dashenifwdinfo.cpp` (EniAclRule::fire, LocalEniNH::resolve, RemoteEniNH::resolve)
- `sonic-swss/orchagent/dash/dashenifwdorch.h` (ProducerStateTable 宣言, NeighOrch attach/detach)

---

## 直接 DB 書込

### APPL_DB への書込 (ProducerStateTable)

`EniFwdCtxBase` のコンストラクタで 3 本の `ProducerStateTable` を生成する (`dashenifwdorch.cpp:403-405`):

```cpp
rule_table_      = make_unique<ProducerStateTable>(applDb, APP_ACL_RULE_TABLE_NAME);
acl_table_type_  = make_unique<ProducerStateTable>(applDb, APP_ACL_TABLE_TYPE_TABLE_NAME);
acl_table_       = make_unique<ProducerStateTable>(applDb, APP_ACL_TABLE_TABLE_NAME);
```

| 書込テーブル | 操作 | トリガ | 証跡 |
|------------|------|--------|------|
| `APPL_DB:ACL_TABLE_TYPE_TABLE` | SET `ENI_REDIRECT` | ENI ACL ルール 1 件目の作成時 (`addAclTable()`) | `dashenifwdorch.cpp:603-630` |
| `APPL_DB:ACL_TABLE_TABLE` | SET `ENI` | 同上 | `dashenifwdorch.cpp:631-642` |
| `APPL_DB:ACL_RULE_TABLE` | SET `ENI:<vnet>_<MAC>[_TERM]` | `EniAclRule::fire()` で RESOLVED 時 | `dashenifwdinfo.cpp:205` |
| `APPL_DB:ACL_RULE_TABLE` | DEL `ENI:<vnet>_<MAC>[_TERM]` | ENI 削除 / primary endpoint 変更 | `dashenifwdinfo.cpp:182, 220` |
| `APPL_DB:ACL_TABLE_TYPE_TABLE` | DEL `ENI_REDIRECT` | ENI ACL ルール件数が 0 になったとき (`deleteAclTable()`) | `dashenifwdorch.cpp:594` |
| `APPL_DB:ACL_TABLE_TABLE` | DEL `ENI` | 同上 | `dashenifwdorch.cpp:594` |

### STATE_DB / COUNTERS_DB / ASIC_DB / FLEX_COUNTER_DB

`DashEniFwdOrch` / `EniFwdCtxBase` は `state_db` / `StateDBConnector` を持たない。STATE_DB への直接書込なし。

ASIC_DB は `AclOrch` が APPL_DB の `ACL_RULE_TABLE` エントリを受け取り SAI 経由で間接更新する（本orch は APPL_DB 書込のみ）。COUNTERS_DB / FLEX_COUNTER_DB への書込も存在しない。

---

## NeighOrch 副次効果 (ARP/NDP 解決)

### NeighOrch へのアタッチ

コンストラクタ (`dashenifwdorch.cpp:19`) で `neighorch_->attach(this)` を呼び、`NeighOrch` の Observer として登録される。これにより `NeighborUpdate` イベントを受信する。

### resolveNeighbor() — ARP/NDP 解決依頼

ローカル DPU (`dpu_type_t::LOCAL`) への ENI フォワーディングルール作成時、`LocalEniNH::resolve()` が `ctx->resolveNeighbor(nh)` を呼ぶ (`dashenifwdinfo.cpp:30`)。これは `NeighOrch::resolveNeighbor()` に委譲され、Neighbor が未解決の場合は ARP/NDP プローブを送出する副次効果を生む。

| ケース | 副次効果 |
|--------|---------|
| LOCAL DPU endpoint が未解決 | `NeighOrch::resolveNeighbor()` → ARP/NDP プローブ送出 |
| CLUSTER DPU endpoint | resolveNeighbor() 呼び出しなし。VxLAN トンネルのみ使用 |

### handleNeighUpdate() — Neighbor 解決後の ACL ルール再インストール

Neighbor が解決されると `DashEniFwdOrch::update()` → `handleNeighUpdate()` が呼ばれ (`dashenifwdorch.cpp:31-44`)、影響を受ける ENI の `fireAllRules()` を実行する。これが APPL_DB `ACL_RULE_TABLE` への SET 書込を副次的に発生させる。

---

## acl_rule_count_ — インメモリカウンタ

`EniFwdCtxBase::acl_rule_count_` が ACL ルール件数を追跡する。0 → 1 遷移で `addAclTable()` (APPL_DB SET)、1 → 0 遷移で `deleteAclTable()` (APPL_DB DEL) を発生させる。このカウンタは DB には露出しない。

---

## まとめ

| 副次 DB / リソース | 書込有無 | 根拠 |
|---|---|---|
| APPL_DB: ACL_TABLE_TYPE_TABLE | SET / DEL あり | `addAclTable()` / `deleteAclTable()` — `dashenifwdorch.cpp:603-648` |
| APPL_DB: ACL_TABLE_TABLE | SET / DEL あり | 同上 |
| APPL_DB: ACL_RULE_TABLE | SET / DEL あり | `createAclRule()` / `deleteAclRule()` — `dashenifwdorch.cpp:574-601` |
| STATE_DB | なし | `state_db` 参照なし |
| ASIC_DB | SAI 経由で間接更新 (AclOrch が担当) | — |
| COUNTERS_DB | なし | — |
| FLEX_COUNTER_DB | なし | — |
| NeighOrch: ARP/NDP プローブ | LOCAL DPU 時のみ副次送出 | `dashenifwdinfo.cpp:30` `resolveNeighbor()` |
