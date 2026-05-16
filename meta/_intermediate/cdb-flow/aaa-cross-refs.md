# AAA テーブル 暗黙参照スキャン (Phase C)

`docs/reference/config-db/aaa.md` の Phase C (暗黙参照) ブロック裏付け資料。

ソースは `sonic-net/sonic-host-services/scripts/hostcfgd` および同 `scripts/ldap.py`。`AAA` テーブル変更時に `hostcfgd` (`AaaCfg`) が間接的に読み出す関連 CONFIG_DB テーブルを列挙する。

## スキャン手順

```
grep -nE 'subscribe\(|init_data\[|config_db\.get_(table|keys)|self\.(tacplus|radius|ldap|tacacs)_(global|servers|server)' \
    .cache/sonic-sources/sonic-host-services/scripts/hostcfgd
```

`hostcfgd` の `load_independent_config()` (L2222-L2231) で `AaaCfg.load()` に渡される 7 テーブル、`modify_conf_file()` 経由で参照される動的解決テーブル群、および `register_callbacks()` (L2470-L2509) で AAA に直接影響する subscribe を抽出。

## 検出された暗黙参照テーブル

### 起動時一括ロード (load_independent_config — hostcfgd:2222-2231)

`AaaCfg.load(aaa, tacacs_global, tacacs_server, radius_global, radius_server, ldap_global, ldap_server)` に渡されるテーブル。

| テーブル | 参照タイミング | 用途 | evidence |
|---|---|---|---|
| `AAA` | load + subscribe | `aaa_update()` の本テーブル | hostcfgd:2223,2470 |
| `TACPLUS` | load + subscribe | TACACS+ global (`passkey` / `auth_type` / `timeout` / `src_intf`) を PAM/NSS テンプレに統合 | hostcfgd:2224,2471 |
| `TACPLUS_SERVER` | load + subscribe | TACACS+ サーバ毎の `priority`/`tcp_port`/`passkey` を `common-auth-sonic.j2` の chain 生成に使用 | hostcfgd:2225,2472 |
| `RADIUS` | load + subscribe | RADIUS global (`nas_ip`/`nas_id`/`src_intf`/`statistics`) を PAM/NSS に統合 | hostcfgd:2226,2473 |
| `RADIUS_SERVER` | load + subscribe | RADIUS サーバ毎の `auth_port`/`passkey`/`retransmit`/`timeout`/`src_intf` | hostcfgd:2227,2474 |
| `LDAP` | load + subscribe | LDAP global (`bind_dn`/`base_dn`/`bind_password`/`search_timeout`/`bind_timeout`) — `is_ldap_config_complete()` の判定対象 | hostcfgd:2228,2475 |
| `LDAP_SERVER` | load + subscribe | LDAP サーバ毎の `port`/`priority` — 空なら `nslcd` を mask | hostcfgd:2229,2476 |

> これら 7 テーブルは AAA の構成材料そのもの (Direction A 入り口テーブル) であり、純粋な「暗黙参照」ではなく **共依存テーブル群** として一括ロードされる。1 テーブルが変化しても `modify_conf_file()` 内で **全 7 テーブル分** の dict を結合してから PAM/NSS テンプレを丸ごと再生成する。

### ランタイム間接読み出し (動的解決)

`AaaCfg` のフィールド読み出し以外で、`modify_conf_file()` 実行中に内部から `config_db.get_keys()` で都度読み出される CONFIG_DB テーブル。

| テーブル | 参照箇所 | 用途 | evidence |
|---|---|---|---|
| `MGMT_INTERFACE` | `get_interface_ip("eth0")` (hostcfgd:600) | RADIUS `nas_ip` 未指定時に `eth0` の管理 IP を取得して `nas_ip` に設定 | hostcfgd:600,670-674 |
| `INTERFACE` | `get_interface_ip("Eth...")` (hostcfgd:586) | `RADIUS_SERVER.src_intf` が物理ポートのとき、その IP を `src_ip` に解決 | hostcfgd:586,694 |
| `VLAN_INTERFACE` | `get_interface_ip("Vlan...")` (hostcfgd:593) | `src_intf` が VLAN のとき IP 解決 | hostcfgd:593 |
| `VLAN_SUB_INTERFACE` | `get_interface_ip` 分岐 (hostcfgd:588,591) | `src_intf` が VLAN sub-interface のとき | hostcfgd:588 |
| `PORTCHANNEL_INTERFACE` | `get_interface_ip("Po...")` (hostcfgd:591) | `src_intf` が PortChannel のとき | hostcfgd:591 |
| `LOOPBACK_INTERFACE` | `get_interface_ip("Loopback...")` (hostcfgd:595) | `src_intf` が Loopback のとき | hostcfgd:595 |
| `DEVICE_METADATA.localhost.hostname` | `aaacfg.hostname_update(self.devmetacfg.hostname)` (hostcfgd:2280) | RADIUS `nas_id` 未指定時にホスト名を代入。`device_metadata_handler` 経由でランタイムにも反映 | hostcfgd:566-577,670,683-686,2280,2406 |

### subscribe レベルでの間接連動

`AaaCfg.aaa_update()` を直接呼ばないが、`AaaCfg` の状態を更新する handler を登録する subscribe。

| テーブル | handler | AAA への影響 | evidence |
|---|---|---|---|
| `MGMT_INTERFACE` | `mgmt_intf_handler` → `aaacfg.handle_radius_nas_ip_chg()` | `eth0` の IP 変化時に RADIUS `nas_ip` を再計算 | hostcfgd:2349,2485 |
| `VLAN_INTERFACE` / `VLAN_SUB_INTERFACE` / `PORTCHANNEL_INTERFACE` / `INTERFACE` | `vlan_intf_handler` / `vlan_sub_intf_handler` / `portchannel_intf_handler` / `phy_intf_handler` | `src_intf` の IP 変化時に RADIUS src_ip を更新 | hostcfgd:2486-2489 |
| `DEVICE_METADATA` | `device_metadata_handler` → `devmetacfg.hostname_update` → `aaacfg.hostname_update` | hostname 変化時に RADIUS `nas_id` を再生成 | hostcfgd:2406,2492 |
| `MGMT_VRF_CONFIG` | `mgmt_vrf_handler` | 管理 VRF 切替時に `eth0` の到達性が変わるため間接的に nas_ip 解決に影響 | hostcfgd:2496 |

### `FIPS` テーブル

`FIPS` テーブルは `AaaCfg` から**直接参照されない**。`FipsCfg` (`hostcfgd:1753-1843`) が独立して購読し OpenSSL FIPS フラグと `ssh`/`telemetry`/`restapi` の再起動を司る。AAA との関連は「同じ `hostcfgd` プロセスがホスト全体のセキュリティ設定を司る」点のみで、CONFIG_DB レベルでの読み合いはない。

> したがって `FIPS` は AAA テーブルの暗黙参照には **含めない**（Phase C 外）。AAA 関連ページからの参照は「同 daemon が扱う隣接テーブル」として `関連 CONFIG_DB` セクションに留める。

### `SSH_SERVER` テーブル

`AaaCfg` からは参照されないが、`PamLimitsCfg.update_config_file()` (hostcfgd:1422-1430) が `DEVICE_METADATA` と併せて読み出す。PAM stack の隣接コンポーネントだが AAA 経路とは独立。

> Phase C 範囲外。AAA ページの cross-refs ブロックには含めず、`関連 CONFIG_DB` で隣接情報として触れるに留める。

## まとめ — `aaa.md` Phase C 記載対象

| カテゴリ | テーブル |
|---|---|
| 共依存 (load 一括) | `TACPLUS` / `TACPLUS_SERVER` / `RADIUS` / `RADIUS_SERVER` / `LDAP` / `LDAP_SERVER` |
| RADIUS 動的解決 (`src_intf`/`nas_ip` 解決) | `MGMT_INTERFACE` / `INTERFACE` / `VLAN_INTERFACE` / `VLAN_SUB_INTERFACE` / `PORTCHANNEL_INTERFACE` / `LOOPBACK_INTERFACE` |
| `nas_id` 解決 | `DEVICE_METADATA.localhost.hostname` |
| ランタイム連動 (subscribe ハンドラ経由) | `MGMT_VRF_CONFIG` |

## 検証コマンド

```bash
grep -n "subscribe\|init_data\['\(AAA\|TACPLUS\|RADIUS\|LDAP\)" \
    .cache/sonic-sources/sonic-host-services/scripts/hostcfgd

grep -nE "get_interface_ip|get_keys\('(MGMT_INTERFACE|INTERFACE|VLAN_|PORTCHANNEL|LOOPBACK)" \
    .cache/sonic-sources/sonic-host-services/scripts/hostcfgd
```

このスキャン結果から派生して `docs/reference/config-db/aaa.md` の `<!-- cross-refs -->` ブロックを生成する。
