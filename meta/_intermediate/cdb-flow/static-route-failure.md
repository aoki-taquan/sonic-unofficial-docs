# STATIC_ROUTE 失敗挙動調査 (Phase D)

## 調査対象ソース

- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_static_rt.py`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/frr.py`
- `sonic-swss/fpmsyncd/routesync.cpp`

---

## bgpcfgd: StaticRouteMgr 失敗パス

### 1. IpNextHopSet 構築例外 (set_handler)

**トリガー**: nexthop / ifname / blackhole / distance / nexthop-vrf のカンマ区切りリスト長が不一致。

```python
# managers_static_rt.py L57-63
try:
    ip_nh_set = IpNextHopSet(is_ipv6, bkh_list, nh_list, intf_list, dist_list, nh_vrf_list)
    cur_nh_set, cur_route_tag = self.static_routes.get(vrf, {}).get(ip_prefix, ...)
    cmd_list = self.static_route_commands(...)
except Exception as exc:
    log_crit("Got an exception %s: Traceback: %s" % (str(exc), traceback.format_exc()))
    return False
```

**結果**: `return False` により当該静的経路は FRR に設定されない。内部キャッシュ (`static_routes`) も更新されない。

**evidence**: `managers_static_rt.py` L57-63

---

### 2. IpNextHopSet リスト長不一致 (ValueError)

**トリガー**: `IpNextHopSet.__init__()` でフィールドリストの要素数が異なる場合。

```python
# managers_static_rt.py L316-321
nums = {len(x) for x in [bkh_list, ip_list, intf_list, dist_list, vrf_list] if x is not None}
if len(nums) != 1:
    log_err("Lists of next-hop attribute have different sizes: %s" % nums)
    ...
    raise ValueError
```

**結果**: `ValueError` が `set_handler()` の `try/except` でキャッチされ `log_crit` + `return False`。

**evidence**: `managers_static_rt.py` L316-321

---

### 3. nexthop 必須属性未指定 (ValueError)

**トリガー**: `blackhole != 'true'` かつ nexthop IP がゼロ IP かつ interface 名も未指定。

```python
# managers_static_rt.py L273-275
if self.blackhole != 'true' and self.is_zero_ip() and not self.is_portchannel() and len(self.interface.strip()) == 0:
    log_err('Mandatory attribute not found for nexthop')
    raise ValueError
```

**結果**: 当該 nexthop エントリのみ `IpNextHopSet.add()` でスキップ (`IpNextHopSet.__init__()` の `except ValueError: continue`)。他の nexthop は処理継続。

**evidence**: `managers_static_rt.py` L273-275, L325-328

---

### 4. VRF キー解析失敗 (APPL_DB)

**トリガー**: APPL_DB の key が `vrf:prefix` 形式でなく、かつ `ip_network()` でも解析できない場合。

```python
# managers_static_rt.py L176-182
output = key.split(':', 1)
if len(output) < 2:
    log_debug("invalid input in APPL_DB {}".format(key))
    raise ValueError
```

**結果**: `split_key()` が `ValueError` を raise。呼び出し元の `set_handler()` / `del_handler()` が例外で中断。

**evidence**: `managers_static_rt.py` L176-182

---

### 5. BGP ASN 未設定時の redistribute 保留

**トリガー**: 最初の静的経路設定時に `DEVICE_METADATA|localhost|bgp_asn` が CONFIG_DB に存在しない。

```python
# managers_static_rt.py L66-70
if not self.static_routes.get(vrf, {}):
    if self.directory.path_exist("CONFIG_DB", swsscommon.CFG_DEVICE_METADATA_TABLE_NAME, "localhost/bgp_asn"):
        cmd_list.extend(self.enable_redistribution_command(vrf))
    else:
        self.vrf_pending_redistribution.add(vrf)
```

**結果**: `redistribute static` コマンドが保留される。`on_bgp_asn_change()` が bgp_asn 設定を検知した時点で自動適用。それまでは BGP への static route 広告が行われない。

**evidence**: `managers_static_rt.py` L66-70, L254-258

---

## bgpcfgd: FRR vtysh 失敗パス

### 6. vtysh 書き込み失敗

**トリガー**: `vtysh -f <tmpfile>` の戻り値が非 0（FRR デーモン未起動、設定エラー等）。

```python
# frr.py L47-54
command = ["vtysh", "-f", tmp_filename]
ret_code, out, err = run_command(command)
if ret_code != 0:
    err_tuple = tmp_filename, ret_code, out, err
    log_err("ConfigMgr::commit(): can't push configuration from file='%s', rc='%d', stdout='%s', stderr='%s'" % err_tuple)
return ret_code == 0
```

**結果**: エラーログのみ。`push_list()` は失敗を返すが、`set_handler()` / `del_handler()` はこの戻り値をチェックしない。内部キャッシュは既に更新済みのため再試行されない。FRR の running-config と CONFIG_DB が乖離した状態になる。

**evidence**: `frr.py` L47-54

---

### 7. FRR デーモン起動タイムアウト

**トリガー**: bgpcfgd 起動時に FRR デーモンが指定秒数以内に応答しない。

```python
# frr.py L24-31
ret_code, out, err = run_command(["vtysh", "-c", "show daemons"], hide_errors=True)
if ret_code == 0 and all(daemon in out for daemon in self.daemons):
    return
else:
    log_warn("Can't read daemon status from FRR: %s" % str(err))
time.sleep(0.1)
...
raise RuntimeError("FRR daemons hasn't been started in %d seconds" % seconds)
```

**結果**: `RuntimeError` により bgpcfgd プロセスが起動失敗。`systemctl restart bgp` が必要。静的経路は一切 FRR に設定されない。

**evidence**: `frr.py` L16-31

---

## fpmsyncd: routesync.cpp 失敗パス

### 8. VRF ifindex 名前解決失敗

**トリガー**: netlink メッセージの RTA_TABLE に格納された ifindex から VRF デバイス名を取得できない。

```cpp
// routesync.cpp L819-822
if (!getIfName(vrf_index, destipprefix, IFNAMSIZ))
{
    SWSS_LOG_ERROR("Fail to get the VRF name (ifindex %u)", vrf_index);
    return;
}
```

**結果**: 当該 RTM_NEWROUTE メッセージを破棄。APP_DB `ROUTE_TABLE` に反映されない。orchagent / SAI へも到達しない。

**evidence**: `routesync.cpp` L819-822

---

### 9. VRF 名フォーマット不正

**トリガー**: VRF デバイス名が `Vrf` プレフィクスで始まらない（`mgmt` VRF 以外の非標準名など）。

```cpp
// routesync.cpp L828-832
if (memcmp(destipprefix, VRF_PREFIX, strlen(VRF_PREFIX)))
{
    SWSS_LOG_ERROR("Invalid VRF name %s (ifindex %u)", destipprefix, vrf_index);
    return;
}
```

**結果**: 同上。メッセージ破棄。

**evidence**: `routesync.cpp` L828-832

---

### 10. RTN_BLACKHOLE / RTN_UNREACHABLE / RTN_PROHIBIT ルート受信

**トリガー**: FRR から blackhole / unreachable / prohibit 型の static route の netlink メッセージを受信。

```cpp
// routesync.cpp L874-880
case RTN_BLACKHOLE:
case RTN_UNREACHABLE:
case RTN_PROHIBIT:
{
    SWSS_LOG_ERROR("RTN_BLACKHOLE route not expected (%s)", destipprefix);
    return;
}
```

**結果**: fpmsyncd はこれらのルートタイプを APP_DB に書き込まない。blackhole static route は bgpcfgd 経路（CONFIG_DB → FRR vtysh コマンド）で設定する設計のため、fpmsyncd 側での処理は不要。

**evidence**: `routesync.cpp` L874-880

---

## 失敗時のログ確認方法

```bash
# bgpcfgd (static route 関連)
journalctl -u bgp | grep -E "static route|IpNextHop|Got an exception|redistribute"

# fpmsyncd / swss (VRF, RTN_BLACKHOLE)
journalctl -u swss | grep -E "Fail to get the VRF name|Invalid VRF name|RTN_BLACKHOLE"

# vtysh 設定失敗
journalctl -u bgp | grep "can't push configuration"
```

---

## 要約

| 失敗種別 | 発生箇所 | 自動回復 |
|---------|---------|---------|
| 不正 prefix / nexthop 属性 | bgpcfgd `IpNextHopSet` | なし（設定修正が必要） |
| nexthop 必須属性未指定 | bgpcfgd `IpNextHop.__init__` | なし |
| VRF 未解決 (APPL_DB key) | bgpcfgd `split_key` | なし |
| BGP ASN 未設定 | bgpcfgd `set_handler` | あり（ASN 設定後に自動適用） |
| FRR vtysh 失敗 | bgpcfgd `FRR.write()` | なし（プロセス継続だが設定乖離） |
| FRR デーモンタイムアウト | bgpcfgd `FRR.wait_for_daemons()` | bgp サービス再起動が必要 |
| VRF ifindex 解決失敗 | fpmsyncd `routesync.cpp` | なし（netlink メッセージ破棄） |
| VRF 名フォーマット不正 | fpmsyncd `routesync.cpp` | なし |
| blackhole ルートタイプ | fpmsyncd `routesync.cpp` | N/A（設計上 bgpcfgd 経路が正） |
