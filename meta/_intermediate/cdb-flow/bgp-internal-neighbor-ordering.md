# BGP_INTERNAL_NEIGHBOR — Phase B 書込み順依存スキャンノート

対象テーブル: `BGP_INTERNAL_NEIGHBOR`
Consumer: `bgpcfgd` / `BGPPeerMgrBase(peer_type="internal")` (`sonic-bgpcfgd/bgpcfgd/managers_bgp.py`)
スキャン範囲: `managers_bgp.py` 全行精読、`frrcfgd/frrcfgd.py` 起動・BGP_GLOBALS ハンドラ精読、`policies.conf.j2` 全行精読

---

## 検出した順序依存・タイミング依存

### 1. DEVICE_METADATA.bgp_asn 先行必須（deps 宣言 + add_peer 参照）

`BGPPeerMgrBase.__init__()` は `deps` リストに以下を登録する:

```python
("CONFIG_DB", swsscommon.CFG_DEVICE_METADATA_TABLE_NAME, "localhost/bgp_asn"),
("CONFIG_DB", swsscommon.CFG_DEVICE_METADATA_TABLE_NAME, "localhost/type"),
```

`add_peer()` (managers_bgp.py L192) は:

```python
bgp_asn = self.directory.get_slot("CONFIG_DB", swsscommon.CFG_DEVICE_METADATA_TABLE_NAME)["localhost"]["bgp_asn"]
```

として `bgp_asn` を必須参照する。この値が存在しない場合、`deps` チェックによってテーブルイベント自体がハンドラに届かない（ManagerBase のフレームワークが deps 充足まで `set_handler` を保留する）。

**順序依存**: `DEVICE_METADATA|localhost.bgp_asn` は `BGP_INTERNAL_NEIGHBOR` エントリより**先行して** CONFIG_DB に書かれていなければならない。

evidence: `managers_bgp.py` L118-119, L192

---

### 2. DEVICE_METADATA.type 先行必須（deps 宣言）

`deps` リストに `"localhost/type"` が含まれる (L120)。`type` フィールドが未設定の場合も deps 充足待ちになる。

**順序依存**: `DEVICE_METADATA|localhost.type` が `bgp_asn` と同時に存在していること（通常 minigraph 生成で同時書き込みされるため実害は少ないが、手動書き込み時は注意）。

evidence: `managers_bgp.py` L120

---

### 3. Loopback0 先行必須（deps 宣言 + ipv4 チェック）

`deps` リストに:

```python
("CONFIG_DB", swsscommon.CFG_LOOPBACK_INTERFACE_TABLE_NAME, "Loopback0"),
```

が含まれる (L121)。さらに `add_peer()` (L184-189) では:

```python
for loopback in self.loopbacks:
    lo_ipv4 = self.get_lo_ipv4(loopback + "|")
    if (lo_ipv4 is None and "bgp_router_id"
            not in self.directory.get_slot("CONFIG_DB", ...["localhost"]):
        log_warn(loopback + " ipv4 address is not presented yet ...")
        return False
```

Loopback0 の IPv4 アドレスが設定されておらず、かつ `DEVICE_METADATA.bgp_router_id` も未設定の場合は `return False`（再試行待ち）。

**順序依存**: `LOOPBACK_INTERFACE|Loopback0|<IPv4>` エントリ（またはフォールバックとして `DEVICE_METADATA.bgp_router_id`）が `BGP_INTERNAL_NEIGHBOR` エントリより先行している必要がある。

evidence: `managers_bgp.py` L121, L184-189

---

### 4. Loopback4096 先行必須（peer_type="internal" 専用 dep）

`peer_type == 'internal'` の場合のみ:

```python
deps.append(("CONFIG_DB", swsscommon.CFG_LOOPBACK_INTERFACE_TABLE_NAME, "Loopback4096"))
```

が追加される (L145-146)。`BGP_INTERNAL_NEIGHBOR` はこの専用ハンドラで処理されるため、`Loopback4096` エントリが CONFIG_DB に存在するまでテーブルイベントは保留される。

`policies.conf.j2` (L7) も:

```jinja
{% set lo4096_ipv4 = get_ipv4_loopback_address(CONFIG_DB__LOOPBACK_INTERFACE, "Loopback4096") | ip %}
```

として Loopback4096 IPv4 を参照し、`sub_role == 'BackEnd'` 時の `originator-id` 設定に使用する。

**順序依存**: `LOOPBACK_INTERFACE|Loopback4096|<IPv4>` は `BGP_INTERNAL_NEIGHBOR` エントリより**先行**していなければならない。通常、minigraph 生成時はマルチ ASIC プラットフォームで自動生成されるが、手動 CONFIG_DB 操作では注意が必要。

evidence: `managers_bgp.py` L145-146; `policies.conf.j2` L7

---

### 5. local_addr に対応する INTERFACE 先行必須（interface 解決待ち）

`add_peer()` (L194-202):

```python
if "local_addr" not in data:
    log_warn("Peer %s. Missing attribute 'local_addr'" % nbr)
else:
    data["local_addr"] = str(netaddr.IPNetwork(str(data["local_addr"])).ip)
    interface = self.get_local_interface(data["local_addr"])
    if not interface:
        log_debug("Peer '%s' with local address '%s' wait for the corresponding interface to be set" % ...)
        return False
```

`get_local_interface()` (L526-542) は `LOCAL.local_addresses` と `LOCAL.interfaces` ディレクトリスロットを参照し、`local_addr` に対応する interface が登録済みかを確認する。未登録の場合は `return False`（再試行待ち、イベントは破棄されず `set_handler` が次回イベントで再試行される）。

`deps` にも:

```python
("LOCAL", "local_addresses", ""),
("LOCAL", "interfaces", ""),
```

が含まれる (L124-125)。これらは `PORT` / `PORTCHANNEL` / `INTERFACE` テーブルのイベントによって `LOCAL` スロットに書き込まれる。

**順序依存**: `BGP_INTERNAL_NEIGHBOR` エントリの `local_addr` に対応する `INTERFACE` / `PORTCHANNEL_INTERFACE` / `LOOPBACK_INTERFACE` エントリが先行して CONFIG_DB に存在していなければ peer 確立が延期される。

evidence: `managers_bgp.py` L124-125, L194-202, L526-542

---

### 6. BGP_GLOBALS.local_asn 先行必須（frrcfgd — bgpd ルーターインスタンス生成順）

`frrcfgd.py` (frrcfgd) は FRR 管理フレームワーク側のハンドラ。`BGP_GLOBALS` の `local_asn` を受信すると:

```python
command = ['vtysh', '-c', 'configure terminal',
           '-c', 'router bgp {} vrf {}'.format(dval.data, vrf), ...]
self.bgp_asn[vrf] = dval.data
```

として FRR bgpd に `router bgp <ASN>` インスタンスを生成する (frrcfgd.py L2700-2703)。

VRF に対する他のすべての BGP 設定ハンドラ（BGP_NEIGHBOR 等）は `__get_vrf_asn(vrf)` が `None` を返す間は:

```python
if local_asn is None and (table != 'BGP_GLOBALS' or 'local_asn' not in data):
    syslog.syslog(LOG_DEBUG, 'ignore table ... update because local_asn for VRF ... was not configured')
    continue
```

で**スキップ**される (frrcfgd.py L2659-2662)。

ただし `BGP_INTERNAL_NEIGHBOR` は `bgpcfgd` ハンドラが処理するため `frrcfgd` 側のこのガードは直接は関係しない。しかし `bgpcfgd` テンプレートが生成する FRR コマンドは `router bgp <ASN>` コンテキスト内で実行されるため、FRR bgpd 側に該当 ASN のルーターインスタンスが存在しなければならない。

**順序依存（FRR レイヤ）**: `BGP_GLOBALS|default.local_asn`（デフォルト VRF の ASN）が frrcfgd によって FRR に反映された後に、`bgpcfgd` が `BGP_INTERNAL_NEIGHBOR` を FRR へ送信する必要がある。通常、bgpcfgd の起動タイミングと frrcfgd の適用順で保証されるが、手動で CONFIG_DB を操作する場合は `BGP_GLOBALS` を先に書くこと。

evidence: `frrcfgd.py` L2177-2178, L2658-2662, L2687-2707

---

### 7. bgpd ソケット待ち（frrcfgd 起動時の retry ループ）

`frrcfgd.py` の `BgpdClientMgr.__create_frr_client()` (L181-218):

```python
serv_addr = '/run/frr/%s.vty' % daemon
retry_cnt = 0
while True:
    try:
        sock.connect(serv_addr)
        break
    except socket.error as msg:
        retry_cnt += 1
        if retry_cnt > 100 or not main_loop:
            ...return False
        time.sleep(2)
        continue
```

各 FRR デーモン（`bgpd`, `zebra`, `staticd`, `bfdd`, `ospfd`, `pimd`, `mgmtd`）のソケット `/run/frr/<daemon>.vty` が存在するまで最大 100 回 × 2秒 = 200秒 リトライする。bgpd が起動完了してソケットを作成するまで、frrcfgd は FRR への設定配信を一切開始できない。

**順序依存（プロセス起動順）**: `docker-fpm-frr` 内で bgpd プロセスが `vty` ソケットを公開した後でなければ、frrcfgd/bgpcfgd からの設定投入は待機状態になる。コンテナ起動直後の数秒間、CONFIG_DB にエントリが存在しても FRR への反映は遅延する。

evidence: `frrcfgd.py` L183-200

---

### 8. bgpcfgd ハンドラ起動順（peer_type 登録順）

`managers_bgp.py` の `BGPPeerMgrBase.__init__()` が複数 peer type でインスタンス化される（`main.py` 参照）:

- `BGPPeerMgrBase(peer_type="internal")` で `BGP_INTERNAL_NEIGHBOR` ハンドラが登録される
- `post_dependencies_init()` (L245-268): 最初の `set_handler` 呼び出し時に遅延初期化される（`post_dependencies_init_complete = False` で初期化、L101）

`post_dependencies_init()` は `additional_loopbacks.conf.j2` が存在すれば追加 loopback リストを拡張する。この初期化は peer ハンドラの**最初の呼び出し時**に一度だけ実行される。

**順序依存**: deps が充足された直後の最初のイベントで `post_dependencies_init()` が実行されるため、deps（DEVICE_METADATA, Loopback0, Loopback4096）は`add_peer()` 最初の呼び出し前に揃っていること。

evidence: `managers_bgp.py` L101, L181-182, L245-268

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 影響 | 緩和策 |
|---|----------|------|------|--------|
| 1 | DEVICE_METADATA.bgp_asn → BGP_INTERNAL_NEIGHBOR | 先行必須 | deps 未充足でイベント保留 | minigraph が同時書き込み |
| 2 | DEVICE_METADATA.type → BGP_INTERNAL_NEIGHBOR | 先行必須 | deps 未充足 | minigraph が同時書き込み |
| 3 | LOOPBACK_INTERFACE|Loopback0 → BGP_INTERNAL_NEIGHBOR | 先行必須（Loopback0 IPv4 or bgp_router_id） | return False で再試行待ち | bgp_router_id フォールバックあり |
| 4 | LOOPBACK_INTERFACE|Loopback4096 → BGP_INTERNAL_NEIGHBOR | 先行必須（internal 専用） | deps 未充足でイベント保留 | マルチ ASIC minigraph が自動生成 |
| 5 | INTERFACE|PORT|PORTCHANNEL（local_addr対応） → BGP_INTERNAL_NEIGHBOR | 先行必須 | return False で interface 解決待ち | runtime は自動再試行 |
| 6 | BGP_GLOBALS.local_asn → BGP_INTERNAL_NEIGHBOR（FRR レイヤ） | 先行必須 | bgpd の router bgp インスタンスが未作成 | 通常は frrcfgd が先に処理 |
| 7 | bgpd ソケット存在 → frrcfgd/bgpcfgd 設定投入 | 起動順依存 | 最大 200秒 リトライ待ち | docker-fpm-frr の起動シーケンスで保証 |
| 8 | DEVICE_METADATA/Loopback0/Loopback4096 充足 → post_dependencies_init() | 一回性初期化 | 最初の add_peer 時に実行 | deps リスト充足後に自動実行 |

## evidence ファイル

- `sonic-net/sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py`
- `sonic-net/sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`
- `sonic-net/sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/templates/internal/policies.conf.j2`
