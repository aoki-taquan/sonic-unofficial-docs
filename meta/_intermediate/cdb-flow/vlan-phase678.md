# VLAN — Phase 6/7/8 derivation & handler-branching

対象ページ: `docs/reference/config-db/vlan.md`
バッチ: cdb_batch_9

---

## Phase 6: 自動派生 (minigraph.py / init_cfg.json.j2 代入)

<!-- derivation -->

### 1. `dhcp_servers` — minigraph.py による自動付与

**ソース**: `sonic-buildimage/src/sonic-config-engine/minigraph.py:1069`

```python
vlan_attributes['dhcp_servers'] = vdhcpserver_list
```

- XML の `<VlanInterface><Dhcp_Relay>` タグに記述された DHCP サーバ IP リストを解析し、`VLAN|Vlan<id>.dhcp_servers` フィールドとして代入。
- 複数サーバはカンマ区切りリストで格納。フィールドが XML に存在しない場合は付与されない（デフォルトなし）。

### 2. `dhcpv6_servers` — minigraph.py による自動付与

**ソース**: `sonic-buildimage/src/sonic-config-engine/minigraph.py:1075`

```python
vlan_attributes['dhcpv6_servers'] = vdhcpserver_list
vlan_attributes['dhcpv6_servers'] = vdhcpserver_list  # dhcpv6
```

- 同様に `<Dhcpv6_Relay>` タグから IPv6 DHCP サーバを抽出。

### 3. `mac` — minigraph.py による仮想 MAC 代入

**ソース**: `sonic-buildimage/src/sonic-config-engine/minigraph.py:1082`

```python
vlan_attributes['mac'] = vlanmac.text
```

- `<VlanInterface><MacAddress>` が定義されている場合のみ付与。未定義時は省略（システム MAC 継承）。

### 4. `alias` — インターフェース別名の自動付与

**ソース**: `sonic-buildimage/src/sonic-config-engine/minigraph.py:1097`

```python
vlan_attributes['alias'] = vintfname
```

- XML の `<VlanInterface>` 名から alias を取得。`results['VLAN'] = vlans` でまとめて CONFIG_DB に書込み（minigraph.py:2610）。

<!-- /derivation -->

---

## Phase 7: 条件付き登録 (add_manager)

<!-- derivation -->

該当なし。

`vlanmgrd` は `orchdaemon` の初期化時に無条件登録される。ASIC 能力チェックや platform 条件に依らず常時 APP_DB `APP_VLAN_TABLE` を購読する。

<!-- /derivation -->

---

## Phase 8: manager メソッド内 early return / dispatch

<!-- handler-branching -->

### vlanmgrd の doVlanTask() 分岐

**ソース**: `sonic-swss/cfgmgr/vlanmgrd.cpp`

1. **op == "SET"**: VLAN 属性を受け取り、`addBridgeVlan()` → Linux bridge VLAN に反映。`admin_status` が `down` の場合は `setVlanDown()` を呼び出して即時 early return しない（admin-down でも bridge エントリは作成する）。
2. **op == "DEL"**: `delBridgeVlan()` を呼び出し bridge から削除。MAC / DHCP 関連フィールドはカーネルに直接影響しないため no-op。
3. `mux_cable` サブタイプが存在する場合、muxorch との協調のため `notifyMuxState()` を追加で発火。

<!-- /handler-branching -->
