# syslog-config-feature — プラットフォーム差 (Phase H) 調査ログ

調査日: 2026-05-18  
対象: `SYSLOG_CONFIG_FEATURE` テーブル / `containercfgd` / `config syslog` CLI

## 調査対象ファイル

- `sonic-buildimage/src/sonic-containercfgd/containercfgd/containercfgd.py` (全行精読)
- `sonic-utilities/syslog_util/common.py` (全行精読)
- `sonic-utilities/config/syslog.py` (multi-asic 関連部分)

---

## 1. ASIC ベンダー差異

`containercfgd` は SAI 非経由。`containercfgd.py` を `platform|vendor|broadcom|mellanox|marvell|innovium|cisco` でスキャンして 0 ヒット。

**結論: ASIC ベンダー差異なし**

---

## 2. multi-asic (is_multi_asic == True) の挙動

### containercfgd 側

`containercfgd/main()` (L187-197) は環境変数 `NAMESPACE_ID` を読み取り、
- `NAMESPACE_ID` が空文字: `service_name = container_name` (シングル ASIC)
- `NAMESPACE_ID` が非空: `service_name = container_name.rstrip(namespace_id)`

`rstrip` によって `container_name` 末尾の `NAMESPACE_ID` 文字列を除去し、config DB のキー名と一致させる。
例: `container_name=swss0, NAMESPACE_ID=0` → `service_name="swss"` (DB key は `SYSLOG_CONFIG_FEATURE|swss`)。

ただし `rstrip` は文字単位の除去 (`str.rstrip`) であるため、`NAMESPACE_ID="0"` なら末尾の数字文字 `'0'` が全て除去される点に注意。

### CLI (config syslog rate-limit-container) 側

`config/syslog.py:469-501` に `--namespace` オプションあり。
- `namespace=None` (デフォルト): `db.cfgdb_clients` を全 namespace 分 iterate し、global_scope feature は全 namespace に書込み、per-asic feature は asic namespaceN のみ書込み
- `namespace="default"`: global namespace のみに書込み
- `namespace="asicN"`: 指定 asic namespace のみに書込み

`syslog_util/common.py:extract_feature_data()` (L81-105) は multi-asic 環境で:
- `has_global_scope=True` の feature → `global_feature_data` に分類 → 全 namespace に書込み
- `has_per_asic_scope=True` の feature → `per_ns_feature_data` に分類 → asic namespace のみに書込み

feature の scope 設定 (`has_global_scope`/`has_per_asic_scope`) は `FEATURE` テーブルに格納されており、
`SYSLOG_CONFIG_FEATURE` の書込み先 namespace が feature ごとに異なる可能性がある。

**結論: multi-asic 環境では CLI が namespace 分散書込みを行い、containercfgd がコンテナ内で `NAMESPACE_ID` strip を行う。DB key 自体は共通形式 (`service_name` ベース、asic suffix なし)。**

---

## 3. VOQ chassis (supervisor + line card)

`containercfgd.py` を `chassis|CHASSIS|chassisdb|REDIS_CHASSIS_SERVER|supervisor|linecard` でスキャンして 0 ヒット。

`ConfigDBConnector` は Unix socket 経由で host ローカル CONFIG_DB のみ接続 (`wait_for_init=True`)。
chassis 全体の集中設定機構なし。

**結論: VOQ chassis 差異なし。各 line card host で独立動作。**

---

## 4. SmartSwitch DPU

`containercfgd.py` を `DPU|dpu|smartswitch|SmartSwitch` でスキャンして 0 ヒット。
DPU コンテナが core dump を出しても、host の `SYSLOG_CONFIG_FEATURE` key が `service_name` 一致で処理される構造と同一。

**結論: SmartSwitch / DPU 差異なし。**

---

## 5. namespace (asic0..asicN 独立 CONFIG_DB)

multi-asic では各 asic namespace が独立した CONFIG_DB インスタンスを持つ。
CLI は namespace ごとに `cfgdb_clients[namespace]` で別インスタンスに書き込む。
`containercfgd` は `NAMESPACE_ID` に対応した service_name を使い、同 namespace の CONFIG_DB を購読する。
各 asic namespace の `containercfgd` インスタンスは独立して動作し、他 namespace の設定変更は受信しない。

**結論: namespace 分離は CLI + containercfgd の連携で自動管理。**

---

## エビデンス

- `containercfgd.py:190-195` — NAMESPACE_ID strip
- `syslog_util/common.py:92-104` — multi-asic での global/per-ns feature 振り分け
- `config/syslog.py:469-501` — --namespace オプション処理
- `config/syslog.py:513-560` — `get_feature_names_to_proceed()` — asic 別 feature 名生成
