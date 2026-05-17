# ACL_TABLE (CTRLPLANE) — Phase C: 暗黙参照テーブル分析 (cross-refs)

対象ドキュメント: `docs/reference/config-db/control-plane-acl.md`
解析日: 2026-05-17
根拠ソース:
  - `sonic-host-services/scripts/caclmgrd` (sonic-host-services)
  - `sonic-swss/orchagent/aclorch.cpp` sha `4305596`

---

## 目的

`ACL_TABLE|<name>` (type=CTRLPLANE) が CONFIG_DB に書かれたとき、`caclmgrd` が**暗黙的に**
参照する他テーブルのキー / フィールドを網羅する。orchagent 側は SAI に投入しないため参照はほぼゼロ。
caclmgrd 側が iptables ルール生成のために参照するテーブルを列挙する。

---

## 1. ACL_RULE テーブル (必須参照)

### 参照箇所

`get_acl_rules_and_translate_to_iptables_commands()` (caclmgrd L729-730):

```python
self._tables_db_info = config_db_connector.get_table(self.ACL_TABLE)
self._rules_db_info  = config_db_connector.get_table(self.ACL_RULE)
```

### 依存内容

| 参照元フィールド | 参照先テーブル | 参照先フィールド | 参照タイミング |
|---|---|---|---|
| (ACL_TABLE の type=CTRLPLANE フィルタ後) | `ACL_RULE` | `PRIORITY`, `PACKET_ACTION`, `SRC_IP`, `DST_IP`, `IP_PROTOCOL`, 等 | iptables ルール生成時 (全テーブルスキャン) |

---

## 2. DEVICE_METADATA テーブル (暗黙参照: namespace / platform 判定)

### 参照箇所

`__init__()` (caclmgrd L165):
```python
metadata = self.config_db_map[DEFAULT_NAMESPACE].get_table(self.DEVICE_METADATA_TABLE)
```

- `subtype` フィールドで DualToR 判定
- `platform` フィールドで SmartSwitch 等の判定

### 依存内容

| 参照先テーブル | 参照先フィールド | 用途 |
|---|---|---|
| `DEVICE_METADATA` | `localhost.subtype` | `DualToR` 判定: DHCP チェーン保持の要否 |
| `DEVICE_METADATA` | `localhost.platform` | SmartSwitch / 機種判定 |

---

## 3. VXLAN_TUNNEL テーブル (暗黙参照: VxLAN ルール生成)

### 参照箇所

`main()` (caclmgrd L1160):
```python
subscribe_vxlan_table = swsscommon.SubscriberStateTable(config_db_connector, self.VXLAN_TUNNEL_TABLE)
```

`get_acl_rules_and_translate_to_iptables_commands()` 内で VxLAN UDP 4789 ACCEPT ルールを
生成するために `VXLAN_TUNNEL` テーブルの `src_ip` フィールドを参照する。

### 依存内容

| 参照先テーブル | 参照先フィールド | 用途 |
|---|---|---|
| `VXLAN_TUNNEL` | `src_ip` | `iptables -A INPUT -p udp --dport 4789 -j ACCEPT` ルール生成条件 |

---

## 4. STATE_DB BFD_SESSION_TABLE (暗黙参照: BFD ルール生成)

### 参照箇所

`main()` (caclmgrd L1157):
```python
subscribe_bfd_session = swsscommon.SubscriberStateTable(state_db_connector, self.BFD_SESSION_TABLE)
```

STATE_DB の `BFD_SESSION_TABLE` を購読し、BFD セッション存在時に UDP 3784/4784 ACCEPT ルールを生成。

### 依存内容

| 参照先 DB | 参照先テーブル | 用途 |
|---|---|---|
| `STATE_DB` | `BFD_SESSION_TABLE` | BFD セッション存在確認 → UDP 3784/4784 ACCEPT 生成 |

---

## 5. LOOPBACK_INTERFACE / VLAN_INTERFACE / PORT / PORTCHANNEL (ip2me DROP ルール)

### 参照箇所

`generate_block_ip2me_traffic_iptables_commands()` (caclmgrd L286-330):
```python
INTERFACE_TABLE_NAME_LIST = [
    "LOOPBACK_INTERFACE", "VLAN_INTERFACE", "INTERFACE", "PORTCHANNEL_INTERFACE"
]
for iface_table_name in INTERFACE_TABLE_NAME_LIST:
    iface_table = config_db_connector.get_table(iface_table_name)
```

インターフェースに割り当てられた IP アドレスを ip2me DROP ルールの対象として取得。

### 依存内容

| 参照先テーブル | 用途 |
|---|---|
| `LOOPBACK_INTERFACE` | ip2me DROP ルール生成 |
| `VLAN_INTERFACE` | ip2me DROP ルール生成 |
| `INTERFACE` | ip2me DROP ルール生成 |
| `PORTCHANNEL_INTERFACE` | ip2me DROP ルール生成 |

---

## 6. cross-refs ブロック (最終形)

以下を `docs/reference/config-db/control-plane-acl.md` の `<!-- /ordering -->` 直後に挿入する。

```markdown
<!-- cross-refs -->
## 暗黙参照テーブル (Phase C)

`ACL_TABLE (CTRLPLANE)` は `orchagent` 側では SAI に投入されず参照テーブルが最小限に留まる。
実際の CPU 宛ルール生成は `caclmgrd` が行い、複数の CONFIG_DB / STATE_DB テーブルを暗黙参照する。

| 参照元 (caclmgrd) | 参照先テーブル | 参照先フィールド | 用途 | evidence |
|---|---|---|---|---|
| `get_acl_rules_*()` | `ACL_RULE` | `PRIORITY`, `PACKET_ACTION`, `SRC_IP`, `IP_PROTOCOL` 等 | iptables ルール本体の生成 | `caclmgrd L729-730` |
| `__init__()` | `DEVICE_METADATA` | `localhost.subtype`, `localhost.platform` | DualToR 判定・プラットフォーム判定 | `caclmgrd L165` |
| `main()` — VxLAN subscribe | `VXLAN_TUNNEL` | `src_ip` | VxLAN UDP 4789 ACCEPT 生成条件 | `caclmgrd L1160` |
| `main()` — BFD subscribe | `STATE_DB / BFD_SESSION_TABLE` | セッション存在 | BFD UDP 3784/4784 ACCEPT 生成条件 | `caclmgrd L1157` |
| `generate_block_ip2me_*()` | `LOOPBACK_INTERFACE`, `VLAN_INTERFACE`, `INTERFACE`, `PORTCHANNEL_INTERFACE` | 各 IP prefix | ip2me DROP ルール生成 | `caclmgrd L286-330` |

### orchagent 側の参照

`AclOrch` は CTRLPLANE テーブルを `m_ctrlAclTables` に登録するのみ。SAI / APPL_DB への書き込みなし。
他テーブルへの暗黙参照もない。

<!-- /cross-refs -->
```
