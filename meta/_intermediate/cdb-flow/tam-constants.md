# TAM — Phase E: ハードコード定数調査

## 対象ファイル

- `sonic-net/sonic-mgmt-common/cvl/testdata/schema/sonic-tam.yang`
- `sonic-net/sonic-mgmt-common/cvl/testdata/schema/sonic-ifa.yang`
- `sonic-net/sonic-swss/orchagent/portsorch.cpp`
- `sonic-net/sonic-swss/orchagent/high_frequency_telemetry/hftelorch.cpp`
- `sonic-net/sonic-swss-common/common/schema.h`

---

## 1. YANG 固定キー値（`enum` 型 singleton キー）

TAM テーブルの singleton エントリは YANG `enumeration` でキーを強制固定している。

| テーブル | キーフィールド名 | 固定値 | 根拠 |
|---------|---------------|-------|------|
| `TAM_DEVICE_TABLE` | `name` | `"device"` | `sonic-tam.yang:31` — `enum device` のみ |
| `TAM_INT_IFA_FEATURE_TABLE` | `name` | `"feature"` | `sonic-ifa.yang:34` — `enum feature` のみ |

これらのテーブルには `"device"` / `"feature"` 以外のキーを投入できない（CVL が `enumeration` 制約で拒否する）。

---

## 2. `TAM_DEVICE_TABLE.deviceid` デフォルト値

| フィールド | 値 | 根拠 |
|-----------|----|----|
| `deviceid` YANG default | `0` | `sonic-tam.yang:37` — `default 0` |

`portsorch.cpp` の `createPtTam()` は `TAM_DEVICE_TABLE` を **読まず**、`SAI_TAM_INT_ATTR_DEVICE_ID` に直接 `0` をハードコードして SAI に渡す（`portsorch.cpp:11597-11598`）。YANG の `default 0` は CVL/GNMI 経由のデフォルト補完にのみ影響し、orchagent 側では参照されない。

---

## 3. CVL YANG エラータグ文字列

| YANG ステートメント | 文字列 | 根拠 |
|-------------------|-------|------|
| `ipaddress-type` `must` 制約 `error-app-tag` | `ipaddres-type-mismatch`（typo あり: `ipaddres`） | `sonic-tam.yang:62` |
| `ipaddress-type` `must` 制約 `error-message` | `"IP address and IP address type does not match."` | `sonic-tam.yang:63` |
| `sampling-rate` range `error-app-tag` | `"Invalid IFA flow sampling rate."` | `sonic-ifa.yang:73` |

!!! note "typo: `ipaddres-type-mismatch`"
    `ipaddres-type-mismatch`（`s` が 1 つ欠落）は YANG ソースの typo だが、CVL が返す実際のエラータグもこの文字列で固定。GNMI/REST クライアントがエラータグでフィルタする場合はこの文字列をそのまま使う必要がある。

---

## 4. portsorch.cpp Path Tracing TAM ハードコード定数

`portsorch.cpp` の `createPtTam()` で使われる固定値（CONFIG_DB の値から導出されない）:

| 属性 | ハードコード値 | 根拠 |
|------|-------------|------|
| `SAI_TAM_REPORT_ATTR_TYPE` | `SAI_TAM_REPORT_TYPE_VENDOR_EXTN` | `portsorch.cpp:11568` |
| `SAI_TAM_INT_ATTR_TYPE` | `SAI_TAM_INT_TYPE_PATH_TRACING` | `portsorch.cpp:11594` |
| `SAI_TAM_INT_ATTR_DEVICE_ID` | `0`（固定） | `portsorch.cpp:11598` |
| `SAI_TAM_INT_ATTR_INT_PRESENCE_TYPE` | `SAI_TAM_INT_PRESENCE_TYPE_UNDEFINED` | `portsorch.cpp:11602` |
| `SAI_TAM_INT_ATTR_INLINE` | `false` | `portsorch.cpp:11606` |

`pt_timestamp_template_map` にはポートのパスマーキング用タイムスタンプテンプレート名から SAI enum への変換テーブルも静的定義されている（`portsorch.cpp:213-218`）:

| 文字列値 | SAI enum |
|--------|---------|
| `"template1"` | `SAI_PORT_PATH_TRACING_TIMESTAMP_TYPE_8_15` |
| `"template2"` | `SAI_PORT_PATH_TRACING_TIMESTAMP_TYPE_12_19` |
| `"template3"` | `SAI_PORT_PATH_TRACING_TIMESTAMP_TYPE_16_23` |
| `"template4"` | `SAI_PORT_PATH_TRACING_TIMESTAMP_TYPE_20_27` |

これらは PATH_TRACING 機能で使用され、TAM_DEVICE_TABLE とは独立している。

---

## 5. HFTelOrch ハードコード定数（TAM_COLLECTOR_TABLE 参照）

`HFTelOrch` は `TAM_COLLECTOR_TABLE` を直接参照しないが、内部で同じ "collector" 役割を SAI TAM Collector オブジェクトとして生成する。関連ハードコード値:

| 定数 | 値 | 根拠 |
|-----|----|------|
| GenL family | `"sonic_stel"` | `hftelorch.cpp:78` |
| GenL group | `"ipfix"` | `hftelorch.cpp:78` |
| `session_type` フィールド値 | `"ipfix"` | `hftelorch.cpp:552` |
| `stream_status` 有効時の値 | `"enabled"` | `hftelorch.cpp:534` |
| `stream_status` 無効時の値 | `"disabled"` | `hftelorch.cpp:538` |
| STATE_DB テーブル名マクロ | `STATE_HIGH_FREQUENCY_TELEMETRY_SESSION_TABLE_NAME` | `schema.h:509` |
| STATE_DB テーブル名文字列 | `"HIGH_FREQUENCY_TELEMETRY_SESSION_TABLE"` | `schema.h:509` |
| CONSTANTS_FILE パス | `"/et/sonic/constants.yml"` (typo あり) | `hftelorch.cpp:23` |

!!! note "typo: `/et/sonic/constants.yml`"
    `CONSTANTS_FILE "/et/sonic/constants.yml"` は `/etc/sonic/constants.yml` の typo だが、このマクロはソースコード内で実際には使用されていない（定義のみ、`grep` で使用箇所なし）。実害はない。

---

## 出典

- `sonic-net/sonic-mgmt-common/cvl/testdata/schema/sonic-tam.yang` L31, L37, L56-57, L62-63
- `sonic-net/sonic-mgmt-common/cvl/testdata/schema/sonic-ifa.yang` L34, L73
- `sonic-net/sonic-swss/orchagent/portsorch.cpp` L11567-11608, L213-218
- `sonic-net/sonic-swss/orchagent/high_frequency_telemetry/hftelorch.cpp` L23, L45-55, L78, L534, L538, L552
- `sonic-net/sonic-swss-common/common/schema.h` L509
