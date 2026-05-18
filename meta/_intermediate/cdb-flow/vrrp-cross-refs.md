# VRRP テーブル 暗黙参照スキャン (Phase C)

`docs/reference/config-db/vrrp.md` の Phase C (暗黙参照) ブロック裏付け資料。

ソースは `sonic-net/SONiC/doc/vrrp/sonic-vrrp.yang`、`sonic-net/sonic-utilities/config/main.py`、および VRRP HLD (`doc/vrrp/VRRP_Adaptation_HLD.md`)。

## スキャン手順

```
# YANG leafref 解析
grep -n "leafref\|path" .cache/sonic-sources/SONiC/doc/vrrp/sonic-vrrp.yang

# CLI 存在確認コード
grep -n "get_interface_table_name\|get_table\|get_entry\|ctx.fail" \
    .cache/sonic-sources/sonic-utilities/config/main.py | sed -n '6877,7080p'
```

## 検出された参照テーブル

### YANG leafref (VRRP テーブル — ifname フィールド)

`VRRP_LIST.ifname` は union leafref で以下 4 テーブルのいずれかを参照。
YANG バリデーション (`sonic-yang-mgmt` / gNMI 経路) で検証される。

| 参照先テーブル | YANG path | 条件 | evidence |
|---|---|---|---|
| `INTERFACE` (portname) | `/sonic-interface/INTERFACE/INTERFACE_LIST/portname` | `Ethernet*` インタフェース | `sonic-vrrp.yang` L65-67 |
| `PORTCHANNEL_INTERFACE` (pch_name) | `/sonic-portchannel-interface/PORTCHANNEL_INTERFACE/PORTCHANNEL_INTERFACE_LIST/pch_name` | `PortChannel*` インタフェース | `sonic-vrrp.yang` L68-70 |
| `VLAN_INTERFACE` (vlanName) | `/sonic-vlan-interface/VLAN_INTERFACE/VLAN_INTERFACE_LIST/vlanName` | `Vlan*` インタフェース | `sonic-vrrp.yang` L71-73 |
| `VLAN_SUB_INTERFACE` (id) | `/sonic-interface/VLAN_SUB_INTERFACE/VLAN_SUB_INTERFACE_LIST/id` | サブインタフェース (e.g. `Ethernet0.10`) | `sonic-vrrp.yang` L74-76 |

### YANG leafref (VRRP6 テーブル — ifname フィールド)

`VRRP6_LIST.ifname` も同一 4 テーブルを leafref 参照 (YANG L190-205)。

### YANG leafref (VRRP_TRACK テーブル)

`VRRP_TRACK_LIST` の各フィールドが参照するテーブル:

| フィールド | 参照先テーブル | YANG path | evidence |
|---|---|---|---|
| `baseifname` | `VRRP_LIST/ifname` (自テーブル内) | `../../../VRRP/VRRP_LIST/ifname` | `sonic-vrrp.yang` L144-146 |
| `idkey` | `VRRP_LIST/idkey` (自テーブル内) | `../../../VRRP/VRRP_LIST/idkey` | `sonic-vrrp.yang` L150-152 |
| `trackifname` (PORT) | `PORT/PORT_LIST/ifname` | `/sonic-port/PORT/PORT_LIST/ifname` | `sonic-vrrp.yang` L158-160 |
| `trackifname` (PortChannel) | `PORTCHANNEL/PORTCHANNEL_LIST/name` | `/sonic-portchannel/PORTCHANNEL/PORTCHANNEL_LIST/name` | `sonic-vrrp.yang` L161-163 |
| `trackifname` (VLAN) | `VLAN/VLAN_LIST/name` | `/sonic-vlan/VLAN/VLAN_LIST/name` | `sonic-vrrp.yang` L164-166 |
| `trackifname` (Sub-IF) | `VLAN_SUB_INTERFACE/VLAN_SUB_INTERFACE_LIST/id` | `/sonic-interface/VLAN_SUB_INTERFACE/…` | `sonic-vrrp.yang` L167-169 |

### YANG leafref (VRRP6_TRACK テーブル)

`VRRP6_TRACK_LIST` も同様に `VRRP6_LIST` へ baseifname/idkey leafref、trackifname は上記 4 テーブルへ leafref (YANG L263-291)。

### CLI レベルの暗黙参照 (config/main.py)

CLI による書き込み時に実行時存在チェックを行う参照。YANG バリデーションとは独立して `ctx.fail()` を発火させる。

| 参照先テーブル | 参照箇所 | 用途 | evidence |
|---|---|---|---|
| `INTERFACE` / `PORTCHANNEL_INTERFACE` / `VLAN_INTERFACE` | `get_interface_table_name()` + `get_table()` | VRRP インスタンス作成時の基底インタフェース存在確認 | `config/main.py` L6886-6890 |
| `INTERFACE` / `PORTCHANNEL_INTERFACE` / `VLAN_INTERFACE` (track base) | `get_interface_table_name()` + `get_table()` | VRRP_TRACK 追加時の基底インタフェース確認 | `config/main.py` L7000-7006 |
| `INTERFACE` / `PORTCHANNEL_INTERFACE` / `VLAN_INTERFACE` (track target) | `get_interface_table_name()` + `get_table()` | VRRP_TRACK 追加時の追跡対象インタフェース確認 | `config/main.py` L7007-7014 |
| `VRRP` (itself) | `config_db.get_entry("VRRP", ...)` | VRRP_TRACK 追加/削除前の親インスタンス存在確認 | `config/main.py` L7017-7019, L7070-7072 |

### データ流出先 (書き込み先テーブル / プロセス間参照)

`macvlanmgrd` が CONFIG_DB の VRRP / VRRP6 変更を受けて以下を書き込む:

| 書き込み先 | 内容 | 後続 Consumer |
|---|---|---|
| `APPL_DB.VRRP_TABLE` | VMAC アドレス・インタフェース状態 | `intforch` が VIP / VMAC エントリを `ASIC_DB` へ書き込む |
| Linux macvlan デバイス | カーネルレベルの仮想 MAC インタフェース | `vrrpsyncd` が状態変化を監視 |

`vrrpsyncd` → `APPL_DB.INTF_TABLE` → `intforch` → `ASIC_DB` の経路も存在する。

## 結論

VRRP / VRRP6 テーブルは YANG leafref により `INTERFACE`・`PORTCHANNEL_INTERFACE`・`VLAN_INTERFACE`・`VLAN_SUB_INTERFACE` の 4 テーブルに強い参照を持つ。VRRP_TRACK / VRRP6_TRACK はさらに親 VRRP インスタンステーブルと `PORT`・`PORTCHANNEL`・`VLAN` テーブルへの leafref を持つ。CLI レベルでは実行時の `get_table()` 存在確認が追加安全網として機能する。
