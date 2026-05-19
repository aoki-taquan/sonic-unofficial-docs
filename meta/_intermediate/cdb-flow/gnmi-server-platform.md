# gnmi-server platform差分 根拠メモ

## 調査対象ソース

- `sonic-net/sonic-buildimage` `dockers/docker-sonic-gnmi/gnmi-native.sh` (sha: 9ea932ec)
- `sonic-net/sonic-gnmi` `telemetry/telemetry.go` (sha: eb635b76)
- `sonic-net/sonic-gnmi` `gnmi_server/connection_manager.go` (sha: eb635b76)
- `sonic-net/sonic-gnmi` `sonic_db_config/db_config.go` (sha: eb635b76)
- `sonic-net/sonic-gnmi` `sonic_data_client/db_client.go` (sha: eb635b76)

## CONFIG_DB テーブルスコープ

GNMI / GNMI_CLIENT_CERT / TELEMETRY_CLIENT テーブルは host CONFIG_DB にのみ存在する。
`gnmi-native.sh` の `sonic-cfggen -d` は host DB のみを参照し、`asicN` namespace を
iterate しない。

multi-asic 機での `GetDbDefaultNamespace()` 呼び出し (`connection_manager.go:33`) は
デフォルト namespace (host scope) を返す。CONFIG_DB テーブルの書込先は常に host DB。

## SmartSwitch 専用分岐

`gnmi-native.sh:89-92` の `LOCALHOST_SUBTYPE == "SmartSwitch"` 判定が唯一の
プラットフォーム条件。該当時 `-zmq_port=8100` を付与して orchagent ZMQ 経路を
有効化する。非 SmartSwitch 機では ZMQ ポートは付与されず、Redis ベース通信のみ。

```bash
# gnmi-native.sh:89-92
LOCALHOST_SUBTYPE=`sonic-db-cli CONFIG_DB hget "DEVICE_METADATA|localhost" "subtype"`
if [[ x"${LOCALHOST_SUBTYPE}" == x"SmartSwitch" ]]; then
    TELEMETRY_ARGS+=" -zmq_port=8100"
fi
```

GNMI テーブルに `zmq_port` フィールドは存在しない。値 `8100` はハードコード定数
(`gnmi-native.sh:91`, Phase E 参照)。

## multi-asic / VOQ chassis

`sonic_data_client/db_client.go:initRedisDbClients()` は `GetDbAllNamespaces()` で
全 namespace の Redis クライアントを初期化する。これは gNMI の **データ参照経路**
(Subscribe / Get の gNMI パスにおける DB ターゲット解決) に影響するが、
CONFIG_DB の GNMI / GNMI_CLIENT_CERT / TELEMETRY_CLIENT テーブル自体の
スキーマ・書込先・処理ロジックには影響しない。

gNMI パスに `/<dbName>/<namespace>` 形式でターゲットを指定することで
multi-asic 機の asicN namespace DB を参照できるが、これは CONFIG_DB テーブルの
フィールド定義とは独立した機能である。

## VRF 連携

`MGMT_VRF_CONFIG|vrf_global.mgmtVrfEnabled == "true"` 時に `--vrf mgmt` を付与
(`gnmi-native.sh:95-98`)。これは VRF 対応機種全般に共通であり、特定 ASIC への
依存はない。

## ASIC 種別依存なし

- gNMI サーバは SAI 非経由。ASIC ドライバ (Broadcom / Mellanox / Marvell 等) に
  依存するコードパスなし。
- `telemetry.go` / `gnmi-native.sh` / `connection_manager.go` を
  `platform|asic|vendor|broadcom|mellanox` で grep → 0 ヒット。
- ビルドタグ `gnmi_native_write` / `gnmi_translib_write` はビルド時条件分岐だが
  ハードウェア ASIC 種別ではなく管理フレームワーク統合の有無に依存する。
  コミュニティ版標準SONiC では常に `false`。

## 結論

プラットフォーム差は SmartSwitch (`subtype == "SmartSwitch"`) に局所化される。
それ以外の ASIC 種別・multi-asic・VOQ chassis 構成は CONFIG_DB テーブルの
定義・処理ロジックに影響しない。
