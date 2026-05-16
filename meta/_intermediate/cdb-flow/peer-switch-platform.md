# PEER_SWITCH — プラットフォーム差調査

Task F Phase H: `PEER_SWITCH` テーブル適用時のプラットフォーム/構成差を `muxorch.cpp` (`sonic-swss`) および `minigraph.py` / YANG モデル (`sonic-buildimage`) から精読した結果。

## 結論

**Dual-ToR 専用テーブル。Single-ToR では存在しない。SmartSwitch DPU では MuxOrch は起動するが PEER_SWITCH は投入されない。**

## 根拠

### 1. Dual-ToR vs Single-ToR

- **Dual-ToR**: `minigraph.py` の `get_peer_switch_info()` (line 465) が `GeminiPeeringLink` または `LibraPeeringLink` リンクメタデータを検出した場合のみ `PEER_SWITCH` テーブルに `address_ipv4` を投入する。`DEVICE_METADATA.localhost.subtype` が `"DualToR"` の場合に該当。
- **Single-ToR**: `GeminiPeeringLink` / `LibraPeeringLink` が存在しないため `get_peer_switch_info()` は空の dict と `None` を返す。`results['PEER_SWITCH']` が空のため CONFIG_DB に PEER_SWITCH エントリは存在しない。`MuxOrch` は orchdaemon 上で起動するが、`mux_peer_switch_` は `IpAddress(0x0)` のまま（isZero() == true）で、MUX_CABLE の処理が defer 状態になる。

#### コード証跡

```python
# minigraph.py:1568-1599
has_peer_switch = False
...
elif name in ["GeminiPeeringLink", "LibraPeeringLink"]:
    has_peer_switch = True
...
if has_peer_switch:
    linkmetas[port]["PeerSwitch"] = lower_tor_hostname (or upper_tor_hostname)
```

```python
# minigraph.py:2186-2193
results['PEER_SWITCH'], mux_tunnel_name, peer_switch_ip = get_peer_switch_info(linkmetas, devices)
if bool(results['PEER_SWITCH']):
    results['DEVICE_METADATA']['localhost']['peer_switch'] = list(results['PEER_SWITCH'].keys())[0]
```

### 2. SmartSwitch DPU

- `DEVICE_METADATA.localhost.subtype` が `"SmartSwitch"` の場合、`orchdaemon.cpp:613` で `DashEniFwdOrch` を追加起動するが、`MuxOrch` は条件なしで起動する（orchdaemon.cpp:471）。
- ただし SmartSwitch トポロジでは `GeminiPeeringLink` / `LibraPeeringLink` は定義されないため、minigraph が PEER_SWITCH を生成しない。
- 結果として SmartSwitch DPU ノードの CONFIG_DB には PEER_SWITCH エントリが存在しない。MuxOrch は起動するが `handlePeerSwitch()` は呼ばれず、MUX_CABLE 処理も無効のまま。

#### コード証跡

```cpp
// orchdaemon.cpp:613
if (gMySwitchSubType == "SmartSwitch")
{
    DashEniFwdOrch *dash_eni_fwd_orch = new DashEniFwdOrch(...);
    // MuxOrch は条件外で無条件に生成済み (line 471)
}
```

### 3. muxorch.cpp 内に platform 分岐なし

`muxorch.cpp` 自体には `platform`、`SmartSwitch`、`DualToR`、`switch_type`、`subtype` の文字列による分岐が存在しない（grep 0 ヒット）。プラットフォーム差は「PEER_SWITCH エントリが CONFIG_DB に存在するか否か」によって暗黙的に決まる。

### 4. multi-ASIC / VOQ chassis

- Dual-ToR 構成は ToR スイッチ（T0）スケールの Single ASIC デバイスを前提とする。
- PEER_SWITCH YANG の `max-elements 1` 制約と Dual-ToR の 2 ノード構成が一致しており、multi-ASIC / VOQ chassis での Dual-ToR 動作は未定義・未テスト。
- `orchdaemon.cpp` が multi-asic 環境で `MuxOrch` を per-ASIC で起動するかは未確認だが、PEER_SWITCH テーブルは host CONFIG_DB に 1 エントリのみ存在する想定。

## まとめ

| 構成 | PEER_SWITCH エントリ | MuxOrch mux_peer_switch_ | MUX_CABLE 動作 |
|------|---------------------|--------------------------|----------------|
| Dual-ToR | 存在（1 エントリ） | peer IPv4 アドレスに設定 | 正常動作 |
| Single-ToR | 存在しない | `0.0.0.0`（isZero=true）のまま | MUX_CABLE が pending |
| SmartSwitch DPU | 存在しない | `0.0.0.0`（isZero=true）のまま | MUX_CABLE 処理なし |
| multi-ASIC / VOQ | 未定義・非サポート | — | — |

PEER_SWITCH テーブルは Dual-ToR 構成を識別するシグナルでもあり、未設定の場合は `mux_peer_switch_.isZero()` が true となって MUX_CABLE の orchagent 処理全体が停止する (`muxorch.cpp:2271`)。
