# FEATURE (STATE_DB) — Phase B 書込み順依存スキャンノート

対象ページ: `docs/reference/config-db/feature-state.md`
対象テーブル: `STATE_DB FEATURE`
Producer:
  - `featured` (`sonic-host-services/scripts/featured`) — `state` フィールド
  - `container_startup.py` (`sonic-buildimage/src/sonic-ctrmgrd/ctrmgr/container_startup.py`) — `current_owner` / `container_id` / `container_version` / `remote_state` 等
  - `ctrmgrd.py` (`sonic-buildimage/src/sonic-ctrmgrd/ctrmgr/ctrmgrd.py`) — `container_stable_version` / `container_last_version` / `remote_state`
スキャン範囲: `featured:1-680`; `container_startup.py:1-300`; `ctrmgrd.py:1-650`

---

## 検出した順序依存・タイミング依存

### 1. featured 起動 → CONFIG_DB 接続完了 → subscribe → state 書込み

- `featured` は `self.config_db.connect(wait_for_init=True, retry_on=True)` で CONFIG_DB が ready になるまで待機する (`featured:610-611`)。
- connect 完了後に `SubscriberStateTable` を `FEATURE_TBL` に登録し、既存エントリを全読み込みして `handler()` を呼ぶ。
- **順序依存**: `featured` が起動・接続完了するまで STATE_DB の `FEATURE|*` テーブルには `state` フィールドが書かれない。boot 直後の短い窓で `show feature status` を実行すると `state` 列が空になる。
- evidence: `featured:600-648`

### 2. delayed feature: APP_DB PORT_TABLE 初期化待ち → state 書込み

- `featured:21` で `PORT_TBL = swsscommon.APP_PORT_TABLE_NAME`、`featured:24` で `PORT_INIT_TIMEOUT_SEC = 180`。
- `featured` は APP_DB `PORT_TABLE` を subscribe し (`featured:647-648`)、`port_listener()` が最初の PORT エントリを受け取ると `enable_delayed_services()` を呼び出す (`featured:179-184`)。
- `delayed=True` な feature（例: `lldp`）は `is_delayed_enabled=False` の間 `enable_feature()` / `disable_feature()` を実行しない (`featured:273-274`)。
- `PORT_INIT_TIMEOUT_SEC` が経過しても PORT イベントが来ない場合はタイムアウトで強制 enable (`featured:659-660`)。
- **順序依存（強制先行）**: port init 完了か 180 秒 timeout まで `state` は STATE_DB に書かれない。boot 直後の数十秒〜数分間は delayed feature の `state` フィールドが存在しないかデフォルト初期状態となる。
- evidence: `featured:23-24,143,163-177,273-274,647-660`

### 3. advanced boot 完了待ち → featured 処理開始

- warm boot / fast boot 時は `RestartWaiter.isAdvancedBootInProgress(state_db_conn)` が真を返す。この場合 `featured` は `waitAdvancedBootDone()` でブロックし、STATE_DB に advanced boot 完了が書かれるまで feature 処理を開始しない (`featured:607-609`)。
- **順序依存（強制先行）**: advanced boot 中は `FEATURE_TBL` の subscribe ループが開始されず、STATE_DB の `FEATURE` テーブルへの書込みがブロックされる。
- evidence: `featured:607-609`

### 4. multi-asic 環境: 全インスタンス systemctl 成功後に state 書込み

- `enable_feature()` は `get_multiasic_feature_instances()` で返される全インスタンス名をループし、各インスタンスの `systemctl start` を逐次実行する (`featured:490-513`)。
- いずれかのインスタンスで失敗した時点で `set_feature_state(FAILED)` を書いて `return False` する。全インスタンス成功後にのみ `set_feature_state(ENABLED)` が呼ばれる (`featured:513`)。
- **順序依存（直列先行）**: multi-asic 環境では全インスタンスの起動が直列完了するまで `state=enabled` は書かれない。インスタンス数が多いほど書込みが遅延する。
- evidence: `featured:466-513`

### 5. state (featured) と current_owner (container_startup.py) は非同期独立書込み

- `featured` は `FEATURE|<name>` エントリの `state` フィールドのみを HSET で書き込む (`featured:585-590`)。
- `container_startup.py` は同エントリの `current_owner` / `update_time` / `container_id` / `container_version` / `remote_state` を別 HSET で書き込む。
- 両者は別プロセスであり、Redis に対してアトミックに **フィールド単位** で書くため、以下の中間状態が観測されうる:
  - `state=enabled` だが `current_owner=none` / `container_id=""` (featured が先行して書いた後、ctrmgrd 未稼働)
  - `current_owner=local` / `container_id=bgp` だが `state` フィールドなし (ctrmgrd が先行して書き、featured が未起動)
- **順序依存（非同期）**: `show feature status` は STATE_DB を直接読むため、中間状態がそのまま表示される。
- evidence: `featured:585-590`; `container_startup.py:164-186`

### 6. CONFIG_DB FEATURE エントリ削除 → STATE_DB エントリ全体削除

- CONFIG_DB で `FEATURE` エントリが削除されると `featured` の `handler()` が `DEL` イベントを受け取り、`_feature_state_table._del(feature_name)` を呼んで STATE_DB エントリ全体を削除する (`featured:190`)。
- **順序依存**: エントリ削除後に `container_startup.py` や `ctrmgrd.py` が同エントリに書き込もうとすると、削除されたはずのエントリが再生成される可能性がある（Redis HSET は存在しないキーに対しても書き込む）。運用上は CONFIG_DB からの feature 削除後に ctrmgrd の再起動を行うことが推奨される。
- evidence: `featured:190`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | `featured` 起動 → CONFIG_DB 接続 → subscribe → `state` 書込み | 強制先行 | boot 直後は `state` フィールドが存在しない窓あり |
| 2 | `delayed=True` feature: APP_DB PORT init または 180s timeout → `state` 書込み | **強制先行** | port init 完了まで delayed feature の `state` は書かれない |
| 3 | advanced boot (warm/fast boot) 完了 → featured 処理開始 | 強制先行 | advanced boot 中は全 feature の STATE_DB 書込みがブロック |
| 4 | multi-asic 環境: 全インスタンス systemctl 成功 → `state=enabled` 書込み | 直列先行 | インスタンス数に比例して書込みが遅延 |
| 5 | `state` (featured) と `current_owner` 等 (container_startup.py) は独立書込み | **非同期** | 中間状態あり; consumer は両フィールドが揃うまで再読が必要 |
| 6 | CONFIG_DB FEATURE エントリ削除 → STATE_DB エントリ全体削除 | 強制後行 | ctrmgrd が削除後に同エントリ書込みするとエントリが再生成される可能性 |

---

## ページ反映方針

- `<!-- ordering -->` ブロックを既存の `<!-- /defaults -->` と `<!-- cdb-exceptions -->` の間に挿入する。
- サマリ表 + 依存 #2（delayed feature）と #5（state/current_owner 非同期）を主軸とした散文を含める。
- 既存の `<!-- defaults -->` / `<!-- cdb-mermaid -->` / `<!-- cdb-exceptions -->` / `<!-- ops-hint -->` ブロックは触らない。
