# CHASSIS_ORCH / PASS_THROUGH_ROUTE_TABLE フィールド暗黙デフォルト調査メモ

調査日: 2026-05-15
対象テーブル: CONFIG_DB `PASS_THROUGH_ROUTE_TABLE`、APP_DB `PASS_THROUGH_ROUTE_TABLE`

## 調査対象ファイル

- `sonic-swss/orchagent/chassisorch.cpp` (ChassisOrch 実装)
- `sonic-swss/orchagent/chassisorch.h` (ChassisOrch 定義)
- `sonic-swss/orchagent/orchdaemon.cpp` (ChassisOrch 登録・テーブル名指定)
- `sonic-swss/orchagent/vnetorch.h` (VNetNextHopUpdate 構造体)
- `sonic-swss-common/common/schema.h` (CFG_PASS_THROUGH_ROUTE_TABLE_NAME / APP_PASS_THROUGH_ROUTE_TABLE_NAME)

---

## 概要

`ChassisOrch` は `orchagent` 内のオーケストレータで、VoQ (Virtual Output Queue) チャシスの**フロントエンドルータ**が使用する。

**役割**: CONFIG_DB `PASS_THROUGH_ROUTE_TABLE` を購読し、VNet nextHop 更新 (`VNetNextHopUpdate`) を受けたとき APP_DB `PASS_THROUGH_ROUTE_TABLE` にパススルールートを書き込む。

```
CONFIG_DB PASS_THROUGH_ROUTE_TABLE (key: IP prefix)
    ↓ doTask() → attach/detach VNetRouteOrch observer
VNetRouteOrch (nextHop 変化通知)
    ↓ update() → addRouteToPassThroughRouteTable()
APP_DB PASS_THROUGH_ROUTE_TABLE (key: IP prefix)
  fields: redistribute, next_vrf_name, next_hop_ip, ifname, source
```

---

## CONFIG_DB: PASS_THROUGH_ROUTE_TABLE

### key

```
PASS_THROUGH_ROUTE_TABLE|<IP_prefix>
```

- `<IP_prefix>` は VNet ルートの宛先 IP プレフィックス (`IpPrefix` 形式、例: `10.1.0.0/16`)
- `IpPrefix.to_string()` で正規化された文字列キー (chassisorch.cpp:44)

### フィールド

このテーブルには**フィールドなし（key のみ）**。

- ChassisOrch の `doTask()` は key を読み取り、`SET` 操作なら VNetRouteOrch に自分自身を observer として `attach(this, ip)`、`DEL` 操作なら `detach(this, ip)` するのみ (chassisorch.cpp:50-67)
- フィールド値は CONFIG_DB に格納されない。APP_DB への書き込みは VNetNextHopUpdate の通知経由で行われる

**YANG スキーマ**: 存在しない。YANG モデル未定義のテーブル。

---

## APP_DB: PASS_THROUGH_ROUTE_TABLE (ChassisOrch が書き込む出力)

### key

```
PASS_THROUGH_ROUTE_TABLE|<IP_prefix>
```

CONFIG_DB と同一のプレフィックスが使用される (`IpPrefix(update.destination.to_string()).to_string()`, chassisorch.cpp:44)。

### フィールドと暗黙デフォルト

`addRouteToPassThroughRouteTable()` がすべてのフィールドを固定値でセットする:

```cpp
// chassisorch.cpp:29-42
fvVector.emplace_back("redistribute", "true");        // ハードコード固定 "true"
fvVector.emplace_back("next_vrf_name", update.vnet);  // VNet 名 (VNetNextHopUpdate.vnet)
fvVector.emplace_back("next_hop_ip", update.nexthop.ips.to_string());  // nextHop IP
fvVector.emplace_back("ifname", update.nexthop.ifname);               // インタフェース名
fvVector.emplace_back("source", "CHASSIS_ORCH");      // ハードコード固定 "CHASSIS_ORCH"
```

| フィールド | 型 | 由来 | コード由来デフォルト / 固定値 |
|-----------|-----|------|---------------------------|
| `redistribute` | string | ChassisOrch ハードコード | 常に `"true"` (chassisorch.cpp:34) |
| `next_vrf_name` | string | VNetNextHopUpdate.vnet | VNet 名。空は発生しない（VNetRouteOrch が保証） |
| `next_hop_ip` | string | VNetNextHopUpdate.nexthop.ips | `IpAddresses.to_string()` 形式。platform API 失敗なし |
| `ifname` | string | VNetNextHopUpdate.nexthop.ifname | インタフェース名。空文字列の可能性あり（VNet トンネル経由） |
| `source` | string | ChassisOrch ハードコード | 常に `"CHASSIS_ORCH"` (chassisorch.cpp:38) |

---

## 暗黙デフォルト・コード由来挙動

### `redistribute = "true"` の固定値

ChassisOrch がルートを書き込む際、`redistribute` は常に `"true"` で固定されている。ユーザー設定不可・YANG 未定義・変更不可のハードコード値。

**用途**: routeorch が APP_DB の `PASS_THROUGH_ROUTE_TABLE` を処理する際にこのフィールドを参照し、ルートの再配布制御を行う（実装は routeorch 側）。

### `source = "CHASSIS_ORCH"` の識別子

全エントリに `source = "CHASSIS_ORCH"` が付与される。これにより routeorch 側で書き込み主体を識別できる（ただし routeorch 側での使用コードは確認されず）。

### エントリ削除のハンドリング

CONFIG_DB から `PASS_THROUGH_ROUTE_TABLE|<prefix>` が削除 (`DEL`) された場合:

```cpp
// chassisorch.cpp:57-60
m_vNetRouteOrch->detach(this, ip);
```

VNetRouteOrch の observer から切り離される。VNetNextHopUpdate の通知が止まり、次回 update 呼び出し時に `deleteRoutePassThroughRouteTable()` で APP_DB からエントリを削除する:

```cpp
// chassisorch.cpp:43-47
void ChassisOrch::deleteRoutePassThroughRouteTable(const VNetNextHopUpdate& update)
{
    const std::string everflow_route = IpPrefix(update.destination.to_string()).to_string();
    m_passThroughRouteTable.del(everflow_route);
}
```

### ChassisOrch の登録条件（orchdaemon.cpp）

ChassisOrch は orchdaemon の VNET 系orch が全て初期化された後に登録される:

```cpp
// orchdaemon.cpp:290-294
const vector<string> chassis_frontend_tables = {
    CFG_PASS_THROUGH_ROUTE_TABLE_NAME,  // = "PASS_THROUGH_ROUTE_TABLE"
};
ChassisOrch* chassis_frontend_orch = new ChassisOrch(m_configDb, m_applDb, chassis_frontend_tables, vnet_rt_orch);
```

VNetRouteOrch の vnet_rt_orch インスタンスを保持する。VNet 系orch なしには機能しない。

---

## ハードコード定数一覧

| 定数 | 値 | 場所 | 備考 |
|------|-----|------|------|
| CONFIG_DB テーブル名 | `"PASS_THROUGH_ROUTE_TABLE"` | schema.h:371 `CFG_PASS_THROUGH_ROUTE_TABLE_NAME` | YANG 未定義 |
| APP_DB テーブル名 | `"PASS_THROUGH_ROUTE_TABLE"` | schema.h:93 `APP_PASS_THROUGH_ROUTE_TABLE_NAME` | 同名 |
| `redistribute` | `"true"` | chassisorch.cpp:34 | 固定値 |
| `source` | `"CHASSIS_ORCH"` | chassisorch.cpp:38 | 固定値 |

---

## 結論

`PASS_THROUGH_ROUTE_TABLE` (CONFIG_DB) はフィールドを持たない key-only テーブル。ChassisOrch が observer パターンで VNet nextHop の変化を APP_DB に反映する際のトリガーテーブルとして機能する。APP_DB 側の `redistribute` と `source` はハードコード固定値であり、ユーザー設定不可。YANG モデルは存在しない。
