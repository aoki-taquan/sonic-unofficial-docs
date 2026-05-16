# Phase A — BGP_AGGREGATE_ADDRESS コード由来の暗黙デフォルト

## 対象ファイル

- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_aggregate_address.py`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-bgp-aggregate-address.yang`
- `sonic-utilities/config/bgp_cli.py`

## フィールド別デフォルト分析

### 1. `bbr-required`

| 種別 | 値 | 根拠 |
|------|----|------|
| YANG `default` | `false` | `sonic-bgp-aggregate-address.yang` L45 |
| Python `.get()` fallback | `COMMON_FALSE_STRING = "false"` | `managers_aggregate_address.py` L77: `data.get(BBR_REQUIRED_KEY, COMMON_FALSE_STRING)` |
| CLI option default | `False` (is_flag) | `bgp_cli.py` L243: `@click.option("--bbr-required", is_flag=True, default=False, ...)` |
| STATE_DB write fallback | `"false"` | `managers_aggregate_address.py` L210: `data.get(BBR_REQUIRED_KEY, COMMON_FALSE_STRING)` |

**結論**: YANG / Python / CLI の三層すべてで `false` に統一。欠落時は `.get(BBR_REQUIRED_KEY, COMMON_FALSE_STRING)` によって明示的に `"false"` を補完する。

### 2. `summary-only`

| 種別 | 値 | 根拠 |
|------|----|------|
| YANG `default` | `false` | `sonic-bgp-aggregate-address.yang` L51 |
| `generate_aggregate_address_commands()` 引数デフォルト | `COMMON_FALSE_STRING` | `managers_aggregate_address.py` L239: `summary_only=COMMON_FALSE_STRING` |
| `address_set_handler` `.get()` | `COMMON_FALSE_STRING` | L109: `data.get(SUMMARY_ONLY_KEY, COMMON_FALSE_STRING)` |
| CLI option default | `False` (is_flag) | `bgp_cli.py` L245: `@click.option("--summary-only", is_flag=True, default=False, ...)` |
| STATE_DB write fallback | `"false"` | `managers_aggregate_address.py` L212: `data.get(SUMMARY_ONLY_KEY, COMMON_FALSE_STRING)` |

**結論**: `false` の場合 FRR コマンドに `summary-only` キーワードは追加されない (`L245: if not is_remove and summary_only == COMMON_TRUE_STRING`)。欠落時は `COMMON_FALSE_STRING` で補完されるため FRR への影響なし。

### 3. `as-set`

| 種別 | 値 | 根拠 |
|------|----|------|
| YANG `default` | `false` | `sonic-bgp-aggregate-address.yang` L57 |
| `generate_aggregate_address_commands()` 引数デフォルト | `COMMON_FALSE_STRING` | `managers_aggregate_address.py` L239: `as_set=COMMON_FALSE_STRING` |
| `address_set_handler` `.get()` | `COMMON_FALSE_STRING` | L110: `data.get(AS_SET_KEY, COMMON_FALSE_STRING)` |
| CLI option default | `False` (is_flag) | `bgp_cli.py` L247: `@click.option("--as-set", is_flag=True, default=False, ...)` |
| STATE_DB write fallback | `"false"` | `managers_aggregate_address.py` L213: `data.get(AS_SET_KEY, COMMON_FALSE_STRING)` |

**結論**: `summary-only` と同構造。欠落時は `COMMON_FALSE_STRING` で補完、FRR コマンドに `as-set` キーワードなし。

### 4. `aggregate-address-prefix-list`

| 種別 | 値 | 根拠 |
|------|----|------|
| YANG `default` | `""` (空文字列) | `sonic-bgp-aggregate-address.yang` L65 |
| CLI option default | `""` | `bgp_cli.py` L249: `@click.option("--aggregate-address-prefix-list", default="", ...)` |
| STATE_DB write fallback | `""` | `managers_aggregate_address.py` L214: `data.get(AGGREGATE_ADDRESS_PREFIX_LIST_KEY, "")` |
| 適用条件 (実質デフォルト) | **スキップ** | `managers_aggregate_address.py` L114: `if AGGREGATE_ADDRESS_PREFIX_LIST_KEY in data and data[AGGREGATE_ADDRESS_PREFIX_LIST_KEY]:` — キーが存在しないか空文字列の場合は prefix-list コマンドを生成しない |

**結論**: 空文字列 (`""`) がデフォルト。空の場合は `generate_prefix_list_commands()` が呼ばれず、FRR の prefix-list 設定に影響しない。`in data and data[...]` の二重チェックにより、キー不在でも空文字列でも同様にスキップされる。

### 5. `contributing-address-prefix-list`

| 種別 | 値 | 根拠 |
|------|----|------|
| YANG `default` | `""` (空文字列) | `sonic-bgp-aggregate-address.yang` L71 |
| CLI option default | `""` | `bgp_cli.py` L250: `@click.option("--contributing-address-prefix-list", default="", ...)` |
| STATE_DB write fallback | `""` | `managers_aggregate_address.py` L215: `data.get(CONTRIBUTING_ADDRESS_PREFIX_LIST_KEY, "")` |
| 適用条件 (実質デフォルト) | **スキップ** | `managers_aggregate_address.py` L124: `if CONTRIBUTING_ADDRESS_PREFIX_LIST_KEY in data and data[CONTRIBUTING_ADDRESS_PREFIX_LIST_KEY]:` |
| `le` suffix (IPv4) | `le 32` | `managers_aggregate_address.py` L262: contributing prefix-list には `le 32` / `le 128` を付加して "以下のすべて" を許可する |

**結論**: `aggregate-address-prefix-list` と同構造。追加で、contributing 用の FRR コマンドには `is_con=True` によって IPv4 は `le 32`、IPv6 は `le 128` suffix が付く (サブネット全体を contributing として扱うため)。

## BBR 状態と各フィールドの暗黙連動

`bbr-required` フィールドが明示されない場合のデフォルト動作 (`false`) では:

- `bbr_status` の値に関わらず `bbr_required = False` → BBR 状態チェックをバイパス
- 常に `address_set_handler()` が実行される (`managers_aggregate_address.py` L84-86)
- STATE_DB に `state=active` が書き込まれる (FRR push 成功時)

`bbr_status` のデフォルト (`""`) についても注記:

```python
# managers_aggregate_address.py L73-76
if self.directory.path_exist(CONFIG_DB_NAME, BGP_BBR_TABLE_NAME, BGP_BBR_STATUS_KEY):
    bbr_status = self.directory.get(CONFIG_DB_NAME, BGP_BBR_TABLE_NAME, BGP_BBR_STATUS_KEY)
else:
    bbr_status = ""  # ← BBR テーブル未設定時の暗黙デフォルト
```

BBR テーブルが存在しない環境では `bbr_status = ""` となり、`bbr-required=true` のエントリは `ADDRESS_INACTIVE_STATE` に落とされる (L78-80)。

## YANG default vs コード実装の整合性

| フィールド | YANG default | コード fallback | 整合 |
|-----------|-------------|-----------------|------|
| `bbr-required` | `false` | `COMMON_FALSE_STRING` | OK |
| `summary-only` | `false` | `COMMON_FALSE_STRING` | OK |
| `as-set` | `false` | `COMMON_FALSE_STRING` | OK |
| `aggregate-address-prefix-list` | `""` | `""` | OK |
| `contributing-address-prefix-list` | `""` | `""` | OK |

全フィールドで YANG default とコード fallback が一致している。YANG が CONFIG_DB への書き込み時にデフォルトを保証するが、bgpcfgd は `.get()` で独立して同値を再定義している (防御的実装)。

## evidence

- `managers_aggregate_address.py`: `sonic-net/sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_aggregate_address.py`
- `sonic-bgp-aggregate-address.yang`: `sonic-net/sonic-buildimage/src/sonic-yang-models/yang-models/sonic-bgp-aggregate-address.yang`
- `bgp_cli.py (config)`: `sonic-net/sonic-utilities/config/bgp_cli.py`
