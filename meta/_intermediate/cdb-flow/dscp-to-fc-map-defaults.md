# DSCP_TO_FC_MAP Phase A — コード由来の暗黙デフォルト調査

調査日: 2026-05-14
対象ページ: `docs/reference/config-db/dscp-to-fc-map.md`

## 1. フィールド列挙

| フィールド | YANG 型 | 役割 |
|-----------|---------|------|
| `name` (key, L1) | string 1..32, `[a-zA-Z0-9][-a-zA-Z0-9_]*` | マップ名 |
| `dscp` (key, L2) | string `"6[0-3]\|[1-5][0-9]?\|[0-9]?"` (0..63) | DSCP 値 |
| `fc` | string `"[0-7]?"` | 転送クラス (Forwarding Class) |

## 2. Consumer 精読結果

### 2.1 主 consumer: `DscpToFcMapHandler` (qosorch.cpp:1039-1130)

`QosMapHandler::processWorkItem()` を継承。固有オーバーライドは:
- `convertFieldValuesToAttributes()` (L1039)
- `addQosItem()` (L1095)

**`convertFieldValuesToAttributes` の検証ロジック**:
```
dscp = stoi(fvField(*i))  // key = dscp 値
  < 0        → SWSS_LOG_ERROR + return false (task_invalid_entry)
  > 63       → SWSS_LOG_ERROR + return false (task_invalid_entry)
  OK → list[ind].key.dscp = (uint8_t)value

fc = stoi(fvValue(*i))   // value = FC 値
  < 0 or >= max_num_fcs → SWSS_LOG_ERROR + return false (task_invalid_entry)
  OK → list[ind].value.fc = (uint8_t)value

非整数文字列 → invalid_argument catch → return false (task_invalid_entry)
```

両フィールドとも `try/catch(invalid_argument)` あり。`DscpToTcMapHandler` と異なり例外処理が実装されている。

### 2.2 `max_num_fcs` — ランタイム上限 (nhgmaporch.cpp:299-324)

```cpp
sai_uint8_t NhgMapOrch::getMaxNumFcs() {
    static int max_num_fcs = -1;
    if (max_num_fcs == -1) {
        // SAI_SWITCH_ATTR_MAX_NUMBER_OF_FORWARDING_CLASSES を問い合わせ
        if (get_switch_attribute(...) == SUCCESS)
            max_num_fcs = attr.value.u8;
        else {
            SWSS_LOG_WARN("Switch does not support FCs");
            max_num_fcs = 0;  // サポートなし → 0
        }
    }
    return max_num_fcs;
}
```

- **静的変数**: 初回呼び出し時のみ SAI 問い合わせ。以降はキャッシュ値を使用
- FC サポートなし場合: `max_num_fcs = 0` → `fc >= 0` が常に true → **全 FC 値が reject**
- テストでは `SAI_SWITCH_ATTR_MAX_NUMBER_OF_FORWARDING_CLASSES = 63` を設定 → FC 0..62 が有効

### 2.3 YANG-実装 Discrepancy: `fc` フィールド上限

| 観点 | 内容 |
|------|------|
| YANG pattern | `[0-7]?` → 0..7 のみ許可（YANG バリデーション段階） |
| SAI ランタイム上限 | `max_num_fcs - 1`（SAI query 次第。典型的に 63） |
| テスト期待値 | FC `0..62` が有効（test_qos_map.py:314, L313-314） |
| 結論 | **YANG は 0..7 を強制するが、実装は SAI capability まで許可**。YANG バリデーションなしで直接 CONFIG_DB 書き込み時は 0..62 が通過する可能性 |

### 2.4 `fc` field が 0 のとき (FC 未定義 DSCP)

DSCP_TO_FC_MAP はスパース定義可能（全 64 DSCP エントリ不要）。未定義 DSCP に対するデフォルト FC は SAI/ASIC 実装依存（一般に FC=0 だが非保証）。

### 2.5 SAI map 型

`addQosItem()` で使用する SAI type:
- `SAI_QOS_MAP_ATTR_TYPE = SAI_QOS_MAP_TYPE_DSCP_TO_FORWARDING_CLASS`
- `SAI_PORT_ATTR_QOS_DSCP_TO_FORWARDING_CLASS_MAP` でポートにバインド

### 2.6 pendingRemove ロック

`QosMapHandler::processWorkItem()` 共通ロジック（L136-186）:
- DEL 時に `PORT_QOS_MAP` 等から参照中 → `m_pendingRemove = true` + `task_need_retry`
- pending 中に SET → `task_need_retry`（実行せず）

## 3. 書き込み入り口

| 入り口 | 詳細 |
|--------|------|
| `config cbf reload` | `cbf.json.j2` テンプレートから CONFIG_DB に書き込む |
| `config cbf clear` | `DSCP_TO_FC_MAP` テーブルを全削除 |
| minigraph/sonic-cfggen | **なし** |
| db_migrator | **なし** |
| gNMI/REST | **なし** |

## 4. ビルド時デフォルト (`cbf_config.j2`)

`DSCP_TO_FC_MAP|AZURE` マップ（全 64 エントリ定義）:

| DSCP | FC | 備考 |
|------|----|------|
| 0,1,2,6,7,9..45,47,49..63 | 1 | デフォルト低優先度 |
| 3 | 3 | lossless class |
| 4 | 4 | lossless class |
| 5 | 2 | — |
| 8 | 0 | CS1: best-effort |
| 46 | 5 | EF: expedited forwarding |
| 48 | 6 | CS6: network control |

マップ名は `AZURE`（`cbf_config.j2:3`）。プラットフォーム HW SKU 配下の `cbf.json.j2` で上書き可能。

## 5. dead consumer 確認

- bufferorch_ut.cpp, portsorch_ut.cpp, sfloworh_ut.cpp, copporch_ut.cpp: テスト mock のみ。本番 consumer は `qosorch` のみ
- `NhgMapOrch` (cbfnhgorch.cpp L311): nhg map 側で `getMaxNumFcs()` を使用してグループ数バリデーション。DSCP_TO_FC_MAP の direct consumer ではない

## 6. 検出された discrepancy / 注目点まとめ

1. **YANG fc pattern `[0-7]?` vs 実装上限 `max_num_fcs-1`**: YANG は 0..7 を宣言するが実装は SAI capability まで許可
2. **FC サポートなしスイッチ**: `max_num_fcs=0` → 全 FC 値 reject → `task_invalid_entry`（silent drop ではなく明示エラー）
3. **スパース定義時の未定義 DSCP**: SAI/ASIC 依存の暗黙デフォルト FC（通常 0）
4. **例外処理あり**: `DscpToFcMapHandler` は dscp/fc 両フィールドで `try/catch(invalid_argument)` を実装（`DscpToTcMapHandler` より堅牢）

## Evidence

- `sonic-swss/orchagent/qosorch.cpp:1039-1130` (DscpToFcMapHandler)
- `sonic-swss/orchagent/cbf/nhgmaporch.cpp:299-325` (getMaxNumFcs)
- `sonic-buildimage/files/build_templates/cbf_config.j2:1-69` (AZURE default map)
- `sonic-swss/tests/test_qos_map.py:300-374` (TestCbf)
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-dscp-fc-map.yang` (YANG model)
