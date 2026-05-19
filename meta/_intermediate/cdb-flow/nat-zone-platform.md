# NAT ゾーン (nat_zone) — Phase H プラットフォーム差異スキャンノート

対象ページ: `docs/reference/config-db/nat-zone.md`
対象フィールド: `nat_zone` (INTERFACE / VLAN_INTERFACE / PORTCHANNEL_INTERFACE / LOOPBACK_INTERFACE)
Producer: `natmgrd` (NatMgr) / `orchagent` (IntfsOrch)
スキャン範囲: `intfsorch.cpp:36,272-299,978-986,1287-1294` / `natmgr.cpp:274-275,7415,7484,7525-7581` / `main.cpp:936-948`

---

## 検出したプラットフォーム差異

### 1. `gIsNatSupported` による SAI RIF zone_id 書き込みのゲーティング

`IntfsOrch` は `doIntfTask()` (`intfsorch.cpp:974-986`) と RIF 作成パス (`intfsorch.cpp:1287-1294`) の両方で `gIsNatSupported` を参照する。

```cpp
// intfsorch.cpp:978-986
if (gIsNatSupported)
{
    setRouterIntfsNatZoneId(port);
}
else
{
    SWSS_LOG_NOTICE("Not set router interface %s NAT Zone Id to %u, as NAT is not supported", ...);
}

// intfsorch.cpp:1287-1294 (RIF 作成時)
if (gIsNatSupported)
{
    attr.id = SAI_ROUTER_INTERFACE_ATTR_NAT_ZONE_ID;
    attr.value.u32 = port.m_nat_zone_id;
    attrs.push_back(attr);
}
```

`gIsNatSupported` は `main.cpp:936-948` で一度だけ決定される:
- `SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY` の取得成功 かつ 値 > 0 → `gIsNatSupported = true`
- 取得失敗または値 == 0 → `gIsNatSupported = false`（初期値のまま）

### 2. iptables mangle 経路はプラットフォーム非依存

`natmgrd` (`NatMgr::doNatZoneIntfTask`) は `gIsNatSupported` を参照しない。`nat_zone` フィールドを受信した場合、NAT 非サポートプラットフォームを含む **全プラットフォーム** で iptables mangle MARK ルールを設定しようとする。

ただし、iptables が使用可能かどうかはカーネル/OS の設定に依存するため、コンテナ環境や VS では iptables 操作自体が失敗する場合がある（natmgr はエラーをログに出力して続行）。

### 3. Loopback インタフェースは iptables MARK をスキップ

`natmgr.cpp:7526-7528` および `natmgr.cpp:7548-7549`:

```cpp
// ゾーン削除時
if (strncmp(keys[0].c_str(), LOOPBACK_PREFIX, strlen(LOOPBACK_PREFIX)))
{
    /* Delete the mangle iptables rules for non-loopback interface */
    setMangleIptablesRules(DELETE, keys[0], nat_zone);
}
// ゾーン追加時
if (strncmp(keys[0].c_str(), LOOPBACK_PREFIX, strlen(LOOPBACK_PREFIX)))
{
    setMangleIptablesRules(ADD, keys[0], nat_zone);
}
```

Loopback (`Loopback*`) インタフェースは iptables MARK ルールの設定・削除対象外。SAI への zone_id 設定 (`orchagent` / `IntfsOrch` 経由) は行われる。

### 4. VS (Virtual Switch) / テスト環境

VS では `SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY` の取得が失敗するため `gIsNatSupported = false`。orchagent 側の SAI `SAI_ROUTER_INTERFACE_ATTR_NAT_ZONE_ID` 書き込みはスキップされる。CONFIG_DB の `nat_zone` フィールドは書けるが、SAI への反映がないため実質的な NAT 境界設定は無効。

natmgrd 経由の iptables MARK ルールは VS でも試みられる（VS では iptables が動作しないケースがある）。

### 5. Broadcom 固有の DNAT NH 追跡

`nat_zone` フィールド自体は Broadcom 固有の処理を持たない。DNAT エントリの SAI プログラミング（`gNhTrackingSupported` の分岐）は `NatOrch` 側の処理であり、`nat_zone` の書き込みには影響しない。

---

## まとめ表

| 条件 | natmgrd iptables MARK | orchagent SAI zone_id |
|------|----------------------|----------------------|
| NAT サポートプラットフォーム (`gIsNatSupported=true`) | 設定される (Loopback 除く) | 設定される |
| NAT 非サポートプラットフォーム (`gIsNatSupported=false`) | 設定される (Loopback 除く) | スキップ (NOTICE ログのみ) |
| Loopback インタフェース (`Loopback*`) | スキップ | 設定される (gIsNatSupported=true の場合) |
| VS / テスト環境 | 試みるが失敗する場合あり | スキップ |

evidence: `intfsorch.cpp:978-986,1287-1294`, `natmgr.cpp:7526-7549`, `main.cpp:936-948`
