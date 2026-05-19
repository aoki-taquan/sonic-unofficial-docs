---
title: EVPN DIP トンネル (動的生成)
description: "EVPN DIP トンネル — BGP EVPN でリモート VTEP を学習した際に orchagent が動的生成する per-remote-VTEP P2P トンネルのコード由来デフォルトと暗黙挙動を解説する。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-14
sources:
  - repo: sonic-net/sonic-swss
    path: orchagent/vxlanorch.cpp
    ref: master
  - repo: sonic-net/sonic-swss
    path: orchagent/vxlanorch.h
    ref: master
related:
  config_db:
    - VXLAN_TUNNEL
    - VXLAN_EVPN_NVO
    - VXLAN_TUNNEL_MAP
  cli:
    - config vxlan
  yang:
    - sonic-vxlan
---

# EVPN DIP トンネル (動的生成)

## 概要

[CONFIG_DB](../../reference/glossary.md#term-config_db) に `VXLAN_EVPN_TUNNEL` テーブルは存在しない。
本ページで扱う **EVPN DIP トンネル** は、`orchagent` の `VxlanTunnel::createDynamicDIPTunnel()` が
[BGP](../../reference/glossary.md#term-bgp) [EVPN](../../reference/glossary.md#term-evpn) でリモート
[VTEP](../../reference/glossary.md#term-vtep) を学習した際に**ランタイムで動的生成**する
per-remote-VTEP P2P トンネルである[^1]。

- トンネル名: `EVPN_<remote_vtep_ip>` (prefix `EVPN_TUNNEL_NAME_PREFIX`)
- トンネルポート名: `Port_EVPN_<remote_vtep_ip>` (prefix `EVPN_TUNNEL_PORT_PREFIX`)
- 生成元: `vxlanorch.cpp:1160` — `new VxlanTunnel(tunnel_name, src_ip_, dipaddr, TNL_CREATION_SRC_EVPN)`

この動的トンネルは `VXLAN_TUNNEL` [CONFIG_DB](../../reference/glossary.md#term-config_db) テーブルの
CLI 生成エントリ (`TNL_CREATION_SRC_CLI`) とは別物であり、オペレータが直接設定する対象ではない。
[VXLAN_EVPN_NVO](vxlan-evpn-nvo.md) を通じて有効化された EVPN コントロールプレーンが自動管理する。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  BGP["bgpd / FRR<br/>(EVPN type-2/3)"]
  FPMSYNCD["fpmsyncd"]
  APPDB[("APP_DB<br/>EVPN_REMOTE_VNI_TABLE")]
  BGP --> FPMSYNCD
  FPMSYNCD --> APPDB
  APPDB --> ORCH["orchagent<br/>EvpnRemoteVniOrch"]
  ORCH --> SAI["SAI<br/>sai_tunnel_api (P2P)"]
```

!!! note "凡例"
    CONFIG_DB 由来ではなく APP_DB 経由の動的生成フロー。`VXLAN_TUNNEL` (CONFIG_DB) で定義した
    VTEP が先に有効化されている前提で動作する。
<!-- /cdb-mermaid -->

## トンネル識別

| 属性 | 値 | 根拠 |
|------|----|------|
| 名前プレフィックス | `EVPN_` | `vxlanorch.h:43` `EVPN_TUNNEL_NAME_PREFIX` |
| ポートプレフィックス | `Port_EVPN_` | `vxlanorch.h:42` `EVPN_TUNNEL_PORT_PREFIX` |
| 生成元種別 | `TNL_CREATION_SRC_EVPN` | `vxlanorch.h:54` |
| STATE_DB `tnl_src` | `"EVPN"` | `vxlanorch.cpp:1939` |

## 購読者

- `orchagent` `EvpnRemoteVniOrch` / `EvpnRemoteVnip2pOrch`: `EVPN_REMOTE_VNI_TABLE` (APP_DB) を
  購読し DIP トンネルを生成
- `EvpnNvoOrch`: EVPN VTEP ポインタを管理し `getEVPNVtep()` で参照提供

<!-- defaults -->
## コード由来の暗黙デフォルト (Phase A)

| 属性 / 挙動 | デフォルト / 実挙動 | 分類 | 根拠 |
|------------|-------------------|------|------|
| `decap_ttl_mode` | `VxlanTunnelTTLMode::NOT_SET` → `SAI_TUNNEL_ATTR_DECAP_TTL_MODE` を SAI に渡さない → プラットフォーム依存 | プラットフォーム依存 silent default | `vxlanorch.h:152` (デフォルト引数), `vxlanorch.cpp:1160`, `vxlanorch.cpp:372-383` |
| `peer_mode` | 常に `SAI_TUNNEL_PEER_MODE_P2P` (`TNL_CREATION_SRC_EVPN` ハードコード) | ハードコード | `vxlanorch.cpp:903`, `vxlanorch.cpp:356-363` |
| `mapper_list` | VLAN + VRF のみ (BRIDGE なし) + `TUNNEL_MAP_USE_COMMON_ENCAP_DECAP` | ハードコード | `vxlanorch.cpp:1167-1169` |
| `with_term` | `false` (SAI tunnel termination を生成しない) | ハードコード | `vxlanorch.cpp:1169` |
| `tagging_mode` | `"untagged"` (VLAN flood domain 参加時) | ハードコード | `vxlanorch.cpp:2525-2527`, `vxlanorch.cpp:2685-2687` |
| `operstatus` 初期値 | `"down"` (STATE_DB 初期登録時) | ハードコード初期値 | `vxlanorch.cpp:1942` |
| EVPN VTEP 不在時 | `addTunnelUser()` が `false` を返しサイレント失敗。キュー残留なし | dead-consumer / silent drop | `vxlanorch.cpp:1685-1692` |
| VTEP 未 active 時 | `SWSS_LOG_WARN("VTEP not yet active")` で `false` 返却。リトライは呼び出し元依存 | dead-consumer / silent drop | `vxlanorch.cpp:1694-1699` |

### `decap_ttl_mode` の詳細

EVPN DIP トンネルの `VxlanTunnel` コンストラクタ呼び出し (`vxlanorch.cpp:1160`) は
`ttl_mode` 引数を省略するため、ヘッダで定義されたデフォルト値 `VxlanTunnelTTLMode::NOT_SET`
が適用される。`createTunnelHw()` 内の `create_tunnel()` では `NOT_SET` の場合は
`SAI_TUNNEL_ATTR_DECAP_TTL_MODE` を属性リストに追加しない。結果として SAI プラットフォーム
実装のデフォルト TTL モードが適用される（通常は `PIPE` または `UNIFORM` だがプラットフォーム依存）。

### `tagging_mode` の設計上の注記

コード内に明示的なコメント `// NOTE: does 'untagged' make the most sense here?` が 2 箇所存在
(`vxlanorch.cpp:2525`, `vxlanorch.cpp:2685`)。実装者が `"untagged"` の妥当性に迷いを示しているが、
実装はハードコードされており設定変更手段はない。

<!-- /defaults -->

<!-- ordering -->
## 書込み順依存 (Phase B)

EVPN DIP トンネルは CONFIG_DB の直接エントリを持たないが、APP_DB 経由の動的生成フローにおいて
複数の「先行条件が満たされなければ処理が進まない」強制順序依存が存在する。

### 検出された順序依存

| # | 先行条件 | 後続操作 | 強制度 | 根拠 |
|---|----------|----------|--------|------|
| 1 | `VXLAN_EVPN_NVO` 処理済み (`getEVPNVtep()` 非 NULL) | DIP トンネル生成 | **強制先行** | `vxlanorch.cpp:1685-1692` |
| 2 | `VXLAN_TUNNEL` (VTEP) が active (`isActive()` = true) | DIP トンネル生成 | **強制先行** | `vxlanorch.cpp:1694-1699` |
| 3 | `VXLAN_TUNNEL_MAP` でローカル VNI-VLAN マップが存在 | `EVPN_REMOTE_VNI_TABLE` 処理 | **強制先行** | `vxlanorch.cpp:2490-2494` |
| 4 | 対象 VLAN が存在 (`getVlanByVlanId()` 成功) | `EVPN_REMOTE_VNI_TABLE` 処理 | **強制先行** | `vxlanorch.cpp:2483-2487` |
| 5 | 全 DIP トンネルの参照カウント = 0 (`del_tnl_hw_pending` = false) | `VXLAN_EVPN_NVO` 削除 | **強制先行** | `vxlanorch.cpp:2803-2807` |

### 主要な制約詳細

**EVPN VTEP 未設定 / 未 active の場合の silent drop (依存 #1, #2)**:
`VxlanTunnelOrch::addTunnelUser()` は冒頭で `evpn_orch->getEVPNVtep()` を呼ぶ。
VTEP ポインタが NULL の場合（`VXLAN_EVPN_NVO` 未設定）は `SWSS_LOG_WARN("Unable to find EVPN VTEP")` を
出力して即 `false` を返す。VTEP ポインタが非 NULL でも `isActive()` が false の場合は
`SWSS_LOG_WARN("VTEP not yet active")` を出力して `false` を返す。
どちらの場合もリクエストは **再エンキューされない**。再試行は上位呼び出し元（`EvpnRemoteVnip2pOrch::addOperation()`
が `return false` を返した場合に orchagent のイベントループが次の消費サイクルで再処理する）
に依存する（`vxlanorch.cpp:1687-1699`）。

**VXLAN_TUNNEL_MAP が先に必要 (依存 #3)**:
`EvpnRemoteVnip2pOrch::addOperation()` は
`vxlan_tun_map_orch->isVniVlanMapExists(vni_id, ...)` を呼び、ローカル VNI マップが
存在しない場合は `SWSS_LOG_WARN("Vxlan tunnel map is not created for vni:%d")` を出力し
`return false` で処理を中断する。`VXLAN_TUNNEL_MAP` で VNI-VLAN ペアを事前登録してから
BGP EVPN がリモート VTEP を学習する順序が必要
（`vxlanorch.cpp:2489-2494`、コメント `"Remote end point can be added only after local VLAN to VNI map gets created"`）。

**NVO 削除が DIP トンネル完全削除まで待機 (依存 #5)**:
`EvpnNvoOrch::delOperation()` は `source_vtep_ptr->del_tnl_hw_pending` が true の場合に
`SWSS_LOG_WARN("NVO not deleted as hw delete is pending")` を出力して `return false` を返す。
`del_tnl_hw_pending` は DIP トンネルが HW 削除ペンディング状態の間 true を保持し、
`deletePendingSIPTunnel()` が全 DIP トンネルの参照カウント = 0 を確認してから `false` に戻す。
`config vxlan evpn_nvo del` を実行しても、既存リモート VTEP への DIP トンネルが残存していると
CONFIG_DB 削除が SAI に反映されない（`vxlanorch.cpp:2803-2807`, `vxlanorch.cpp:952-964`）。

<!-- /ordering -->

<!-- cross-refs -->
## 暗黙参照 (Phase C)

EVPN DIP トンネルは CONFIG_DB に直接テーブルを持たないため YANG `leafref` 制約は存在しない。
しかし DIP トンネルを生成・VLAN flood domain に参加させるまでの処理チェーンに複数の暗黙参照が存在する。

### YANG leafref (sonic-vxlan.yang)

`VXLAN_EVPN_TUNNEL` テーブル自体は YANG モデル化されていない。関連テーブルの leafref は以下の 2 点のみ:

| テーブル | フィールド | leafref 先 | 根拠 |
|---------|-----------|-----------|------|
| `VXLAN_EVPN_NVO` | `source_vtep` | `VXLAN_TUNNEL_LIST/name` | `sonic-vxlan.yang:123-124` |
| `VXLAN_TUNNEL_MAP` | `name` | `VXLAN_TUNNEL_LIST/name` | `sonic-vxlan.yang:75-76` |

VLAN への leafref (`VXLAN_TUNNEL_MAP.name → VLAN.name`) はコメントアウトされており未実施 (`sonic-vxlan.yang:89-90`)。

### 暗黙参照テーブル一覧

| # | 参照先 | 方向 | 強制度 | 意味 | 根拠 |
|---|--------|------|--------|------|------|
| 1 | `CONFIG_DB VXLAN_EVPN_NVO` | 読み取り (EvpnNvoOrch::getEVPNVtep()) | **必須** (NULL → silent drop) | EVPN VTEP ポインタが NULL の場合 `addTunnelUser()` は即 `false` を返しトンネル生成をスキップ | `vxlanorch.cpp:1685-1692` |
| 2 | `CONFIG_DB VXLAN_TUNNEL` | 読み取り (VxlanTunnel::isActive()) | **必須** (false → silent drop) | VTEP ポインタが非 NULL でも `isActive()` が false の場合 `addTunnelUser()` は `false` を返す | `vxlanorch.cpp:1694-1699` |
| 3 | `CONFIG_DB VXLAN_TUNNEL_MAP` | 読み取り (isVniVlanMapExists()) | **必須** (未存在 → return false) | `EvpnRemoteVnip2pOrch::addOperation()` で VNI-VLAN マップ未存在なら処理中断。コード注記: `"Remote end point can be added only after local VLAN to VNI map gets created"` | `vxlanorch.cpp:2490-2494` |
| 4 | `CONFIG_DB VLAN` (PortsOrch) | 読み取り (getVlanByVlanId()) | **必須** (未存在 → return false) | VLAN が PortsOrch に未登録の場合 `addOperation()` は処理を中断。DIP トンネルポートを VLAN flood domain へ参加させる前提 | `vxlanorch.cpp:2483-2487` |
| 5 | `APP_DB EVPN_REMOTE_VNI_TABLE` | 読み取り (EvpnRemoteVnip2pOrch subscribe) | 起動トリガ | BGP EVPN が学習したリモート VTEP を fpmsyncd が書き込み、`EvpnRemoteVnip2pOrch` が購読して DIP トンネル生成を開始 | `vxlanorch.cpp:2447-2520` |
| 6 | `STATE_DB VXLAN_TUNNEL_TABLE` | 書き込み (m_stateVxlanTable.set()) | 書き込み先 | DIP トンネル生成後に `src_ip`, `dst_ip`, `tnl_src="EVPN"`, `operstatus` を書き込む。削除時は del | `vxlanorch.cpp:1910`, `1928-1953` |

### 参照グラフ

```
fpmsyncd (BGP EVPN type-2/3)
  └─→ APP_DB EVPN_REMOTE_VNI_TABLE
        └─→ EvpnRemoteVnip2pOrch::addOperation()
              ├─[必須] CONFIG_DB VXLAN_EVPN_NVO  ─→ getEVPNVtep() ── NULL → skip
              ├─[必須] CONFIG_DB VXLAN_TUNNEL     ─→ isActive()    ── false → skip
              ├─[必須] CONFIG_DB VXLAN_TUNNEL_MAP ─→ isVniVlanMapExists() ── 未存在 → return false
              ├─[必須] CONFIG_DB VLAN             ─→ getVlanByVlanId()     ── 未存在 → return false
              └─→ addTunnelUser() ─→ createDynamicDIPTunnel()
                    └─→ STATE_DB VXLAN_TUNNEL_TABLE (tnl_src="EVPN", operstatus="down"→"up")
```

詳細解析: `meta/_intermediate/cdb-flow/vxlan-evpn-tunnel-cross-refs.md`

<!-- evidence: vxlanorch.cpp:1685-1699 (addTunnelUser VTEP ガード); vxlanorch.cpp:2483-2494 (VLAN + VNI-VLAN マップ確認); vxlanorch.cpp:2516 (addTunnelUser 呼び出し); vxlanorch.cpp:1910,1928-1953 (STATE_DB 書き込み); sonic-vxlan.yang:75-76,89-90,123-124 (leafref) -->
<!-- /cross-refs -->

<!-- failure -->
## 失敗挙動 (Phase D)

EVPN DIP トンネルは CONFIG_DB エントリを持たず、`APP_DB EVPN_REMOTE_VNI_TABLE` への書き込みを
`EvpnRemoteVnip2pOrch` が処理する形で動的に生成される。失敗経路は大別して
「SET 処理（生成）側」と「DEL 処理（削除）側」で return 値の扱いが異なる。

### SET 処理 (addTunnelUser → createDynamicDIPTunnel) における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `getEVPNVtep()` が nullptr（VXLAN_EVPN_NVO 未設定） | `VxlanTunnelOrch::addTunnelUser()` | `return false` — orchagent タスクキューに残留してリトライ | SWSS_LOG_WARN `"Unable to find EVPN VTEP. user=%d remote_vtep=%s"` | `vxlanorch.cpp:1689` |
| VTEP が存在するが `isActive()` が false | `VxlanTunnelOrch::addTunnelUser()` | `return false` — タスクキューに残留してリトライ | SWSS_LOG_WARN `"VTEP not yet active.user=%d remote_vtep=%s"` | `vxlanorch.cpp:1696` |
| `isDipTunnelsSupported()` が false（プラットフォーム非対応） | `VxlanTunnelOrch::addTunnelUser()` | DIP トンネル作成をスキップし `return true`。`updateRemoteEndPointIpRef()` で IP 参照カウントのみ更新（縮退動作） | （ログなし） | `vxlanorch.cpp:1701-1704` |
| VLAN が PortsOrch 未登録（`getVlanByVlanId()` 失敗） | `EvpnRemoteVniOrch::addOperation()` | `return false` — タスクキューに残留してリトライ | SWSS_LOG_WARN `"Vxlan tunnel map vlan id doesn't exist: %d"` | `vxlanorch.cpp:2483-2487` |
| VNI-VLAN マップ未存在（`isVniVlanMapExists()` 失敗） | `EvpnRemoteVniOrch::addOperation()` | `return false` — タスクキューに残留してリトライ | SWSS_LOG_WARN `"Vxlan tunnel map is not created for vni:%d"` | `vxlanorch.cpp:2491-2494` |
| L3 VNI として登録済みの VNI に対する Remote VNI add | `EvpnRemoteVniOrch::addOperation()` | `return false`（再試行なし扱い） | SWSS_LOG_WARN `"Ignoring remote VNI add for L3 VNI:%d, remote:%s"` | `vxlanorch.cpp:2499` |
| `getTunnelPort()` 失敗（addTunnelUser 後にポート未生成） | `EvpnRemoteVniOrch::addOperation()` | `return false` — タスクキューに残留してリトライ | SWSS_LOG_WARN `"Vxlan tunnelPort doesn't exist: %s"` | `vxlanorch.cpp:2520` |
| トンネルポートがすでに VLAN メンバ（重複 add） | `EvpnRemoteVniOrch::addOperation()` | `return true`（スキップ）。`increment_spurious_imr_add()` でカウンタ更新のみ | SWSS_LOG_WARN `"tunnelPort %s already member of vid %d"` | `vxlanorch.cpp:2513` |

### DEL 処理 (deleteDynamicDIPTunnel / RemoteVniDel) における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| 参照カウント > 0 の DIP が残存する間の削除要求（`del_tnl_hw_pending`） | `VxlanTunnel::deleteDynamicDIPTunnel()` | `return true`（削除スキップ・HW ペンディング維持）。FDB 参照カウントが 0 になるまでポートを保持 | SWSS_LOG_NOTICE `"DIP = %s Not deleting tunnel from HW as tunnelPort is not yet deleted. fdbcount = %d"` | `vxlanorch.cpp:1213` |
| DIP トンネルオブジェクトが nullptr（`getVxlanTunnel()` 失敗） | `VxlanTunnel::deleteDynamicDIPTunnel()` | `return false`（異常扱い） | SWSS_LOG_INFO `"DIP Tunnel is NULL unexpected"` | `vxlanorch.cpp:1222` |
| `tnl_users_` マップに対象 DIP エントリが存在しない | `VxlanTunnel::deleteDynamicDIPTunnel()` | WARN ログを出力して `return true`（no-op） | SWSS_LOG_WARN `"Unable to find dynamic tunnel for deletion"` | `vxlanorch.cpp:1235` |
| Remote VNI DEL 時に `getTunnelPort()` 失敗 | `EvpnRemoteVniOrch::delOperation()` | `return true`（スキップ・再試行なし） | SWSS_LOG_WARN `"RemoteVniDel getTunnelPort Fails: %s"` | `vxlanorch.cpp:2567` |
| Remote VNI DEL 時に `getEVPNVtep()` が nullptr | `EvpnRemoteVniOrch::delOperation()` | `return true`（スキップ・再試行なし） | SWSS_LOG_WARN `"Remote VNI del: VTEP not found. remote=%s vid=%d"` | `vxlanorch.cpp:2575` |
| トンネルポートが VLAN の非メンバ状態での DEL（spurious del） | `EvpnRemoteVniOrch::delOperation()` | `return true`（スキップ）。`increment_spurious_imr_del()` でカウンタ更新のみ | SWSS_LOG_WARN `"marking it as spurious tunnelPort %s not a member of vid %d"` | `vxlanorch.cpp:2582` |
| `removeVlanMember()` 失敗 | `EvpnRemoteVniOrch::delOperation()` | `return true`（スキップ・再試行なし） | SWSS_LOG_WARN `"RemoteVniDel remove vlan member fails: %s"` | `vxlanorch.cpp:2593` |
| IP 参照カウントのデクリメント対象エントリが未存在 | `VxlanTunnel::updateRemoteEndPointIpRef()` | no-op（カウンタ不整合の可能性） | SWSS_LOG_ERROR `"Cannot decrement ref. End point not referenced %s"` | `vxlanorch.cpp:1133` |

### retry 挙動まとめ

| シナリオ | return 値 | retry 挙動 |
|---|---|---|
| EVPN VTEP 未登録 / 非 active での DIP トンネル生成要求 | `false` | orchagent タスクキューで自動リトライ（VTEP active 化で解消） |
| VLAN 未存在 / VNI-VLAN マップ未存在 での Remote VNI add | `false` | orchagent タスクキューで自動リトライ（VLAN / TUNNEL_MAP 設定後に解消） |
| tunnelPort 生成待ち (addTunnelUser 後の getPort 失敗) | `false` | タスクキューでリトライ |
| DIP トンネル参照カウント > 0 での HW 削除スキップ | `true` | **リトライなし**。FDB カウント解消後に再 DEL イベントが必要 |
| getTunnelPort / VLAN 未存在 での DEL スキップ | `true` | **リトライなし**（エントリが残存しないため実害は少ない） |
| `isDipTunnelsSupported()` = false | `true` | リトライなし — 縮退動作として設計上許容 |

詳細解析: `meta/_intermediate/cdb-flow/vxlan-evpn-tunnel-failure.md`

<!-- evidence: vxlanorch.cpp:1133 (ref decrement error); vxlanorch.cpp:1213,1222,1235 (deleteDynamicDIPTunnel); vxlanorch.cpp:1689,1696,1701-1704 (addTunnelUser guards); vxlanorch.cpp:2483-2494 (VLAN+VNI checks); vxlanorch.cpp:2499 (L3 VNI ignore); vxlanorch.cpp:2513,2520 (tunnelPort checks); vxlanorch.cpp:2567,2575,2582,2593 (delOperation) -->
<!-- /failure -->

<!-- constants -->
## ハードコード定数 (Phase E)

ソース: `sonic-swss/orchagent/vxlanorch.h`、`sonic-swss/orchagent/vxlanorch.cpp`、`sonic-swss-common/common/schema.h`

### 名前プレフィックス定数

| 定数 | 値 | 用途 | 根拠 |
|------|----|------|------|
| `EVPN_TUNNEL_NAME_PREFIX` | `"EVPN_"` | DIP トンネル名: `EVPN_<remote_vtep_ip>` | `vxlanorch.h:43` |
| `EVPN_TUNNEL_PORT_PREFIX` | `"Port_EVPN_"` | DIP トンネルポート名: `Port_EVPN_<remote_vtep_ip>` | `vxlanorch.h:42` |

### 数値境界値

| 定数 | 値 | 用途 | 根拠 |
|------|----|------|------|
| `MIN_VLAN_ID` | `1` | VLAN ID 下限 — `to_uint<sai_vlan_id_t>()` の境界チェック | `vxlanorch.h:45` |
| `MAX_VLAN_ID` | `4095` | VLAN ID 上限 (IEEE 802.1Q) | `vxlanorch.h:46` |
| `MAX_VNI_ID` | `16777215` (= 2²⁴ − 1) | VNI 上限 (24-bit)。超過時は `SWSS_LOG_WARN` + `return false` | `vxlanorch.h:48` |
| `DEFAULT_TUNNEL_ENCAP_TTL` | `255` | CLI 生成トンネルのデフォルト encap TTL。EVPN DIP トンネルは TTL 属性を SAI に渡さないため**適用外** | `vxlanorch.h:49` |

### tunnel_creation_src_t enum

| enum 値 | 意味 | 用途 |
|---------|------|------|
| `TNL_CREATION_SRC_CLI` | CLI 生成トンネル | peer_mode 判定・`tnl_src` 分岐 |
| `TNL_CREATION_SRC_EVPN` | EVPN 動的生成トンネル | EVPN DIP トンネルはこの値で固定 (`vxlanorch.cpp:1160`) |

`TNL_CREATION_SRC_EVPN` は peer_mode を `SAI_TUNNEL_PEER_MODE_P2P` に固定する分岐 (`vxlanorch.cpp:903`) と、STATE_DB `tnl_src="EVPN"` 書き込みの分岐 (`vxlanorch.cpp:1934-1939`) で参照される。

### STATE_DB / APP_DB テーブル名定数

| 定数 | 値 | 根拠 |
|------|----|------|
| `STATE_VXLAN_TUNNEL_TABLE_NAME` | `"VXLAN_TUNNEL_TABLE"` | `schema.h:435` |
| `APP_VXLAN_REMOTE_VNI_TABLE_NAME` | `"VXLAN_REMOTE_VNI_TABLE"` | `schema.h:88` |

DIP トンネルの生成・oper status 変更はすべて `STATE_VXLAN_TUNNEL_TABLE_NAME` に書き込まれ、
`EvpnRemoteVnip2pOrch` は `APP_VXLAN_REMOTE_VNI_TABLE_NAME` を購読して処理を行う。

### STATE_DB フィールドのハードコード文字列値

| フィールド | ハードコード値 | タイミング | 根拠 |
|-----------|--------------|-----------|------|
| `tnl_src` | `"EVPN"` | 初期登録時 | `vxlanorch.cpp:1939` |
| `operstatus` | `"down"` | 初期登録時 / down 遷移 | `vxlanorch.cpp:1942`, `1905` |
| `operstatus` | `"up"` | up 遷移 | `vxlanorch.cpp:1901` |
| VLAN メンバ `tagging_mode` | `"untagged"` | flood domain 追加時 (設計上の注記あり) | `vxlanorch.cpp:2525`, `2685` |

詳細解析: `meta/_intermediate/cdb-flow/vxlan-evpn-tunnel-constants.md`

<!-- evidence: vxlanorch.h:42-49 (prefix/bounds defines); vxlanorch.h:52-55 (tunnel_creation_src_t); vxlanorch.cpp:903,1160,1169 (enum 参照); vxlanorch.cpp:1901,1905,1934-1942 (STATE_DB ハードコード値); vxlanorch.cpp:2037,2461,2621 (VNI/VLAN 境界チェック); schema.h:88,435 (テーブル名定数) -->
<!-- /constants -->

## 例外条件・特殊挙動

- **isDipTunnelsSupported() = false の場合**: DIP トンネルは作成されず、リモート VTEP の
  IP 参照カウントのみ更新される (`vxlanorch.cpp:1701-1704`)。プラットフォームが DIP トンネルを
  サポートしない場合の縮退動作。
- **重複リモート VTEP**: `tnl_users_` マップにすでに DIP が存在する場合、新規トンネル作成は
  行われず参照カウントのみインクリメントされる (`vxlanorch.cpp:1173-1177`)。
- **削除順序依存**: EVPN NVO 削除は DIP トンネルの `del_tnl_hw_pending` フラグが true の場合に
  ブロックされる (`vxlanorch.cpp:2803-2807`)。

## 関連 CONFIG_DB / YANG / CLI

- 関連 [CONFIG_DB](../../reference/glossary.md#term-config_db): [`VXLAN_TUNNEL`](vxlan-tunnel.md)、[`VXLAN_EVPN_NVO`](vxlan-evpn-nvo.md)、[`VXLAN_TUNNEL_MAP`](vxlan-tunnel-map.md)
- 関連 [YANG](../../reference/glossary.md#term-yang): `sonic-vxlan`
- 関連 CLI: [`config vxlan`](../cli/config-vxlan.md)

<!-- ref-triangle:start -->

## 関連リファレンス

- [CONFIG_DB: VXLAN_TUNNEL](vxlan-tunnel.md)
- [CONFIG_DB: VXLAN_EVPN_NVO](vxlan-evpn-nvo.md)
- [YANG: sonic-vxlan](../yang/sonic-vxlan.md)
- [CLI: config vxlan](../cli/config-vxlan.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: `sonic-swss/orchagent/vxlanorch.cpp` `createDynamicDIPTunnel()` <https://github.com/sonic-net/sonic-swss/blob/master/orchagent/vxlanorch.cpp>

## 関連ページ

- [HLD: VXLAN / VNet 全体設計](../../overlay/vxlan-sonic.md)
- [CONFIG_DB: VXLAN_TUNNEL](vxlan-tunnel.md)
- [CONFIG_DB: VXLAN_EVPN_NVO](vxlan-evpn-nvo.md)
- [CONFIG_DB: VXLAN_TUNNEL_MAP](vxlan-tunnel-map.md)
- [YANG: sonic-vxlan](../yang/sonic-vxlan.md)

<!-- ops-hint -->
## 運用ヒント

### EVPN DIP トンネルの確認

```bash
# STATE_DB でダイナミックトンネルを確認 (tnl_src=EVPN のもの)
sonic-db-cli STATE_DB keys 'VXLAN_TUNNEL_TABLE|EVPN_*'

# 個別トンネルの状態
sonic-db-cli STATE_DB hgetall 'VXLAN_TUNNEL_TABLE|EVPN_<remote_vtep_ip>'

# show コマンド
show vxlan tunnel
show vxlan remotevtep
```

### よくある問題

- **EVPN VTEP 不在**: `VXLAN_EVPN_NVO` が設定されていないと DIP トンネルが生成されない。
  先に `config vxlan evpn_nvo add <name> <vtep>` を実行する。
- **VTEP 未 active**: `VXLAN_TUNNEL` テーブルの `src_ip` が設定されており active でないと
  DIP トンネル生成が `false` を返す。VTEP の active 状態を `show vxlan tunnel` で確認。
- **`decap_ttl_mode` の挙動**: EVPN DIP トンネルは TTL モードを SAI に渡さないため、
  プラットフォームの ASIC デフォルトが適用される。TTL 関連のトラフィック問題時は ASIC
  ベンダーのドキュメントを参照。
<!-- /ops-hint -->
