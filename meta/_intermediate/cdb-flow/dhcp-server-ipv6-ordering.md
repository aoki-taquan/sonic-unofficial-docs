# DHCP_SERVER_IPV6 — Phase B 書込み順依存スキャンノート

対象テーブル: `DHCP_SERVER_IPV6`（未実装）/ 実装済み関連: `DHCP_RELAY`
Consumer: `dhcp6relay` (`sonic-net/sonic-dhcp-relay dhcp6relay/`)
スキャン範囲: `dhcp6relay/src/config_interface.cpp`, `dhcp6relay/src/main.cpp`,
              `sonic-buildimage/dockers/docker-dhcp-relay/dhcpv6-relay.agents.j2`,
              `sonic-buildimage/dockers/docker-dhcp-relay/dhcp-relay.programs.j2`,
              `sonic-buildimage/files/build_templates/dhcp_relay.service.j2`

---

## 検出した順序依存・タイミング依存

### 1. VLAN_INTERFACE に IPv6 アドレスが必須（processRelayNotification の早期スキップ）

- `processRelayNotification()` (config_interface.cpp:130–148) は `DHCP_RELAY` エントリを処理する際、
  対応する VLAN に対して `VLAN_INTERFACE|<vlan>|*` キーを CONFIG_DB から検索し、
  コロン `:` を含む（IPv6）アドレスが 1 件も存在しない場合、ログ警告を出して **そのエントリ全体をスキップ**する。
- **順序依存（強制）**: `DHCP_RELAY|<vlan>` を CONFIG_DB に書く前に、対応する
  `VLAN_INTERFACE|<vlan>|<ipv6-prefix>` エントリが存在しなければ `dhcp6relay` の起動時処理で
  当該 VLAN の中継設定が無視される。後から `VLAN_INTERFACE` に IPv6 アドレスを追加しても
  runtime の dynamic 更新は行われない（dynamic=true 時は "need restart container" ログが出るのみ）。
- **推奨書込み順**: `VLAN` → `VLAN_INTERFACE`（IPv6 アドレス付き）→ `DHCP_RELAY`
- evidence: `dhcp6relay/src/config_interface.cpp:130-148`

### 2. `dhcp6relay` プロセスは VLAN_INTERFACE 内 IPv6 アドレスを要求するが LLA はリレー開始後に確認

- `check_is_lla_ready()` (config_interface.cpp:195–209) は `ip -6 addr show <vlan> scope link` を
  実行して Link-Local Address (LLA) の存在を確認する。
- ただし `processRelayNotification()` での VLAN 受付判定（#1）は LLA ではなく VLAN_INTERFACE
  テーブルの IPv6 グローバルアドレス有無で行われる。LLA チェックはリレーソケット開設時に
  別途実施される。
- **順序依存**: VLAN に IPv6 グローバルアドレスが設定されていれば `DHCP_RELAY` 書込みは受理されるが、
  LLA が未生成（インターフェース未 UP）の場合はソケット開設時に失敗し、リレーが機能しない。
  実運用では `VLAN_INTERFACE` 設定後に `teamd` / カーネルが LLA を自動生成するまでの時間が必要。
- evidence: `dhcp6relay/src/config_interface.cpp:195-209`

### 3. `dhcp-relay.service` の起動順序（systemd レベル）

- `dhcp_relay.service.j2` (sonic-buildimage:files/build_templates/dhcp_relay.service.j2):
  ```
  After=config-setup.service swss.service syncd.service teamd.service
  ```
- `dhcp-relay` コンテナは `swss.service`（SWSS / Redis / CONFIG_DB 初期化）と
  `teamd.service`（PortChannel / VLAN インターフェース UP 管理）の起動完了後に起動する。
- **順序依存**: `dhcp6relay` プロセスが `initialize_swss()` → `get_dhcp()` を呼んで
  CONFIG_DB を読む時点では、上記サービスは既に稼働済みであることが systemd レベルで保証される。
- ただし `After=` は依存の完了順序を定めるが全データの書込み完了を保証しない。
  VLAN_INTERFACE エントリが `config-setup.service` によって CONFIG_DB に投入された後に
  `dhcp-relay` が起動するため、通常は問題ない。
- evidence: `sonic-buildimage/files/build_templates/dhcp_relay.service.j2:4`

### 4. supervisor `dhcp6relay` プログラムエントリの生成条件

- `dhcpv6-relay.agents.j2` / `dhcp-relay.programs.j2` は Jinja2 テンプレートで動的生成される。
  `dhcp6relay` プログラムエントリは以下の条件がすべて真のときのみ supervisord に登録される:
  1. `VLAN_INTERFACE` に VLAN エントリが存在する
  2. 当該 VLAN が `DHCP_RELAY` に存在し `dhcpv6_servers` リストが空でない
  3. `dhcpv6_servers` に有効な IPv6 アドレスが 1 件以上含まれる（`| ipv6` フィルタ通過）
- **順序依存**: コンテナ起動時に上記条件を満たさない場合、`dhcp6relay` プロセスはそもそも
  supervisord に登録されず `autostart=false` ゆえ起動もしない。条件を満たすには
  コンテナ起動前（= `config-setup.service` 完了前）に CONFIG_DB へ
  `VLAN_INTERFACE` + `DHCP_RELAY[vlan].dhcpv6_servers` が揃っていること。
- evidence: `sonic-buildimage/dockers/docker-dhcp-relay/dhcpv6-relay.agents.j2:2-10`
           `sonic-buildimage/dockers/docker-dhcp-relay/dhcp-relay.programs.j2:6-10`

### 5. DHCP_SERVER_IPV6 未実装の影響（本テーブル固有の留意点）

- `DHCP_SERVER_IPV6` テーブルは 2026-05-14 時点で存在しない。
  上記 #1〜#4 の順序依存は `DHCP_RELAY` テーブル経由の **DHCPv6 リレー**に関するものであり、
  将来 `DHCP_SERVER_IPV6` が実装された場合のデーモン（kea-dhcp6 管理デーモン）の
  起動順依存は別途調査が必要。
- IPv4 参考実装（`dhcpservd`）では `DHCP_SERVER_IPV4` → `dhcpservd` → kea-dhcp4 の順で設定が
  投入されるが、同等の DHCPv6 版チェーンは未設計。

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | `VLAN_INTERFACE|<vlan>|<ipv6>` → `DHCP_RELAY|<vlan>` | 先行必須（欠如時エントリ全スキップ） | DHCP_RELAY 書込み前に IPv6 アドレス付与 |
| 2 | VLAN インターフェース UP + LLA 生成 → dhcp6relay ソケット開設 | 先行必須（未 UP 時ソケット開設失敗） | teamd.service 完了後に dhcp-relay 起動（systemd After= で保証）|
| 3 | swss / config-setup / teamd → dhcp-relay.service | systemd After= で保証 | 通常は意識不要 |
| 4 | VLAN_INTERFACE + DHCP_RELAY[vlan].dhcpv6_servers → dhcp6relay 登録 | コンテナ起動前に必須 | config-setup 完了前に CONFIG_DB を揃えること |
| 5 | DHCP_SERVER_IPV6 は未実装 | N/A（将来実装時に再調査） | IPv4 版 dhcpservd を参考に設計 |
