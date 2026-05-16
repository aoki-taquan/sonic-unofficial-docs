# SYSLOG_SERVER テーブル 暗黙参照スキャン (Phase C)

`docs/reference/config-db/syslog-server.md` の Phase C (暗黙参照) ブロック裏付け資料。

ソースは:

- `sonic-net/sonic-host-services/scripts/hostcfgd` (`RSyslogCfg` クラス + `rsyslog_server_handler`)
- `sonic-net/sonic-buildimage/files/image_config/rsyslog/rsyslog-config.sh`
- `sonic-net/sonic-buildimage/files/image_config/rsyslog/rsyslog.conf.j2`

`SYSLOG_SERVER` テーブル変更時に `hostcfgd` の `RSyslogCfg` が間接的に駆動する **暗黙の CONFIG_DB 参照** を列挙する。`rsyslog_server_handler` が呼ばれると `SYSLOG_CONFIG` テーブルも必ず再取得し、さらに rsyslog-config.sh が `DEVICE_METADATA|localhost` を直接参照するという二段階の暗黙参照が存在する。

## スキャン手順

```bash
# 1. rsyslog_server_handler が呼ばれると何を読み直すか
grep -n "rsyslog_handler\|rsyslog_server_handler\|SYSLOG_CONFIG\|SYSLOG_SERVER\|get_table" \
    .cache/sonic-sources/sonic-host-services/scripts/hostcfgd \
  | sed -n '2410,2420p'

# 2. rsyslog-config.sh が CONFIG_DB から読む key
grep -n "sonic-db-cli\|CONFIG_DB\|DEVICE_METADATA" \
    .cache/sonic-sources/sonic-buildimage/files/image_config/rsyslog/rsyslog-config.sh

# 3. rsyslog.conf.j2 がテンプレート変数として受け取る値
grep -n "hostname\|udp_server_ip\|syslog_with_osversion\|syslog_counter\|SYSLOG_CONFIG\|SYSLOG_SERVER" \
    .cache/sonic-sources/sonic-buildimage/files/image_config/rsyslog/rsyslog.conf.j2 | head -30
```

## 検出された暗黙参照テーブル

### CONFIG_DB レベル — 直接暗黙参照

#### `SYSLOG_CONFIG` (共同再取得)

`rsyslog_server_handler` (hostcfgd:2417-2419) は `rsyslog_handler()` を呼ぶ。`rsyslog_handler()` (hostcfgd:2410-2415) は **`SYSLOG_CONFIG` と `SYSLOG_SERVER` の両テーブルを毎回再取得** してから `update_rsyslog_config()` に渡す。`SYSLOG_SERVER` の変化に起因するイベントでも `SYSLOG_CONFIG` が必ず読み直される。

```python
# hostcfgd:2410-2415
def rsyslog_handler(self):
    rsyslog_config = self.config_db.get_table(
        swsscommon.CFG_SYSLOG_CONFIG_TABLE_NAME)
    rsyslog_servers = self.config_db.get_table(
        swsscommon.CFG_SYSLOG_SERVER_TABLE_NAME)
    self.rsyslogcfg.update_rsyslog_config(rsyslog_config, rsyslog_servers)
```

| テーブル | 参照タイミング | 用途 | evidence |
|---|---|---|---|
| `SYSLOG_CONFIG` | `rsyslog_server_handler` 経由毎回 | `GLOBAL.severity` / `rate_limit_interval` / `rate_limit_burst` / `format` / `welf_firewall_name` を rsyslog.conf.j2 に渡す | hostcfgd:2410-2415 / rsyslog.conf.j2:16-18,51-52 |

#### `DEVICE_METADATA` (rsyslog-config.sh 経由)

`hostcfgd` が `systemctl restart rsyslog-config` を発行すると、`rsyslog-config.sh` が実行される (rsyslog-config.service → ExecStart)。このシェルスクリプトは `sonic-db-cli CONFIG_DB HGET` で `DEVICE_METADATA|localhost` を直接参照する。

```bash
# rsyslog-config.sh:3
PLATFORM=$(sonic-db-cli CONFIG_DB HGET 'DEVICE_METADATA|localhost' platform)

# rsyslog-config.sh:28
syslog_with_osversion=$(sonic-db-cli CONFIG_DB hget "DEVICE_METADATA|localhost" "syslog_with_osversion")

# rsyslog-config.sh:38
syslog_counter=$(sonic-db-cli CONFIG_DB hget "DEVICE_METADATA|localhost" "syslog_counter")
```

| フィールド | 用途 | evidence |
|---|---|---|
| `DEVICE_METADATA\|localhost.platform` | ASIC 設定ファイル (`/usr/share/sonic/device/$PLATFORM/asic.conf`) の読み込みパスを決定 → Multi-NPU 判定に使用 | rsyslog-config.sh:3,6-8 |
| `DEVICE_METADATA\|localhost.syslog_with_osversion` | `forward_with_osversion` 変数に代入。`true` の場合 rsyslog が OS バージョン付きフォーマット (`SONiCForwardFormatWithOsVersion`) を使用 | rsyslog-config.sh:28-31 / rsyslog.conf.j2:63,65-69 |
| `DEVICE_METADATA\|localhost.syslog_counter` | `syslog_counter` 変数に代入。`true` の場合 `omprog` モジュールが有効化され `/usr/bin/syslog-counter` が呼ばれる | rsyslog-config.sh:38-41 / rsyslog.conf.j2:25-27,127-129 |

> `hostname` は `hostname` コマンド（OS から直接取得）で、CONFIG_DB からは読まない (rsyslog-config.sh:26)。ただし `DEVICE_METADATA.localhost.hostname` が OS hostname を設定している場合は間接的に一致する。

#### `FEATURE` (SYSLOG_CONFIG_FEATURE 経由)

`SYSLOG_CONFIG_FEATURE|<service>` の `service` key は `FEATURE.name` への leafref。`rsyslog.conf.j2` は `SYSLOG_CONFIG` 経由でフィーチャー別 rate-limit を参照する構造になっているが、`FEATURE` テーブル本体は `rsyslog-config.sh` / `hostcfgd` からは直接 `get_table` されない（YANG 制約レベルの間接参照）。

### systemd unit 依存

`RSyslogCfg.update_rsyslog_config()` (hostcfgd:1715-1743) が発行するコマンド:

```python
run_cmd(['systemctl', 'reset-failed', 'rsyslog-config', 'rsyslog'], ...)
run_cmd(['systemctl', 'restart', 'rsyslog-config'], ...)
```

| 依存対象 | 関係 | 効果 | evidence |
|---|---|---|---|
| `rsyslog-config.service` | `restart` | `rsyslog-config.sh` を再実行して `rsyslog.conf` を再生成・`rsyslog.service` を再起動 | hostcfgd:1733-1736 / rsyslog-config.service |
| `rsyslog.service` | `rsyslog-config.service` が `ExecStart` 後に `systemctl restart rsyslog` を発行 | 設定変更を反映して rsyslog デーモン再起動 | rsyslog-config.sh:65 |
| `database.service` | `rsyslog-config.service` の依存（推定）| Redis 停止時に `sonic-db-cli` が失敗するため整合性確保 | rsyslog-config.service |

### MGMT_INTERFACE / MGMT_VRF_CONFIG (VRF バインド経由)

`SYSLOG_SERVER` エントリの `vrf` フィールドに `mgmt` を指定すると、rsyslog が `Device="mgmt"` でバインドして送信する。この VRF の有効化自体は `MGMT_VRF_CONFIG.mgmtVrfEnabled` で制御されており、`SYSLOG_SERVER` からの YANG `must` 制約が存在する。ただし `hostcfgd` の `RSyslogCfg` は `MGMT_VRF_CONFIG` / `MGMT_INTERFACE` を直接 `get_table` しない（YANG バリデーション層での間接参照）。

| テーブル | 参照種別 | 効果 | evidence |
|---|---|---|---|
| `MGMT_VRF_CONFIG.mgmtVrfEnabled` | YANG `must` 制約（間接参照） | `vrf==mgmt` エントリは `mgmtVrfEnabled==true` が前提。違反時は YANG バリデーションで拒否 | sonic-syslog.yang (must 制約) |
| `MGMT_INTERFACE` | 間接（ルーティング依存） | `vrf==mgmt` 時に rsyslog が `Device=mgmt` でパケットを発出する宛先インターフェース | rsyslog.conf.j2:116-118 |

## 範囲外 (誤解されやすい隣接テーブル)

- **`VRF`**: `vrf` フィールドが `VRF.name` への leafref だが、YANG 制約のみ。`hostcfgd` は `VRF` テーブルを get_table しない
- **`DEVICE_METADATA.localhost.hostname`**: `rsyslog-config.sh` は `hostname` コマンドを使うため CONFIG_DB から直接読まない。ただし `hostname` コマンドの出力は `DEVICE_METADATA.localhost.hostname` と一致する（システム hostname 設定が同期されている前提）
- **`FEATURE`**: SYSLOG_CONFIG_FEATURE の leafref 対象だが、rsyslog 設定生成パスでは直接参照されない

## まとめ — `syslog-server.md` Phase C 記載対象

| カテゴリ | 対象 | 種別 |
|---|---|---|
| 共同再取得 CONFIG_DB テーブル | `SYSLOG_CONFIG` | hostcfgd 内の `rsyslog_handler()` が毎回両テーブルを read |
| rsyslog-config.sh 経由の暗黙参照 | `DEVICE_METADATA\|localhost.platform` / `syslog_with_osversion` / `syslog_counter` | shell スクリプトが `sonic-db-cli HGET` で直接読む |
| YANG 制約レベル参照 | `MGMT_VRF_CONFIG.mgmtVrfEnabled` / `MGMT_INTERFACE` | `vrf==mgmt` 時の前提条件 |
| systemd 依存 | `rsyslog-config.service` / `rsyslog.service` | restart チェーン |
| 範囲外 | `VRF` / `FEATURE` | YANG leafref のみで実行時読み出しなし |

## 検証コマンド

```bash
grep -n "rsyslog_handler\|rsyslog_server_handler\|SYSLOG_CONFIG\|SYSLOG_SERVER" \
    .cache/sonic-sources/sonic-host-services/scripts/hostcfgd | grep -E "2410|2415|2417|2419|2499|2503"

grep -n "sonic-db-cli\|CONFIG_DB\|DEVICE_METADATA" \
    .cache/sonic-sources/sonic-buildimage/files/image_config/rsyslog/rsyslog-config.sh

grep -n "SYSLOG_CONFIG\|SYSLOG_SERVER\|syslog_with_osversion\|syslog_counter\|hostname" \
    .cache/sonic-sources/sonic-buildimage/files/image_config/rsyslog/rsyslog.conf.j2
```

このスキャン結果から派生して `docs/reference/config-db/syslog-server.md` の `<!-- cross-refs -->` ブロックを生成する。
