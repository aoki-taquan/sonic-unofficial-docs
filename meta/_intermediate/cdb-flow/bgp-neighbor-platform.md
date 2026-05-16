# BGP_NEIGHBOR — Phase H: プラットフォーム / SAI 差分

## 調査スコープ

- `DEVICE_METADATA.switch_type` (`voq` / `chassis-packet`) による分岐
- `DEVICE_METADATA.sub_role` (`FrontEnd` / `BackEnd`) による分岐
- `DEVICE_METADATA.type` (SpineRouter, ToRRouter, UpperSpineRouter …) による分岐
- chassis-packet 専用 Jinja2 テンプレート分岐
- VoQ chassis 専用テーブル `BGP_VOQ_CHASSIS_NEIGHBOR`
- Multi-ASIC internal BGP (`BGP_INTERNAL_NEIGHBOR`) と admin_status 強制 up

---

## 1. テーブル振り分けと switch_type

`minigraph.py` が BGP セッションを 3 つのテーブルに振り分ける。

| 条件 | 書き込み先テーブル | admin_status 強制 |
|------|-------------------|------------------|
| `chassis_internal_ibgp == "voq"` (VoQ カード間 iBGP) | `BGP_VOQ_CHASSIS_NEIGHBOR` | `'up'` (L1347) |
| `chassis_internal_ibgp == "chassis-packet"` (パケット型シャーシ内部 iBGP) | `BGP_INTERNAL_NEIGHBOR` | `'up'` (L1350) |
| Multi-ASIC 内部 (両端 `local_devices` 内) | `BGP_INTERNAL_NEIGHBOR` | `'up'` (L1351–1353) |
| その他 (通常 eBGP/iBGP) | `BGP_NEIGHBOR` | なし |

`chassis_internal_ibgp` の決定ロジック（`minigraph.py` L1327–1342）:
- XML `<ChassisInternal>` 要素が存在し、`<BgpGroup><Start>` と `<End>` が両方 `"voq"` → `"voq"`
- 両方 `"chassis-packet"` → `"chassis-packet"`

---

## 2. enable_internal_bgp_session (Multi-ASIC)

`minigraph.py:1888–1901` の `enable_internal_bgp_session()`:

```python
def enable_internal_bgp_session(bgp_sessions, filename, asic_name):
    local_sub_role = parse_asic_sub_role(filename, asic_name)
    for peer_ip in bgp_sessions.keys():
        peer_sub_role = parse_asic_sub_role(filename, peer_name)
        if ((local_sub_role == 'FrontEnd' and peer_sub_role == 'BackEnd') or
            (local_sub_role == 'BackEnd' and peer_sub_role == 'FrontEnd')):
            bgp_sessions[peer_ip].update({'admin_status': 'up'})
```

FrontEnd ↔ BackEnd 間のセッションは **常に admin_status='up'** に強制される。

---

## 3. bgpcfgd main.py — Manager 登録と switch_type

`main.py` L87–92 で `BGPPeerMgrBase` が以下のテーブルを購読:

| テーブル | peer_type (テンプレートディレクトリ) | 登録条件 |
|---------|-------------------------------------|---------|
| `BGP_NEIGHBOR` | `general` | 常時 (check_neig_meta=True) |
| `BGP_INTERNAL_NEIGHBOR` | `internal` | 常時 |
| `BGP_MONITORS` | `monitors` | 常時 |
| `BGP_PEER_RANGE` | `dynamic` | 常時 |
| `BGP_VOQ_CHASSIS_NEIGHBOR` | `voq_chassis` | 常時 |
| `BGP_SENTINELS` | `sentinels` | 常時 |

**ChassisAppDbMgr** (L112–113): `device_info.is_chassis()` が True のとき `CHASSIS_APP_DB.BGP_DEVICE_GLOBAL` を購読し、スーパーバイザーの TSA 状態を LC に伝播。

**AsPathMgr** (L123–130): `DEVICE_METADATA.type == 'SpineRouter' && subtype == 'UpstreamLC'` または `type == 'UpperSpineRouter'` のときのみ追加登録。

---

## 4. Jinja2 テンプレート分岐マトリクス

### 4-1. `internal/instance.conf.j2`

| 条件 | FRR コマンド |
|------|------------|
| `sub_role == 'BackEnd'` または `switch_type == 'chassis-packet'` | `neighbor X next-hop-self force` (IPv4/IPv6 AF) |
| 上記以外 | next-hop-self なし |

ソース: `dockers/docker-fpm-frr/frr/bgpd/templates/internal/instance.conf.j2` L13–23

### 4-2. `internal/peer-group.conf.j2`

| 条件 | FRR コマンド |
|------|------------|
| `switch_type == 'chassis-packet'` | `INTERNAL_PEER_V4/V6` に `update-source Loopback4096` + `ttl-security hops 1` |
| `sub_role == 'BackEnd'` | INTERNAL_PEER_V4/V6 AF で `route-reflector-client` |
| 常時 | `send-community`、`allowas-in 1`、route-map |

ソース: `dockers/docker-fpm-frr/frr/bgpd/templates/internal/peer-group.conf.j2`

### 4-3. `internal/policies.conf.j2`

| 条件 | ポリシー内容 |
|------|------------|
| `sub_role == 'BackEnd'` | `FROM_BGP_INTERNAL_PEER_V4/V6` に `set originator-id <Loopback4096 IP or bgp_router_id>` |
| `switch_type == 'chassis-packet'` | DEVICE_INTERNAL_COMMUNITY / DEVICE_INTERNAL_FALLBACK_COMMUNITY / NO_EXPORT の community-list を生成。`subtype == 'DownstreamLC'` は fallback-community のタグ付けなし |
| FrontEnd (voq など) | `FROM_BGP_INTERNAL_PEER_V6` に `set ipv6 next-hop prefer-global` のみ |

ソース: `dockers/docker-fpm-frr/frr/bgpd/templates/internal/policies.conf.j2`

### 4-4. `general/peer-group.conf.j2`

| 条件 | FRR コマンド |
|------|------------|
| `type == 'ToRRouter'` | `allowas-in 1` (IPv4/IPv6) |
| `type == 'LeafRouter'` かつ BBR enabled | `allowas-in 1` |
| `type == 'SpineRouter' && subtype == 'UpstreamLC'` または `type == 'UpperSpineRouter'` | `table-map SELECTIVE_ROUTE_DOWNLOAD_V4/V6` |

ソース: `dockers/docker-fpm-frr/frr/bgpd/templates/general/peer-group.conf.j2`

### 4-5. `general/instance.conf.j2`

| 条件 | FRR コマンド |
|------|------------|
| `bgp_session["asn"] == bgp_asn` (iBGP) かつ `type == 'SpineChassisFrontendRouter'` | `address-family l2vpn evpn` + `advertise-all-vni` |
| `admin_status == 'down'` または `default_bgp_status == 'down'` | `neighbor X shutdown` |

ソース: `dockers/docker-fpm-frr/frr/bgpd/templates/general/instance.conf.j2`

### 4-6. `general/policies.conf.j2`

| 条件 | ポリシー内容 |
|------|------------|
| `type == 'SpineRouter' && subtype == 'UpstreamLC'` または `type == 'UpperSpineRouter'` | `SELECTIVE_ROUTE_DOWNLOAD_V4/V6` route-map + `TO_BGP_PEER_V4/V6` で anchor-contributing-route community 付与 |
| `switch_type == 'chassis-packet'` (UpstreamLC 内部のサブ分岐) | `route_eligible_for_fallback_to_default_tag` タグを set (非 chassis-packet は `route_do_not_send_appdb_tag`) |

ソース: `dockers/docker-fpm-frr/frr/bgpd/templates/general/policies.conf.j2`

### 4-7. `voq_chassis/instance.conf.j2`

- timers 2/7 (internal より短い)
- `bgp bestpath as-path multipath-relax` + `peer-type multipath-relax`
- `VOQ_CHASSIS_V4_PEER` / `VOQ_CHASSIS_V6_PEER` peer-group に割り当て
- `constants.bgp.maximum_paths.enabled` が true なら `maximum-paths ibgp` 設定

### 4-8. `voq_chassis/peer-group.conf.j2`

| 条件 | FRR コマンド |
|------|------------|
| `type == 'ToRRouter'` | `allowas-in 1` |
| 常時 | `addpath-tx-all-paths`、`send-community`、route-map |

### 4-9. `voq_chassis/policies.conf.j2`

| 条件 | ポリシー内容 |
|------|------------|
| `subtype == 'UpstreamLC'` | `FROM_VOQ_CHASSIS_V4/V6_PEER deny 3/4` で DEVICE_INTERNAL_FALLBACK_COMMUNITY を deny |
| その他 | fallback community を permit し `route_eligible_for_fallback_to_default_tag` タグ付与 |

---

## 5. プラットフォーム差分サマリ表

| DEVICE_METADATA 値 | 影響するテンプレート | 主な差異 |
|-------------------|---------------------|---------|
| `switch_type=voq` | `voq_chassis/*` | BGP_VOQ_CHASSIS_NEIGHBOR テーブル、timers 2/7、multipath-relax、addpath-tx-all-paths |
| `switch_type=chassis-packet` | `internal/*` | Loopback4096 update-source、ttl-security hops 1、next-hop-self force、fallback community 処理 |
| `sub_role=BackEnd` | `internal/*` | route-reflector-client、set originator-id |
| `sub_role=FrontEnd` | `internal/*` | originator-id なし (基本動作) |
| `type=ToRRouter` | `general/*`, `voq_chassis/*` | allowas-in 1 |
| `type=SpineRouter && subtype=UpstreamLC` または `type=UpperSpineRouter` | `general/*` | table-map SELECTIVE_ROUTE_DOWNLOAD、AsPathMgr 有効化、anchor-route community |
| `type=SpineChassisFrontendRouter` | `general/instance.conf.j2` | l2vpn evpn AF activate + advertise-all-vni |
| `type=LeafRouter && BBR=enabled` | `general/peer-group.conf.j2` | allowas-in 1 |
| `is_chassis()=True` | `main.py` | ChassisAppDbMgr 登録 (CHASSIS_APP_DB TSA 伝播) |

---

## 6. SAI 到達パスへの影響

BGP_NEIGHBOR 自体は FRR (`bgpd`) 止まりで SAI に直接は到達しない。ただしプラットフォーム差分により以下が間接的に SAI に影響する:

- `next-hop-self force` → BGP 経路の nexthop が書き換えられ、orchagent の nexthop resolution が変わる
- `addpath-tx-all-paths` (VoQ) → 複数経路が APPL_DB に書き込まれ、`sai_route_entry` の ECMP グループが異なる
- `table-map SELECTIVE_ROUTE_DOWNLOAD_V4/V6` (UpstreamLC) → FIB への再配布経路が選別される

---

## ソース証跡

| ファイル | 行 | 内容 |
|---------|----|------|
| `src/sonic-config-engine/minigraph.py` | L1324–1356 | chassis_internal_ibgp 判定、テーブル振り分け |
| `src/sonic-config-engine/minigraph.py` | L1888–1901 | enable_internal_bgp_session (sub_role FrontEnd↔BackEnd) |
| `src/sonic-bgpcfgd/bgpcfgd/main.py` | L87–92 | BGPPeerMgrBase 登録テーブル |
| `src/sonic-bgpcfgd/bgpcfgd/main.py` | L112–113 | is_chassis() ChassisAppDbMgr 条件登録 |
| `src/sonic-bgpcfgd/bgpcfgd/main.py` | L123–130 | UpstreamLC / UpperSpineRouter AsPathMgr 条件登録 |
| `dockers/docker-fpm-frr/frr/bgpd/templates/internal/instance.conf.j2` | L13–23 | sub_role=BackEnd / chassis-packet → next-hop-self force |
| `dockers/docker-fpm-frr/frr/bgpd/templates/internal/peer-group.conf.j2` | L6–25 | chassis-packet → Loopback4096 update-source + ttl-security; BackEnd → route-reflector-client |
| `dockers/docker-fpm-frr/frr/bgpd/templates/internal/policies.conf.j2` | L8–96 | BackEnd originator-id / chassis-packet community ポリシー分岐 |
| `dockers/docker-fpm-frr/frr/bgpd/templates/general/peer-group.conf.j2` | L7–33 | ToRRouter allowas-in 1; UpstreamLC table-map |
| `dockers/docker-fpm-frr/frr/bgpd/templates/general/instance.conf.j2` | L38–43 | SpineChassisFrontendRouter l2vpn evpn |
| `dockers/docker-fpm-frr/frr/bgpd/templates/general/policies.conf.j2` | L40–55 | chassis-packet tag 分岐 |
| `dockers/docker-fpm-frr/frr/bgpd/templates/voq_chassis/instance.conf.j2` | L4–35 | VoQ timers 2/7, multipath-relax |
| `dockers/docker-fpm-frr/frr/bgpd/templates/voq_chassis/peer-group.conf.j2` | L14–34 | ToRRouter allowas-in 1; addpath-tx-all-paths |
| `dockers/docker-fpm-frr/frr/bgpd/templates/voq_chassis/policies.conf.j2` | L19–62 | UpstreamLC fallback deny; 他 permit+tag |
