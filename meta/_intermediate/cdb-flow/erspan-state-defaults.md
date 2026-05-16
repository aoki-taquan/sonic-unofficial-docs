# STATE_DB MIRROR_SESSION_TABLE (ERSPAN) Phase A: コード由来デフォルト

**対象**: `docs/reference/config-db/erspan.md` の `<!-- defaults -->` ブロック（STATE_DB 書き込みフィールド補足）
**調査日**: 2026-05-15
**evidence**: `sonic-swss/orchagent/mirrororch.cpp`

---

## 調査スコープ

`MirrorOrch::setSessionState()` が STATE_DB `MIRROR_SESSION_TABLE` に書き込むフィールドについて、ERSPAN 種別での値の由来・デフォルト・プラットフォーム依存挙動を調査する。CONFIG_DB フィールドのデフォルトは `erspan-defaults.md` を参照。

---

## STATE_DB MIRROR_SESSION_TABLE フィールド一覧

STATE_DB への書き込みは `MirrorOrch::setSessionState()` (`mirrororch.cpp:579-637`) で行われる。

| フィールド | マクロ定義 | 値の由来 | ERSPAN 固有挙動 |
|-----------|-----------|---------|---------------|
| `status` | `MIRROR_SESSION_STATUS` | `"active"` / `"inactive"` | セッション活性化後に `"active"`、非活性化で `"inactive"` |
| `monitor_port` | `MIRROR_SESSION_MONITOR_PORT` | nexthop port alias | **voq switch では recirc port alias に置換**（非voqは neighbor port alias） |
| `dst_mac` | `MIRROR_SESSION_DST_MAC_ADDRESS` | neighbor MAC アドレス | **voq switch では gMacAddress（ルータ MAC）に固定**（非voqは動的 neighbor MAC） |
| `route_prefix` | `MIRROR_SESSION_ROUTE_PREFIX` | nexthopInfo.prefix.to_string() | RouteOrch が解決した dst_ip の route prefix |
| `vlan_id` | `MIRROR_SESSION_VLAN_ID` | neighborInfo.port.m_vlan_info.vlan_id | nexthop が VLAN ポート経由のとき VLAN ID、非VLAN時は `0` |
| `next_hop_ip` | `MIRROR_SESSION_NEXT_HOP_IP` | nexthopInfo.nexthop.to_string() | RouteOrch が解決した nexthop IP アドレス |

---

## フィールド別詳細

### `status`: "active" / "inactive"

```cpp
// mirrororch.cpp:583-587
value = session.status ? MIRROR_SESSION_STATUS_ACTIVE : MIRROR_SESSION_STATUS_INACTIVE;
fvVector.emplace_back(MIRROR_SESSION_STATUS, value);
```

- 初期状態（createEntry 直後）: `"inactive"`
- activateSession() 成功後: `"active"`
- deactivateSession() 後: `"inactive"`

ERSPAN の場合、dst_ip の nexthop 解決（RouteOrch callback）完了まで `"inactive"` のまま。ルートが存在しなければ永久に `"inactive"`。

### `monitor_port`: voq/非voq でアルゴリズムが異なる

```cpp
// mirrororch.cpp:591-604
if ((gMySwitchType == "voq") && (session.type == MIRROR_SESSION_ERSPAN))
{
    if (!m_portsOrch->getRecircPort(port, Port::Role::Rec))
    {
        SWSS_LOG_ERROR("Failed to get recirc port for mirror session %s", name.c_str());
        return;
    }
}
else
{
    m_portsOrch->getPort(session.neighborInfo.portId, port);
}
fvVector.emplace_back(MIRROR_SESSION_MONITOR_PORT, port.m_alias);
```

- **非voq ERSPAN**: dst_ip の nexthop が向く出口ポートの alias（例: `Ethernet0`）
- **voq ERSPAN**: recirc port の alias（例: `Recirc0`）— nexthop 情報と無関係

### `dst_mac`: voq では gMacAddress 固定

```cpp
// mirrororch.cpp:606-617
if ((gMySwitchType == "voq") && (session.type == MIRROR_SESSION_ERSPAN))
{
    value = gMacAddress.to_string();
} else
{
    value = session.neighborInfo.mac.to_string();
}
fvVector.emplace_back(MIRROR_SESSION_DST_MAC_ADDRESS, value);
```

- **非voq ERSPAN**: ARP/NDP で解決した nexthop neighbor の MAC
- **voq ERSPAN**: スイッチのルータ MAC（`gMacAddress`）に固定

### `route_prefix`: nexthop prefix 表現

RouteOrch が返す prefix（例: `192.168.1.0/24`）。dst_ip が属するルートプレフィックス。デフォルト値なし — RouteOrch が解決した値をそのまま格納。

### `vlan_id`: 非VLAN時は `0`（文字列 `"0"`）

`to_string(session.neighborInfo.port.m_vlan_info.vlan_id)` — nexthop が VLAN ポートでなければ `vlan_id = 0` → STATE_DB に `"0"` が書き込まれる。

### `next_hop_ip`: nexthop IP アドレス文字列

`session.nexthopInfo.nexthop.to_string()` — RouteOrch が解決した nexthop IP（GW アドレス）。直接接続ルートの場合は dst_ip と同じか空文字になりうる。

---

## ウォームリブート時の STATE_DB 読み戻し

```cpp
// mirrororch.cpp:118-151
m_mirrorTable.getKeys(keys);
for (auto& key : keys)
{
    m_mirrorTable.get(key, tuples);
    bool active = false;
    string monitor_port;
    string next_hop_ip;
    for (auto& tuple : tuples)
    {
        if (fvField(tuple) == MIRROR_SESSION_STATUS)
            active = fvValue(tuple) == MIRROR_SESSION_STATUS_ACTIVE;
        if (fvField(tuple) == MIRROR_SESSION_MONITOR_PORT)
            monitor_port = fvValue(tuple);
        if (fvField(tuple) == MIRROR_SESSION_NEXT_HOP_IP)
            next_hop_ip = fvValue(tuple);
    }
    if (active)
        m_recoverySessionMap.emplace(key, monitor_port + state_db_key_delimiter + next_hop_ip);
}
```

ウォームリブート時に STATE_DB から `status`, `monitor_port`, `next_hop_ip` の 3 フィールドのみを読み戻す。`dst_mac`, `route_prefix`, `vlan_id` は読み戻さない（activateSession で再計算される）。

---

## evidence ソース行

| 知見 | ファイル | 行 |
|------|---------|-----|
| `status`: active/inactive 文字列定義 | `mirrororch.cpp` | 15-17 |
| `setSessionState()` 全体 | `mirrororch.cpp` | 579-637 |
| `monitor_port` voq/非voq 分岐 | `mirrororch.cpp` | 591-604 |
| `dst_mac` voq/非voq 分岐 | `mirrororch.cpp` | 606-617 |
| `route_prefix` 書き込み | `mirrororch.cpp` | 619-622 |
| `vlan_id` 書き込み | `mirrororch.cpp` | 624-628 |
| `next_hop_ip` 書き込み | `mirrororch.cpp` | 630-634 |
| warm reboot 読み戻し | `mirrororch.cpp` | 118-151 |
