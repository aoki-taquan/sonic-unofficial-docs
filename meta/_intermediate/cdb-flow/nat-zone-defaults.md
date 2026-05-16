# nat-zone-defaults.md — Phase A 中間ファイル

## 対象

`nat_zone` フィールド（`INTERFACE` / `VLAN_INTERFACE` / `PORTCHANNEL_INTERFACE` / `LOOPBACK_INTERFACE` テーブル内）のコード由来デフォルト調査。

## エビデンス収集

### YANG モデル (sonic-interface.yang L76-84)

```yang
leaf nat_zone {
    description "NAT Zone for the interface";
    type uint8 {
        range "0..3" {
            error-message "Invalid nat zone for the interface.";
            error-app-tag nat-zone-invalid;
        }
    }
    default "0";
}
```

- YANG default: `"0"`（内側ゾーン = inside interface）
- 有効範囲: 0..3（uint8）

### NatMgr コード (natmgr.cpp L7384, L7388, L7499-7514)

```cpp
// L7384: ローカル変数初期化（ハードコード fallback）
string key = kfvKey(t), nat_zone = "1";
int prefixLen = 0, nat_zone_value = 1;

// L7499-7514: フィールドが存在する場合のみ上書き
if (fvField(idx) == NAT_ZONE)
{
    nat_zone_value = stoi(fvValue(idx));  // DB から読んだ値
    // +1 して iptables mangle mark として使用（0 mark を避けるため）
    nat_zone_value++;
    nat_zone = to_string(nat_zone_value);
}
```

- `nat_zone` フィールド不在時のローカル変数初期値: `"1"`（ただし DB から `nat_zone=0` が入る場合は +1 して `"1"` になる）
- **iptables mangle mark = nat_zone_value + 1**（0 mark を避けるため）
- DB 値 `0` → iptables mark `1`
- DB 値 `1` → iptables mark `2`

### IntfsOrch コード (intfsorch.cpp L748-759, L1361)

```cpp
// L748-759: nat_zone フィールドが存在する場合のみ設定
else if (field == "nat_zone")
{
    nat_zone_id = (uint32_t)stoul(value);
    nat_zone = value;
}

// L974-986: nat_zone が空でなく変化した場合のみ SAI 呼び出し
if ((!nat_zone.empty()) and (port.m_nat_zone_id != nat_zone_id))
{
    port.m_nat_zone_id = nat_zone_id;
    if (gIsNatSupported) { setRouterIntfsNatZoneId(port); }
}

// L1361: インタフェース削除時のリセット
port.m_nat_zone_id = 0;
```

- `m_nat_zone_id` の初期値: `0`（ポート作成時）
- インタフェース削除時: `0` にリセット
- フィールド省略時: SAI へは書き込まれない（`nat_zone.empty()` のためスキップ）

### NatMgr ヘッダ (natmgr.h L60, L227)

```cpp
#define NAT_ZONE "nat_zone"
// Value is "nat_zone" (Eg. "1")
```

## まとめ

| フィールド | YANG default | コード hardcode | 乖離 |
|-----------|-------------|----------------|------|
| `nat_zone` | `"0"` | `m_nat_zone_id = 0` (intfsorch.cpp:1361) | なし |
| iptables mark | — | `nat_zone_value + 1` | YANG と異なる内部変換（DB 値に +1） |

## 注意点

1. **YANG default `"0"` は省略時の CONFIG_DB 値**。intfsorch は省略時に SAI 呼び出しを行わない（フィールドが空のため）。
2. **iptables mark の offset**: `natmgr` は DB の `nat_zone` 値に +1 して iptables mangle MARK として使用する。DB の `nat_zone=0` → mark `1`、`nat_zone=1` → mark `2`。これは mark=0 が iptables のデフォルトと衝突するため。
3. **NAT 未サポートプラットフォーム**: `gIsNatSupported == false` の場合、intfsorch は `setRouterIntfsNatZoneId()` を呼ばずに SWSS_LOG_NOTICE を出してスキップする（intfsorch.cpp:978-986）。
