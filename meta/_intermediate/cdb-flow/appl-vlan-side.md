# appl-vlan: 副次 DB 書込（Task F Phase F）

対象ページ: `docs/reference/config-db/appl-vlan.md`
ソース: `sonic-swss/cfgmgr/vlanmgr.cpp` (sha `4305596156d70e9797e8a881b3d19b46de0bce0d`)、`sonic-swss/orchagent/portsorch.cpp` (同 sha)

本ページの対象は `APPL_DB|VLAN_TABLE` および `APPL_DB|VLAN_MEMBER_TABLE` への書込み主体である `vlanmgrd` (cfgmgr/vlanmgr.cpp) と、購読側 `portsorch` (orchagent/portsorch.cpp)。`sonic-swss/orchagent/vlanorch.cpp` は存在せず、VLAN の SAI 反映は `PortsOrch` が担う。以下は **APPL_DB SET / DEL が連鎖的に発火させる副次 DB 書込みのみ** を列挙する。

## 1. STATE_DB

`VlanMgr` コンストラクタ (vlanmgr.cpp:24-32) が `stateDb` 上に 4 つの `swss::Table` を保持:

| メンバ | テーブル名 | スキーマ定数 |
|---|---|---|
| `m_statePortTable` | `PORT_TABLE` | `STATE_PORT_TABLE_NAME` (read-only) |
| `m_stateLagTable` | `LAG_TABLE` | `STATE_LAG_TABLE_NAME` (read-only) |
| `m_stateVlanTable` | `VLAN_TABLE` | `STATE_VLAN_TABLE_NAME` |
| `m_stateVlanMemberTable` | `VLAN_MEMBER_TABLE` | `STATE_VLAN_MEMBER_TABLE_NAME` |

`STATE_PORT_TABLE` / `STATE_LAG_TABLE` は `isPortStateOk()` / `isLagStateOk()` の購読側であり vlanmgrd は書込みしない。APPL_DB 書込みに連動して **書込みが発生するのは STATE_VLAN_TABLE と STATE_VLAN_MEMBER_TABLE の 2 つのみ**。

### 1.1 `STATE_DB|VLAN_TABLE|Vlan<id>`

書き込み箇所: vlanmgr.cpp:443 (SET) / vlanmgr.cpp:463 (DEL)

```cpp
// vlanmgr.cpp:440-443  (doVlanTask SET 経路)
fvVector.clear();
FieldValueTuple s("state", "ok");
fvVector.push_back(s);
m_stateVlanTable.set(key, fvVector);
```

| トリガ | 呼出元 | フィールド |
|---|---|---|
| `doVlanTask()` SET 成功直後 (APPL_DB `VLAN_TABLE` set と同一トランザクション) | vlanmgr.cpp:437→443 | `state="ok"` |
| `doVlanTask()` DEL 成功直後 | vlanmgr.cpp:462→463 | (エントリ削除) |

フィールドは `state` のみ。値は固定文字列 `"ok"`。失敗時の異常値書込みは存在しない（VLAN 作成失敗の `addHostVlan()` 経路は APPL_DB 書込みも行わないため STATE_DB へも書かれない）。

### 1.2 `STATE_DB|VLAN_MEMBER_TABLE|Vlan<id>|<port_alias>`

書込み箇所は **3 経路**:

| 経路 | SET | DEL | フィールド |
|---|---|---|---|
| `doVlanMemberTask()` (通常 `VLAN_MEMBER` 経路) | vlanmgr.cpp:677 | vlanmgr.cpp:698 | `state="ok"` |
| `addPortToVlan()` (CONFIG_DB `VLAN.members@` 経由の minigraph 互換経路) | vlanmgr.cpp:950 | vlanmgr.cpp:973 (`removePortFromVlan`) | `state="ok"` |
| `doVlanPacVlanMemberTask()` (PAC 制御経路) | vlanmgr.cpp:894 | vlanmgr.cpp:907 | `state="ok"` |

```cpp
// vlanmgr.cpp:674-677  (doVlanMemberTask SET 経路)
vector<FieldValueTuple> fvVector;
FieldValueTuple s("state", "ok");
fvVector.push_back(s);
m_stateVlanMemberTable.set(kfvKey(t), fvVector);
```

PAC 経路 (`doVlanPacVlanMemberTask`) の SET (vlanmgr.cpp:894) は `fvVector1` を作成しつつ実際には APPL_DB 用の `fvVector` を流用しており、`state="ok"` だけでなく `dynamic="yes"` を含む field が STATE_DB にも書かれるバグ的挙動が見える。本ページ範囲では `state` のみが意味を持つ。

`addPortToVlan()` の SET は内部で `kfvKey(t)` の `:` 区切りを `|` 区切りに直して書き込む (vlanmgr.cpp:947-950) ため、STATE_DB key は常に `Vlan<id>|<port_alias>` 形式に統一される。

### 1.3 状態遷移意味論

- `STATE_VLAN_TABLE` / `STATE_VLAN_MEMBER_TABLE` は **vlanmgrd 内部の冪等チェック専用**: `isVlanStateOk()` (vlanmgr.cpp:521-523) / `isVlanMemberStateOk()` (vlanmgr.cpp:535-537) で「ホスト netdev (`Vlan<N>` / bridge member) が作成済みか」を判定する。`state` フィールドは `"ok"` 固定で、それ以外の値は書かれない。
- `portsorch` (orchagent) は **これらの STATE_DB エントリを購読しない**。orchagent 側は APPL_DB `VLAN_TABLE` / `VLAN_MEMBER_TABLE` を `ConsumerStateTable` で直接購読する。
- 他プロセス (`teamd`、`fdbsyncd` 等) も `STATE_VLAN_TABLE` を購読し、bridge 上の VLAN が利用可能になったタイミングを検知する用途で参照する（参照のみ・本ページ範囲では書込みは vlanmgrd 単独）。

## 2. COUNTERS_DB

APPL_DB `VLAN_TABLE` / `VLAN_MEMBER_TABLE` SET / DEL に連動する **COUNTERS_DB への書込みは存在しない**。

確認内容:

- `vlanmgr.cpp` 内に `COUNTERS_DB` の `DBConnector` 生成・参照は一切なし（grep 結果ゼロ）。
- `portsorch.cpp` は `m_counter_db` (COUNTERS_DB) を保持するが、その用途は `COUNTERS_PORT_NAME_MAP` / `COUNTERS_QUEUE_NAME_MAP` / `COUNTERS_PG_NAME_MAP` 等 **物理ポート単位** の counter 名マップに限定される (portsorch.cpp:758-785)。`VLAN_TABLE` 受信時の `addVlan()` / `addVlanMember()` 経路では COUNTERS_DB を書込まない。
- SAI 上は `SAI_VLAN_STAT_*` (in/out octets/packets) が定義されるが、SONiC master の portsorch は VLAN 単位 stat の COUNTERS_DB 公開を実装していない（`COUNTERS_VLAN_NAME_MAP` の参照ゼロ）。

## 3. FLEX_COUNTER_DB

APPL_DB `VLAN_TABLE` / `VLAN_MEMBER_TABLE` SET / DEL に連動する **FLEX_COUNTER_DB への書込みは存在しない**。

確認内容:

- `portsorch.cpp` の `FlexCounterManager` インスタンス (`port_stat_manager` / `port_phy_attr_manager` / `queue_stat_manager` 等、portsorch.cpp:727-739) はいずれも **物理ポート / queue / priority-group** スコープであり、VLAN 単位の `FlexCounterManager` は存在しない。
- VLAN ポートに紐づく flex_counter 書込みは `addVlan()` / `addVlanMember()` 内では発火せず、`initializePort()` 等の物理ポート初期化経路で行われる。これは APPL_DB `VLAN_TABLE` SET の副次効果ではなく、`APPL_DB|PORT_TABLE` 経路の副次効果なので本ページ範囲外。

## 4. 書込み元プロセス別 副次効果

| 書込み元 (APPL_DB) | STATE_DB | COUNTERS_DB | FLEX_COUNTER_DB | 備考 |
|---|---|---|---|---|
| `vlanmgrd` (`doVlanTask` SET/DEL) | `VLAN_TABLE\|Vlan<id>` に `state=ok` set/del | — | — | 唯一の VLAN 副次書込み元 |
| `vlanmgrd` (`doVlanMemberTask` SET/DEL) | `VLAN_MEMBER_TABLE\|Vlan<id>\|<port>` に `state=ok` set/del | — | — | 通常 CONFIG_DB `VLAN_MEMBER` 経路 |
| `vlanmgrd` (`addPortToVlan` / `removePortFromVlan`) | 同上 | — | — | minigraph `VLAN.members@` 経由 |
| `vlanmgrd` (`doVlanPacVlanMemberTask`) | 同上 + `dynamic=yes` 混入 | — | — | PAC 制御経路。state vector への `dynamic` 混入は実装の cleanup バグ気味 |
| `portsorch` (APPL_DB 購読側) | — | — | — | SAI 反映のみで副次 DB 書込みなし |

## 5. evidence サマリ

| DB | テーブル | 発火点 |
|---|---|---|
| STATE_DB | `VLAN_TABLE\|Vlan<id>` | vlanmgr.cpp:443 (SET) / 463 (DEL) |
| STATE_DB | `VLAN_MEMBER_TABLE\|Vlan<id>\|<port>` | vlanmgr.cpp:677 / 698 (doVlanMemberTask), 894 / 907 (PAC), 950 / 973 (members@) |
| COUNTERS_DB | (該当なし) | — |
| FLEX_COUNTER_DB | (該当なし) | — |

## 結論

`APPL_DB|VLAN_TABLE` / `APPL_DB|VLAN_MEMBER_TABLE` の SET / DEL は、`STATE_DB` 上の対応エントリ (`STATE_VLAN_TABLE` / `STATE_VLAN_MEMBER_TABLE`、いずれも `state="ok"` 固定 1 フィールド) を **同一トランザクションで** 書込む。COUNTERS_DB / FLEX_COUNTER_DB への副次書込みは存在しない（SAI VLAN counter は master 未実装）。
