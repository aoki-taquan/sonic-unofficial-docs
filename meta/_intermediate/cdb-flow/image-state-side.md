# image-state Phase F — 副次 DB 書込みスキャンノート

対象: `/etc/sonic/sonic_version.yml`
スキャン範囲: `sonic-buildimage/src/sonic-ctrmgrd/ctrmgr/ctrmgrd.py`、`sonic-sairedis/syncd/scripts/syncd_init_common.sh`、`sonic-buildimage/files/image_config/rsyslog/rsyslog-config.sh`、`sonic-utilities/generic_config_updater/field_operation_validators.py`、`sonic-utilities/show/main.py`

---

## 結論

`/etc/sonic/sonic_version.yml` の値を起点に副次的に **DB へ書込む** のは `ctrmgrd` のみ。それ以外のコンポーネントはファイル内容を読み取るが DB への書込は行わない。

### STATE_DB への副次書込み — ctrmgrd

`ctrmgrd.py:292-306` の `set_node_labels()` 関数が `build_version` を読み取り、Kubernetes ノードラベルとして STATE_DB に書き込む。

| 副次 DB | テーブル / キー | フィールド | 書込み値 | evidence |
|---------|--------------|---------|---------|---------|
| STATE_DB | `KUBE_LABEL_TABLE|kube_labels` | `sonic_version` | `version_info['build_version']` | `ctrmgrd.py:301, 305-306` |

`set_node_labels()` は `ctrmgrd` の Kubernetes master 接続確立後（`ctrmgrd.py:440`）に呼ばれる。`build_version` の値がラベルとして Kubernetes ノードに付与され、同時に STATE_DB にも記録される。

### 副次書込みなし（読み取りのみ）のコンポーネント

| コンポーネント | 参照フィールド | 用途 | DB 書込み |
|---|---|---|---|
| `syncd_init_common.sh` | `asic_type` | syncd 起動パラメータ決定 | なし（環境変数として保持） |
| `rsyslog-config.sh` | `build_version` | rsyslog タグ文字列設定 | なし（設定ファイルのみ） |
| `generic_config_updater` | `asic_type`、`build_version` | フィールド操作の ASIC 固有バリデーション | なし（バリデーション判定のみ） |
| `show version` | 全フィールド | CLI 表示 | なし |
| `db_migrator.py` | `asic_type` | asic 固有マイグレーション判定 | なし（asic_type は判定用途のみ） |

---

## 詳細証跡

### ctrmgrd の STATE_DB 書込み（`ctrmgrd.py:292-306`）

```python
def set_node_labels(server):
    labels = {}
    version_info = (device_info.get_sonic_version_info() ...)
    ...
    labels["sonic_version"] = version_info['build_version']  # L301
    labels["hwsku"] = device_info.get_hwsku() ...
    labels["deployment_type"] = dep_type
    ...
    server.mod_db_entry(STATE_DB_NAME,
            KUBE_LABEL_TABLE, KUBE_LABEL_SET_KEY, labels)  # L305-306
```

`ctrmgrd` は Kubernetes 環境においてのみ有効（`FEATURE` テーブルで `set_owner=kube` が設定されている場合）。非 Kubernetes 環境では `set_node_labels()` が呼ばれないため STATE_DB への書込みも発生しない。

### 呼び出しタイミング

1. ctrmgrd 起動時に Kubernetes master 接続を確立
2. 接続確立後に `set_node_labels(server)` を呼び出す（`ctrmgrd.py:440`）
3. 以後は `KUBE_LABEL_TABLE` の変化を監視して Kubernetes API を通じてノードラベルを更新するが、`sonic_version` ラベルは起動時の 1 回のみ設定される（ランタイム更新なし）

### キャッシュによる制約（side-effects の遅延なし）

`device_info.get_sonic_version_info()` は ctrmgrd プロセス起動時に一度だけ呼ばれるため、その後 `/etc/sonic/sonic_version.yml` が変更されても STATE_DB の `sonic_version` ラベルは変わらない。ctrmgrd 再起動によってのみ反映される。
