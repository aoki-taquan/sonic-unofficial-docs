# LOOPBACK_INTERFACE — Phase A コード由来の暗黙デフォルト

対象ページ: `docs/reference/config-db/loopback-interface.md`
作成日: 2026-05-14

---

## 調査方法

1. YANG モデル (`sonic-loopback-interface.yang`) でフィールド列挙
2. `intfmgr.cpp` 全行精読（`doIntfGeneralTask`, `doIntfAddrTask`, `addLoopbackIntf` 等）
3. `natmgr.cpp` の LOOPBACK 処理パス精読
4. `bgpcfgd/managers_bgp.py` の `get_lo_ipv4` / 依存チェック精読
5. minigraph 派生パス確認（Phase 6 中間ファイル参照）

---

## フィールド別デフォルト・暗黙挙動

### `admin_status`

- **YANG default**: `up`
- **コード実装**: `intfmgr.cpp:861-868`
  ```cpp
  if (adminStatus.empty())
  {
      adminStatus = "up";
  }
  else if (adminStatus != "up" && adminStatus != "down")
  {
      SWSS_LOG_WARN("Got incorrect value for admin_status as %s for intf %s, defaulting as up", ...);
      adminStatus = "up";
  }
  ```
- **結論**: YANG と実装は一致。フィールド未設定時も不正値時も `"up"` にフォールバック。
- **種別**: YANG default + コードフォールバック（二重保護）

---

### `nat_zone`

- **YANG default**: `"0"`
- **natmgr.cpp の実装** (`natmgr.cpp:7384`): ループバックへの `nat_zone` 処理は **mangle iptables ルールを生成しない**（silent skip）
  ```cpp
  // loopback では setMangleIptablesRules() を呼ばない
  if (strncmp(keys[0].c_str(), LOOPBACK_PREFIX, strlen(LOOPBACK_PREFIX)))
  {
      setMangleIptablesRules(ADD, port, nat_zone);
  }
  ```
- **YANG-実装 discrepancy**: YANG は Loopback でも `nat_zone` を受け付けるが、`natmgr` は Loopback のインターフェースキー (size==1) に対してもゾーン値をキャッシュ (`m_natZoneInterfaceInfo`) するものの、mangle ルールは生成しない。つまり `nat_zone` を設定してもカーネル側の iptables mark は付与されない。
- **種別**: dead consumer（設定は受理・記録されるが iptables 効果ゼロ）

---

### `vrf_name`

- **YANG default**: なし（任意）
- **コード実装** (`intfmgr.cpp:1007-1009`):
  ```cpp
  if (!vrf_name.empty())
  {
      setIntfVrf(alias, vrf_name);
  }
  ```
  空文字の場合 `setIntfVrf` を呼ばない → Linux の `nomaster` 設定もされない → デフォルト VRF に自動帰属。
- **VRF 未準備時の early return** (`intfmgr.cpp:839-843`): `!isIntfStateOk(vrf_name)` で pending キューに戻す。
- **種別**: 暗黙デフォルト（未設定=デフォルト VRF）

---

### `scope`（IP プレフィクスロウ）

- **YANG default**: なし（enum `global`/`local` 任意）
- **コード実装** (`intfmgr.cpp:1134`): `doIntfAddrTask` は CONFIG_DB の `scope` フィールドを **読まない**。APP_DB への書き込み時は常に `scope = "global"` をハードコードする:
  ```cpp
  FieldValueTuple s("scope", "global");
  fvVector.push_back(s);
  ```
- **結論**: CONFIG_DB に `scope = "local"` を設定しても APP_DB・Orchagent には届かない。**dead field**（CONFIG_DB 書き込み可だが下流への伝播なし）。
- **種別**: dead field（APP_DB 書き込み時に上書き固定）

---

### `family`（IP プレフィクスロウ）

- **YANG default**: なし（`must` 制約でプレフィクスと整合必須）
- **コード実装** (`intfmgr.cpp:1129`): `doIntfAddrTask` は `ip_prefix.isV4()` から family を自動判定して APP_DB に書く。CONFIG_DB の `family` フィールドは **読まない**:
  ```cpp
  FieldValueTuple f("family", ip_prefix.isV4() ? IPV4_NAME : IPV6_NAME);
  ```
- **種別**: dead consumer（YANG で検証されるが intfmgr は無視して再計算）

---

### MTU（loopback 固有ハードコード）

- **YANG定義**: `LOOPBACK_INTERFACE` テーブルに `mtu` フィールドはない
- **コード実装** (`intfmgr.cpp:28, 201`):
  ```cpp
  #define LOOPBACK_DEFAULT_MTU_STR "65536"
  cmd << IP_CMD << " link add " << alias << " mtu " << LOOPBACK_DEFAULT_MTU_STR << " type dummy";
  ```
- **結論**: `ip link add <name> mtu 65536 type dummy` でハードコード。CONFIG_DB から変更不可。
- **種別**: ハードコード（YANG 未定義・変更経路なし）

---

### IPv6 link-local アドレス（プレフィクスロウ）

- **コード実装** (`intfmgr.cpp:1123-1139`):
  ```cpp
  if (!ip_prefix.isV4() && ip_prefix.getIp().getAddrScope() == IpAddress::AddrScope::LINK_SCOPE)
  {
      m_intfLLAddresses[alias].insert(ip_prefix.to_string());
  }
  // Don't send ipv4 link local config to AppDB and Orchagent
  if ((ip_prefix.isV4() == false) || (ip_prefix.getIp().getAddrScope() != IpAddress::AddrScope::LINK_SCOPE))
  {
      // APP_DB へ書く
  }
  ```
- **結論**: `fe80::/10` の IPv6 link-local アドレスは `ip addr add` でカーネルには付与されるが、APP_DB には送信されない（`IntfsOrch` / SAI に伝播しない）。**silent drop**（APP_DB 経由の SAI 通知なし）。
- **種別**: silent drop（カーネルのみ有効、SAI 未通知）

---

### `bgpcfgd` 依存 — Loopback0 IPv4（暗黙の依存）

- **コード実装** (`managers_bgp.py:100, 121, 184-189`):
  ```python
  self.loopbacks = ["Loopback0"]
  deps = [("CONFIG_DB", swsscommon.CFG_LOOPBACK_INTERFACE_TABLE_NAME, "Loopback0"), ...]
  for loopback in self.loopbacks:
      lo_ipv4 = self.get_lo_ipv4(loopback + "|")
      if (lo_ipv4 is None and "bgp_router_id" not in ...:
          return False  # BGP ピア追加をブロック
  ```
- **結論**: `Loopback0` に IPv4 アドレスがなく `DEVICE_METADATA.bgp_router_id` も未設定の場合、BGP peer の追加が**永続的にブロック**される。これは CONFIG_DB フィールドの値ではなくエントリ存在の依存。
- **種別**: 経路依存乖離（bgp_router_id 未設定時のみ Loopback0 IP が必須化）

---

### VOQ 環境 — Loopback4096（条件付き依存）

- **コード実装** (`managers_bgp.py:145-146`):
  ```python
  if self.peer_type == 'internal':
      deps.append(("CONFIG_DB", CFG_LOOPBACK_INTERFACE_TABLE_NAME, "Loopback4096"))
  ```
- **結論**: VOQ トポロジの internal BGP peer では `Loopback4096` エントリの存在が BGP peer 設定の必要条件。非 VOQ 環境では無関係。
- **種別**: プラットフォーム依存（VOQ のみ）

---

### voq スイッチタイプ — IPv6 metric 256（ハードコード）

- **コード実装** (`intfmgr.cpp:103-106`):
  ```cpp
  if(mySwitchType == "voq")
  {
     metric = " metric 256";
  }
  ```
- **結論**: `DEVICE_METADATA.switch_type == "voq"` の場合、IPv6 アドレスの `ip -6 address add` に `metric 256` が自動付与される。Loopback でも同様。CONFIG_DB から変更不可。
- **種別**: プラットフォーム依存ハードコード

---

### `mac_addr`（ループバックへの非適用）

- **コード実装** (`intfmgr.cpp:1012-1021`): `doIntfGeneralTask` では `is_lo` ブランチ外で `mac` を設定する。しかし Loopback が `is_lo == true` の場合、mac 処理ブロックは両方（Loopback と非 Loopback）で実行される。`mac` が空の場合は `MacAddress().to_string()` (= `"00:00:00:00:00:00"`) を APP_DB に送信する。
- **種別**: 暗黙デフォルト（ゼロ MAC を APP_DB に伝播）

---

## サマリー表

| フィールド | YANG default | コード実態 | 種別 |
|-----------|-------------|-----------|------|
| `admin_status` | `up` | 空値/不正値→ `"up"` フォールバック | YANG + コード二重保護 |
| `nat_zone` | `"0"` | mangle iptables ルール未生成（Loopback） | dead consumer |
| `vrf_name` | なし | 未設定→ `setIntfVrf` 未呼び出し→デフォルト VRF | 暗黙デフォルト |
| `scope` | なし | APP_DB 書込み時常に `"global"` 上書き | dead field |
| `family` | なし | `ip_prefix.isV4()` で再計算、CONFIG_DB値は無視 | dead consumer |
| MTU | 未定義 | `65536` ハードコード、変更経路なし | ハードコード |
| IPv6 link-local | — | カーネル付与のみ、APP_DB 未通知 | silent drop |
| Loopback0 IPv4 | — | bgp_router_id 未設定時 BGP peer ブロック | 経路依存乖離 |
| Loopback4096 | — | VOQ internal BGP peer に必須 | プラットフォーム依存 |
| IPv6 metric | — | VOQ 環境で `metric 256` 自動付与 | プラットフォーム依存 |
| `mac_addr` | — | 空→ `00:00:00:00:00:00` を APP_DB に送信 | 暗黙デフォルト |

---

## 証跡

- `sonic-swss/cfgmgr/intfmgr.cpp` L28 (`LOOPBACK_DEFAULT_MTU_STR "65536"`)
- `sonic-swss/cfgmgr/intfmgr.cpp` L201 (`ip link add ... mtu 65536 type dummy`)
- `sonic-swss/cfgmgr/intfmgr.cpp` L861-868 (`adminStatus` フォールバック)
- `sonic-swss/cfgmgr/intfmgr.cpp` L1007-1009 (`vrf_name` 空チェック)
- `sonic-swss/cfgmgr/intfmgr.cpp` L1123-1139 (IPv6 link-local silent drop)
- `sonic-swss/cfgmgr/intfmgr.cpp` L1129, 1134 (`family`/`scope` 再計算)
- `sonic-swss/cfgmgr/natmgr.cpp` L7526-7549, 7581 (Loopback の mangle skip)
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py` L100, 121, 145-146, 184-189
