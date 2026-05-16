# BGP_PEER_GROUP 失敗挙動 (Phase D)

intermediate for `docs/reference/config-db/bgp-peer-group.md` Phase D block.

## 調査対象ソース

- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py` (全行スキャン)
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py` (BGPPeerMgrBase / BGPPeerGroupMgr)

スキャン範囲 (失敗・retry 分岐に関わる箇所):

- `BGPConfigDaemon.__update_bgp()` L2640–2874 (メインディスパッチループ)
- `BGPConfigDaemon.__update_bgp()` — VRF guard L2656–2662
- `BGPConfigDaemon.__update_bgp()` — BGP_PEER_GROUP ブランチ L2790–2864
- `g_run_command()` / `BgpdClientMgr.__create_frr_client()` L47–63, L181–218
- `BGPPeerGroupMgr.update_policy()` L40–52
- `BGPPeerGroupMgr.update_pg()` L54–73
- `BGPPeerMgrBase.add_peer()` L172–243

---

## 失敗パス一覧

### 1. BGP_GLOBALS の `local_asn` 未設定 → silent skip、FRR 未投入、retry なし

`frrcfgd.py:2656–2662` (`__update_bgp`):

```python
if self.__vrf_based_table(table):
    vrf = prefix
    local_asn = self.__get_vrf_asn(vrf)
    if local_asn is None and (table != 'BGP_GLOBALS' or 'local_asn' not in data):
        syslog.syslog(syslog.LOG_DEBUG, 'ignore table {} update because local_asn for VRF {} was not configured'.
                format(table, vrf))
        continue
```

`BGP_PEER_GROUP` は `vrf_tables`（L2136–2140）に含まれるため VRF guard が必ず評価される。対象 VRF の `BGP_GLOBALS.local_asn` が未設定なら、FRR vtysh コマンドは一切発行されず LOG_DEBUG のみで `continue`。CONFIG_DB エントリは残存する。**自動 retry なし** — `BGP_GLOBALS` が後から書かれても `BGP_PEER_GROUP` は自動再投入されない（`__apply_dep_vrf_table` は `BGP_GLOBALS.local_asn` SET 時に `ROUTE_REDISTRIBUTE` のみを再適用し `BGP_PEER_GROUP` は含まない: L2704）。

### 2. peer-group の FRR 自動作成 vtysh 失敗 → LOG_ERR + continue、retry なし

`frrcfgd.py:2793–2801` (`__update_bgp` — BGP_PEER_GROUP ブランチ):

```python
if is_peer_group:
    if key not in self.bgp_peer_group.setdefault(vrf, {}):
        command = ['vtysh', '-c', 'configure terminal',
                   '-c', 'router bgp {} vrf {}'.format(local_asn, vrf),
                   '-c', 'neighbor {} peer-group'.format(key)]
        if not self.__run_command(table, command):
            syslog.syslog(syslog.LOG_ERR, 'failed to create peer-group %s for VRF %s' % (key, vrf))
            continue
```

SET 受信時、frrcfgd は FRR に peer-group が存在しなければ属性コマンドより先に `neighbor <pg_name> peer-group` を自動発行する。`__run_command` が `False` を返す（vtysh 終了コード ≠ 0 / bgpd 接続エラー）と LOG_ERR `'failed to create peer-group %s for VRF %s'` を出力し、**属性設定全体を skip** して `continue`。`self.bgp_peer_group[vrf]` には peer-group エントリが追加されないため、次回同じ SET が届いても再度 vtysh 発行を試みる（再試行的動作だが、外部から再 SET が必要）。

### 3. 属性コマンド (`key_map.run_command`) 失敗 → LOG_ERR + continue、retry なし

`frrcfgd.py:2819–2821` (`__update_bgp`):

```python
if not key_map.run_command(self, table, data, cmd_prefix, key):
    syslog.syslog(syslog.LOG_ERR, 'failed running BGP neighbor config command')
    continue
```

peer-group の属性 vtysh コマンド群（`keepalive`, `holdtime`, `asn` 等）が bgpd 側でエラーを返した場合、LOG_ERR `'failed running BGP neighbor config command'` が出力される。**自動 retry なし** — 部分適用が発生し得る（先行コマンドが成功、後続コマンドが失敗の場合、FRR と CONFIG_DB の整合性が失われる）。

### 4. ROUTE_MAP 未準備 → bgpd 構文エラー返却、LOG_ERR、retry なし

`frrcfgd.py:2669–2676` で `ROUTE_MAP` テーブル変更時は `match_prefix_set` / `match_next_hop_set` の af-mode を解決するが、`BGP_PEER_GROUP` の属性処理（`cmn_key_map`）には route-map 参照フィールドは含まれない（peer-group レベルの route-map は `BGP_PEER_GROUP_AF` 側で管理）。

ただし `bgpcfgd` 経路（`BGPPeerGroupMgr.update_pg`）では Jinja2 テンプレート内で ROUTE_MAP 由来の policy を `peer-group.conf.j2` に展開する。このテンプレートレンダリングが `jinja2.TemplateError` を投げると:

```python
# managers_bgp.py L64–66
except jinja2.TemplateError as e:
    log_err("Can't render peer-group template: '%s': %s" % (name, str(e)))
    return False
```

`update_pg()` が `False` を返す。呼び出し元 `update()` (L36–38) も `False` を返すが、`add_peer()` は戻り値を確認せず処理を継続する（L227）。したがって peer-group テンプレートのレンダリング失敗は **peer 追加自体をブロックしない** が FRR への peer-group 設定が未投入になる。

### 5. BGPPeerGroupMgr.update_policy() Jinja2 エラー → log_err + return False、retry なし

`managers_bgp.py:46–50` (`BGPPeerGroupMgr.update_policy`):

```python
try:
    policy = self.policy_template.render(**kwargs)
except jinja2.TemplateError as e:
    log_err("Can't render policy template name: '%s': %s" % (name, str(e)))
    return False
```

routing policy テンプレート（`policies.conf.j2`）のレンダリング失敗。`log_err` のみで `return False`。`update()` が `False` を返すが `add_peer()` は継続するため peer-group policy が FRR に反映されない。

### 6. Loopback0 アドレス / bgp_router_id 未準備 → return False、retry なし (bgpcfgd 経路)

`managers_bgp.py:184–189` (`BGPPeerMgrBase.add_peer`):

```python
for loopback in self.loopbacks:
    lo_ipv4 = self.get_lo_ipv4(loopback + "|")
    if (lo_ipv4 is None and "bgp_router_id"
        not in self.directory.get_slot("CONFIG_DB", swsscommon.CFG_DEVICE_METADATA_TABLE_NAME)["localhost"]):
        log_warn(loopback + " ipv4 address is not presented yet and bgp_router_id not configured")
        return False
```

`bgpcfgd` 経路で Loopback0 の IPv4 アドレスも `bgp_router_id` も未設定の場合、`add_peer()` が `False` を返して peer-group テンプレートを一切投入しない。Manager 基底クラスが `set_handler` の `False` 戻りを受け取り、エントリを保留キューに戻す（deps 充足まで retry）。

### 7. bgpd ソケット接続失敗 (起動時) → 最大 100 回 retry、超過で frrcfgd 起動失敗

`frrcfgd.py:186–194` (`BgpdClientMgr.__create_frr_client`):

```python
retry_cnt = 0
while True:
    try:
        sock.connect(serv_addr)
        break
    except socket.error as msg:
        syslog.syslog(syslog.LOG_ERR, 'failed to connect to frr daemon %s: %s' % (daemon, msg))
        retry_cnt += 1
        if retry_cnt > 100 or not main_loop:
            syslog.syslog(syslog.LOG_ERR, 're-tried too many times, give up')
            return False
        time.sleep(2)
        continue
```

起動時に `/run/frr/bgpd.vty` への connect を最大 **100 回 / 2秒間隔 (約 200 秒)** で retry。超過時 `RuntimeError` で frrcfgd 起動失敗 — `BGP_PEER_GROUP` を含む全 BGP テーブルが一切処理されない。

---

## まとめ — retry / rollback の有無

| # | 失敗トリガー | retry | rollback | ログ |
|---|------------|------|---------|------|
| 1 | `local_asn` 未設定の VRF guard | なし | — | LOG_DEBUG (silent skip) |
| 2 | peer-group 自動作成 vtysh 失敗 | なし (外部 re-SET で再試行可) | なし | LOG_ERR `failed to create peer-group %s for VRF %s` |
| 3 | 属性コマンド vtysh 失敗 | なし | なし (部分適用あり) | LOG_ERR `failed running BGP neighbor config command` |
| 4 | bgpcfgd: peer-group Jinja2 テンプレートエラー | なし | なし | log_err `Can't render peer-group template` |
| 5 | bgpcfgd: policy Jinja2 テンプレートエラー | なし | なし | log_err `Can't render policy template name` |
| 6 | bgpcfgd: Loopback0 / bgp_router_id 未準備 | deps 充足まで保留 (Manager 基底) | — | log_warn |
| 7 | bgpd socket 接続失敗 (起動時) | 100 回 / 2秒 | — | LOG_ERR × 最大 100 |

### 設計観察

- **frrcfgd (`BGP_PEER_GROUP`) は運用中 retry を持たない**: 失敗時は CONFIG_DB エントリを残したまま `continue` で次イベントへ進む
- **peer-group 自動作成は `BGP_PEER_GROUP` SET 時のみ**: 先行 SET がなければ `BGP_PEER_GROUP_AF` 投入が失敗する
- **rollback は全経路で未実装**: 部分失敗時 FRR と CONFIG_DB の整合性は保証されない
- **bgpcfgd 経路のみ deps 保留あり**: `BGPPeerMgrBase` が `DEVICE_METADATA.bgp_asn` 等の deps 充足まで `set_handler` を保留する
- **推奨書き込み順**: `BGP_GLOBALS` → `ROUTE_MAP` → `BGP_PEER_GROUP` → `BGP_NEIGHBOR`
