# Phase A 分析メモ: APPL_DB STP orchagent 関連テーブル

対象ファイル:
- `sonic-swss/orchagent/stporch.cpp` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/orchagent/stporch.h` (同上)
- `sonic-swss/orchagent/orchdaemon.cpp` (同上)
- `sonic-swss-common/common/schema.h` (テーブル名定義)
- `sonic-swss/tests/mock_tests/stporch_ut.cpp` (UT)

## APPL_DB テーブル一覧 (stporch が購読)

| 定数名 | テーブル名 (実値) | ソース |
|---|---|---|
| `APP_STP_VLAN_INSTANCE_TABLE_NAME` | `"STP_VLAN_INSTANCE_TABLE"` | schema.h |
| `APP_STP_PORT_STATE_TABLE_NAME` | `"STP_PORT_STATE_TABLE"` | schema.h |
| `APP_STP_FASTAGEING_FLUSH_TABLE_NAME` | `"STP_FASTAGEING_FLUSH_TABLE"` | schema.h |
| `APP_STP_INST_PORT_FLUSH_TABLE_NAME` | `"STP_INST_PORT_FLUSH_TABLE"` | stporch.h |

## テーブル別フィールド・デフォルト

### 1. APPL_DB:STP_VLAN_INSTANCE_TABLE

キー形式: `<vlan_alias>` (例: `Vlan1000`)

stpmgrd → stporch 経由のフロー:
- stpmgrd が `STP_VLAN_INSTANCE_TABLE` に書き込む書き込み元: `stpmgr.cpp` 内の IPC→APPL_DB 経路
  ただし stpmgrd は直接 APPL_DB には書かず、stporch が APPL_DB の当該テーブルを購読する構造

実際は stpd (STP デーモン) → stpmgrd (IPC受信) → APPL_DB `STP_VLAN_INSTANCE_TABLE` への SET

フィールド:

| フィールド | 型 | デフォルト / 値 | 備考 |
|---|---|---|---|
| `stp_instance` | uint16_t (文字列) | stpd が割り当て | 0–65534 の範囲。`STP_INVALID_INSTANCE = 0xFFFF` は sentinel |

stporch 側の処理 (`doStpTask()`):
- SET: `stp_instance` を読み取り、`addVlanToStpInstance(vlan_alias, instance)` を呼ぶ
- DEL: `removeVlanFromStpInstance(vlan_alias, 0)` を呼ぶ (instance=0 固定)
- `stp_instance` フィールドがなければ `STP_INVALID_INSTANCE (0xFFFF)` のままエラーログを出力して処理スキップ

### 2. APPL_DB:STP_PORT_STATE_TABLE

キー形式: `<port_alias>:<stp_instance>` (例: `Ethernet0:1`)

フィールド:

| フィールド | 型 | 値域 | デフォルト / 備考 |
|---|---|---|---|
| `state` | uint8_t (文字列) | 0–4 (stp_state enum) | stpd が設定。欠落時は `STP_STATE_INVALID(5)` として処理スキップ |

`stp_state` enum 値 (stporch.h):

| 値 | 定数名 | SAI マッピング |
|---|---|---|
| 0 | `STP_STATE_DISABLED` | `SAI_STP_PORT_STATE_BLOCKING` |
| 1 | `STP_STATE_BLOCKING` | `SAI_STP_PORT_STATE_BLOCKING` |
| 2 | `STP_STATE_LISTENING` | `SAI_STP_PORT_STATE_BLOCKING` |
| 3 | `STP_STATE_LEARNING` | `SAI_STP_PORT_STATE_LEARNING` |
| 4 | `STP_STATE_FORWARDING` | `SAI_STP_PORT_STATE_FORWARDING` |
| 5 | `STP_STATE_INVALID` | (sentinel、処理スキップ) |

stporch 側の処理 (`doStpPortStateTask()`):
- SET: `state` を読み取り、`updateStpPortState()` を呼ぶ。STP ポートが未存在なら `addStpPort()` で新規作成
- DEL: `removeStpPort()` を呼ぶ

STP ポート作成時 (`addStpPort()`):
- `SAI_STP_PORT_ATTR_BRIDGE_PORT`: 既存ブリッジポート OID を使用
- `SAI_STP_PORT_ATTR_STP`: STP インスタンス OID
- `SAI_STP_PORT_ATTR_STATE`: **`SAI_STP_PORT_STATE_BLOCKING` (ハードコード)** ← 作成直後の初期状態

### 3. APPL_DB:STP_FASTAGEING_FLUSH_TABLE

キー形式: `<vlan_alias>` (例: `Vlan1000`)

フィールド:

| フィールド | 型 | 値 | 備考 |
|---|---|---|---|
| `state` | string | `"true"` / (それ以外) | `"true"` のときのみ FDB フラッシュ実行 |

stporch 側の処理 (`doStpFastageTask()`):
- SET: `state == "true"` のみ `stpVlanFdbFlush(vlan_alias)` を呼び、VLAN の FDB を全フラッシュ
- DEL: no-op (コメント明記)

### 4. APPL_DB:STP_INST_PORT_FLUSH_TABLE

キー形式: `<mst_instance>:<port_alias>` (例: `1:Ethernet0`)

フィールド:

| フィールド | 型 | 値 | 備考 |
|---|---|---|---|
| `state` | string | `"true"` / (それ以外) | `"true"` のとき当該 MST インスタンスに属する全 VLAN の FDB をフラッシュ |

stporch 側の処理 (`doMstInstPortFlushTask()`):
- SET: `state == "true"` のとき `m_vlanAliasToStpInstanceMap[instance]` から VLAN リストを取得し各 VLAN を `stpVlanFdbFlush()` で FDB フラッシュ
- DEL: no-op (コメント明記)

## SAI 操作サマリー

| 操作 | SAI API | 初期値 / ハードコード |
|---|---|---|
| STP インスタンス作成 | `create_stp()` | attr.id=0, attr.value.u32=0 でダミー属性 |
| STP ポート作成 | `create_stp_port()` | 初期 STATE = `SAI_STP_PORT_STATE_BLOCKING` (ハードコード) |
| STP ポート状態更新 | `set_stp_port_attribute()` | `getStpSaiState()` で変換 |
| VLAN の STP インスタンス設定 | `set_vlan_attribute(SAI_VLAN_ATTR_STP_INSTANCE)` | 指定インスタンス OID |
| VLAN の STP インスタンス削除 | `set_vlan_attribute(SAI_VLAN_ATTR_STP_INSTANCE)` | `m_defaultStpId` (スイッチ起動時の default STP instance) |

## 初期化

- 起動時に `SAI_SWITCH_ATTR_DEFAULT_STP_INST_ID` / `SAI_SWITCH_ATTR_MAX_STP_INSTANCE` を取得
- `m_maxStpInstance = max_stp_instances - 1` (例: SAI が 510 返せば `m_maxStpInstance = 509`)
- STATE_DB `STP|GLOBAL.max_stp_inst` にも書き込む

## 発見された discrepancy / 暗黙デフォルト

1. **STP ポート初期状態は常に BLOCKING** (`addStpPort()` L.244-245) — `SAI_STP_PORT_STATE_BLOCKING` ハードコード
2. **DISABLED/LISTENING も BLOCKING にマップ** (`getStpSaiState()`) — SAI は 3 状態しかなく、STP の 5 状態を圧縮
3. **DEL コマンドの instance=0 固定** (`doStpTask()` L.419) — DEL 時は常に instance=0 で removeVlanFromStpInstance() を呼ぶ (stpd 側でキー管理)
4. **STP_FASTAGEING_FLUSH_TABLE / STP_INST_PORT_FLUSH_TABLE の DEL は no-op** — フラッシュはべき等操作なので意図的
5. **stp_instance フィールド欠落時はエラーログのみで処理継続** (`doStpTask()` L.404-408)
6. **allPortsReady() ガード** — ポート初期化完了前は全テーブルの処理をスキップ (`doTask()` L.578-581)
