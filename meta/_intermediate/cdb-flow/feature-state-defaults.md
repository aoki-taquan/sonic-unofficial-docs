# FEATURE (STATE_DB) — Phase A コード由来の暗黙デフォルト (grep 証跡)

## 探索対象テーブル

`STATE_DB` の `FEATURE` テーブル（key: `FEATURE|<feature-name>`）。

書き込み元は主に 3 つ:
1. **`featured`** (`sonic-host-services/scripts/featured`) — `state` フィールドのみ書き込む
2. **`container_startup.py`** (`sonic-buildimage/src/sonic-ctrmgrd/ctrmgr/container_startup.py`) — 起動時に `current_owner` / `update_time` / `container_id` / `container_version` / `remote_state` を書き込む
3. **`ctrmgrd.py`** (`sonic-buildimage/src/sonic-ctrmgrd/ctrmgr/ctrmgrd.py`) — Kubernetes 連携時に `container_stable_version` / `container_last_version` を追加書き込みする

---

## field: state

**探索コマンド**:
```
grep -n "FEATURE_STATE_ENABLED\|FEATURE_STATE_DISABLED\|FEATURE_STATE_FAILED\|set_feature_state" featured
```

**結果**:
- `featured:132-134`: 定数定義
  ```python
  FEATURE_STATE_ENABLED = "enabled"
  FEATURE_STATE_DISABLED = "disabled"
  FEATURE_STATE_FAILED = "failed"
  ```
- `featured:585-590`: `set_feature_state(feature, state)` が STATE_DB の `FEATURE` テーブルに `[('state', state)]` を set する
- `featured:513`: `enable_feature()` 成功時 → `FEATURE_STATE_ENABLED` = `"enabled"`
- `featured:547`: `disable_feature()` 成功時 → `FEATURE_STATE_DISABLED` = `"disabled"`
- `featured:344,510,544`: systemctl 失敗時 → `FEATURE_STATE_FAILED` = `"failed"`

**code fallback**: **`"enabled"` / `"disabled"` / `"failed"`** のいずれか。デーモン起動前は STATE_DB にエントリなし（読み取りで空文字列が返る）。YANG schema なし。

---

## field: current_owner

**探索コマンド**:
```
grep -n "CURRENT_OWNER\|current_owner" container_startup.py container ctrmgrd.py
```

**結果**:
- `container_startup.py:16`: `CURRENT_OWNER = "current_owner"`
- `container_startup.py:44-51`: `read_data()` の state_data デフォルト定義:
  ```python
  state_data = {
      CURRENT_OWNER: "none",
      ...
  }
  ```
- `container_startup.py:172-176`: `update_state()` で実際に書き込む:
  ```python
  data = {
      CURRENT_OWNER: owner,  # "local" または "kube"
      ...
  }
  ```
- `ctrmgrd.py:93`: `dflt_st_feat` デフォルト: `ST_FEAT_OWNER: "none"`
- `container.py:23`: `CURRENT_OWNER = "current_owner"`; `read_state()` の fallback: `"none"`

**code fallback**: **`"none"`** — エントリ未存在または DB 欠落時のデフォルト。実稼働時は `"local"` または `"kube"`。

---

## field: update_time

**探索コマンド**:
```
grep -n "UPD_TIMESTAMP\|update_time" container_startup.py ctrmgrd.py
```

**結果**:
- `container_startup.py:17`: `UPD_TIMESTAMP = "update_time"`
- `container_startup.py:44-51`: state_data デフォルト: `UPD_TIMESTAMP: ""`
- `container_startup.py:175`: `update_state()` で書き込み:
  ```python
  UPD_TIMESTAMP: str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
  ```
- `ctrmgrd.py:48,94`: `ST_FEAT_UPDATE_TS = "update_time"`, dflt_st_feat: `ST_FEAT_UPDATE_TS: ""`

**code fallback**: **`""`** (空文字列) — container 起動前の初期状態。起動後は `"YYYY-MM-DD HH:MM:SS"` 形式の文字列。

---

## field: container_id

**探索コマンド**:
```
grep -n "DOCKER_ID\|CONTAINER_ID\|container_id" container_startup.py ctrmgrd.py container
```

**結果**:
- `container_startup.py:18`: `DOCKER_ID = "container_id"`
- `container_startup.py:44-51`: state_data デフォルト: `DOCKER_ID: ""`
- `container_startup.py:172-176`:
  ```python
  DOCKER_ID: get_docker_id() if owner != "local" else feature,
  ```
  - `owner == "local"` の場合: feature 名（例: `"bgp"`）を書き込む
  - `owner == "kube"` の場合: `/proc/self/cgroup` から取得した 12 文字 Docker コンテナ ID を書き込む
- `ctrmgrd.py:49,95`: dflt_st_feat: `ST_FEAT_CTR_ID: ""`

**code fallback**: **`""`** (空文字列) — 未起動時。ローカル管理時は feature 名 (文字列)、Kubernetes 管理時は 12 文字の Docker コンテナ ID。

---

## field: container_version

**探索コマンド**:
```
grep -n "VERSION\|container_version" container_startup.py ctrmgrd.py
```

**結果**:
- `container_startup.py:20`: `VERSION = "container_version"`
- `container_startup.py:44-51`: state_data デフォルト: `VERSION: "0.0.0"`
- `container_startup.py:176`: `update_state()` で書き込み: `VERSION: version` (引数で渡されたバージョン文字列)
- `ctrmgrd.py:50,96`: dflt_st_feat: `ST_FEAT_CTR_VER: ""`

**code fallback**: **`"0.0.0"`** (`container_startup.py:47`) または **`""`** (`ctrmgrd.py:96`)。`container_startup.py` が主書き込み元で `"0.0.0"` をフォールバック値として使用。起動後は docker コンテナの `IMAGE_VERSION` 環境変数から取得したバージョン文字列。

---

## field: container_stable_version

**探索コマンド**:
```
grep -n "container_stable_version\|ST_FEAT_CTR_STABLE_VER" ctrmgrd.py
```

**結果**:
- `ctrmgrd.py:51`: `ST_FEAT_CTR_STABLE_VER = "container_stable_version"`
- `ctrmgrd.py:97`: dflt_st_feat: `ST_FEAT_CTR_STABLE_VER: ""`
- `ctrmgrd.py:608-612`: `do_tag_latest()` 成功後に書き込み:
  ```python
  self.server.mod_db_entry(STATE_DB_NAME, FEATURE_TABLE, feat,
      {ST_FEAT_CTR_STABLE_VER: image_ver, ST_FEAT_CTR_LAST_VER: last_version})
  ```

**code fallback**: **`""`** (空文字列) — Kubernetes 管理機能のみが書き込む。`latest` タグ付け成功後に安定バージョンとして記録。ローカル管理機能では書き込まれない。

---

## field: container_last_version

**探索コマンド**:
```
grep -n "container_last_version\|ST_FEAT_CTR_LAST_VER" ctrmgrd.py
```

**結果**:
- `ctrmgrd.py:52`: `ST_FEAT_CTR_LAST_VER = "container_last_version"`
- `ctrmgrd.py:98`: dflt_st_feat: `ST_FEAT_CTR_LAST_VER: ""`
- `ctrmgrd.py:608-610`: `do_tag_latest()` 成功後に書き込み（直前の stable version を退避）

**code fallback**: **`""`** (空文字列) — Kubernetes 管理機能のみ。`latest` タグ付け成功後に 1 世代前の安定バージョンを保存。ローカル管理機能では書き込まれない。

---

## field: remote_state

**探索コマンド**:
```
grep -n "REMOTE_STATE\|remote_state\|REMOTE_RUNNING\|REMOTE_PENDING\|REMOTE_STOPPED\|REMOTE_NONE\|REMOTE_READY" container_startup.py ctrmgrd.py
```

**結果**:
- `container_startup.py:19`: `REMOTE_STATE = "remote_state"`
- `container_startup.py:44-51`: state_data デフォルト: `REMOTE_STATE: "none"`
- `ctrmgrd.py:64-68`: 定数定義:
  ```python
  REMOTE_RUNNING = "running"
  REMOTE_READY = "ready"
  REMOTE_PENDING = "pending"
  REMOTE_STOPPED = "stopped"
  REMOTE_NONE = "none"
  ```
- `ctrmgrd.py:99`: dflt_st_feat: `ST_FEAT_REMOTE_STATE: "none"`
- `container_startup.py:183`: kube 起動時 → `REMOTE_STATE: "running"` を書き込む
- `container_startup.py:244-245`: pending 遷移: `update_data(state_db, feature, { REMOTE_STATE: "pending" })`
- `ctrmgrd.py:559-566`: ctrmgrd が `REMOTE_RUNNING` 検知後に `latest` タグ処理を起動

**code fallback**: **`"none"`** — Kubernetes 管理外機能、または ctrmgrd 未稼働時。値の遷移は `none` → `pending` → `running` / `ready` → `stopped`。

---

## field: system_state

**探索コマンド**:
```
grep -n "SYSTEM_STATE\|system_state" container_startup.py ctrmgrd.py ctrmgr_tools.py
```

**結果**:
- `container_startup.py:21`: `SYSTEM_STATE = "system_state"`
- `container_startup.py:44-51`: state_data デフォルト: `SYSTEM_STATE: ""`
- `container_startup.py:155-160`:
  ```python
  def is_active(feature, system_state):
      if system_state == "up":
          return True
  ```
- `container_startup.py:223`: `if state_data[SYSTEM_STATE] == '': return` — 空文字列の場合は container_up 処理をスキップ
- `ctrmgr_tools.py:105`: `is_up = data.get(SYSTEM_STATE, "").lower() == "up"`
- `ctrmgrd.py:54,100`: dflt_st_feat: `ST_FEAT_SYS_STATE: ""`

**備考**: `system_state` の書き込み元は sonic-ctrmgrd/featured のコードには直接見つからない。読み込み専用として使われており、外部の systemd/health monitoring ツールが `"up"` / `"down"` を書き込むと推定される（`sonic-buildimage/src/sonic-ctrmgrd/tests/` のモックでは `"up"` / `"down"` が使われる）。

**code fallback**: **`""`** (空文字列) — ctrmgrd `dflt_st_feat` に基づく。`"up"` のとき container_up 処理が進む。`"down"` の場合 container は freeze（スリープ）する。

---

## YANG-コード 乖離サマリ

| フィールド | YANG default | コード fallback | 書き込み元 | 備考 |
|---|---|---|---|---|
| `state` | なし (YANG schema 未存在) | なし (STATE_DB に存在しない初期状態) | `featured` | enabled/disabled/failed の 3 値 |
| `current_owner` | なし | `"none"` | `container_startup.py` | local/kube/none |
| `update_time` | なし | `""` | `container_startup.py` | 起動時刻 (ISO 形式) |
| `container_id` | なし | `""` | `container_startup.py` | local=feature名、kube=12 文字 ID |
| `container_version` | なし | `"0.0.0"` / `""` | `container_startup.py` | IMAGE_VERSION 環境変数から取得 |
| `container_stable_version` | なし | `""` | `ctrmgrd.py` | Kubernetes 管理のみ |
| `container_last_version` | なし | `""` | `ctrmgrd.py` | Kubernetes 管理のみ |
| `remote_state` | なし | `"none"` | `container_startup.py` / `ctrmgrd.py` | none/pending/running/ready/stopped |
| `system_state` | なし | `""` | 外部 health monitoring ツール (推定) | up/down; ctrmgrd は読み取り専用 |

---

## 証跡ソース

| ソースファイル | 参照箇所 |
|---|---|
| `sonic-host-services/scripts/featured` | L132-134 (定数), L585-590 (set_feature_state), L513,547,344,510,544 (state 遷移) |
| `sonic-buildimage/src/sonic-ctrmgrd/ctrmgr/container_startup.py` | L16-51 (定数・デフォルト), L164-186 (update_state), L201-268 (container_up) |
| `sonic-buildimage/src/sonic-ctrmgrd/ctrmgr/ctrmgrd.py` | L47-54 (定数), L92-101 (dflt_st_feat), L593-612 (do_tag_latest) |
| `sonic-buildimage/src/sonic-ctrmgrd/ctrmgr/container` | L23-28 (定数), L99-111 (read_state デフォルト) |
| `sonic-buildimage/src/sonic-ctrmgrd/ctrmgr/ctrmgr_tools.py` | L16-18 (定数), L105 (system_state チェック) |
| `sonic-utilities/show/feature.py` | L44-53 (STATE_DB FEATURE フィールド一覧) |
