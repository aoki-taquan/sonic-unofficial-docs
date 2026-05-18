# DPU / ENI / VDPU / REMOTE_DPU テーブル 暗黙参照スキャン (Phase C)

`docs/reference/config-db/dpu-eni.md` の Phase C (暗黙参照) ブロック裏付け資料。

ソースは `sonic-net/sonic-swss/orchagent/dash/dashenifwdorch.h`、`dashenifwdorch.cpp`。

## スキャン手順

```
grep -nE 'gDirectory\.get|port_tbl_|vip_tbl_|findVnet|getVip|isNeighborResolved|resolveNeighbor|getAllPorts|getRouterIntfsAlias|addAclTable|deleteAclTable|createAclRule|deleteAclRule' \
    .cache/sonic-sources/sonic-swss/orchagent/dash/dashenifwdorch.cpp
grep -nE 'PortsOrch\*|NeighOrch\*|IntfsOrch\*|VNetOrch\*|VxlanTunnelOrch\*' \
    .cache/sonic-sources/sonic-swss/orchagent/dash/dashenifwdorch.h
```

## 検出された暗黙参照テーブル

### CONFIG_DB 読み取り（lazyInit 時のスナップショット読込）

`DashEniFwdOrch::lazyInit()` → `DpuRegistry::populate()` が起動後最初の ENI ADD 時に 3 テーブルをスナップショット読込する。

| テーブル | 参照タイミング | 用途 | evidence |
|---------|-------------|------|---------|
| `DPU` | lazyInit 時（1 回のみ） | LOCAL DPU の `pa_ipv4` / `state` を `DpuData{LOCAL}` として `dpus_name_map_` に登録 | `dashenifwdorch.cpp:223-266` `processDpuTable()` |
| `REMOTE_DPU` | lazyInit 時（1 回のみ） | CLUSTER DPU の `pa_ipv4` / `npu_ipv4` を `DpuData{CLUSTER}` として登録 | `dashenifwdorch.cpp:269-306` `processRemoteDpuTable()` |
| `VDPU` | lazyInit 時（1 回のみ）、DPU/REMOTE_DPU 登録後 | `main_dpu_ids` を `dpus_name_map_` に照合して `vdpus_map_` を構築。未登録 DPU ID は警告スキップ | `dashenifwdorch.cpp:308-347` `processVdpuTable()` |
| `VIP_TABLE` | CLUSTER ENI ルール生成時（lazy、1 回） | `EniFwdCtxBase::getVip()` が `keys()` でプレフィックスを取得。空なら `SWSS_LOG_THROW` で abort | `dashenifwdorch.cpp:492-517` |
| `PORT` (`port_tbl_`) | ACL テーブル作成時 | `findInternalPorts()` が `PORT_ROLE` フィールドで DPC ポートを特定・除外 | `dashenifwdorch.cpp:414-431` |

### orchagent 間参照（EniFwdCtx::initialize() で取得）

`EniFwdCtx::initialize()` (`dashenifwdorch.cpp:519-531`) が `gDirectory.get<T*>()` で参照する orchagent ポインタ群。いずれも assert で NULL チェック済み。

| Orch | 参照用途 | evidence |
|------|---------|---------|
| `NeighOrch` | Neighbor OID 解決 (`isNeighborResolved()`) + Neighbor Up/Down 通知受信 (`attach()`) | `dashenifwdorch.cpp:533-542`, `dashenifwdorch.cpp:17-21` |
| `IntfsOrch` | LOCAL DPU の `pa_ipv4` に対応するインタフェースエイリアス取得 (`getRouterIntfsAlias()`) | `dashenifwdorch.cpp:544-547` |
| `VNetOrch` | CLUSTER ENI の vnet_name から VNI (`getVni()`) とトンネル名 (`getTunnelName()`) を取得 | `dashenifwdorch.cpp:549-567` |
| `VxlanTunnelOrch` | CLUSTER ENI の redirect 先トンネル OID の解決 | `dashenifwdorch.h:393` |
| `PortsOrch` | ACL table の bind points 列挙 (`getAllPorts()`)。PHY/LAG ポートのみ採用し LAG member と DPC ロールを除外 | `dashenifwdorch.cpp:569-572`, `dashenifwdorch.cpp:433-473` |

### APPL_DB 書き込み先

| テーブル | 書き込み条件 | evidence |
|---------|------------|---------|
| `ACL_TABLE_TYPE_TABLE\|ENI_REDIRECT` | 最初の ENI ACL ルール作成時に `addAclTable()` が自動生成。matches=`DST_IP,INNER_DST_MAC,TUNNEL_TERM`、actions=`REDIRECT_ACTION` | `dashenifwdorch.cpp:603-625` |
| `ACL_TABLE_TABLE\|ENI` | `addAclTable()` 内で TABLE_TYPE=`ENI_REDIRECT`、stage=ingress として書き込み | `dashenifwdorch.cpp:636-643` |
| `ACL_RULE_TABLE\|ENI:<vnet>_<MAC>` | ENI ADD/UPDATE 時にフォワードルール + オプションで TERM ルールを生成 | `dashenifwdorch.cpp:574-583` |

## 特記事項

- **VIP_TABLE は THROW 発生源**: 他の参照（VNET 未登録・Neighbor 未解決）は PENDING で保留・自動再評価されるが、`VIP_TABLE` が空の場合のみ orchagent プロセスが `SWSS_LOG_THROW` で終了する
- **lazyInit の 1 回実行制約**: `ctx_initialized_` フラグによりスナップショット読込は 1 回のみ。起動後に CONFIG_DB の DPU/REMOTE_DPU/VDPU を変更しても orchagent 再起動なしには反映されない
