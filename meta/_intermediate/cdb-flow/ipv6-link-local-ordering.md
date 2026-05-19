# ipv6-link-local — Phase B 書込み順依存スキャンノート

対象フィールド: `INTERFACE|<name>.ipv6_use_link_local_only` / `PORTCHANNEL_INTERFACE|<name>` / `VLAN_INTERFACE|<name>`
Consumer: `intfmgrd` (sonic-swss cfgmgr/intfmgr.cpp)、`neighsyncd` (sonic-swss neighsyncd/neighsync.cpp)
スキャン範囲: `cfgmgr/intfmgr.cpp`、`neighsyncd/neighsync.cpp`

---

## 検出した順序依存・タイミング依存

### 1. インターフェース state が STATE_DB で OK になる前の書込みは skipped

`intfmgr.cpp:L833-837` で `isIntfStateOk()` を呼び、STATE_DB の対応エントリが存在しない場合は `return false;`（再キュー）する。

```
if (!isIntfStateOk(parentAlias.empty() ? alias : parentAlias))
{
    SWSS_LOG_DEBUG("Interface is not ready, skipping %s", alias.c_str());
    return false;
}
```

`isIntfStateOk()` は:
- `Vlan*` → `STATE_VLAN_TABLE` にエントリが存在するか
- `PortChannel*` → `STATE_LAG_TABLE` にエントリが存在するか
- その他 (Ethernet*) → `STATE_PORT_TABLE` にエントリが存在し `state` フィールドを持つか

**順序依存（強制）**: `ipv6_use_link_local_only` を CONFIG_DB に書いても、対応インターフェースが
STATE_DB で "ready" にならない限り `intfmgrd` は APP_DB への転送をスキップし続ける。
`intfmgrd` が `false` を返すとイベントは次のポーリングで再処理されるため、最終的には
インターフェースが UP してから自動的に転送される。

evidence: `cfgmgr/intfmgr.cpp:831-837`, `cfgmgr/intfmgr.cpp:649-708`

### 2. VRF バインド後の ipv6_use_link_local_only 設定

`intfmgr.cpp:L839-843` で `vrf_name` が空でない場合は `isIntfStateOk(vrf_name)` も確認する:

```
if (!vrf_name.empty() && !isIntfStateOk(vrf_name))
{
    SWSS_LOG_DEBUG("VRF is not ready, skipping %s", vrf_name.c_str());
    return false;
}
```

インターフェースが VRF にバインドされている場合、VRF 自体の STATE_DB エントリ
（`STATE_VRF_TABLE`）が存在しない状態で属性を設定しても APP_DB 転送がスキップされる。

**順序依存（条件付き）**: VRF を利用する場合は VRF の作成（`VRF|<name>` → vrfmgrd → STATE_VRF_TABLE）
が先行している必要がある。

evidence: `cfgmgr/intfmgr.cpp:839-843`

### 3. neighsyncd の CONFIG_DB 直接参照（APP_DB 依存なし）

`neighsync.cpp` の `isLinkLocalEnabled()` は `intfmgrd` 経由の APP_DB ではなく CONFIG_DB を
直接参照する:

```cpp
// neighsync.cpp:L215-235
if (!m_cfgInterfaceTable.get(port, values))
    return false;
auto it = std::find_if(values.begin(), values.end(), ...);
if (it->second == "enable") return true;
return false;
```

これは APP_DB への転送完了を待たずに link-local neigh の ADD/DEL をフィルタリングする。
**中間状態**: CONFIG_DB に `"enable"` が書かれたが APP_DB にまだ転送されていない場合でも、
neighsyncd はすでに link-local neigh を NEIGH_TABLE に書き込む。逆に CONFIG_DB から削除されると
即座に link-local neigh をフィルタアウトする。

evidence: `neighsyncd/neighsync.cpp:193-239`

### 4. disable 設定時の neigh 削除の順序

`intfmgrd` が `"disable"` を処理する際:
1. `m_ipv6LinkLocalModeList.erase(alias)` でリストから削除
2. `delIpv6LinkLocalNeigh(alias)` で APP_DB NEIGH_TABLE から link-local neigh を即時削除

この処理は SET_COMMAND の処理中（CONFIG_DB イベント受信時）に同期的に実行される。
**副作用**: `"disable"` の CONFIG_DB 書込みは、対応 neigh の APP_DB 削除を即時トリガーする。

evidence: `cfgmgr/intfmgr.cpp:920-923`

### 5. VLAN member / PortChannel member との排他

CLI (`config/main.py`) レベルで VLAN member ポートへの `enable` は拒否されるが、
CONFIG_DB を直接操作した場合は `intfmgrd` が処理を試みる。
`intfmgrd` 内に VLAN member チェックはないため、直接書込みでは技術的に設定できてしまうが、
BGP unnumbered の動作は保証されない。

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | STATE_DB のインターフェース state OK → CONFIG_DB への ipv6_use_link_local_only 書込み効果 | 強制先行（未 OK 時は APP_DB 転送 skipped） | intfmgrd が自動再キューするため起動後に自然反映 |
| 2 | VRF STATE_DB エントリ存在 → VRF バインド済みインターフェースの設定 | 条件付き先行（VRF 未 ready 時は skip） | VRF 作成後に設定するか、自動再キューを利用 |
| 3 | CONFIG_DB 直接参照（neighsyncd）→ APP_DB 転送は無関係 | CONFIG_DB が正 source | APP_DB 転送前でも neighsyncd は CONFIG_DB を読む |
| 4 | CONFIG_DB "disable" 書込み → NEIGH_TABLE 即時削除 | 同期的（同一イベント処理内） | disable 後の neigh は即時消えることを考慮 |
