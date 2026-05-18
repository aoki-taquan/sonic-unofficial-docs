# FEATURE (STATE_DB) — Phase C 暗黙参照テーブル (cross-refs)

対象ページ: `docs/reference/config-db/feature-state.md`
生成日: 2026-05-18

---

## Phase C: 暗黙参照テーブルの分析

<!-- cross-refs -->

### 概要

STATE_DB `FEATURE` テーブルは `featured` と `sonic-ctrmgrd` (`container_startup.py`, `ctrmgrd.py`) が書き手であり、書き込み内容の決定に以下のテーブル・リソースを参照する。

---

### 参照テーブル一覧

| 参照先テーブル / リソース | 参照方向 | 条件 | 参照元 evidence |
|--------------------------|---------|------|----------------|
| `FEATURE\|<name>` (CONFIG_DB) | 購読トリガ + フィールド読込 | 常時。`featured` が SubscriberStateTable で購読し、SET/DEL イベントを受け取ると `state` フィールドを STATE_DB に書き込む | `featured:601,617-623,644-648`; `container_startup.py:57-62` |
| `DEVICE_METADATA\|localhost` (CONFIG_DB) | 読込のみ | 起動時 1 回。`type` フィールドから device_type（SpineRouter 等）を判定し、syncd/gbsyncd の `auto_restart` 上書き可否を決定する | `featured:617`; `featured:374` |
| `PORT_TABLE\|PortInitDone` (APPL_DB) | 購読トリガ | `delayed=True` な feature のみ。`PortInitDone` SET イベントを受け取ると `enable_delayed_services()` が実行され、STATE_DB への `state=enabled` 書込みが初めて発生する | `featured:647-649`; `featured:182-184` |
| `FEATURE\|<name>` (STATE_DB — 自己参照) | 読込のみ | `container_startup.py` が `read_data()` で同じ STATE_DB エントリを読み込み、`current_owner` / `container_version` / `remote_state` の現在値を確認してから書き込む | `container_startup.py:64-68`; `container_startup.py:164-186` |
| `KUBE_LABELS\|SET` (STATE_DB) | 読込 + 書込 | `set_owner=kube` 時のみ。`container_startup.py` が `check_version_blocked()` でバージョンブロックを確認し、`drop_label()` でバージョンラベルを書き込む。`ctrmgrd.py` が kube API から取得したラベルを同テーブルに反映する | `container_startup.py:90-106`; `ctrmgrd.py:305-307` |
| `KUBERNETES_MASTER\|SERVER` (CONFIG_DB / STATE_DB) | 読込 (CONFIG_DB) + 書込 (STATE_DB) | Kubernetes 連携時のみ。`ctrmgrd.py` が CONFIG_DB の接続先情報を読み込み、接続状態を STATE_DB `KUBERNETES_MASTER` に書き込む。STATE_DB `FEATURE` の `remote_state` 書込みは k8s 連携成立後に行われる | `ctrmgrd.py:29,334-342` |
| `IMAGE_VERSION` 環境変数 | プロセス環境変数読込 | コンテナ起動時。`container_startup.py` が `container_version` フィールドの値として `os.environ.get('IMAGE_VERSION', '0.0.0')` を使用する | `container_startup.py:50,176` |
| `RestartWaiter` (STATE_DB 内部機構) | 状態読込 | warm/fast boot 時のみ。`featured` 起動時に `isAdvancedBootInProgress()` が STATE_DB の boot 完了フラグを確認し、`waitAdvancedBootDone()` が完了するまで全 FEATURE 処理を保留する | `featured:607-609` |

<!-- /cross-refs -->

---

## Evidence

- `sonic-host-services/scripts/featured:601,607-609,617-623,644-649,182-184,374,588-590,190` — FeatureDaemon init, subscribe, set_feature_state, namespace propagation
- `sonic-buildimage/src/sonic-ctrmgrd/ctrmgr/container_startup.py:50,57-68,90-106,113-115,164-186,176` — read_data, update_state, drop_label, KUBE_LABELS references
- `sonic-buildimage/src/sonic-ctrmgrd/ctrmgr/ctrmgrd.py:29,305-307,334-342` — KUBERNETES_MASTER subscribe, KUBE_LABELS write
