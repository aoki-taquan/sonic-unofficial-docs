# DSCP_TO_PG_MAP — Phase E: ハードコード定数調査

対象: `DSCP_TO_TC_MAP` / `TC_TO_PRIORITY_GROUP_MAP` / `PORT_QOS_MAP` の 2 段パイプラインを構成する定数群
ソース: `sonic-swss/orchagent/qosorch.h`, `sonic-swss/orchagent/qosorch.cpp`,
        `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-dscp-tc-map.yang`,
        `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-tc-priority-group-map.yang`

---

## 1. CONFIG_DB フィールド名定数 (qosorch.h)

`PORT_QOS_MAP` テーブルの各 leaf 名は `qosorch.h` でハードコードされた `const string` として定義されている。

| 定数名 | 値 | 用途 | ソース |
|-------|----|------|--------|
| `dscp_to_tc_field_name` | `"dscp_to_tc_map"` | `PORT_QOS_MAP.<port>.dscp_to_tc_map` フィールド名。DSCP_TO_TC_MAP へのリファレンス | qosorch.h L11 |
| `tc_to_pg_map_field_name` | `"tc_to_pg_map"` | `PORT_QOS_MAP.<port>.tc_to_pg_map` フィールド名。TC_TO_PRIORITY_GROUP_MAP へのリファレンス | qosorch.h L18 |
| `decap_dscp_to_tc_field_name` | `"decap_dscp_to_tc_map"` | トンネル decap 側の DSCP→TC マップフィールド名 | qosorch.h L34 |
| `decap_tc_to_pg_field_name` | `"decap_tc_to_pg_map"` | トンネル decap 側の TC→PG マップフィールド名 | qosorch.h L35 |

## 2. SAI QOS マップタイプ定数

`qosorch.cpp` の各ハンドラが SAI オブジェクト作成時に `qos_map_attr.value.u32` または `.s32` にセットするハードコード値。

| SAI 定数 | セット箇所 | 意味 |
|----------|-----------|------|
| `SAI_QOS_MAP_TYPE_DSCP_TO_TC` | `qosorch.cpp:265` (`DscpToTcMapHandler::addQosItem`) | DSCP → Traffic Class マップの SAI タイプ ID |
| `SAI_QOS_MAP_TYPE_TC_TO_PRIORITY_GROUP` | `qosorch.cpp:913` (`TcToPgHandler::addQosItem`) | TC → Priority Group マップの SAI タイプ ID |

**注意**: `SAI_QOS_MAP_TYPE_DSCP_TO_PRIORITY_GROUP` は SAI 仕様に存在しない。DSCP から PG への 1 段マップは SONiC SAI インタフェースで定義されておらず、これが `DSCP_TO_PG_MAP` テーブルが存在しない根拠の一つとなっている。

## 3. SAI ポート属性定数 (qosorch.cpp:61, 67)

`PORT_QOS_MAP` を SAI ポートに適用する際の属性 ID。

| SAI 定数 | フィールド名 | 用途 | ソース |
|----------|------------|------|--------|
| `SAI_PORT_ATTR_QOS_DSCP_TO_TC_MAP` | `dscp_to_tc_map` | ポートへの DSCP→TC マップ設定 | qosorch.cpp:61 |
| `SAI_PORT_ATTR_QOS_TC_TO_PRIORITY_GROUP_MAP` | `tc_to_pg_map` | ポートへの TC→PG マップ設定 | qosorch.cpp:67 |

## 4. YANG 値域制約（ハードコードパターン）

YANG バリデーションで強制される値域はコードではなく YANG ファイルにハードコードされている。

### DSCP_TO_TC_MAP の値域

| フィールド | YANG パターン / 型 | 許容値 | ソース |
|-----------|------------------|--------|--------|
| `name` (マップ名) | `[a-zA-Z0-9]{1}([-a-zA-Z0-9_]{0,31})` | 英数字始まり、英数字・ハイフン・アンダースコア、最大 32 文字 | sonic-dscp-tc-map.yang L40-41 |
| `dscp` (key) | `"6[0-3]\|[1-5][0-9]?\|[0-9]?"` | `0`〜`63` の整数文字列のみ | sonic-dscp-tc-map.yang L57-62 |
| `tc` (value) | `stypes:tc_type` = `uint8` range `0..15` | `0`〜`15` | sonic-types.yang L261-267 |

### TC_TO_PRIORITY_GROUP_MAP の値域

| フィールド | YANG パターン / 型 | 許容値 | ソース |
|-----------|------------------|--------|--------|
| `name` (マップ名) | `[a-zA-Z0-9]{1}([-a-zA-Z0-9_]{0,31})` | 英数字始まり、最大 32 文字 | sonic-tc-priority-group-map.yang L40-41 |
| `tc` (key) | `stypes:tc_type` = `uint8` range `0..15` | `0`〜`15` | sonic-types.yang L261-267 |
| `pg` (value) | `"[0-7]?"` | `0`〜`7` または空文字 (`?` は 0 or 1 桁) | sonic-tc-priority-group-map.yang L62-65 |

**注意**: `pg` のパターン `[0-7]?` は空文字も許容する。空文字が渡された場合、`qosorch.cpp:895` の `stoi()` は `std::invalid_argument` を送出しクラッシュする（`stoi("")` は例外）。これは Phase D (failure) で記録されている問題。

## 5. コード変換定数（stoi 非例外処理）

| 変換箇所 | 入力フィールド | 変換関数 | 例外処理 | ソース |
|---------|--------------|---------|--------|--------|
| `DscpToTcMapHandler::convertFieldValuesToAttributes()` | `dscp` key | `stoi(fvField(*i))` | なし（未捕捉 → クラッシュ） | qosorch.cpp:245 |
| `DscpToTcMapHandler::convertFieldValuesToAttributes()` | `tc` value | `stoi(fvValue(*i))` | なし | qosorch.cpp:246 |
| `TcToPgHandler::convertFieldValuesToAttributes()` | `tc` key | `stoi(fvField(*i))` | なし | qosorch.cpp:894 |
| `TcToPgHandler::convertFieldValuesToAttributes()` | `pg` value | `stoi(fvValue(*i))` | なし | qosorch.cpp:895 |

---

## 出典

- `sonic-net/sonic-swss/orchagent/qosorch.h` L11, L18, L34-35
- `sonic-net/sonic-swss/orchagent/qosorch.cpp` L61-67, L245-246, L265, L894-895, L913
- `sonic-net/sonic-buildimage/src/sonic-yang-models/yang-models/sonic-dscp-tc-map.yang` L40-66
- `sonic-net/sonic-buildimage/src/sonic-yang-models/yang-models/sonic-tc-priority-group-map.yang` L40-65
