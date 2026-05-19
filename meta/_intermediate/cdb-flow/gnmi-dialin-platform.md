# gnmi-dialin platform差分 根拠メモ (Phase H)

調査対象: `sonic-net/sonic-gnmi`, `sonic-net/sonic-buildimage`
調査日: 2026-05-19

## 調査ソース

- `sonic-buildimage` `dockers/docker-sonic-gnmi/gnmi-native.sh` (sha: 9ea932ec)
- `sonic-gnmi` `telemetry/telemetry.go` (sha: eb635b76)
- `sonic-gnmi` `gnmi_server/connection_manager.go` (sha: eb635b76)
- `sonic-gnmi` `sonic_data_client/mixed_db_client.go` (sha: eb635b76)
- `sonic-gnmi` `sonic_data_client/db_client.go` (sha: eb635b76)

## platform 分岐の一覧

### 1. SmartSwitch — `-zmq_port=8100`

`gnmi-native.sh:89-92`:
```bash
LOCALHOST_SUBTYPE=`sonic-db-cli CONFIG_DB hget "DEVICE_METADATA|localhost" "subtype"`
if [[ x"${LOCALHOST_SUBTYPE}" == x"SmartSwitch" ]]; then
    TELEMETRY_ARGS+=" -zmq_port=8100"
fi
```

`DEVICE_METADATA|localhost.subtype == "SmartSwitch"` の場合のみ
`telemetry` デーモンに `-zmq_port=8100` フラグが付与される。
これにより orchagent との ZMQ 通信が有効化される。
それ以外の機種では ZMQ ポートは付与されず、ZMQ 経路は使用されない。

値 `8100` はハードコード。CONFIG_DB の GNMI テーブルには zmq_port フィールドは存在しない。

### 2. 管理 VRF — `--vrf mgmt`

`gnmi-native.sh:95-98`:
```bash
MGMT_VRF_ENABLED=`sonic-db-cli CONFIG_DB hget "MGMT_VRF_CONFIG|vrf_global" "mgmtVrfEnabled"`
if [[ x"${MGMT_VRF_ENABLED}" == x"true" ]]; then
    TELEMETRY_ARGS+=" --vrf mgmt"
fi
```

`MGMT_VRF_CONFIG|vrf_global.mgmtVrfEnabled == "true"` の場合のみ
`--vrf mgmt` フラグが付与される。対応機種は管理 VRF をサポートする全プラットフォームに共通。
ASIC 種別非依存。

GNMI テーブル自体に vrf フィールドは存在しない（`gnmi-native.sh` が `MGMT_VRF_CONFIG` を
別途参照する）。

### 3. multi-asic / namespace

GNMI テーブルは host namespace の CONFIG_DB にのみ存在する。
`gnmi-native.sh` の `sonic-cfggen -d` は host DB のみ参照し、`asicN` namespace を
iterate しない。

`sonic_data_client/mixed_db_client.go` の `GetDbAllNamespaces()` 呼び出しは
gNMI **データ参照経路**（Subscribe / Get のターゲット解決）に使用され、
GNMI テーブルの読み込みとは独立している。

multi-asic 機でもデーモンは host namespace で 1 プロセスのみ起動する。

## ASIC 種別非依存確認

`telemetry/telemetry.go`, `gnmi-native.sh`, `gnmi_server/clientCertAuth.go` を
`platform|asic|broadcom|mellanox|marvell|vendor` で grep → 0 ヒット（関連コード除く）。

gNMI サーバは SAI 非経由であり ASIC ドライバに依存しない。
ビルドタグ `gnmi_native_write` / `gnmi_translib_write` は管理フレームワーク統合の有無に依存し
ASIC 種別ではない。

## YANG スキーマ差異

`sonic-gnmi.yang` は単一ファイルであり、platform 固有の if-feature / deviation なし。
すべての機種で同一 YANG スキーマが適用される。

## 結論

GNMI テーブルのスキーマとフィールドは全プラットフォームで同一。
プラットフォーム差は起動スクリプト (`gnmi-native.sh`) の引数付与ロジックに局所化される:
- SmartSwitch のみ ZMQ ポート有効化 (フィールド追加なし、起動フラグのみ)
- 管理 VRF 対応機種で `--vrf mgmt` 付与 (GNMI テーブルフィールドには非依存)
