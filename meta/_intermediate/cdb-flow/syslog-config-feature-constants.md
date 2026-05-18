# SYSLOG_CONFIG_FEATURE — Phase E ハードコード定数スキャンノート

対象ページ: `docs/reference/config-db/syslog-config-feature.md`
スキャン対象: `sonic-buildimage/src/sonic-containercfgd/containercfgd/containercfgd.py`
        および `sonic-buildimage/files/image_config/rsyslog/rsyslog-container.conf.j2`
スキャン日: 2026-05-18

---

## 検出したハードコード定数

### 1. ファイルパス定数 (SyslogHandler クラス変数)

| 定数名 | 値 | 用途 |
|-------|----|------|
| `SYSLOG_CONF_PATH` | `/etc/rsyslog.conf` | コンテナ内の rsyslog 設定ファイル（上書き対象）|
| `TMP_SYSLOG_CONF_PATH` | `/tmp/rsyslog.conf` | sonic-cfggen の出力先一時ファイル |

evidence: `containercfgd.py:101,103`

### 2. 正規表現パターン (既存 conf の解析用)

| 定数名 | 値 | 用途 |
|-------|----|------|
| `INTERVAL_PATTERN` | `r'.*SysSock.RateLimit.Interval="(\d+)".*'` | `/etc/rsyslog.conf` から現在の interval を抽出 |
| `BURST_PATTERN` | `r'.*SysSock.RateLimit.Burst="(\d+)".*'` | `/etc/rsyslog.conf` から現在の burst を抽出 |

evidence: `containercfgd.py:106-107`

### 3. テンプレートデフォルト値 (Jinja2 `|default()` フィルタ)

rsyslog-container.conf.j2 の Jinja2 テンプレートで、CONFIG_DB に値がない場合のフォールバック値。

| 変数 | デフォルト値 | 意味 |
|------|------------|------|
| `rate_limit_interval` | `300` (秒) | SYSLOG_CONFIG_FEATURE[container_name] にキーなし時の rate-limit インターバル |
| `rate_limit_burst` | `20000` (件) | 同上の burst 上限 |

evidence: `rsyslog-container.conf.j2:27`
```
module(load="imuxsock" SysSock.RateLimit.Interval="{{ rate_limit_interval|default('300') }}" SysSock.RateLimit.Burst="{{ rate_limit_burst|default('20000') }}")
```

**注意**: containercfgd の `update_syslog_config()` は DB エントリが空の場合に `'0'` を `new_interval`/`new_burst` として採用するが (`containercfgd.py:143-144`)、これは `sonic-cfggen -d` 実行時に `-a` オプションで渡す引数ではなく、Jinja2 が DB を直接参照するために、**DB にキーが存在しない状態**では Jinja2 の `|default()` フィルタが `300` / `20000` を採用する。
つまり「DB エントリなし」と「DB エントリあり（値 `0`）」では rsyslog の動作が異なる。

### 4. sonic-cfggen コマンド引数 (固定)

| 項目 | 値 | 説明 |
|------|----|------|
| コマンド | `sonic-cfggen` | SONiC 設定生成ツール |
| フラグ | `-d` | CONFIG_DB を読み込む |
| フラグ | `-t /usr/share/sonic/templates/rsyslog-container.conf.j2` | テンプレートファイルパス（固定） |
| フラグ | `-a '{"container_name": "<service_name>"}'` | JSON 変数（`container_name` を渡す） |

evidence: `containercfgd.py:155-156`

### 5. supervisord 制御コマンド (固定)

| 定数 | 値 | 用途 |
|------|----|------|
| 再起動コマンド | `['supervisorctl', 'restart', 'rsyslogd']` | rsyslog デーモンの再起動 |

evidence: `containercfgd.py:159`

### 6. 環境変数依存

| 環境変数 | 用途 |
|---------|------|
| `NAMESPACE_ID` | multi-asic 環境での namespace ID。空文字列なら single-asic |
| `CONTAINER_NAME` | コンテナ名。service_name の基になる |

`service_name` は `container_name.rstrip(namespace_id)` で導出される (`containercfgd.py:195`)。

### 7. OMRELP 転送設定 (固定値)

rsyslog-container.conf.j2 のリモート転送設定:

| rsyslog オプション | 固定値 | 意味 |
|-------------------|--------|------|
| `action.resumeRetryCount` | `"60"` | 接続失敗時の再試行上限 |
| `queue.type` | `"LinkedList"` | 転送キュータイプ |
| `queue.size` | `"20000"` | 転送キューサイズ（メッセージ数） |
| `port` | `"2514"` | OMRELP 転送ポート（`$SYSLOG_TARGET_IP` 宛） |

evidence: `rsyslog-container.conf.j2:63`

---

## ページ反映方針

- `<!-- failure -->` ブロック (`<!-- /failure -->`) の直後に `<!-- constants -->` ブロックを挿入する。
- テーブルパス定数・テンプレートデフォルト値・OMRELP 固定値の 3 グループを表形式でまとめる。
- 「DB エントリなしと値 `0` の違い」の注意点（テンプレートデフォルト `300`/`20000` が作動する条件）を散文で補足する。
