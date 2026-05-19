# IP マルチキャストルート (P4RT) — Phase F 副作用スキャンノート

対象テーブル: `REPLICATION_IP_MULTICAST_TABLE` / `FIXED_IPV4_MULTICAST_TABLE` / `FIXED_IPV6_MULTICAST_TABLE`
Writer: `p4rt-app`
Consumer: `L3MulticastManager` / `IpMulticastManager` (`sonic-swss/orchagent/p4orch/`)
スキャン範囲: `ip_multicast_manager.cpp:L760-890`, `l3_multicast_manager.cpp:L2190-2270`

---

## 検出した副作用

### 1. P4OidMapper への OID 登録・参照カウント変更

REPLICATION_IP_MULTICAST_TABLE (SET):
- `m_p4OidMapper->setOID(SAI_OBJECT_TYPE_IPMC_GROUP, entry.multicast_group_id, mcast_group_oid)` — SAI グループ OID を登録 (`l3_multicast_manager.cpp:L2196-2197`)
- `m_p4OidMapper->setOID(SAI_OBJECT_TYPE_IPMC_GROUP_MEMBER, ...)` — 各メンバーの OID を登録 (`l3_multicast_manager.cpp:L2262`)
- `FIXED_IPV4/IPV6_MULTICAST_TABLE` が存在する場合、そのグループに対する参照カウントを管理するため、削除順を誤ると SWSS_RC_NOT_FOUND が発生する

FIXED_IPV4/IPV6_MULTICAST_TABLE (SET):
- `m_p4OidMapper->setDummyOID(SAI_OBJECT_TYPE_IPMC_ENTRY, key)` — 逆引き用ダミー OID 登録 (`ip_multicast_manager.cpp:L772-773`)
- `m_p4OidMapper->increaseRefCount(SAI_OBJECT_TYPE_IPMC_GROUP, multicast_group_id)` — グループの参照カウントをインクリメント (`ip_multicast_manager.cpp:L776-777`)
- `m_vrfOrch->increaseVrfRefCount(vrf_id)` — VRF の参照カウントをインクリメント (`ip_multicast_manager.cpp:L775`)

FIXED_IPV4/IPV6_MULTICAST_TABLE (DEL):
- `m_p4OidMapper->decreaseRefCount(SAI_OBJECT_TYPE_IPMC_GROUP, multicast_group_id)` — グループの参照カウントをデクリメント (`ip_multicast_manager.cpp:L881-882`)
- `m_p4OidMapper->eraseOID(SAI_OBJECT_TYPE_IPMC_ENTRY, key)` — IPMC エントリ OID を削除 (`ip_multicast_manager.cpp:L883-884`)
- `m_vrfOrch->decreaseVrfRefCount(vrf_id)` — VRF の参照カウントをデクリメント (`ip_multicast_manager.cpp:L886`)

### 2. CRM (Capacity Resource Manager) カウンタ更新

FIXED_IPV4/IPV6_MULTICAST_TABLE:
- SET (CREATE) 成功時: `gCrmOrch->incCrmResUsedCounter(CrmResourceType::CRM_IPMC_ENTRY)` (`ip_multicast_manager.cpp:L774`)
- DEL 成功時: `gCrmOrch->decCrmResUsedCounter(CrmResourceType::CRM_IPMC_ENTRY)` (`ip_multicast_manager.cpp:L885`)
- CRM は STATE_DB `CRM_STATS_TABLE` の使用量カウンタに反映される。閾値超過時に syslog アラートが発生する

### 3. 内部キャッシュ更新

- IpMulticastManager: `m_ipMulticastTable[key] = entry` で内部マップ更新 (`ip_multicast_manager.cpp:L768-771`)
- L3MulticastManager: `m_multicastGroupTable[key]` に SAI グループ・メンバー情報を格納

### 4. APP_DB への応答 publish

- 処理完了（成功・失敗問わず）後に `m_publisher->publish(APP_P4RT_TABLE_NAME, key, fvs, status)` でコントローラ (`p4rt-app`) に結果を書き戻す (`ip_multicast_manager.cpp:L183-189`, `l3_multicast_manager.cpp:L375,L433,L448,L476`)
- 失敗時は残りエントリに `SWSS_RC_NOT_EXECUTED` を付与してバッチ中断

### 5. SAI オブジェクト作成・削除

- REPLICATION SET: `SAI_OBJECT_TYPE_IPMC_GROUP` + `SAI_OBJECT_TYPE_IPMC_GROUP_MEMBER` を SAI に作成
- FIXED SET: `SAI_OBJECT_TYPE_IPMC_ENTRY` + 必要に応じて `SAI_OBJECT_TYPE_RPF_GROUP` / `SAI_OBJECT_TYPE_RPF_GROUP_MEMBER` / `SAI_OBJECT_TYPE_ROUTER_INTERFACE` / `SAI_OBJECT_TYPE_NEXT_HOP` を SAI に作成
- 初回 FIXED エントリ追加時は `createDefaultRpfGroup()` が RPF group を自動作成 (`ip_multicast_manager.cpp:L647-697`)
- 全 FIXED エントリ削除後は `deleteDefaultRpfGroup()` が RPF group を自動削除

---

## 副作用サマリ

| 操作 | 直接副作用 | 間接副作用 |
|------|-----------|-----------|
| REPLICATION SET | P4OidMapper IPMC_GROUP/MEMBER OID 登録、SAI IPMC_GROUP/MEMBER 作成 | FIXED テーブルから GROUP への参照カウント管理が有効化 |
| REPLICATION DEL | P4OidMapper OID 削除、SAI IPMC_GROUP/MEMBER 削除 | FIXED エントリが参照カウントを保持している間は削除失敗 |
| FIXED SET (初回) | P4OidMapper IPMC_ENTRY ダミー OID 登録、VRF refcount 増加、GROUP refcount 増加、CRM_IPMC_ENTRY インクリメント、RPF group 自動作成 | SAI IPMC_ENTRY 作成 |
| FIXED SET (UPDATE) | 古い GROUP refcount 減少、新 GROUP refcount 増加 | SAI IPMC_ENTRY 属性更新 |
| FIXED DEL | P4OidMapper IPMC_ENTRY OID 削除、VRF refcount 減少、GROUP refcount 減少、CRM_IPMC_ENTRY デクリメント | 全エントリ削除後に RPF group 自動削除 |
