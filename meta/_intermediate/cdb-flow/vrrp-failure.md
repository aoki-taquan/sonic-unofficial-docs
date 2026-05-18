# vrrp — Phase D 失敗挙動スキャンノート

調査日: 2026-05-18  
対象ページ: `docs/reference/config-db/vrrp.md`  
対象テーブル: `VRRP` / `VRRP6` / `VRRP_TRACK` / `VRRP6_TRACK`

---

## 調査対象

- `sonic-utilities/config/main.py` — CLI バリデーション (add_vrrp_ip, priority, adv_interval, pre_empt, version, add_track_interface, remove_track_interface)
- `SONiC/doc/vrrp/VRRP_Adaptation_HLD.md` — macvlanmgrd / vrrpsyncd 挙動
- `SONiC/doc/vrrp/sonic-vrrp.yang` — YANG leafref / constraint

---

## CLI 経路の失敗パターン (config/main.py)

### add_vrrp_ip (VIP 追加 / インスタンス新規作成)

| 失敗ケース | コード箇所 | 挙動 |
|---|---|---|
| インタフェース名が Loopback 系 | L6884-6886 | `ctx.fail("'interface_name' is not valid.")` 永続拒絶 |
| INTERFACE/VLAN_INTERFACE/PORTCHANNEL_INTERFACE 未存在 | L6887-6890 | `ctx.fail("Router Interface '{}' not found")` 永続拒絶 |
| VIP アドレス形式不正 | L6892-6893 | `ctx.abort()` |
| VIP が別インスタンスで既に使用中 | L6894-6895 (`check_vrrp_ip_exist`) | `ctx.abort()` |
| VIP に "/" (prefix) がない | L6897-6898 | `ctx.fail("IP address {} is missing a mask.")` |
| 同インスタンスが既に 4 VIP 設定済み | L6906-6909 | `ctx.fail("...already configured 4 IP addresses")` |
| システム全体 254 インスタンス上限超過 | L6914-6916 | `ctx.fail("Has already configured 254 vrrp instances")` |
| 同 VRID が別インタフェースで既存 | L6919-6920 | `ctx.fail("The vrrp instance {} has already configured!")` |
| 同インタフェースで 16 インスタンス上限超過 | L6922-6924 | `ctx.fail("{} has already configured 16 vrrp instances!")` |

### priority / adv_interval / pre_empt / version (パラメータ変更)

- インタフェース未存在 → `ctx.fail("Router Interface '{}' not found")`
- VRRP インスタンス未存在 → `ctx.fail("vrrp instance {} not found on interface {}")`
- パラメータ範囲外 → Click の `IntRange` / `Choice` で即時拒絶（CLIレイヤ）

### add_track_interface

| 失敗ケース | コード箇所 | 挙動 |
|---|---|---|
| ベースインタフェース未存在 | L7000-7006 | `ctx.fail("Router Interface '{}' not found")` |
| 追跡インタフェース未存在 | L7007-7014 | `ctx.fail("Router Interface '{}' not found")` |
| 親 VRRP インスタンス未存在 | L7017-7019 | `ctx.fail("vrrp instance {} not found on interface {}")` |
| 同インスタンスに 8 トラック済み | L7028-7038 | `ctx.fail("...already configured 8 track interfaces")` |

---

## macvlanmgrd の失敗挙動 (HLD 記述)

HLD の記述 (L219-225) による macvlanmgrd の動作:

- Linux macvlan デバイス追加/削除の失敗 → HLD は明示的なリトライ/ロールバック仕様を記述していない。macvlan デバイス作成失敗時の挙動は実装依存（カーネルエラー）
- macvlanmgrd 未起動時 → CONFIG_DB に書き込まれたエントリは購読キューに滞留し、macvlanmgrd 起動後にリプレイされる（HLD L461-466 参照）
- vtysh コマンド失敗時 → HLD は明示的な失敗処理を記述していない

## vrrpsyncd の失敗挙動 (HLD 記述)

vrrpsyncd は MACVLAN インタフェースの kernel イベント（protodown on/off）を listen し APPL_DB を更新する。HLD では以下が示される:

- Master 状態遷移時: macvlan デバイスを protodown off → vrrpsyncd が APPL_DB.VRRP_TABLE に VIP エントリを追加
- Backup 状態遷移時: macvlan デバイスを protodown on → vrrpsyncd が APPL_DB.VRRP_TABLE から VIP エントリを削除

カーネル Linux 5.1+ が必要。旧カーネルでは macvlan の protodown がサポートされない (HLD L199-200)。

## Warmboot 非対応

HLD L622-628: VRRP は Warm boot 非対応。VRRP が有効な状態でユーザが warmboot を試みるとエラーメッセージが表示される。VRRP を先に無効化する必要がある。
