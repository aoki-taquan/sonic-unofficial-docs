# CHASSIS_ORCH / PASS_THROUGH_ROUTE_TABLE ハードコード定数調査メモ

調査日: 2026-05-17
対象テーブル: CONFIG_DB `PASS_THROUGH_ROUTE_TABLE`、APP_DB `PASS_THROUGH_ROUTE_TABLE`

## 調査対象ファイル

- `sonic-swss/orchagent/chassisorch.cpp` — ChassisOrch 実装
- `sonic-swss/orchagent/chassisorch.h` — ChassisOrch ヘッダ
- `sonic-swss-common/common/schema.h` — テーブル名定数

---

## テーブル名定数

`schema.h` で定義される 2 つのマクロが CONFIG_DB / APP_DB テーブル名として使用される。

```c
// sonic-swss-common/common/schema.h
#define APP_PASS_THROUGH_ROUTE_TABLE_NAME  "PASS_THROUGH_ROUTE_TABLE"  // line 93
#define CFG_PASS_THROUGH_ROUTE_TABLE_NAME  "PASS_THROUGH_ROUTE_TABLE"  // line 371
```

両者は同一文字列 `"PASS_THROUGH_ROUTE_TABLE"` を持ち、CONFIG_DB 側と APP_DB 側で同名テーブルが使用される。

orchdaemon.cpp での登録:

```cpp
// orchagent/orchdaemon.cpp:290-293
const vector<string> chassis_frontend_tables = {
    CFG_PASS_THROUGH_ROUTE_TABLE_NAME,  // "PASS_THROUGH_ROUTE_TABLE"
};
ChassisOrch* chassis_frontend_orch = new ChassisOrch(
    m_configDb, m_applDb, chassis_frontend_tables, vnet_rt_orch);
```

## フィールド値固定定数

`chassisorch.cpp` の `addRouteToPassThroughRouteTable()` 内でハードコードされるフィールド値:

```cpp
// orchagent/chassisorch.cpp:34
fvVector.emplace_back("redistribute", "true");
// orchagent/chassisorch.cpp:38
fvVector.emplace_back("source", "CHASSIS_ORCH");
```

| 定数種別 | キー | 固定値 | 行 |
|---------|------|-------|-----|
| APP_DB フィールド | `redistribute` | `"true"` | `chassisorch.cpp:34` |
| APP_DB フィールド | `source` | `"CHASSIS_ORCH"` | `chassisorch.cpp:38` |

これらは変数ではなくリテラル文字列であり、ユーザー設定不可・YANG 未定義。

## ChassisOrch のフィールド名定数（ヘッダ側）

`chassisorch.h` にフィールド名を定義する文字列定数は存在しない。`chassisorch.cpp` 内でフィールド名がリテラルとして直接 `emplace_back()` に渡される。

## key 正規化

ChassisOrch は IP プレフィックス文字列を `IpPrefix::to_string()` で正規化する:

```cpp
// chassisorch.cpp:39,46
const std::string everflow_route = IpPrefix(update.destination.to_string()).to_string();
```

`IpPrefix` クラス（`sonic-swss-common`）はホストビットを自動的にマスクして正規化する。例: `10.1.0.1/16` → `10.1.0.0/16`。

## まとめ

`PASS_THROUGH_ROUTE_TABLE` は最小規模のハードコード定数セットを持つ:

| 定数 | 値 | 場所 |
|------|-----|------|
| CONFIG_DB テーブル名 | `"PASS_THROUGH_ROUTE_TABLE"` | `schema.h:371` `CFG_PASS_THROUGH_ROUTE_TABLE_NAME` |
| APP_DB テーブル名 | `"PASS_THROUGH_ROUTE_TABLE"` | `schema.h:93` `APP_PASS_THROUGH_ROUTE_TABLE_NAME` |
| `redistribute` フィールド値 | `"true"` | `chassisorch.cpp:34` |
| `source` フィールド値 | `"CHASSIS_ORCH"` | `chassisorch.cpp:38` |

YANG スキーマ未定義のため、YANG 側にも定数定義は存在しない。
