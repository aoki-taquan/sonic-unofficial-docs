# tam Phase E — ハードコード定数スキャンノート

調査日: 2026-05-19
対象ページ: `docs/reference/config-db/tam.md`
フェーズ: Phase E (ハードコード定数)

## 調査対象ソース

| ファイル | リポジトリ | SHA | 役割 |
|---------|-----------|-----|------|
| `cvl/testdata/schema/sonic-tam.yang` | sonic-net/sonic-mgmt-common | HEAD | TAM/Collector YANG スキーマ |
| `cvl/testdata/schema/sonic-ifa.yang` | sonic-net/sonic-mgmt-common | HEAD | IFA YANG スキーマ |
| `orchagent/portsorch.cpp` | sonic-net/sonic-swss | HEAD | Path Tracing TAM SAI オブジェクト生成 |
| `orchagent/high_frequency_telemetry/hftelorch.cpp` | sonic-net/sonic-swss | HEAD | HFTel TAM オブジェクト生成 |

## 検出した定数一覧

### YANG スキーマ由来のハードコード定数

| 定数 | 値 | 宣言箇所 | 説明 |
|------|----|---------|------|
| `TAM_DEVICE_TABLE.deviceid` YANG default | `0` | `sonic-tam.yang:36` | DB に存在しない場合のデフォルト TAM デバイス ID |
| `TAM_DEVICE_TABLE.name` 許容値 | `device`（enumeration 固定） | `sonic-tam.yang:28-31` | singleton キー; `device` 以外は CVL が拒否 |
| `TAM_INT_IFA_FEATURE_TABLE.name` 許容値 | `feature`（enumeration 固定） | `sonic-ifa.yang:28-31` | singleton キー; `feature` 以外は CVL が拒否 |
| `TAM_COLLECTOR_TABLE.name` 最大長 | `32` 文字 | `sonic-tam.yang:50` | YANG `length 1..32` |
| `TAM_COLLECTOR_TABLE.name` 文字パターン | `[a-zA-Z0-9]{1}([-a-zA-Z0-9_]{0,32})` | `sonic-tam.yang:49` | 先頭は英数字必須 |
| `TAM_INT_IFA_FLOW_TABLE.name` 最大長 | `32` 文字 | `sonic-ifa.yang:47` | YANG `length 1..32` |
| `TAM_INT_IFA_FLOW_TABLE.name` 文字パターン | `[a-zA-Z0-9]{1}([-a-zA-Z0-9_]{0,32})` | `sonic-ifa.yang:46` | 先頭は英数字必須 |
| `TAM_INT_IFA_FLOW_TABLE.sampling-rate` 最小値 | `1` | `sonic-ifa.yang:64` | `range "1..10000"` |
| `TAM_INT_IFA_FLOW_TABLE.sampling-rate` 最大値 | `10000` | `sonic-ifa.yang:64` | 超過時 ErrAppTag `"Invalid IFA flow sampling rate."` |
| `TAM_COLLECTOR_TABLE.port` 範囲 | `0..65535` (`inet:port-number`) | `sonic-tam.yang:57` | ポート番号 IANA 型 |
| `TAM_COLLECTOR_TABLE` `must` `error-app-tag` | `ipaddres-type-mismatch`（typo: `s` 欠落） | `sonic-tam.yang:62` | CVL が実際に返す文字列（typo のまま固定） |

### portsorch.cpp の Path Tracing TAM ハードコード値

`createPtTam()` は `TAM_DEVICE_TABLE` の `deviceid` を**読まず**、SAI TAM INT オブジェクトに固定値を使用する。

| 定数 | 値 | 宣言箇所 | 説明 |
|------|----|---------|------|
| `SAI_TAM_INT_ATTR_DEVICE_ID` | `0`（固定） | `portsorch.cpp:11597-11598` | CONFIG_DB の `deviceid` に関わらず 0 を使用 (dead field) |
| `SAI_TAM_INT_ATTR_TYPE` | `SAI_TAM_INT_TYPE_PATH_TRACING` | `portsorch.cpp:11593-11594` | Path Tracing 専用 |
| `SAI_TAM_INT_ATTR_INT_PRESENCE_TYPE` | `SAI_TAM_INT_PRESENCE_TYPE_UNDEFINED` | `portsorch.cpp:11601-11602` | プレゼンス検出なし |
| `SAI_TAM_INT_ATTR_INLINE` | `false` | `portsorch.cpp:11605-11606` | インライン処理なし |
| `SAI_TAM_REPORT_ATTR_TYPE` | `SAI_TAM_REPORT_TYPE_VENDOR_EXTN` | `portsorch.cpp:11567-11568` | ベンダー拡張レポート形式 |

### hftelorch.cpp の HFTel TAM ハードコード値

`createTAM()` が作成する SAI TAM オブジェクト群はすべてハードコード値を使用する（`TAM_COLLECTOR_TABLE` の CONFIG_DB 設定は SAI 操作に反映されない）。

| 定数 | 値 | 宣言箇所 | 説明 |
|------|----|---------|------|
| `SAI_TAM_TRANSPORT_ATTR_TRANSPORT_TYPE` | `SAI_TAM_TRANSPORT_TYPE_NONE` | `hftelorch.cpp:751-752` | Transport なし（netlink 経由） |
| `SAI_TAM_COLLECTOR_ATTR_SRC_IP` | `0.0.0.0`（固定） | `hftelorch.cpp:766-768` | 送信元 IP 固定値 |
| `SAI_TAM_COLLECTOR_ATTR_DST_IP` | `0.0.0.0`（固定） | `hftelorch.cpp:771-773` | 宛先 IP 固定値（localhost） |
| `SAI_TAM_COLLECTOR_ATTR_LOCALHOST` | `true` | `hftelorch.cpp:780-781` | ローカルホスト向け |
| `SAI_TAM_COLLECTOR_ATTR_DSCP_VALUE` | `0` | `hftelorch.cpp:788-789` | DSCP 値 0 固定 |
| `SAI_TAM_ATTR_TAM_BIND_POINT_TYPE_LIST` | `SAI_TAM_BIND_POINT_TYPE_SWITCH` | `hftelorch.cpp:802-807` | Switch レベルバインド |
| `CONSTANTS_FILE` パス | `/et/sonic/constants.yml` ※ | `hftelorch.cpp:23` | typo: `/etc/` でなく `/et/` (誤植と思われる) |

> ※ `#define CONSTANTS_FILE "/et/sonic/constants.yml"` はタイポ（`/etc/` の `c` が脱落）。現在このパスは `hftelorch.cpp` 内で参照されていない（定義のみ）。

## ページ反映方針

- `<!-- constants -->` ブロックを `<!-- failure --> ... <!-- /failure -->` の直後に挿入する。
- `deviceid` の dead field（CONFIG_DB 値が SAI に反映されない）は注意事項として明記する。
- HFTel の `TAM_COLLECTOR_TABLE` は CONFIG_DB から SAI に反映されないことを明記する。
