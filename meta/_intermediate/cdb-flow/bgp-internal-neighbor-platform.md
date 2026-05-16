# BGP_INTERNAL_NEIGHBOR — Phase H プラットフォーム差異スキャンノート

生成日: 2026-05-16 (Task F Phase H)

## スキャン対象ファイル

| ファイル | パス |
|---|---|
| managers_bgp.py | `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py` |
| frrcfgd.py | `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py` |
| policies.conf.j2 (internal) | `sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/templates/internal/policies.conf.j2` |
| minigraph.py | `sonic-buildimage/src/sonic-config-engine/minigraph.py` |

## 検出結果

### 1. テーブル生成プラットフォーム限定（minigraph.py）

`BGP_INTERNAL_NEIGHBOR` は以下の 2 系統でのみ生成される:

- **chassis-packet 分岐** (L1341-1350): `<ChassisInternal>` == `"chassis-packet"` または BgpGroup の Start/End が `CHASSIS_CARD_PACKET`
- **multi-ASIC 内部セッション分岐** (L1351-1353): 両端が `local_devices` 内（FrontEnd/BackEnd ASIC ペア）

VOQ chassis は `BGP_VOQ_CHASSIS_NEIGHBOR` に分類され、本テーブルには入らない（L1345-1347）。

### 2. managers_bgp.py の内部 peer 固有分岐

- L145-146: `peer_type == 'internal'` のとき `Loopback4096` を依存として追加。他 peer_type にはこの依存がない。
- main.py L88: `check_neig_meta=False` 固定で登録。DEVICE_NEIGHBOR_METADATA に依存しない。

### 3. frrcfgd.py — 対象なし（根拠付き）

`BGP_INTERNAL_NEIGHBOR`・`internal_neighbor` キーワードでスキャン。ヒットなし。`frrcfgd.py` はこのテーブルを購読しない。`bgpcfgd` 専用パス。

### 4. internal/policies.conf.j2 の 3 分岐

```
sub_role == 'BackEnd'
  → set originator-id (bgp_router_id or Loopback4096 IP)

switch_type == 'chassis-packet'
  → community-list 定義 + FROM/TO_BGP_INTERNAL_PEER route-map
  → subtype == 'DownstreamLC': fallback community delete のみ
  → その他: fallback community delete + set tag route_eligible_for_fallback_to_default_tag

それ以外（multi-ASIC FrontEnd 等）
  → FROM_BGP_INTERNAL_PEER_V6 に set ipv6 next-hop prefer-global のみ
```

### 5. VOQ chassis との比較

`voq_chassis/policies.conf.j2` は `subtype == 'UpstreamLC'` で FROM route-map を **deny** に分岐する（`internal/policies.conf.j2` は permit で subtype 分岐）。Loopback 依存も異なる（VOQ は Loopback4096 依存なし）。

## 結論

プラットフォーム分岐は **明確に存在**。`<!-- platform -->` ブロックとして `docs/reference/config-db/bgp-internal-neighbor.md` に反映済み。
