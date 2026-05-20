---
title: bgpcfgd の dynamic BGP peer 動的変更（update.conf.j2 / delete.conf.j2）
description: bgpcfgd の dynamic BGP peer 動的変更 — 従来 bgpcfgd は BGP_PEER_RANGE を create
  only で扱い、runtime での range 追加/削除や route-map / prefix-list / peer-group 等の付随設定変更を受け付けなかった。
area: routing
verification: discrepancy-found
last_verified: 2026-05-13
monitor: partially_implemented
sources:
- repo: sonic-net/SONiC
  path: doc/BGP/Bgpcfgd-dyn-peer-modification-support.md
  ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
  - BGP_PEER_RANGE
  - VNET
  - VRF
  - BGP_NEIGHBOR
  - BGP_GLOBALS
  - BGP_PEER_GROUP_AF
  - BGP_GLOBALS_AF_NETWORK
  cli:
  - show ip bgp vrf
  - show ipv6 bgp vrf
  - show ip
  - config bgp
  - show bgp
  - config vrf
  - config vnet
  yang:
  - sonic-bgp-global
  - sonic-bgp-neighbor
  - sonic-bgp-peergroup
  - sonic-bgp-aggregate-address
  - sonic-bgp-sentinel
  - sonic-bgp-peerrange
  - sonic-bgp-bbr
---

<!-- topics-tip -->
!!! tip "Topics で読み物として読む"
    この HLD は実装詳細を含みます。機能の概念・設定・運用を読み物として読みたい場合は [Topics 02 章: BGP と FRR 制御プレーン](../topics/02-bgp/index.md) を参照。
<!-- /topics-tip -->

!!! warning "裏取りステータス: Discrepancy-found (partially_implemented)"
    `bgpcfgd/managers_bgp.py` L87 `BGPPeerMgrBase`、L112-115 で `update.conf.j2` / `delete.conf.j2` の searchpath ロード、L287-297 で `STATE_BGP_PEER_CONFIGURED_TABLE_NAME` への CRUD。`sonic-swss-common/common/schema.h` L511 で `STATE_BGP_PEER_CONFIGURED_TABLE_NAME = "BGP_PEER_CONFIGURED_TABLE"`。`docker-fpm-frr/frr/bgpd/templates/dynamic/{update,delete}.conf.j2` の `add_ranges` / `delete_ranges` ロジック。`sonic-utilities/show/bgp_frr_v4.py` L103-168 で `show ip bgp vrf` 系、`utilities_common/bgp_util.py` L304-320 で vtysh 経由の vrf JSON 取得を確認 (verified at: 2026-05-09)。降格詳細は本ページ末尾の補足節を参照 (2026-05-13)。

# bgpcfgd の dynamic BGP peer 動的変更

## 読み手が知りたいこと

- SDN コントローラから dynamic [BGP](../reference/glossary.md#term-bgp) peer（listen-range）を動的に追加・削除したい。今までの [bgpcfgd](../reference/glossary.md#term-bgpcfgd) で何が足りなかったか
- update / delete が `bgpcfgd` のどこで処理されるか、後方互換は保たれるか
- SDN 側はどこで「反映済み」を確認できるか
- 何が **peer_type 依存** なのか

## 何が問題だったか

従来 bgpcfgd は `BGP_PEER_RANGE` を **create only** で扱い、runtime での range 追加/削除や route-map / prefix-list / peer-group 等の付随設定変更を受け付けなかった[^1]。SDN コントローラから [VNET](../reference/glossary.md#term-vnet) / [VRF](../reference/glossary.md#term-vrf) 単位で dynamic peer を CRUD する要件に応えるため、本 [HLD](../reference/glossary.md#term-hld) は **update / delete テンプレート** と **[STATE_DB](../reference/glossary.md#term-state_db) ミラー table** を追加する。

スケール目標[^1]:

| 要素 | 目標 |
|------|------|
| Dynamic BGP peer 数（route-map / prefix-list / peer-group 含む） | 2k 合計（VRF/VNET あたり ~1） |
| listen-range 数 | 4k 合計（VRF/VNET あたり ~2） |
| route-map / prefix-list サイズ | 各 < 10 |

## スキーマ（CONFIG_DB / STATE_DB）

既存 `CONFIG_DB.BGP_PEER_RANGE` をそのまま使い、**新規 table 追加なし**。反映確認用に `STATE_DB.BGP_PEER_CONFIGURED_TABLE` を追加する[^1]。

```text
CONFIG_DB.BGP_PEER_RANGE|<VRF/VNET>|<Peer>
    ip_range:    [list of IP ranges]
    name:        <Peer>
    peer_asn:    <ASN>           (optional)
    src_address: <source IP>     (optional)

STATE_DB.BGP_PEER_CONFIGURED_TABLE|<VRF/VNET>|<Peer>
    （CONFIG_DB と同じフィールドのミラー）
```

dynamic / static 両 peer で同じ table 名を使う。SDN は [CONFIG_DB](../reference/glossary.md#term-config_db) に投入 → STATE_DB をポーリングして反映確認する想定[^1]。

## bgpcfgd の挙動

### 起動時のテンプレート探索

`BGPPeerMgrBase` は init 時に peer_type ごとのテンプレート directory を探す[^1]。

```text
bgpd/templates/<peer_type_dir>/update.conf.j2
bgpd/templates/<peer_type_dir>/delete.conf.j2
```

両ファイルが存在すれば `self.templates["update"]` / `["delete"]` にロードし、その peer_type は update/delete をサポートと判定。**無ければ従来挙動**（update は no-op、delete は `no neighbor <addr>`）を維持し、完全な後方互換を保つ[^1]。

### update / delete フロー

```mermaid
sequenceDiagram
    participant SDN
    participant CDB as CONFIG_DB.BGP_PEER_RANGE
    participant BCD as bgpcfgd
    participant V as vtysh / bgpd
    participant SDB as STATE_DB.BGP_PEER_CONFIGURED_TABLE
    SDN->>CDB: ip_range 追加
    CDB->>BCD: notify
    BCD->>V: 現行 listen-range 取得
    V-->>BCD: 現行 ranges
    BCD->>BCD: diff = (add_ranges, delete_ranges)
    BCD->>V: update.conf.j2 render → vtysh
    BCD->>SDB: BGP_PEER_CONFIGURED_TABLE 反映
    SDN->>SDB: ポーリングで確認
```

render 時の kwargs[^1]:

```python
kwargs = {
    'vrf': vrf, 'neighbor_addr': nbr, 'bgp_session': data,
    'delete_ranges': ip_ranges_to_del,
    'add_ranges':    ip_ranges_to_add,
}
cmd = self.templates["update"].render(**kwargs)
```

delete も同様で、`delete.conf.j2` がロード済みなら render して発行、未ロードなら `no neighbor <addr>`[^1]。

### docker-fpm-frr のテンプレート構成

既存の 3 系統に並べる形で 2 ファイルを追加する[^1]。

```text
docker-fpm-frr/.../bgpd/templates/<peer_type>/
  ├ instance.conf.j2     (既存)
  ├ policies.conf.j2     (既存)
  ├ peer-group.conf.j2   (既存)
  ├ update.conf.j2       (新規)
  └ delete.conf.j2       (新規)
```

設計選択として、update/delete 各 1 ファイルで instance/policies/peer-group を全部扱うシンプル案を採用（6 ファイル分割案は将来必要なら移行可）[^1]。

## CLI（VRF 表示の追加）

VRF 指定の bgp 表示を default VRF と同等に揃える[^1]:

| Command |
|---------|
| `show ip bgp vrf <vrf> {summary,network,neighbors}` |
| `show ipv6 bgp vrf <vrf> {summary,network,neighbors}` |

## 設定

### 関連する CONFIG_DB / STATE_DB

| Table | Key | フィールド | 説明 |
|-------|-----|-----------|------|
| `BGP_PEER_RANGE` | `<VRF>\|<Peer>` | `ip_range`, `name`, `peer_asn`(opt), `src_address`(opt) | dynamic peer の listen-range |
| `BGP_PEER_CONFIGURED_TABLE` (STATE_DB) | `<VRF>\|<Peer>` | 同上 | bgpcfgd 反映済みミラー |

### 設定例

```bash
# dynamic peer 追加 (default VRF)
sonic-db-cli CONFIG_DB hset 'BGP_PEER_RANGE|default|VnetPeer1' \
  ip_range '["10.0.0.0/24","10.0.1.0/24"]' \
  name 'VnetPeer1' peer_asn 65010

# 反映確認
sonic-db-cli STATE_DB hgetall 'BGP_PEER_CONFIGURED_TABLE|default|VnetPeer1'

# VNET 上の表示
show ip bgp vrf Vnet1 summary
```

## 制限事項

### unnumbered（インタフェースベース）BGP neighbor は非対応

**CONFIG_DB の `BGP_NEIGHBOR` テーブルは IP アドレスキーのみ受け付ける**。`neighbor PortChannel101 interface v6only remote-as 64001` のような unnumbered BGP neighbor は bgpcfgd 経由では設定できない。

制約の全容（3 層）:

1. **YANG スキーマ**: `sonic-bgp-neighbor.yang` の `BGP_NEIGHBOR_LIST` は `inet:ip-address` 型のキーを使用。`frrcfgd` が使う `BGP_NEIGHBOR_LIST` は union 型（Port / PortChannel / Vlan pattern を含む）だが `bgpcfgd` 側は未対応
2. **bgpcfgd の `add_peer()`**: IP アドレス前提のコードパスのみ。インタフェース名が渡されても `neighbor <intf> interface` FRR 構文を生成しない
3. **Jinja2 template**: `general/instance.conf.j2` 等が `| ipv4` / `| ipv6` フィルタで分岐するため、インタフェース名だと両方とも `False` になりアドレスファミリブロックがスキップされる

**回避策**: `frrcfgd` 経由または `vtysh` で直接 FRR 設定を投入する（FRR 自体は unnumbered BGP をサポート済み）。

**参照**: sonic-net/sonic-buildimage#26960（Bug, Triaged、修正 PR 検討中）

---

- **`update.conf.j2` / `delete.conf.j2` が peer_type の template directory に無いと機能しない**[^1]。dynamic peer の動的編集が peer_type 依存
- update/delete 各 1 ファイルで instance/policies/peer-group を全部扱う粗粒度設計
- diff 算出は vtysh の現行値を信頼するため、**vtysh と bgpcfgd の整合**が崩れると delete_ranges が誤算出され得る
- `BGP_PEER_CONFIGURED_TABLE` は **bgpcfgd の処理完了** をミラーするだけで、BGP session 確立までは追跡しない
- HLD は 2025-07 Rev 1.0。master 取り込み状況は要追跡

## 干渉する機能

- **bgpcfgd / docker-fpm-frr**: 主体
- **[FRR](../reference/glossary.md#term-frr) bgpd / vtysh**: 現行 listen-range の取得と適用先
- **SDN controller**: CONFIG_DB 投入と STATE_DB ポーリング
- **VRF / VNET**: 名前解決と routing instance 切替

## トラブルシューティング

- listen-range 追加が反映されない → ベンダ template dir に `update.conf.j2` があるか確認
- `BGP_PEER_CONFIGURED_TABLE` に entry が出ない → bgpcfgd ログで render エラーを確認
- diff が誤算出 → vtysh の `show ip bgp listen range` と CONFIG_DB を突き合わせ
- VNET 上で `show ip bgp vrf <name>` が動かない → [sonic-utilities](../reference/glossary.md#term-sonic-utilities) のバージョン確認

### コマンド例

bgpcfgd の動的ピア更新と config 反映を確認する。

```bash
docker logs bgp 2>&1 | grep -i bgpcfgd | tail
sonic-cfggen -d -v 'BGP_NEIGHBOR'
docker exec bgp vtysh -c 'show bgp neighbors' | head
```

## 関連 Topic

- [02 BGP / internals](../topics/02-bgp/internals.md)
- [02 BGP / operations](../topics/02-bgp/operations.md)
- [04 VRF & ECMP / concept](../topics/04-vrf-ecmp/concept.md)


<!-- demoted-by:q52-az-b-demote -->
## 実装フェーズ境界

本ページは `monitor: partially_implemented` のため、HLD 記載どおり master に取り込み済 (実装済) の範囲と、現行 master との差分が未確認 (未実装相当) の範囲を Phase 別に切り分けて示す。詳細は本文・[実装との乖離 / 補足] 節および各引用元 HLD を参照。

| Phase | 実装済 | 未実装 |
|-------|--------|--------|
| Phase 1: STATE_DB BGP_PEER_CONFIGURED_TABLE スキーマ | HLD 記載どおり実装済 | — |
| Phase 2: 動的 peer 追加 / 削除 | bgpcfgd への差分適用ロジックは実装済 | VRF 表示 CLI 等の派生機能は未確認・未実装の可能性 |
| Phase 3: 大規模 peer flap 時の安定性 | — | 競合ケースの保証は未実装 / 未確認 |

## 実装との乖離 / 補足

- 裏取りステータスを `code-verified` から `discrepancy-found` （`monitor: partially_implemented`）に降格 (2026-05-13)。HLD は 2025-07 Rev 1.0 で master 取り込み状況は本文で「要追跡」と明示している。
- 本文に残る「未確認 / 要確認 / 要追跡 / TBD」等の hedge 表現は HLD と実装の差分が未特定であることを示し、後続の裏取り対象。

## 引用元

[^1]: `sonic-net/SONiC` `doc/BGP/Bgpcfgd-dyn-peer-modification-support.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- glossary-links-injected: f2b208f4ed9e -->
