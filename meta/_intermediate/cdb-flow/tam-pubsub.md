# TAM テーブル群 — Phase G Redis 通知メカニズム 調査証跡

生成日: 2026-05-19  
対象ページ: `docs/reference/config-db/tam.md`  
調査コミット: sonic-swss `orchagent/high_frequency_telemetry/hftelorch.cpp`; sonic-mgmt-common CVL

---

## 1. 概要

TAM テーブル群（`TAM_DEVICE_TABLE` / `TAM_COLLECTOR_TABLE` / `TAM_INT_IFA_FEATURE_TABLE` / `TAM_INT_IFA_FLOW_TABLE`）は、コミュニティ版 orchagent の購読対象に含まれない。これらのテーブルへの書き込みは管理フレームワーク（REST/gNMI、`sonic-mgmt-framework`）経由で行われ、CVL バリデーション後に CONFIG_DB に格納される。

---

## 2. 管理フレームワーク経由の書き込みパス

`sonic-mgmt-framework` の Transformer は YANG / CVL を使って CONFIG_DB に書き込む。書き込み後の keyspace notification は自動的に発行されるが、コミュニティ版 orchagent でこれを受信するハンドラは存在しない。

```
REST/gNMI 操作
  → sonic-mgmt-framework (Transformer + CVL バリデーション)
    → CONFIG_DB SET: TAM_DEVICE_TABLE|device / TAM_COLLECTOR_TABLE|<name> / TAM_INT_IFA_*
      → Redis keyspace notification (__keyspace@4__:TAM_*|*)
        → orchagent: 購読なし（コミュニティ版）
```

---

## 3. HFTelOrch — SAI TAM オブジェクトは CONFIG_DB 非購読

`hftelorch.cpp` は SAI TAM オブジェクトを生成するが、CONFIG_DB の `TAM_*_TABLE` を `SubscriberStateTable` で購読しない。HFTelOrch が読む HFTel 系テーブルと TAM テーブルは別系統である。

---

## 4. HFTelOrch の NotificationConsumer（SAI 通知）

`HFTelOrch::doTask(NotificationConsumer&)` は APPL_DB / CONFIG_DB のテーブル変化ではなく、SAI から届くハードウェア通知（`SAI_SWITCH_NOTIFICATION_ATTR_*`）を処理する。この通知経路は keyspace ベースの pubsub とは異なる SAI コールバックメカニズムである。

---

## 5. evidence

- `sonic-swss/orchagent/high_frequency_telemetry/hftelorch.cpp` — `SubscriberStateTable` で TAM テーブル購読なし
- `sonic-mgmt-common/cvl/testdata/schema/sonic-tam.yang` — YANG スキーマ定義
- `sonic-mgmt-common/cvl/testdata/schema/sonic-ifa.yang` — CVL leafref 制約定義
- `meta/_intermediate/cdb-flow/tam-ordering.md` — orchagent 購読ゼロを確認
