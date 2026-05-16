# RADIUS_SERVER テーブル 暗黙参照スキャン (Phase C)

`docs/reference/config-db/radius-server.md` の Phase C (暗黙参照) ブロック裏付け資料。

ソースは `sonic-net/sonic-host-services/scripts/hostcfgd`。`RADIUS_SERVER` テーブル変更時に `hostcfgd` (`AaaCfg`) が `modify_conf_file()` 内で間接的に読み出す関連 CONFIG_DB テーブルを列挙する。

## スキャン手順

```
grep -nE 'subscribe\(|init_data\[|self\.(authentication|authorization|tacplus|radius)_' \
    .cache/sonic-sources/sonic-host-services/scripts/hostcfgd
```

`hostcfgd` の `load_independent_config()` (L2222-2231) で `AaaCfg.load()` に渡される 7 テーブル、`modify_conf_file()` 経由で参照される動的解決テーブル群、および `register_callbacks()` (L2470-2509) で RADIUS_SERVER に間接影響する subscribe を抽出。

## 検出された暗黙参照テーブル

### `modify_conf_file()` 内で参照される共依存テーブル

`radius_server_update()` が呼ばれると `modify_conf_file()` が実行される。この関数内では `RADIUS_SERVER` 以外の以下のテーブルが結合される。

| テーブル | 参照タイミング | 用途 | evidence |
|---|---|---|---|
| `AAA` (`authentication`) | `modify_conf_file()` 冒頭 | `authentication['login']` に `radius` が含まれるかチェック。含まれない場合 PAM に RADIUS スタックが組まれない | hostcfgd:639,722,763,840 |
| `TACPLUS_SERVER` | `modify_conf_file()` — `servers_conf` 構築 | TACACS+ サーバ設定と並列でテンプレートに渡す。`tacacs+` が login に含まれる場合は TACACS サーバが優先されるため RADIUS サーバ設定が PAM に反映されない | hostcfgd:648-666 |
| `RADIUS` (`radius_global`) | `modify_conf_file()` — `radius_global` 構築 | `nas_ip` / `nas_id` / `src_intf` / `statistics` を各 RADIUS_SERVER エントリにマージ | hostcfgd:667-686 |

### ランタイム間接読み出し (動的解決)

`modify_conf_file()` 実行中に `get_interface_ip()` / `get_hostname()` 経由で間接参照される CONFIG_DB テーブル。

| テーブル | 参照箇所 | 用途 | evidence |
|---|---|---|---|
| `MGMT_INTERFACE` | `get_interface_ip("eth0")` (hostcfgd:600) | `RADIUS|global` に `nas_ip` 未設定の場合、eth0 の管理 IP を `nas_ip` として自動補完 | hostcfgd:600,671-674 |
| `INTERFACE` | `get_interface_ip("Eth...")` (hostcfgd:586) | `RADIUS_SERVER.src_intf` が物理ポートの場合 src_ip を解決 | hostcfgd:586,694 |
| `VLAN_INTERFACE` | `get_interface_ip("Vlan...")` (hostcfgd:593) | `src_intf` が VLAN のとき src_ip を解決 | hostcfgd:593 |
| `VLAN_SUB_INTERFACE` | `get_interface_ip` 分岐 (hostcfgd:588,591) | `src_intf` が VLAN sub-interface のとき | hostcfgd:588 |
| `PORTCHANNEL_INTERFACE` | `get_interface_ip("Po...")` (hostcfgd:591) | `src_intf` が PortChannel のとき | hostcfgd:591 |
| `LOOPBACK_INTERFACE` | `get_interface_ip("Loopback...")` (hostcfgd:595) | `src_intf` が Loopback のとき | hostcfgd:595 |
| `DEVICE_METADATA` (`localhost.hostname`) | `get_hostname()` (hostcfgd:566-577,683-686) | `RADIUS|global` に `nas_id` 未設定の場合、ホスト名を `nas_id` として自動補完 | hostcfgd:566-577,675-678 |

### 連動 subscribe (RADIUS_SERVER 状態を間接更新)

RADIUS_SERVER に直接 SET/DEL されなくても、以下のテーブル変化が `AaaCfg` の状態を更新し `modify_conf_file()` を再トリガーする。

| テーブル | handler | RADIUS_SERVER への影響 | evidence |
|---|---|---|---|
| `AAA` | `aaa_handler` → `aaacfg.aaa_update()` | `authentication['login']` が変化すると PAM に RADIUS スタックを組み込むかどうかが切り替わる | hostcfgd:2289-2291,2470 |
| `TACPLUS_SERVER` | `tacacs_server_handler` → `aaacfg.tacacs_server_update()` | TACACS+ サーバ追加/削除で `servers_conf` が変化し RADIUS PAM 優先順に影響 | hostcfgd:2304,2472 |
| `MGMT_INTERFACE` | `mgmt_intf_handler` → `aaacfg.handle_radius_nas_ip_chg()` | eth0 IP 変化時に RADIUS `nas_ip` を再計算 | hostcfgd:2348-2349,2485 |
| `MGMT_VRF_CONFIG` | `mgmt_vrf_handler` | 管理 VRF 切替時に eth0 の到達性が変わり nas_ip 解決に影響。`vrf=mgmt` フィールドを持つ RADIUS_SERVER エントリの接続経路が切り替わる | hostcfgd:2352-2353,2496 |
| `INTERFACE` / `VLAN_INTERFACE` / `VLAN_SUB_INTERFACE` / `PORTCHANNEL_INTERFACE` | 各 `*_intf_handler` → `aaacfg.handle_radius_source_intf_ip_chg()` | `src_intf` の IP 変化時に RADIUS src_ip を更新 | hostcfgd:2365-2381,2486-2489 |
| `DEVICE_METADATA` | `device_metadata_handler` → `devmetacfg.hostname_update` → `aaacfg.hostname_update` | hostname 変化時に RADIUS `nas_id` を再生成 | hostcfgd:2406,2492 |

## まとめ — `radius-server.md` Phase C 記載対象

| カテゴリ | テーブル |
|---|---|
| 共依存 (modify_conf_file 内で結合) | `AAA` / `TACPLUS_SERVER` / `RADIUS` |
| 動的 IP 解決 (`src_intf`/`nas_ip`) | `MGMT_INTERFACE` / `INTERFACE` / `VLAN_INTERFACE` / `VLAN_SUB_INTERFACE` / `PORTCHANNEL_INTERFACE` / `LOOPBACK_INTERFACE` |
| `nas_id` 自動補完 | `DEVICE_METADATA.localhost.hostname` |
| ランタイム subscribe 連動 | `AAA` / `TACPLUS_SERVER` / `MGMT_INTERFACE` / `MGMT_VRF_CONFIG` |

## 検証コマンド

```bash
grep -n "authentication\['login'\]\|self\.authentication\|aaa_update\|tacplus_servers\|radius_global" \
    .cache/sonic-sources/sonic-host-services/scripts/hostcfgd | head -40

grep -n "subscribe.*AAA\|subscribe.*TACPLUS\|subscribe.*MGMT_VRF\|subscribe.*RADIUS" \
    .cache/sonic-sources/sonic-host-services/scripts/hostcfgd
```

このスキャン結果から派生して `docs/reference/config-db/radius-server.md` の `<!-- cross-refs -->` ブロックを生成した。
