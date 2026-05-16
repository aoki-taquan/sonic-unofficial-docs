# bgp-internal-neighbor — Phase E ハードコード定数調査

対象ハンドラ: `bgpcfgd` (`managers_bgp.py`, `BGPPeerMgrBase(peer_type="internal")`)、Jinja2 テンプレート (`bgpd/templates/internal/instance.conf.j2`, `peer-group.conf.j2`, `policies.conf.j2`)

## 抽出した定数

### タイマーハードコード値（instance.conf.j2）

CONFIG_DB の `holdtime` / `keepalive` / `conn_retry` フィールドを **完全無視** してテンプレートが固定値を適用する。

| 定数 | 値 | 用途 | evidence |
|-----|-----|------|---------|
| keepalive ハードコード | `3`（秒） | `neighbor <addr> timers 3 10` として FRR に投入。CONFIG_DB の `keepalive` 値は参照されない | `internal/instance.conf.j2:6` |
| holdtime ハードコード | `10`（秒） | `neighbor <addr> timers 3 10` として FRR に投入。CONFIG_DB の `holdtime` 値は参照されない | `internal/instance.conf.j2:6` |
| connect-retry ハードコード | `10`（秒） | `neighbor <addr> timers connect 10` として FRR に投入。CONFIG_DB フィールドなし | `internal/instance.conf.j2:7` |

> **備考**: minigraph は `holdtime=180, keepalive=60` を CONFIG_DB に書き込むが（test_bgp.py のテストデータも同様）、bgpcfgd テンプレートはこれらを読まず `3 10` を強制する。YANG の `uint16` フィールドとして定義されているが **dead field**。

### peer-group 名定数（peer-group.conf.j2）

| 定数 | 値 | 用途 | evidence |
|-----|-----|------|---------|
| IPv4 peer-group 名 | `INTERNAL_PEER_V4` | `neighbor INTERNAL_PEER_V4 peer-group` として定義。全 internal IPv4 peer に適用 | `internal/peer-group.conf.j2:4` |
| IPv6 peer-group 名 | `INTERNAL_PEER_V6` | `neighbor INTERNAL_PEER_V6 peer-group` として定義。全 internal IPv6 peer に適用 | `internal/peer-group.conf.j2:5` |

### peer-group 固定設定（peer-group.conf.j2）

CONFIG_DB フィールドの値に依存せず常時付与されるハードコード設定。

| 定数 | 値 | 用途 | evidence |
|-----|-----|------|---------|
| soft-reconfiguration | `inbound` | IPv4/IPv6 両 AF に `soft-reconfiguration inbound` 付与 | `internal/peer-group.conf.j2:14,28` |
| allowas-in | `1` | `allowas-in 1` を両 AF に付与（AS ループ 1 回許可） | `internal/peer-group.conf.j2:15,29` |
| send-community | （フラグ） | `send-community` を両 AF に付与 | `internal/peer-group.conf.j2:18,32` |
| ttl-security hops | `1` | `chassis-packet` 時のみ。`ttl-security hops 1` を IPv4/IPv6 peer-group に付与 | `internal/peer-group.conf.j2:8,22` |

### route-map 名定数（policies.conf.j2 / peer-group.conf.j2）

| 定数 | 値 | 用途 | evidence |
|-----|-----|------|---------|
| FROM_BGP_INTERNAL_PEER_V4 | `FROM_BGP_INTERNAL_PEER_V4` | IPv4 inbound route-map 名。peer-group の `route-map ... in` に使用 | `internal/peer-group.conf.j2:16`、`policies.conf.j2:9,32,37,43,47,99` |
| TO_BGP_INTERNAL_PEER_V4 | `TO_BGP_INTERNAL_PEER_V4` | IPv4 outbound route-map 名。peer-group の `route-map ... out` に使用 | `internal/peer-group.conf.j2:17`、`policies.conf.j2:78,82,103` |
| FROM_BGP_INTERNAL_PEER_V6 | `FROM_BGP_INTERNAL_PEER_V6` | IPv6 inbound route-map 名 | `internal/peer-group.conf.j2:30`、`policies.conf.j2:16,20,53,57,62,68,72,93,101` |
| TO_BGP_INTERNAL_PEER_V6 | `TO_BGP_INTERNAL_PEER_V6` | IPv6 outbound route-map 名 | `internal/peer-group.conf.j2:31`、`policies.conf.j2:85,89,105` |

### chassis-packet community-list 定数（policies.conf.j2）

`constants.bgp.*` から参照される値。bgpcfgd の `constants.json` または CHASSIS_APP_DB からロード。

| 定数キー | テスト参照値 | 用途 | evidence |
|---------|------------|------|---------|
| `constants.bgp.internal_community` | `12345:556` | `DEVICE_INTERNAL_COMMUNITY` community-list に設定。`TO_BGP_INTERNAL_PEER_V4/V6` でタグ付与に使用 | `policies.conf.j2:34`、`tests/data/internal/policies.conf/param_chasiss_packet.json:9` |
| `constants.bgp.internal_fallback_community` | `1111:2222` | `DEVICE_INTERNAL_FALLBACK_COMMUNITY` community-list に設定。fallback route の識別に使用 | `policies.conf.j2:35`、`tests/data/internal/policies.conf/param_chasiss_packet.json:15` |
| `constants.bgp.local_anchor_route_community` | `12345:555` | `LOCAL_ANCHOR_ROUTE_COMMUNITY` community-list に設定。`TO_BGP_INTERNAL_PEER deny 15` で deny 判定に使用 | `policies.conf.j2:36`、`tests/data/internal/policies.conf/param_chasiss_packet.json:16` |
| `constants.bgp.internal_community_match_tag` | `101` | `set tag` に使用。`FROM_BGP_INTERNAL_PEER_V4 permit 1` / `V6 permit 2` でタグを付与 | `policies.conf.j2:40,58`、`tests/data/internal/policies.conf/param_chasiss_packet.json:13` |
| `constants.bgp.route_eligible_for_fallback_to_default_tag` | `203` | `FROM_BGP_INTERNAL_PEER_V4/V6 permit 3/4`（非 DownstreamLC）でフォールバック eligible を示す `set tag` に使用 | `policies.conf.j2:50,70`、`tests/data/internal/policies.conf/param_chasiss_packet.json:14` |

> **備考**: これらはハードコードではなく `constants.bgp.*` 経由の設定注入だが、**展開結果として FRR コンフィグに埋め込まれるリテラル文字列**となるため定数扱いとする。実際の値はデプロイ時 constants ファイル（または CHASSIS_APP_DB）に依存する。

### community-list 名定数（policies.conf.j2）

| 定数 | 値 | 用途 | evidence |
|-----|-----|------|---------|
| DEVICE_INTERNAL_COMMUNITY（list 名） | `DEVICE_INTERNAL_COMMUNITY` | `bgp community-list standard` の名前。内部経路の識別に使用 | `policies.conf.j2:34` |
| DEVICE_INTERNAL_FALLBACK_COMMUNITY（list 名） | `DEVICE_INTERNAL_FALLBACK_COMMUNITY` | フォールバック経路の識別 community-list | `policies.conf.j2:35` |
| LOCAL_ANCHOR_ROUTE_COMMUNITY（list 名） | `LOCAL_ANCHOR_ROUTE_COMMUNITY` | local anchor route の deny 用 community-list | `policies.conf.j2:36` |
| NO_EXPORT（list 名） | `NO_EXPORT` | `bgp community-list standard NO_EXPORT permit no-export`。local-preference 80 処理に使用 | `policies.conf.j2:37` |

### local-preference ハードコード値（policies.conf.j2）

| 定数 | 値 | 用途 | evidence |
|-----|-----|------|---------|
| NO_EXPORT route の local-preference | `80` | `chassis-packet` 時の `FROM_BGP_INTERNAL_PEER_V4 permit 2` / `V6 permit 3` で NO_EXPORT community 経路に設定 | `policies.conf.j2:45,65` |

### Loopback 依存定数（managers_bgp.py）

| 定数 | 値 | 用途 | evidence |
|-----|-----|------|---------|
| internal peer deps 追加 loopback | `"Loopback4096"` | `peer_type == 'internal'` のときのみ deps に追加。他の peer_type にはない固有依存 | `managers_bgp.py:146` |

## スキャン証跡

- `internal/instance.conf.j2` 全行精読: timers 3 10、connect 10 のハードコード確認
- `internal/peer-group.conf.j2` 全行精読: INTERNAL_PEER_V4/V6 peer-group 名、allowas-in 1、send-community、soft-reconfiguration inbound、ttl-security hops 1 確認
- `internal/policies.conf.j2` 全行精読: FROM/TO_BGP_INTERNAL_PEER_V4/V6 全 route-map 名、community-list 名 4 件、local-preference 80 確認
- `tests/data/internal/policies.conf/param_chasiss_packet.json`: constants.bgp.* のテスト参照値確認
- `managers_bgp.py` L145-146: peer_type='internal' 専用 Loopback4096 deps 確認
- 抽出件数: タイマー 3 件 + peer-group 名 2 件 + peer-group 固定設定 4 件 + route-map 名 4 件 + community 定数 5 件 + community-list 名 4 件 + local-preference 1 件 + loopback 定数 1 件 = 計 24 件
