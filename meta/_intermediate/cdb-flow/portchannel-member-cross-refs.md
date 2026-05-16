# PORTCHANNEL_MEMBER — Phase C 暗黙参照マップ 調査メモ

## 調査目的

PORTCHANNEL_MEMBER が持つ「leafref 以外の暗黙参照」を網羅的に列挙する。
Phase C: `<!-- cross-refs -->` セクション用。

## 1. YANG leafref による明示的依存 (参考・再掲)

`sonic-portchannel.yang` の `PORTCHANNEL_MEMBER_LIST` は 2 つの leafref を持つ:

- `name` → `sonic-portchannel/PORTCHANNEL/PORTCHANNEL_LIST/name`
- `port` → `sonic-port/PORT/PORT_LIST/name`

これらは config-load / `sonic-cfggen` 適用時に YANG バリデーションで強制される明示依存。  
evidence: `sonic-portchannel.yang:140-153`

## 2. YANG `must` 制約による他テーブルへの暗黙依存

### sonic-vlan.yang — VLAN_MEMBER に対する must 制約

`VLAN_MEMBER_LIST.port` の must 制約として:

```yang
must "not(/lag:sonic-portchannel/lag:PORTCHANNEL_MEMBER/lag:PORTCHANNEL_MEMBER_LIST[lag:port=current()]/lag:name)"
{
    error-message "Port is a member of a port channel.";
}
```

- **含意**: あるポートが `PORTCHANNEL_MEMBER` に存在する間は、同一ポートを `VLAN_MEMBER` に追加できない。
- **方向**: `VLAN_MEMBER` → `PORTCHANNEL_MEMBER` (YANG schema レベルの相互排他)
- evidence: `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-vlan.yang:302-304`

## 3. orchagent portsorch — `m_port_ref_count` 機構

`portsorch.cpp` は `m_port_ref_count[port_alias]` を増減させる仕組みを持つ。

### PORTCHANNEL_MEMBER 追加・削除時

| 操作 | 行 | 効果 |
|---|---|---|
| PORTCHANNEL_MEMBER SET → `addLagMember()` 成功 | `portsorch.cpp:8205` | `increasePortRefCount(port.m_alias)` |
| PORTCHANNEL_MEMBER DEL → `removeLagMember()` 成功 | `portsorch.cpp:8253` | `decreasePortRefCount(port.m_alias)` |

`m_port_ref_count` が 0 でない PORT は `removePort()` で拒否される (`portsorch.cpp:5649`)。  
つまり **PORTCHANNEL_MEMBER エントリが存在する間は、対応する PORT を CONFIG_DB から DEL できない**。

evidence: `sonic-swss/orchagent/portsorch.cpp:8205,8253,5649`

### LAG (PORTCHANNEL) 自体の ref_count も管理

| 操作 | 行 | 効果 |
|---|---|---|
| `addLag()` (PORTCHANNEL SET) | `portsorch.cpp:8012` | `m_port_ref_count[lag_alias] = 0` で初期化 |
| `removeLag()` (PORTCHANNEL DEL) 前チェック | `portsorch.cpp:8049` | `m_port_ref_count[lag.m_alias] > 0` の場合 DEL 拒否 |

evidence: `sonic-swss/orchagent/portsorch.cpp:8012,8049`

## 4. teammgrd — DEVICE_METADATA|localhost|mac への暗黙依存

`teammgr.cpp` は起動時に `DEVICE_METADATA|localhost|mac` を読み取り、PortChannel の switch MAC に使用する。  
`mac` が未設定だと `teammgrd` が起動失敗するため、PORTCHANNEL_MEMBER の適用も不可能になる。

evidence: `sonic-swss/cfgmgr/teammgr.cpp:31,54-57`

## 5. teammgrd — STATE_LAG_TABLE / STATE_PORT_TABLE への runtime ゲート依存

`TeamMgr::doLagMemberTask()` は以下の State DB を runtime ゲートとして参照する:

| State DB テーブル | チェック内容 | 効果 |
|---|---|---|
| `STATE_LAG_TABLE` | `isLagStateOk(lag_name)` | LAG が teamd に登録されるまで PORTCHANNEL_MEMBER の適用を保留 |
| `STATE_PORT_TABLE` | port が `state=ok` で存在するか | PORT ready まで enslave 保留 |

evidence: `sonic-swss/cfgmgr/teammgr.cpp:89-102, 357`

## 6. MACsec — STATE_MACSEC_INGRESS_SA_TABLE への runtime ゲート依存

MACsec が設定されたポートの場合、`isMACsecIngressSAOk()` が STATE_DB `STATE_MACSEC_INGRESS_SA_TABLE` を参照し、Ingress SA ready になるまで enslave を保留する。

evidence: `sonic-swss/cfgmgr/teammgr.cpp:362-366`

## 7. multi_asic — LAG member 経由でポートの ASIC 帰属を判定

`sonic_py_common/multi_asic.py` の `is_port_channel_internal()` / バックエンド LAG 判定で `PORTCHANNEL_MEMBER` を参照し、ポートの internal/backend 区別を行う。

evidence: `sonic-buildimage/src/sonic-py-common/sonic_py_common/multi_asic.py:410,435`

## 8. sonic-utilities — config vlan / switchport での参照

### config vlan member add (`config/vlan.py:379`)

```python
portchannel_member_table = db.cfgdb.get_table('PORTCHANNEL_MEMBER')
if clicommon.interface_is_in_portchannel(portchannel_member_table, port):
    ctx.fail("{} is part of portchannel!".format(port))
```

- **含意**: ポートが `PORTCHANNEL_MEMBER` に存在する場合、`config vlan member add` を拒否する (CLI レベルの相互排他)

evidence: `sonic-utilities/config/vlan.py:379-382`

### config switchport mode (`config/switchport.py:44-47`)

```python
portchannel_member_table = db.cfgdb.get_table('PORTCHANNEL_MEMBER')
if clicommon.interface_is_in_portchannel(portchannel_member_table, port):
    ctx.fail("{} is part of portchannel!".format(port))
```

- **含意**: ポートが `PORTCHANNEL_MEMBER` に存在する場合、switchport mode 変更を拒否する

evidence: `sonic-utilities/config/switchport.py:44-47`

### config stp (`config/stp.py:331`)

STP がポートの LAG メンバー判定に `PORTCHANNEL_MEMBER` テーブルを参照する。

evidence: `sonic-utilities/config/stp.py:331`

## 9. show interfaces portchannel での参照

`show/interfaces/__init__.py:1141,1173` が `PORTCHANNEL_MEMBER` テーブルを読み取り、ポートチャネルメンバーシップ表示に使用する。

evidence: `sonic-utilities/show/interfaces/__init__.py:1141,1173`

## 10. 暗黙参照マップ サマリー

### PORTCHANNEL_MEMBER が「参照している」テーブル/リソース (下流依存)

| 対象 | 参照機構 | 効果 |
|---|---|---|
| `PORTCHANNEL` (`PORTCHANNEL_LIST.name`) | YANG leafref | 参照先なければ reject |
| `PORT` (`PORT_LIST.name`) | YANG leafref | 参照先なければ reject |
| `STATE_LAG_TABLE` | runtime ゲート (teammgrd) | LAG ready まで SET 保留 |
| `STATE_PORT_TABLE` | runtime ゲート (teammgrd) | PORT ready まで SET 保留 |
| `STATE_MACSEC_INGRESS_SA_TABLE` | runtime ゲート (teammgrd, MACsec 時) | SA ready まで enslave 保留 |
| `DEVICE_METADATA|localhost|mac` | 起動時読み取り (teammgrd) | PortChannel MAC 設定; 欠如で起動失敗 |

### PORTCHANNEL_MEMBER を「参照している」テーブル/コンポーネント (上流制約)

| 参照元 | 参照機構 | 効果 |
|---|---|---|
| `VLAN_MEMBER` | YANG `must` 制約 | 同一ポートの VLAN_MEMBER 追加を禁止 |
| `config vlan member add` (CLI) | Python get_table | ポートが PORTCHANNEL_MEMBER 在籍時は拒否 |
| `config switchport mode` (CLI) | Python get_table | ポートが PORTCHANNEL_MEMBER 在籍時は拒否 |
| `config stp` (CLI) | Python get_table | LAG メンバー判定に使用 |
| `multi_asic` (sonic-py-common) | Python get_keys | LAG の internal/backend 属性伝播 |
| `PORT` DEL guard | `m_port_ref_count` (portsorch) | PORTCHANNEL_MEMBER 在籍中は PORT DEL 不可 |
| `show interfaces portchannel` | Python get_table | メンバー表示 |
