# NAT_BINDINGS — Phase E: ハードコード定数調査

## 対象ファイル

- `sonic-swss/orchagent/natorch.cpp`
- `sonic-swss/orchagent/natorch.h`

---

## `nat_type` enum 文字列値（orchagent レベル）

`NatOrch` は APPL_DB から受け取る `nat_type` フィールド文字列を直接比較し、対応する SAI NAT タイプに変換する。

| 文字列値 | 対応 SAI 定数 | SAI 操作 | ソース |
|---------|-------------|---------|--------|
| `"snat"` | `SAI_NAT_TYPE_SOURCE_NAT` | `snat_entry.nat_type = SAI_NAT_TYPE_SOURCE_NAT` | `natorch.cpp:1302, 1466, 1630, 1713` |
| `"dnat"` | `SAI_NAT_TYPE_DESTINATION_NAT` | `dnat_entry.nat_type = SAI_NAT_TYPE_DESTINATION_NAT` | `natorch.cpp:769, 847, 923, 1104` |

```cpp
// natorch.cpp:1901-1921 (addNatEntry 内 nat_type 分岐)
if (entry.nat_type == "snat")
{
    snat_entry.nat_type = SAI_NAT_TYPE_SOURCE_NAT;
    // SAI SNAT entry 作成
}
else if (entry.nat_type == "dnat")
{
    dnat_entry.nat_type = SAI_NAT_TYPE_DESTINATION_NAT;
    // SAI DNAT entry 作成
}
```

---

## `entry_type` enum 文字列値

APPL_DB の NAT エントリに付与される `entry_type` フィールド。`natorch.cpp:2659` の assert で有効値を明示。

| 文字列値 | 意味 | 由来 |
|---------|------|------|
| `"static"` | 静的 NAT エントリ | `STATIC_NAT` / `STATIC_NAPT` テーブルから `natmgrd` が設定 |
| `"dynamic"` | 動的 NAT エントリ | `NAT_BINDINGS` + `NAT_POOL` の組み合わせから `natmgrd` が生成 |

```cpp
// natorch.cpp:2659
assert(type == "dynamic" || type == "static");
```

---

## `dnat_pool` NAT タイプ定数

動的 NAT の逆方向エントリ管理に使用される専用 SAI タイプ。`NAT_DNAT_POOL_TABLE` エントリ処理（`doDnatPoolTableTask`）で使用。

| SAI 定数 | 用途 | ソース |
|---------|------|--------|
| `SAI_NAT_TYPE_DESTINATION_NAT_POOL` | DNAT pool エントリ（動的 SNAT の逆引き） | `natorch.cpp:1801, 1833` |
| `SAI_NAT_TYPE_DOUBLE_NAT` | Twice NAT エントリ（双方向同時変換） | `natorch.cpp:1009, 1200, 1379, 1556` |

```cpp
// natorch.cpp:1799-1805 (addDnatPoolEntry)
dnat_pool_entry.vr_id = gVirtualRouterId;
dnat_pool_entry.switch_id = gSwitchId;
dnat_pool_entry.nat_type = SAI_NAT_TYPE_DESTINATION_NAT_POOL;
dnat_pool_entry.data.key.dst_ip = ip_address.getV4Addr();
dnat_pool_entry.data.mask.dst_ip = 0xffffffff;
status = sai_nat_api->create_nat_entry(&dnat_pool_entry, attr_count, nat_entry_attr);
```

---

## NAT_BINDINGS 固有の `nat_type` 制約（orchagent 確認）

`NAT_BINDINGS` は実質 SNAT 専用テーブル。`natorch.cpp:1879-1880` で動的 NAT エントリの追加は `nat_type=="snat"` かつ `entry_type=="dynamic"` の組み合わせのみ受け付ける。

```cpp
// natorch.cpp:1879-1880
if ((entry.nat_type == "snat") and
    (entry.entry_type == "dynamic"))
{
    // 動的 SNAT ルールの追加処理
}
```

`nat_type=="dnat"` の動的エントリは `cfgmgr/natmgr.cpp:6986-6991` で既に拒否（`SWSS_LOG_ERROR` + スキップ）されるため、orchagent に到達しない。

---

## ACL_BIND_POINT について

`natorch.cpp` / `natorch.h` に ACL_BIND_POINT の直接参照は存在しない。NAT の ACL バインドは CONFIG_DB `NAT_BINDINGS.access_list` フィールドで ACL 名を指定し、`natmgrd`（`cfgmgr/natmgr.cpp`）が iptables ルールとして展開する。orchagent レベルでは ACL オブジェクトを直接操作しない。

---

## 出典

- `sonic-swss/orchagent/natorch.cpp` lines 769, 847, 923, 1009, 1104, 1200, 1302, 1379, 1466, 1556, 1630, 1713, 1799-1805, 1825-1837, 1879-1880, 2659
- `sonic-swss/orchagent/natorch.h` lines 18, 36-39
