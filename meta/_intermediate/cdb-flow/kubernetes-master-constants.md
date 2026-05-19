# KUBERNETES_MASTER テーブル — ハードコード定数 (Phase E) 解析メモ

対象: `KUBERNETES_MASTER|SERVER` テーブルの処理デーモン `ctrmgrd` に埋め込まれた、CONFIG_DB / YANG で管理されないハードコード定数の一覧。

ソース確認:
- `sonic-buildimage/src/sonic-ctrmgrd/ctrmgr/ctrmgrd.py:19-119` — 全定数宣言
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-kubernetes_master.yang:38-54` — YANG デフォルト値（参照）

## 1. リタイム定数 (`remote_ctr_config` デフォルト辞書)

`ctrmgrd.py:103-119` で定義される `remote_ctr_config` 辞書がタイミング制御の全デフォルト値を保持する。この辞書は `/etc/sonic/remote_ctr.config.json` が存在する場合にその内容で上書きされるが、ファイルが存在しない（標準インストール）場合はすべてハードコードデフォルトが使用される。

| キー定数名 | 辞書キー文字列 | デフォルト値 | 用途 | ソース行 |
|-----------|-------------|------------|------|---------|
| `JOIN_LATENCY` | `"join_latency_on_boot_seconds"` | `10` 秒 | 初回起動時に join を遅延させる待機時間 | `ctrmgrd.py:103,112` |
| `JOIN_RETRY` | `"retry_join_interval_seconds"` | `10` 秒 | `kube_join_master` 失敗時のリトライ間隔 | `ctrmgrd.py:104,113` |
| `LABEL_RETRY` | `"retry_labels_update_seconds"` | `2` 秒 | `kube_write_labels` 失敗時のリトライ間隔 | `ctrmgrd.py:105,114` |
| `TAG_IMAGE_LATEST` | `"tag_latest_image_on_wait_seconds"` | `5` 秒 | 最新イメージタグ待機時間 | `ctrmgrd.py:106,115` |
| `TAG_RETRY` | `"retry_tag_latest_seconds"` | `5` 秒 | タグ付け失敗時のリトライ間隔 | `ctrmgrd.py:107,116` |
| `CLEAN_IMAGE_RETRY` | `"retry_clean_image_seconds"` | `5` 秒 | 古いイメージ削除失敗時のリトライ間隔 | `ctrmgrd.py:108,117` |
| `USE_K8S_PROXY` | `"use_k8s_as_http_proxy"` | `""` (空文字) | K8s を HTTP プロキシとして使用するかどうか | `ctrmgrd.py:109,118` |

## 2. ファイルパス定数

| 定数名 | 値 | 用途 | ソース行 |
|--------|-----|------|---------|
| `SONIC_CTR_CONFIG` | `"/etc/sonic/remote_ctr.config.json"` | タイミング定数の上書きファイルパス。存在しない場合は `remote_ctr_config` のデフォルト値が使用される | `ctrmgrd.py:23` |

## 3. テーブル・キー文字列定数

これらの文字列定数は CONFIG_DB / STATE_DB のテーブル名・キー名として使用される。YANG モデル内の定義と一致している。

| 定数名 | 値 | 用途 |
|--------|-----|------|
| `SERVER_TABLE` | `"KUBERNETES_MASTER"` | CONFIG_DB / STATE_DB テーブル名 |
| `SERVER_KEY` | `"SERVER"` | テーブル内の固定キー名 |
| `KUBE_LABEL_TABLE` | `"KUBE_LABELS"` | Kubernetes ノードラベル書き込み先テーブル名 |
| `KUBE_LABEL_SET_KEY` | `"SET"` | KUBE_LABELS テーブルのキー名 |

## 4. select ループタイムアウト

| 定数名 | 値 | 用途 | ソース行 |
|--------|-----|------|---------|
| `MainServer.SELECT_TIMEOUT` | `1000` ms | `select()` ループのタイムアウト。1 秒ごとに wakeup して pending 処理を確認する | `ctrmgrd.py:181` |

## 5. CONFIG_DB フィールドデフォルト値（`dflt_cfg_ser` 辞書）

`dflt_cfg_ser` (`ctrmgrd.py:72-77`) は CONFIG_DB のエントリが存在しない場合のデフォルト値を定義する。YANG の `default` 宣言と一致している。

| フィールド | デフォルト値 | YANG default との一致 |
|-----------|------------|---------------------|
| `ip` | `""` (空文字) | YANG に default なし（一致） |
| `port` | `"6443"` | YANG: `default 6443`（一致） |
| `disable` | `"false"` | YANG: `default "false"`（一致） |
| `insecure` | `"true"` | YANG: `default "true"`（一致） |

## 6. 上書き可能性の判断

`SONIC_CTR_CONFIG` (`/etc/sonic/remote_ctr.config.json`) が存在する場合、`ctrmgrd.py:169-173` でファイルを読み込み `remote_ctr_config` 辞書を更新する。標準 SONiC インストールではこのファイルは存在しないため、`JOIN_RETRY` / `JOIN_LATENCY` 等はすべてハードコードデフォルト値が使われる。

## 7. Evidence

- `sonic-buildimage/src/sonic-ctrmgrd/ctrmgr/ctrmgrd.py:23` — `SONIC_CTR_CONFIG = "/etc/sonic/remote_ctr.config.json"`
- `sonic-buildimage/src/sonic-ctrmgrd/ctrmgr/ctrmgrd.py:103-119` — `JOIN_LATENCY = "join_latency_on_boot_seconds"` 等の定数宣言と `remote_ctr_config` デフォルト辞書
- `sonic-buildimage/src/sonic-ctrmgrd/ctrmgr/ctrmgrd.py:169-173` — `SONIC_CTR_CONFIG` からの辞書上書きロジック
- `sonic-buildimage/src/sonic-ctrmgrd/ctrmgr/ctrmgrd.py:181` — `SELECT_TIMEOUT = 1000`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-kubernetes_master.yang:38-54` — YANG デフォルト値（`port=6443`, `disable="false"`, `insecure="true"`）
