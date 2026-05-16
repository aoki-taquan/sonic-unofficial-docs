# SYSLOG_SERVER — Phase F 副次 DB 書込 中間ファイル

生成日: 2026-05-16
ソース: `sonic-host-services/scripts/hostcfgd` (`RSyslogCfg.update_rsyslog_config`)、`sonic-buildimage/files/image_config/rsyslog/rsyslog-config.sh`

---

## 概要

`SYSLOG_SERVER` の SET/DEL 処理後に `RSyslogCfg` が書き込む副次 DB は **0 件**。
副作用はすべて Linux ホスト OS ファイルシステムへの書込および systemd サービス制御に閉じる。

---

## 1. DB 書込スキャン結果

スキャン対象: `sonic-host-services/scripts/hostcfgd` の `RSyslogCfg` クラス (L1695–1743)

grep キーワード: `set(`、`hset(`、`hmset(`、`Producer(`、`Table(`、`Notification`、`STATE_DB`、`APPL_DB`、`COUNTERS_DB`

| DB | ヒット数 | 判定 |
|----|---------|------|
| APPL_DB | 0 | 書込なし |
| STATE_DB | 0 (クラス内) | 書込なし (`state_db_conn` を RSyslogCfg は保持しない) |
| COUNTERS_DB | 0 | 書込なし |
| FLEX_COUNTER_DB | 0 | 書込なし |
| ASIC_DB | 0 | 書込なし (SAI 非経由) |

---

## 2. 実際の副作用（ファイル書換 + systemd 制御）

### トリガ

`hostcfgd` の `rsyslog_server_handler()` (L2421) が `SYSLOG_SERVER` テーブルへの変更を検知すると `update_rsyslog_config()` を呼び出す。

### 副作用シーケンス

```
SYSLOG_SERVER 変更 (CONFIG_DB)
  └─ rsyslog_server_handler() → update_rsyslog_config()
       ├─ [1] systemctl reset-failed rsyslog-config rsyslog    # 前回失敗状態をクリア
       └─ [2] systemctl restart rsyslog-config
                └─ /usr/bin/rsyslog-config.sh
                     ├─ [3] sonic-cfggen -d -t rsyslog.conf.j2 → /tmp/rsyslog.conf.XXXXXX
                     ├─ [4] cmp /tmp/rsyslog.conf.XXXXXX /etc/rsyslog.conf
                     │    ├─ 差分あり:
                     │    │   [5] cp /tmp/rsyslog.conf.XXXXXX /etc/rsyslog.conf  ← ファイル書込
                     │    │   [6] systemctl restart rsyslog                       ← rsyslog 再起動
                     │    └─ 差分なし:
                     │        [7] systemctl kill -s HUP rsyslog                  ← SIGHUP のみ
                     └─ [8] rm /tmp/rsyslog.conf.XXXXXX
```

### ファイル書込詳細

| ファイル | 内容 | 条件 |
|---------|------|------|
| `/etc/rsyslog.conf` | `rsyslog.conf.j2` を `sonic-cfggen` で展開した rsyslog 設定全体 | `/tmp/rsyslog.conf.XXXXXX` との差分があるとき |

`rsyslog.conf.j2` は `SYSLOG_SERVER` 全エントリと `SYSLOG_CONFIG|GLOBAL` を参照し、リモート転送先 Action ブロックを生成する。エントリが 0 件の場合は転送 Action なしの設定が書き込まれる。

### systemd 制御詳細

| アクション | 対象サービス | 条件 | evidence |
|-----------|------------|------|----------|
| `reset-failed` | `rsyslog-config`、`rsyslog` | 毎回（ガード前） | hostcfgd:1732 |
| `restart rsyslog-config` | `rsyslog-config.service` | キャッシュ差分あり | hostcfgd:1734 |
| `restart rsyslog` | `rsyslog.service` | `/etc/rsyslog.conf` 差分あり | rsyslog-config.sh |
| `kill -s HUP rsyslog` | `rsyslog.service` | `/etc/rsyslog.conf` 差分なし | rsyslog-config.sh |

---

## 3. 失敗時の挙動

`systemctl restart rsyslog-config` が例外を送出した場合:
- `syslog.LOG_ERR` で `"RSyslogCfg: Failed to restart rsyslog service"` を記録
- `cache` を更新せずに `return` (キャッシュが旧状態のまま残る)
- 次回 `SYSLOG_SERVER` または `SYSLOG_CONFIG` の変更時に再試行される

evidence: `hostcfgd:1737-1740`

---

## 4. SYSLOG_CONFIG との結合処理

`update_rsyslog_config(rsyslog_config, rsyslog_servers)` は `SYSLOG_CONFIG` と `SYSLOG_SERVER` の**両テーブルをまとめてキャッシュ比較**する。

```python
if (self.cache.get('config', {}) != rsyslog_config or
    self.cache.get('servers', {}) != rsyslog_servers):
    # restart rsyslog-config
```

`SYSLOG_SERVER` 1 エントリの変更でも `SYSLOG_CONFIG` を含めた全設定が再生成・上書きされる。

---

## 5. 最適化（差分チェック）

`rsyslog-config.sh` は `/etc/rsyslog.conf` と一時ファイルを `cmp -s` で比較し、差分がない場合は `systemctl restart rsyslog` をスキップして `SIGHUP` のみ送信する。

これは Debian 13 (Trixie) の rsyslog.service における systemd サンドボックス (`PrivateTmp`, `ProtectSystem` 等) による再起動オーバーヘッド（約 4 秒）を回避するための最適化。

evidence: `rsyslog-config.sh` コメント行、`sonic-buildimage#25382`

---

## まとめ

`SYSLOG_SERVER` は SAI / orchagent 経由を持たないホスト設定テーブルであるため、副次 DB 書込は発生しない。
副作用の全体は「`/etc/rsyslog.conf` ファイル上書き」と「`rsyslog-config.service` / `rsyslog.service` の systemd 制御」に限定される。
