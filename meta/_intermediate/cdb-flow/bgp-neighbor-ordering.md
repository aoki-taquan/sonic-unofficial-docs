# BGP_NEIGHBOR — Phase B 書込み順依存 調査メモ

対象ページ: `docs/reference/config-db/bgp-neighbor.md`
調査日: 2026-05-15

## 調査対象ファイル

| ファイル | 役割 |
|---------|------|
| `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py` | `BGPPeerMgrBase` — BGP_NEIGHBOR の SET/DEL ハンドラ本体 |
| `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/main.py` | bgpcfgd エントリポイント。deps 登録と Manager 初期化順 |
| `sonic-buildimage/dockers/docker-fpm-frr/frr/supervisord/supervisord.conf.j2` | docker-fpm-frr の supervisord 起動順定義 |
| `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py` | frrcfgd 経路の BGP_NEIGHBOR / BGP_GLOBALS 処理 |
| `sonic-swss/fpmsyncd/bgp_eoiu_marker.py` | warm-restart 時の EOR (End-of-RIB) マーカー |
| `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-bgp-neighbor.yang` | YANG: BGP_GLOBALS.vrf_name / BGP_PEER_GROUP leafref 制約 |

## 検出した書込み順依存

### 1. DEVICE_METADATA.bgp_asn 先行必須（最上位依存）

`BGPPeerMgrBase.__init__` (managers_bgp.py:118-126) は以下を `deps` として登録する:

```python
deps = [
    ("CONFIG_DB", CFG_DEVICE_METADATA_TABLE_NAME, "localhost/bgp_asn"),
    ("CONFIG_DB", CFG_DEVICE_METADATA_TABLE_NAME, "localhost/type"),
    ("CONFIG_DB", CFG_LOOPBACK_INTERFACE_TABLE_NAME, "Loopback0"),
    ("CONFIG_DB", CFG_BGP_DEVICE_GLOBAL_TABLE_NAME, "tsa_enabled"),
    ("CONFIG_DB", CFG_BGP_DEVICE_GLOBAL_TABLE_NAME, "idf_isolation_state"),
    ("LOCAL", "local_addresses", ""),
    ("LOCAL", "interfaces", ""),
]
```

`Manager` 基底クラスは deps が未解決のうちは `set_handler()` を呼ばない。`DEVICE_METADATA|localhost|bgp_asn` が存在しない限り BGP_NEIGHBOR の SET は処理されない。

- evidence: `managers_bgp.py:118-126`

### 2. LOOPBACK_INTERFACE|Loopback0 先行必須（add_peer ガード）

`add_peer()` (managers_bgp.py:184-189) は Loopback0 の IPv4 アドレスを確認する:

```python
for loopback in self.loopbacks:
    lo_ipv4 = self.get_lo_ipv4(loopback + "|")
    if (lo_ipv4 is None and "bgp_router_id"
        not in self.directory.get_slot("CONFIG_DB", CFG_DEVICE_METADATA_TABLE_NAME)["localhost"]):
        log_warn(loopback + " ipv4 address is not presented yet and bgp_router_id not configured")
        return False
```

Loopback0 に IPv4 prefix が設定されておらず、かつ `DEVICE_METADATA.localhost.bgp_router_id` も未設定の場合、`add_peer` は `return False`（再試行待ち）する。

- **順序制約**: `LOOPBACK_INTERFACE|Loopback0|<ipv4_prefix>` の書き込み → BGP_NEIGHBOR SET の順。もしくは `DEVICE_METADATA.bgp_router_id` を先に設定すること。
- evidence: `managers_bgp.py:184-189`

### 3. local_addr が参照するインタフェース先行必須

`add_peer()` (managers_bgp.py:194-202):

```python
if "local_addr" not in data:
    log_warn("Peer %s. Missing attribute 'local_addr'" % nbr)
else:
    data["local_addr"] = str(netaddr.IPNetwork(str(data["local_addr"])).ip)
    interface = self.get_local_interface(data["local_addr"])
    if not interface:
        log_debug("Peer '%s' with local address '%s' wait for the corresponding interface to be set" % print_data)
        return False
```

`local_addr` フィールドが設定されている場合、そのアドレスを持つインタフェース（`LOCAL|local_addresses` ディレクトリ）が先に存在していなければ `return False`。`local_addr` が未設定の場合は `log_warn` のみで続行（FRR が送信元アドレスを自動選択）。

- **順序制約**: `local_addr` に対応するインタフェース (`INTERFACE|<intf>|<ip>` または `LOOPBACK_INTERFACE|<lo>|<ip>`) の書き込み → BGP_NEIGHBOR SET の順。
- evidence: `managers_bgp.py:194-202`, `managers_bgp.py:526-544`

### 4. DEVICE_NEIGHBOR_METADATA 先行必須（check_neig_meta=True 時）

`add_peer()` (managers_bgp.py:219-223):

```python
if self.check_neig_meta:
    neigmeta = self.directory.get_slot("CONFIG_DB", CFG_DEVICE_NEIGHBOR_METADATA_TABLE_NAME)
    if 'name' in data and data["name"] not in neigmeta:
        log_info("DEVICE_NEIGHBOR_METADATA is not ready for neighbor '%s' - '%s'" % (nbr, data['name']))
        return False
```

`general` ピアタイプ（BGP_NEIGHBOR テーブル）は `check_neig_meta=True`（main.py:87）。`constants.yml` の `bgp.use_neighbors_meta=true` が設定されている場合、`BGP_NEIGHBOR` の `name` フィールドが DEVICE_NEIGHBOR_METADATA に未登録だと `return False`。

- **順序制約**: `DEVICE_NEIGHBOR_METADATA|<name>` の書き込み → BGP_NEIGHBOR SET の順（`use_neighbors_meta=true` の環境のみ）。
- evidence: `managers_bgp.py:128-143`, `managers_bgp.py:219-223`, `main.py:87`

### 5. BGP_GLOBALS 先行必須（frrcfgd 経路のみ）

`frrcfgd.py:2661-2666` (`__update_bgp`) :

```python
if self.__vrf_based_table(table):
    vrf = prefix
    local_asn = self.__get_vrf_asn(vrf)
    if local_asn is None and (table != 'BGP_GLOBALS' or 'local_asn' not in data):
        syslog.syslog(syslog.LOG_DEBUG, 'ignore table {} update because local_asn for VRF {} was not configured'.format(table, vrf))
        continue
```

`DEVICE_METADATA.frr_mgmt_framework_config = true` の環境（frrcfgd 経路）では、`BGP_GLOBALS|<vrf>|local_asn` が未設定のまま `BGP_NEIGHBOR` を書き込むと、frrcfgd が当該エントリを **サイレントに無視**する（LOG_DEBUG のみ）。

- **順序制約**: `BGP_GLOBALS|<vrf>` (local_asn 付き) → `BGP_NEIGHBOR|<vrf>|<neighbor>` の順。
- evidence: `frrcfgd.py:2660-2666`

### 6. BGP_PEER_GROUP 先行必須（frrcfgd 経路, peer_group_name 参照時）

`frrcfgd.py:2828-2832`:

```python
if vrf not in self.bgp_peer_group or dval.data not in self.bgp_peer_group[vrf]:
    syslog.syslog(syslog.LOG_ERR, 'invalid peer-group %s was referenced' % dval.data)
    continue
```

`BGP_NEIGHBOR` の `peer_group_name` フィールドが存在する peer-group を参照していない場合、frrcfgd は `LOG_ERR` を出してスキップする（neighbor は未作成のまま）。

- **順序制約**: `BGP_PEER_GROUP|<vrf>|<pg_name>` → `BGP_NEIGHBOR|<vrf>|<neighbor>` (peer_group_name 設定時) の順。
- evidence: `frrcfgd.py:2828-2832`

### 7. SET → DEL 順序：BGP セッション即断の副作用

`del_handler()` (managers_bgp.py:446-492):
- DEL が来ると `no neighbor <addr>` を vtysh 経由で FRR に発行し、BGP NOTIFICATION を送信して session を即座に切断する。
- `dynamic` / `sentinels` タイプでは DEL の前に `no bgp listen range ...` を先に発行する（FRR 10.1 以降の要件）。
- BGP_NEIGHBOR 削除後は STATE_DB の `BGP_PEER_CONFIGURED_TABLE` からも削除される。

SET → DEL の間隔が短いと（再設定など）FRR セッションが一旦切断されてから再接続待ちになる。FRR の Graceful-Restart（`bgp graceful-restart` は BGP_GLOBALS レベルで設定）が有効でも、`del_handler` → `no neighbor` → 即断のフローは変わらない。

- **順序制約**: 同一 neighbor の DEL → SET を短時間で行う場合、FRR 側の session establish タイムアウト (connect retry) が発生する。`conn_retry` 値は bgpcfgd 経路では無視（ハードコード 10 秒）。

### 8. supervisord 起動順（bgpcfgd が bgpd 後に起動）

`supervisord.conf.j2:167-179` (docker-fpm-frr):

```ini
[program:bgpcfgd]  # または frrcfgd（frr_mgmt_framework_config=true 時）
priority=6
dependent_startup_wait_for=bgpd:running
```

起動順: `rsyslogd` (p=1) → `zebra` / `mgmtd` (p=4) → `bgpd` (p=5) → `bgpcfgd` / `fpmsyncd` (p=6)

bgpcfgd は bgpd が running 状態になった後にのみ起動する。bgpd が起動する前に CONFIG_DB に BGP_NEIGHBOR を書き込んでも問題はないが、FRR への反映は bgpcfgd 起動後まで遅延する。

- evidence: `docker-fpm-frr/frr/supervisord/supervisord.conf.j2:167-179`

### 9. warm-restart / warm-reboot 挙動

`bgp_eoiu_marker.py` は warm-reboot 時に BGP の EOR (End-of-RIB) 状態を監視し、STATE_DB の `BGP_STATE_TABLE|IPv4|eoiu` / `BGP_STATE_TABLE|IPv6|eoiu` に `state=reached` を書き込む。これにより `fpmsyncd` が経路 reconcile を開始する。

- `WARM_RESTART.bgp.bgp_eoiu = "true"` が設定されている場合のみ `bgp_eoiu_marker` が supervisord に登録される（supervisord.conf.j2:239-253）。
- bgpcfgd はインメモリの `self.peers` セットを FRR の running-config（`show bgp vrfs json`）から初期読み込み（`load_peers()`）する。warm-restart 後も CONFIG_DB の全エントリを replay して自動復元する。
- **CONFIG_DB の BGP_NEIGHBOR 自体の永続化**: CONFIG_DB は Redis で永続化されているため、warm-reboot 後も設定は保持される。bgpcfgd 再起動後は `load_peers()` で FRR 側の現状を読み、差分を適用する。

- evidence: `bgp_eoiu_marker.py:1-206`, `managers_bgp.py:571-597`, `supervisord.conf.j2:239-253`

## 順序依存サマリ

| # | 依存関係 | 方向 | 対象パス | 違反時の挙動 |
|---|----------|------|---------|------------|
| 1 | `DEVICE_METADATA.localhost.bgp_asn` 存在 | 強制先行（deps） | bgpcfgd 全経路 | Manager が set_handler を呼ばない（無限再試行待ち） |
| 2 | `LOOPBACK_INTERFACE\|Loopback0\|<ipv4>` または `bgp_router_id` | 強制先行 | bgpcfgd 経路 | `add_peer` が `return False`（再試行待ち） |
| 3 | `local_addr` に対応するインタフェース設定 | 強制先行 | bgpcfgd 経路 | `add_peer` が `return False`（再試行待ち） |
| 4 | `DEVICE_NEIGHBOR_METADATA\|<name>` | 強制先行（条件付き） | bgpcfgd / use_neighbors_meta=true 時 | `return False`（再試行待ち） |
| 5 | `BGP_GLOBALS\|<vrf>` (local_asn) | 強制先行 | frrcfgd 経路のみ | LOG_DEBUG のみ / サイレント無視 |
| 6 | `BGP_PEER_GROUP\|<vrf>\|<pg>` | 強制先行（peer_group_name 使用時） | frrcfgd 経路のみ | LOG_ERR / neighbor 未作成 |
| 7 | DEL → SET の短時間繰り返し | 副作用 | 全経路 | BGP session 一時断（connect retry 10 秒） |
| 8 | bgpd running → bgpcfgd 起動 | supervisord 制御 | 起動時 | bgpcfgd は bgpd 起動前に FRR 操作不可 |
| 9 | warm-restart EOR 待機 | 条件付き遅延 | warm-reboot 時 | `bgp_eoiu_marker` が EOR 完了を STATE_DB に通知するまで fpmsyncd が経路 reconcile を保留 |
