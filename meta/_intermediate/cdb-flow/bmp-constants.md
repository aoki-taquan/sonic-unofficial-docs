# BMP ハードコード定数 (Phase E)

調査日: 2026-05-16
対象ページ: `docs/reference/config-db/bmp.md`

## ソースファイル

| ファイル | 役割 |
|---------|------|
| `sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/bgpd.main.conf.j2` | FRR BMP 設定テンプレート（主要定数源） |
| `sonic-buildimage/src/sonic-config-engine/tests/sample_output/py3/bgpd_frr_bmp.conf` | 生成済みサンプル出力（定数確認） |
| `sonic-buildimage/src/sonic-bmpcfgd/bmpcfgd/bmpcfgd.py` | bmpcfgd デーモン |
| `sonic-buildimage/dockers/docker-bmp-watchdog/watchdog/src/main.rs` | BMP watchdog（ポート監視） |
| `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-bmp.yang` | YANG モデル（デフォルト値） |

## 検出されたハードコード定数

### FRR BMP 設定定数（`bgpd.main.conf.j2` L130-136）

| 定数名 | 値 | 説明 |
|--------|-----|------|
| `bmp targets` | `sonic-bmp` | BMP target station 名（FRR vtysh コマンド内固定） |
| `bmp mirror buffer-limit` | `4294967214` | BMP mirror バッファ上限（バイト）。`2^32 - 82` に相当 |
| `bmp stats interval` | `1000` | BMP 統計送信間隔（ミリ秒）。= 1 秒 |
| `bmp connect` host | `127.0.0.1` | openbmpd 接続先 IP（ローカルホスト固定） |
| `bmp connect` port | `5000` | openbmpd 待ち受けポート（TCP） |
| `min-retry` | `10000` | BMP 再接続最小待機時間（ミリ秒）。= 10 秒 |
| `max-retry` | `15000` | BMP 再接続最大待機時間（ミリ秒）。= 15 秒 |

### BMP Watchdog 定数（`main.rs` L41, L49-50）

| 定数名 | 値 | 説明 |
|--------|-----|------|
| BMP 接続確認ポート | `5000` | watchdog が openbmpd の生死を確認する TCP ポート（`bgpd.main.conf.j2` と一致） |
| watchdog HTTP ポート | `50060` | watchdog 自身の Health Check HTTP サーバポート |

### bmpcfgd 定数（`bmpcfgd.py` L20-24）

| 定数名 | 値 | 説明 |
|--------|-----|------|
| `CFG_DB` | `"CONFIG_DB"` | 購読対象 DB 名 |
| `BMP_STATE_DB` | `"BMP_STATE_DB"` | BMP 状態書き込み先 DB 名 |
| `REDIS_HOSTIP` | `"127.0.0.1"` | Redis 接続先 IP（固定） |
| `BMP_TABLE` | `"BMP"` | 購読テーブル名 |

### YANG モデル デフォルト値（`sonic-bmp.yang`）

| フィールド | YANG default |
|-----------|-------------|
| `bgp_neighbor_table` | `"true"` |
| `bgp_rib_in_table` | `"false"` |
| `bgp_rib_out_table` | `"false"` |

## 特記事項

- `bmp mirror buffer-limit 4294967214` は `2^32 - 82` = `4294967214` であり、FRR 内部の最大値に近い値を意図的に大きく設定している可能性がある
- `bmp targets sonic-bmp` の target 名 `sonic-bmp` は watchdog や各スクリプトでも参照されるが、USER 設定不可（テンプレートハードコード）
- openbmpd 接続先は常に `127.0.0.1:5000`。外部 BMP collector に直接送る構成は非サポート（openbmpd がゲートウェイになる）
- watchdog ポート `50060` はコンテナ内部のみで使用（外部公開なし）
