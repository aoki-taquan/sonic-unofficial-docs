# STATE_DB FEATURE テーブル — Phase E ハードコード定数スキャンノート

対象テーブル: `STATE_DB FEATURE`
書き込み主体: `featured` (`sonic-host-services/scripts/featured`), `container_startup.py` (`sonic-buildimage/src/sonic-ctrmgrd/ctrmgr/container_startup.py`), `ctrmgrd.py` (`sonic-buildimage/src/sonic-ctrmgrd/ctrmgr/ctrmgrd.py`)
スキャン範囲: featured:L1-50 (モジュール定数), L125-135 (FeatureHandler 定数), L426-427 (wait 定数); container_startup.py:L14-51 (DB フィールド定数・初期値); ctrmgrd.py:L181 (SELECT_TIMEOUT)

---

## 検出したハードコード定数一覧

### featured — モジュールレベル定数

| 定数名 | 値 | 用途 | ソース行 |
|--------|----|------|---------|
| `HOSTCFGD_MAX_PRI` | `10` | hostcfgd 配下デーモン間の ordering 優先度上限 | `featured:22` |
| `DEFAULT_SELECT_TIMEOUT` | `1000` (ms) | メインループの Redis select タイムアウト (1 秒) | `featured:23` |
| `PORT_INIT_TIMEOUT_SEC` | `180` (秒) | `delayed=True` feature の強制 enable タイムアウト。PORT_TABLE イベントが来なくても 180 秒経過後に enable_delayed_services() を強制実行 | `featured:24` |

### FeatureHandler — クラス定数

| 定数名 | 値 | 用途 | ソース行 |
|--------|----|------|---------|
| `FEATURE_STATE_ENABLED` | `"enabled"` | STATE_DB `state` フィールドへの書き込み値 (enable 成功時) | `featured:132` |
| `FEATURE_STATE_DISABLED` | `"disabled"` | STATE_DB `state` フィールドへの書き込み値 (disable 成功時) | `featured:133` |
| `FEATURE_STATE_FAILED` | `"failed"` | STATE_DB `state` フィールドへの書き込み値 (systemctl 失敗時) | `featured:134` |
| `FEATURE_EXCLUSION_LIST` | `{"telemetry", "frr_bmp"}` | enable/disable 操作をスキップする feature 名の集合。これらの feature は STATE_DB への `state` 書き込みが行われない | `featured:135` |
| `WAIT_FOR_STABLE_TIMEOUT` | `60` (秒) | systemd service が `activating` 状態を離れるまでの最大待機時間。超過時は警告ログのみで stop を続行 | `featured:426` |
| `WAIT_FOR_STABLE_POLL_INTERVAL` | `1` (秒) | `wait_for_service_stable()` のポーリング間隔 | `featured:427` |
| `SYSTEMD_SYSTEM_DIR` | `'/etc/systemd/system/'` | systemd ユニットファイルの配置ディレクトリ | `featured:128` |

### container_startup.py — DB フィールド名定数

| 定数名 | 値 | 対応 STATE_DB フィールド | ソース行 |
|--------|----|------------------------|---------|
| `CURRENT_OWNER` | `"current_owner"` | `FEATURE|<name>.current_owner` | `container_startup.py:16` |
| `UPD_TIMESTAMP` | `"update_time"` | `FEATURE|<name>.update_time` | `container_startup.py:17` |
| `DOCKER_ID` | `"container_id"` | `FEATURE|<name>.container_id` | `container_startup.py:18` |
| `REMOTE_STATE` | `"remote_state"` | `FEATURE|<name>.remote_state` | `container_startup.py:19` |
| `VERSION` | `"container_version"` | `FEATURE|<name>.container_version` | `container_startup.py:20` |
| `SYSTEM_STATE` | `"system_state"` | `FEATURE|<name>.system_state` | `container_startup.py:21` |

### container_startup.py — フィールド初期値

`read_data()` で STATE_DB からの読み込みが失敗した場合（エントリ不在）のデフォルト初期値:

| フィールド | 初期値 | ソース行 |
|-----------|--------|---------|
| `current_owner` | `"none"` | `container_startup.py:46` |
| `update_time` | `""` | `container_startup.py:47` |
| `container_id` | `""` | `container_startup.py:48` |
| `remote_state` | `"none"` | `container_startup.py:49` |
| `container_version` | `"0.0.0"` | `container_startup.py:50` (環境変数 `IMAGE_VERSION` の fallback も `'0.0.0'`) |
| `system_state` | `""` | `container_startup.py:51` |

> **注意**: `container_version` の初期値は `container_startup.py` では `"0.0.0"` だが、`ctrmgrd.py` の `dflt_st_feat` 辞書では `""` (L96)。ctrmgrd が STATE_DB を初期化する場合のみ `""` になる。

### ctrmgrd.py — タイムアウト定数

| 定数名 | 値 | 用途 | ソース行 |
|--------|----|------|---------|
| `MainServer.SELECT_TIMEOUT` | `1000` (ms) | ctrmgrd メインループの Redis select タイムアウト (1 秒) | `ctrmgrd.py:181` |

---

## CONFIG_DB/YANG で管理されない暗黙ルール

1. **`FEATURE_EXCLUSION_LIST` はコードにのみ存在**: `{"telemetry", "frr_bmp"}` は CONFIG_DB にも YANG にも設定パスがない。featured のソースコードを変更しない限り追加・削除できない。

2. **`PORT_INIT_TIMEOUT_SEC = 180` 秒**: `delayed=True` feature が依存する PORT_TABLE の初期化タイムアウト。デプロイ環境で PORT 初期化が 180 秒を超えた場合、タイムアウトで強制 enable されるため、コンテナが不完全な状態で起動しうる。

3. **`WAIT_FOR_STABLE_TIMEOUT = 60` 秒**: systemctl stop 前に service が `activating` を離れるのを最大 60 秒待機する。60 秒内に離れない場合は `"activating"` 状態のまま stop コマンドを発行し、ExecStop が実行されない可能性がある（Docker コンテナが孤立するリスク）。

4. **`container_version` の二元管理**: `container_startup.py` は `IMAGE_VERSION` 環境変数から取得し (`os.environ.get('IMAGE_VERSION', '0.0.0')`)、fallback は `"0.0.0"`。ctrmgrd が STATE_DB エントリを初期化する場合の fallback は `""` (ctrmgrd.py:96)。同一フィールドで異なる fallback が存在することに注意。
