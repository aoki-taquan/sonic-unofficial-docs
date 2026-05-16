# TELEMETRY フィールドデフォルト調査 (Phase A)

## 調査対象

`docs/reference/config-db/telemetry.md` — `TELEMETRY|certs` / `TELEMETRY|gnmi` 全フィールド

## ソースコード由来デフォルト

### TELEMETRY|gnmi

| フィールド | デフォルト値 | 由来 | エビデンス |
|-----------|-------------|------|-----------|
| `port` | `50051` (minigraph 経由) / `8080` (gnmi なし時) | minigraph.py で `50051` を注入。GNMI キーが存在しない場合 `telemetry.sh` が `PORT=8080` にフォールバック | `sonic-buildimage/src/sonic-config-engine/minigraph.py` L2680; `dockers/docker-sonic-telemetry/telemetry.sh` L85 |
| `client_auth` | `"true"` (minigraph 注入) / 未設定なら `false` 扱い | minigraph.py が `'true'` を設定。`telemetry.sh` は空または `"false"` の場合 `--allow_no_client_auth` を付与 | `minigraph.py` L2679; `telemetry.sh` L96 |
| `log_level` | `2` | minigraph.py が `'2'` を注入。未設定 or 数字以外なら `telemetry.sh` が `-v=2` にフォールバック | `minigraph.py` L2681; `telemetry.sh` L104 |
| `save_on_set` | 未設定（= 無効） | コメントに明記: "gNMI save-on-set behavior is disabled by default" | `telemetry.sh` L107-113 |
| `enable_crl` | 未設定（= 無効） | `user_auth=cert` かつ `enable_crl=true` のときのみ有効化 | `telemetry.sh` L150-153 |
| `crl_expire_duration` | 未設定（= デフォルトなし、gnmiサーバ組み込み値を使用） | 設定がある場合のみフラグ渡し | `telemetry.sh` L155-158 |
| `user_auth` | 未設定（= 認証なし） | 未設定 or `null` のとき `--client_auth` 引数が付かない | `telemetry.sh` L142-144 |

### TELEMETRY|certs

| フィールド | デフォルト値 | 由来 | エビデンス |
|-----------|-------------|------|-----------|
| `server_crt` | `/etc/sonic/telemetry/streamingtelemetryserver.cer` | minigraph.py が注入 | `minigraph.py` L2684 |
| `server_key` | `/etc/sonic/telemetry/streamingtelemetryserver.key` | minigraph.py が注入 | `minigraph.py` L2685 |
| `ca_crt` | `/etc/sonic/telemetry/dsmsroot.cer` | minigraph.py が注入 | `minigraph.py` L2686 |

### フォールバック動作まとめ

- `TELEMETRY|certs` 未設定、かつ `DEVICE_METADATA.x509` も未設定 → `--noTLS` で起動
- `TELEMETRY|certs` あるが `server_crt`/`server_key` が空 → `--insecure` で起動
- `TELEMETRY|gnmi` キー自体が存在しない → `PORT=8080`、threshold=100、idle_conn_duration=5 でデフォルト起動
- threshold デフォルト: `100`（telemetry.sh L121）
- idle_conn_duration デフォルト: `5`（秒）（telemetry.sh L134）

## YANG でのデフォルト定義状況

`sonic-telemetry.yang` には `default` 文が一切定義されていない。すべてのフォールバックはランタイム側（`telemetry.sh` / `minigraph.py`）で実装されている。
