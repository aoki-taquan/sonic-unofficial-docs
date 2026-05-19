# CONFIG_DB LOGGER テーブル — Phase B 書込み順依存スキャンノート

対象テーブル: `CONFIG_DB LOGGER`
Consumer: 各デーモン (`Logger::settingThread`) が `SubscriberStateTable` で購読
スキャン範囲: `sonic-swss-common/common/logger.cpp` (linkToDbWithOutput L114-156, settingThread L192-263)

---

## LOGGER テーブルの書込み経路

LOGGER テーブルは他の CONFIG_DB テーブルと異なり、**各デーモン自身が起動時に自分のエントリを書き込む**自己登録型である。

```
daemon 起動
  |
  | linkToDbNative() / linkToDbWithOutput()
  v
CONFIG_DB LOGGER|<component>  ← デーモンが自分のエントリを SET
  |
  | SubscriberStateTable (settingThread)
  v
デーモン内部の loglevel 変更
```

---

## 検出した順序依存・タイミング依存

### 1. 他テーブルとの依存関係 — なし

- `logger.cpp:linkToDbWithOutput()` は `LOGGER` テーブルのみを読み書きし、`VLAN`/`PORT`/`DEVICE_METADATA` 等のテーブル参照を行わない。
- `settingThread` も `CFG_LOGGER_TABLE_NAME` のみを購読する。
- **LOGGER テーブルは他テーブルに対する先行条件が存在しない**。

### 2. 起動前設定 vs 起動後設定

- **起動前 SET**: `linkToDbWithOutput()` (L132-137) は `table.hget(dbName, DAEMON_LOGLEVEL, prio)` で既存値を読む。CONFIG_DB に `LOGLEVEL` が既に設定されていれば、その値を使用しデフォルト上書きをスキップ (`doUpdate=false`)。
- **起動後 SET**: `settingThread` が `SubscriberStateTable` でリアルタイム変更を受け取り即時反映。遅延は SELECT タイムアウト最大 1000 ms。
- どちらのタイミングで書いても機能するが、**起動前設定はデフォルト上書きコストがなく確実**。

  evidence: `logger.cpp:132-148`

### 3. DEL コマンドは処理されない

- `settingThread` (L237-238): `op != SET_COMMAND` または `!m_settingChangeObservers.contains(key)` の場合は `continue` して無視。
- LOGGER エントリを `DEL` しても稼動中デーモンの loglevel は変化しない。
- デーモン再起動時に `linkToDbWithOutput()` がデフォルト値で再書き込みする。

  evidence: `logger.cpp:237-238`

### 4. 未登録コンポーネント名への SET

- `settingThread` は `m_settingChangeObservers.contains(key)` が false の場合スキップ (L238)。
- 存在しないコンポーネント名への SET は silently ignored。
- **コンポーネント名は `swssloglevel -p` で確認してから操作すること**。

### 5. 無効な loglevel 値へのフォールバック

- `swssPrioNotify()` (logger.cpp:83-84) が未知の文字列を受け取ると `"NOTICE"` にフォールバックしてエラーログを出力。
- SAI コンポーネントの場合は `SAI_LOG_LEVEL_NOTICE` にフォールバック。
- デーモンはクラッシュせず継続動作するが、設定は意図通りに反映されない。

---

## 推奨書込み順序

```text
# LOGGER テーブルは他テーブルに対する先行条件がないため、
# 任意タイミングで SET 可能。

# (推奨) デーモン起動前に事前設定:
SET CONFIG_DB LOGGER|orchagent  LOGLEVEL=DEBUG  LOGOUTPUT=SYSLOG
SET CONFIG_DB LOGGER|syncd      LOGLEVEL=INFO   LOGOUTPUT=SYSLOG

# デーモン起動後でもリアルタイム反映される (反映遅延最大 1000 ms):
SET CONFIG_DB LOGGER|orchagent  LOGLEVEL=INFO
```

- DEL は稼動中デーモンに影響を与えない（デーモン再起動まで変化なし）。
- コンポーネント名の大文字小文字は完全一致が必要 (`SAI_API_LAG` など)。
