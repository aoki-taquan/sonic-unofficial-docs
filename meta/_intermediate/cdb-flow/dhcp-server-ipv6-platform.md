# DHCP_SERVER_IPV6 / dhcp6relay — プラットフォーム差調査

Task F Phase H: `DHCP_SERVER_IPV6` テーブルおよび DHCPv6 リレー (`dhcp6relay`) のプラットフォーム差を `sonic-dhcp-relay` と `sonic-buildimage` から精読した結果。

## 結論

**3 点のプラットフォーム差あり**:

1. **DualToR 構成**: `dhcp6relay` が `-u Loopback0` オプションで起動し、MUX ケーブル状態（standby/active）によってクライアントパケットの転送を制御する
2. **SmartSwitch DPU**: `dhcp6relay` 自体は DPU 対応コードを持たない。DHCPv4 側 (`dhcp4relay`) が SmartSwitch/DPU 固有処理を持つのと対照的に、DHCPv6 リレーは DPU 経路を実装していない
3. **IPv6 link-local アドレス (LLA)**: LLA 生成完了をポーリングして待機する固有ロジックがある（60 秒タイマー）

## 根拠

### 1. DualToR — Loopback ソケットによる MUX 状態制御

`dhcpv6-relay.agents.j2` (sonic-buildimage) の行 16:

```jinja2
{% if 'subtype' in DEVICE_METADATA['localhost'] and DEVICE_METADATA['localhost']['subtype'] == 'DualToR' %} -u Loopback0 {% endif %}
```

`DEVICE_METADATA.localhost.subtype == "DualToR"` の場合のみ `dhcp6relay -u Loopback0` として起動する。`-u` オプションが渡ると `main.cpp:27` で `dual_tor_sock = true` がセットされる。

この flag が true の場合:

- `relay.cpp:1270-1285`: `prepare_lo_socket("Loopback0")` で Loopback0 GUA アドレスに追加ソケットを作成し、`server_callback_dualtor` イベントを登録する
- `relay.cpp:913-921`: `client_callback` 内で `HW_MUX_CABLE_TABLE|<intf>` を `hget(intf, "state", state)` し、`state == "standby"` の場合はパケット転送をスキップする（active トール側のみが中継を行う）
- `relay.cpp:1411-1418`: `lla_check_callback` 内で `!dual_tor_sock` の場合のみ `server_callback` を通常ソケットに登録し、DualToR 時は Loopback ソケット専用の `server_callback_dualtor` を使う

**影響**: DualToR 以外 (通常 T0/T1 等) では `-u` オプションなし、Loopback ソケット不使用、MUX 状態チェックなし。

### 2. SmartSwitch DPU — dhcp6relay は非対応

`dhcp4relay/src/dhcp4relay.cpp` には `is_SmartSwitch` フラグと `dpu` インターフェース判定（`dhcp4relay_mgr.cpp`）が実装されている。`DPUS` テーブルの監視、`bridge-midplane` MAC 取得、DPU 向けの GIADDR 書き換えが DHCPv4 リレーには存在する。

一方、`dhcp6relay/src/` にはこれらの実装が**一切存在しない**:

- `grep "SmartSwitch\|DPU\|dpu\|midplane\|multi_asic\|namespace" dhcp6relay/src/*.cpp` → 0 ヒット
- `relay.h` にも `is_SmartSwitch` フィールドなし

SmartSwitch 環境での DHCPv6 サービス (DPU へのアドレス配布) については、community master に対応実装がない。

### 3. IPv6 link-local アドレス (LLA) 生成待機

DHCPv4 リレーにはない DHCPv6 固有の起動制約がある。`config_interface.cpp:195-209` の `check_is_lla_ready()`:

```cpp
const std::string cmd = "ip -6 addr show " + vlan + " scope link 2> /dev/null";
// 出力が空でなければ LLA 存在 → true
```

`lla_check_callback` (`relay.cpp:1361-`) が 60 秒タイマーで定期実行され、LLA が未生成の VLAN はソケット作成・イベント登録をスキップする。LLA が生成されると `is_lla_ready = true` としてソケットを動的に追加する。

起動シーケンス上の注意:

- VLAN インターフェースに IPv6 GUA が設定されていても LLA が kernel によって未生成の場合、`prepare_vlan_sockets()` での `lla_sock` バインドが失敗する (`relay.cpp:651-655`)
- `dhcp_relay.service.j2` の `After=teamd.service` は VLAN インターフェース UP を保証するが、LLA (`fe80::`) の kernel 生成は数ミリ秒〜数秒の遅延がある場合があり、タイマーポーリングで吸収している
- multi-asic 構成では `dhcp-relay` コンテナは host 側でのみ動作し、`asicN` namespace を横断しない（`initialize_swss()` は `CONFIG_DB` を引数なしで接続）

### 4. multi-asic — host namespace のみ

`config_interface.cpp:21`:

```cpp
std::shared_ptr<swss::DBConnector> configDbPtr = std::make_shared<swss::DBConnector>("CONFIG_DB", 0);
```

`namespace` 引数を持たない単純な `DBConnector` 生成。`asic0..N` namespace を iterate するコードは存在しない。multi-asic 構成でも `dhcp6relay` は host CONFIG_DB の `DHCP_RELAY` / `VLAN_INTERFACE` のみを参照し、各 ASIC の CONFIG_DB には関与しない。DHCPv6 リレーは pure L3 処理のため ASIC 数に依存しない。

## まとめ

| 観点 | 結果 | 根拠 |
|------|------|------|
| DualToR | 差異あり | `-u Loopback0` オプション、MUX 状態チェック (`relay.cpp:913-921`) |
| SmartSwitch DPU | dhcp6relay 非対応 | `dhcp6relay/src/` に SmartSwitch/DPU コードなし |
| IPv6 LLA 生成待機 | DHCPv6 固有 | `check_is_lla_ready()` + 60 秒タイマー (`relay.cpp:1288-1310`) |
| multi-asic | 影響なし | host CONFIG_DB のみ接続、namespace iterate なし |
| ASIC ベンダー | 影響なし | `dhcp6relay` は純粋 L3 UDP リレー。SAI 非経由 |
