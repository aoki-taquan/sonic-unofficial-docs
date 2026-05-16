# BGP_MONITORS — Phase H プラットフォーム差異スキャンノート

生成日: 2026-05-16 (Task F Phase H)

## スキャン対象ファイル

| ファイル | パス |
|---|---|
| managers_bgp.py | `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py` |
| frrcfgd.py | `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py` |
| policies.conf.j2 (monitors) | `sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/templates/monitors/policies.conf.j2` |
| peer-group.conf.j2 (monitors) | `sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/templates/monitors/peer-group.conf.j2` |
| instance.conf.j2 (monitors) | `sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/templates/monitors/instance.conf.j2` |

## 検出結果

### 1. peer-group.conf.j2 — 明確なプラットフォーム分岐（3 分岐）

`peer-group.conf.j2` は `DEVICE_METADATA.localhost.switch_type` および `chassisdb.conf` の有無で 3 分岐する:

**分岐 1: VOQ chassis** (`switch_type == 'voq'` かつ `chassisdb_conf_present` または `/usr/share/sonic/platform/chassisdb.conf` が存在)
- `neighbor BGPMON update-source Loopback4096` を使用（L10）
- IPv6 AF も有効化（`neighbor BGPMON activate` + route-map + send-community + maximum-prefix 1）（L23-31）

**分岐 2: chassis-packet** (`switch_type == 'chassis-packet'`)
- 同様に `neighbor BGPMON update-source Loopback4096` を使用（L10, `voq_chassis is defined or chassis-packet`）
- IPv6 AF も有効化（同上）（L23-31）

**分岐 3: 通常スイッチ**（上記以外）
- `loopback0_ipv4` が存在すれば `neighbor BGPMON update-source <loopback0_ipv4>` を使用（L12）
- IPv6 AF を有効化 **しない**（`address-family ipv6` ブロックなし）

### 2. policies.conf.j2 (monitors) — 分岐なし

`FROM_BGPMON deny 10` / `TO_BGPMON permit 10` の 2 行のみ。プラットフォーム条件なし。

### 3. instance.conf.j2 (monitors) — 分岐なし

`neighbor {{ neighbor_addr }} remote-as {{ bgp_asn }}` 他の固定設定のみ。プラットフォーム条件なし。

### 4. managers_bgp.py — monitors peer_type 固有: Loopback4096 依存なし

`peer_type == 'internal'` 時のみ `Loopback4096` が deps に追加される（L145-146）。
`monitors` peer_type にはこの追加がない。全 peer_type 共通の `Loopback0` 依存のみ。

### 5. frrcfgd.py — 非対応（根拠付き）

`BGP_MONITORS` / `BGPMON` / `monitor` キーワードでスキャンしたが一致なし。`frrcfgd.py` はこのテーブルを購読しない。`bgpcfgd` 専用パスのみで処理される。

## 結論

プラットフォーム分岐は **peer-group.conf.j2 に明確に存在**する。
- VOQ chassis / chassis-packet では `Loopback4096` を `update-source` として使用し、IPv6 AF も有効化する
- 通常スイッチでは `Loopback0` IPv4 を `update-source` として使用し、IPv6 AF を有効化しない
`<!-- platform -->` ブロックとして `docs/reference/config-db/bgp-monitors.md` に追加する。
