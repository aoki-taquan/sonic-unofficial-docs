# gnmi-state platform差分 根拠メモ

## 調査対象ソース

- `sonic-net/sonic-gnmi` `gnmi_server/connection_manager.go` (sha: eb635b7679b260c3fd0786a6d0734fc8e82c9a22)
- `sonic-net/sonic-gnmi` `gnmi_server/client_subscribe.go` (sha: eb635b7679b260c3fd0786a6d0734fc8e82c9a22)
- `sonic-net/sonic-gnmi` `telemetry/telemetry.go` (sha: eb635b7679b260c3fd0786a6d0734fc8e82c9a22)
- `sonic-net/sonic-gnmi` `sonic_db_config/db_config.go` (sha: eb635b7679b260c3fd0786a6d0734fc8e82c9a22)
- `sonic-net/sonic-buildimage` `dockers/docker-sonic-gnmi/gnmi-native.sh` (sha: 9ea932ec)

## TELEMETRY_CONNECTIONS の書込先 — 常に host STATE_DB

`connection_manager.go:33` の `sdcfg.GetDbDefaultNamespace()` は空文字列
(SONIC_DEFAULT_NAMESPACE) を返す (`db_config.go:15,29`)。
STATE_DB のアドレス・DB 番号解決は `GetDbTcpAddr("STATE_DB", "")` / `GetDbId("STATE_DB", "")` で
行われ、host namespace の database_config.json を参照する。

multi-asic 機で各 ASIC namespace (`asic0`, `asic1`, ...) に独立した STATE_DB が存在しても、
`TELEMETRY_CONNECTIONS` は **host namespace の STATE_DB にのみ** 書き込まれる。
gNMI サーバコンテナは host namespace で動作するため、per-asic 分岐は存在しない。

## platform 分岐コードの不在

`connection_manager.go`, `client_subscribe.go`, `telemetry.go` を
`multi_asic|is_multi_npu|chassis|asic[0-9]|namespace|platform|vendor` で grep → **0 ヒット**。

`TELEMETRY_CONNECTIONS` の HSet / HDel ロジックにプラットフォーム条件分岐は一切存在しない。

## SmartSwitch 構成

`gnmi-native.sh:89-92` の `LOCALHOST_SUBTYPE == "SmartSwitch"` 分岐は
`-zmq_port=8100` フラグを付与するのみ。これは gNMI サーバの **データ参照経路**
(orchagent ZMQ) に影響するが、`TELEMETRY_CONNECTIONS` テーブルの書込ロジックには
影響しない。SmartSwitch 機でも `ConnectionManager` は同一コードパスを走る。

## VOQ chassis / disaggregated chassis

TELEMETRY_CONNECTIONS を読み書きするのは `telemetry` デーモン単体のみ。
VOQ chassis 構成では supervisor / line card 各ホストが独立した `telemetry` デーモンを
持ち、それぞれ独立した STATE_DB に書き込む。chassis 全体の集中 TELEMETRY_CONNECTIONS
ストアは存在しない。

## ビルドタグ

`gnmi_native_write` / `gnmi_translib_write` はビルド時条件分岐だが、
これは管理フレームワーク統合の有無 (translib vs native Redis) に依存するものであり、
TELEMETRY_CONNECTIONS の書込処理とは無関係。`connection_manager.go` にビルドタグなし。

## 結論

TELEMETRY_CONNECTIONS テーブルのスキーマ・書込ロジック・書込先は
全プラットフォーム・全構成で同一。プラットフォーム依存コードパスは存在しない。
