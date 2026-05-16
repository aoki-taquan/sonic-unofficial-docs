# bgp-internal-neighbor — Phase C 暗黙参照 証跡

**調査日**: 2026-05-16
**対象ページ**: `docs/reference/config-db/bgp-internal-neighbor.md`
**調査ソース**:
- `src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py`（598 行全行精読）
- `src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`（関連箇所精読）
- `dockers/docker-fpm-frr/frr/bgpd/templates/internal/policies.conf.j2`（110 行全行精読）

---

## 検出した暗黙参照一覧

| # | 参照先テーブル / フィールド | 参照方向 | YANG leafref | 必須度 | ソース行 |
|---|---|---|---|---|---|
| 1 | `DEVICE_METADATA\|localhost.bgp_asn` | CONFIG_DB 読み取り | なし | 必須 (deps) | managers_bgp.py L119, L192 |
| 2 | `DEVICE_METADATA\|localhost.type` | CONFIG_DB 読み取り | なし | 必須 (deps) | managers_bgp.py L120 |
| 3 | `DEVICE_METADATA\|localhost.sub_role` | CONFIG_DB 読み取り (ルートマップ分岐) | なし | プラットフォーム依存 | policies.conf.j2 L8 |
| 4 | `DEVICE_METADATA\|localhost.switch_type` | CONFIG_DB 読み取り (chassis-packet 分岐) | なし | プラットフォーム依存 | policies.conf.j2 L26 |
| 5 | `DEVICE_METADATA\|localhost.bgp_router_id` | CONFIG_DB 読み取り (originator-id) | なし | 省略可 | policies.conf.j2 L10-11 |
| 6 | `BGP_GLOBALS\|<vrf>.local_asn` | FRR レイヤ前提条件 | なし | 実質必須 | frrcfgd.py L2700-2703 |
| 7 | `LOOPBACK_INTERFACE\|Loopback0` | CONFIG_DB 読み取り (router-id) | なし | 必須 (deps) | managers_bgp.py L121, L216 |
| 8 | `LOOPBACK_INTERFACE\|Loopback4096` | CONFIG_DB 読み取り (originator-id / update-source) | なし | internal 専用 deps | managers_bgp.py L146; policies.conf.j2 L7 |
| 9 | `INTERFACE` / `PORTCHANNEL_INTERFACE` | CONFIG_DB 読み取り (local_addr 解決) | なし | local_addr 使用時必須 | managers_bgp.py L124-125, L198-201 |
| 10 | `ROUTE_MAP\|FROM_BGP_INTERNAL_PEER_V*` | FRR 書き込み (テンプレート生成) | なし | ハードコード | policies.conf.j2 L9, L32, L93, L99, L101 |
| 11 | `ROUTE_MAP\|TO_BGP_INTERNAL_PEER_V*` | FRR 書き込み (テンプレート生成) | なし | ハードコード | policies.conf.j2 L78, L85, L103, L105 |
| 12 | `BGP_PEER_GROUP\|INTERNAL_PEER_V4/V6` | FRR 書き込み (peer-group.conf.j2 生成) | なし | ハードコード | peer-group.conf.j2 全体 |

---

## 詳細証跡

### 1-5. DEVICE_METADATA

**deps 宣言** (`managers_bgp.py` L118-120):
```python
("CONFIG_DB", swsscommon.CFG_DEVICE_METADATA_TABLE_NAME, "localhost/bgp_asn"),
("CONFIG_DB", swsscommon.CFG_DEVICE_METADATA_TABLE_NAME, "localhost/type"),
```
`post_dependencies_init_complete` が False の間はイベント配送が止まる。

**add_peer() 内 bgp_asn 読み取り** (L192):
```python
bgp_asn = self.directory.get_slot("CONFIG_DB", swsscommon.CFG_DEVICE_METADATA_TABLE_NAME)["localhost"]["bgp_asn"]
```

**テンプレート渡し** (L205):
```python
'CONFIG_DB__DEVICE_METADATA': self.directory.get_slot("CONFIG_DB", swsscommon.CFG_DEVICE_METADATA_TABLE_NAME),
```

**policies.conf.j2 での sub_role/switch_type 分岐** (L8, L26):
```jinja2
{% if CONFIG_DB__DEVICE_METADATA['localhost']['sub_role'] == 'BackEnd' %}
...
{% elif CONFIG_DB__DEVICE_METADATA['localhost']['switch_type'] == 'chassis-packet' %}
```

**bgp_router_id 参照** (L10-11, L21-22):
```jinja2
{% if "localhost" in CONFIG_DB__DEVICE_METADATA and "bgp_router_id" in CONFIG_DB__DEVICE_METADATA["localhost"] %}
 set originator-id {{ CONFIG_DB__DEVICE_METADATA["localhost"]["bgp_router_id"] }}
{% elif lo4096_ipv4 is not none %}
 set originator-id {{ lo4096_ipv4 }}
```

### 6. BGP_GLOBALS

**frrcfgd.py** (L2659-2662, L2700-2703):
```python
# vrf_tables チェック - local_asn がなければスキップ
# router bgp <ASN> インスタンス生成
```
`BGP_GLOBALS|<vrf>.local_asn` が CONFIG_DB にない VRF への設定はすべて無視される。bgpcfgd テンプレートも同じ bgpd インスタンスを前提とするため間接的に依存。

### 7-8. Loopback0 / Loopback4096

**deps 宣言** (L121, L146):
```python
("CONFIG_DB", swsscommon.CFG_LOOPBACK_INTERFACE_TABLE_NAME, "Loopback0"),
# peer_type == 'internal' のみ:
deps.append(("CONFIG_DB", swsscommon.CFG_LOOPBACK_INTERFACE_TABLE_NAME, "Loopback4096"))
```

**Loopback0 router-id 解決** (L184-189):
`bgp_router_id` 未設定かつ Loopback0 IPv4 取得不可の場合、`return False`（peer 確立延期）。

**Loopback4096 originator-id** (policies.conf.j2 L7):
```jinja2
{% set lo4096_ipv4 = get_ipv4_loopback_address(CONFIG_DB__LOOPBACK_INTERFACE, "Loopback4096") | ip %}
```

### 9. INTERFACE / PORTCHANNEL_INTERFACE

**deps 宣言** (L124-125):
```python
("LOCAL", "local_addresses", ""),
("LOCAL", "interfaces", ""),
```

**get_local_interface() 呼び出し** (L198-201):
`local_addr` に対応するインターフェースエントリが `LOCAL.interfaces` に未登録の場合 `return False`（自動再試行）。

### 10-12. ROUTE_MAP / BGP_PEER_GROUP

`policies.conf.j2` が生成するルートマップ（YANG leafref なし、FRR への直接 vtysh 注入）:
- `FROM_BGP_INTERNAL_PEER_V4` permit 1/2/3/100
- `FROM_BGP_INTERNAL_PEER_V6` permit 1/2/3/4/100
- `TO_BGP_INTERNAL_PEER_V4` permit 1/deny 15/permit 100
- `TO_BGP_INTERNAL_PEER_V6` permit 2/deny 15/permit 100

`peer-group.conf.j2` が生成するピアグループ（YANG leafref なし）:
- `INTERNAL_PEER_V4`, `INTERNAL_PEER_V6`

`frrcfgd.py` (L81-90): `BGP_GLOBALS`・`ROUTE_MAP`・`BGP_PEER_GROUP` はいずれも `bgpd` 宛テーブルとして登録されており、frrcfgd 経由の設定と bgpcfgd テンプレート経由の設定が同一 FRR bgpd インスタンスに並存する。

---

## SAI / APPL_DB 参照

なし。bgpcfgd / frrcfgd は CONFIG_DB → FRR（ユーザー空間）への経路であり SAI/ASIC に直接触れない。
