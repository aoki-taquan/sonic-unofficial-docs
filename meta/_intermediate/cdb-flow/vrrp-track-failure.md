# vrrp-track — Phase D 失敗挙動スキャンノート

調査日: 2026-05-18  
対象テーブル: `VRRP_TRACK` / `VRRP6_TRACK`

## ソース調査範囲

- `sonic-utilities/config/main.py` — `add_track_interface()` L6993-7040, `remove_track_interface()` L7048-7077, `add_track_interface_v6()` L7426-7470, `remove_track_interface_v6()` L7478-7506
- `SONiC/doc/vrrp/sonic-vrrp.yang` — VRRP_TRACK container L135-183, VRRP6_TRACK L252-306
- `SONiC/doc/vrrp/VRRP_Adaptation_HLD.md` — Warmboot セクション L622-628, Uplink tracking L481-492

## add_track_interface() 失敗パターン

### エイリアスモード (interface alias)

| 失敗ケース | 箇所 | 挙動 |
|---|---|---|
| `interface_name` のエイリアス解決失敗 | L7000-7001 | `ctx.fail("'interface_name' is None!")` |
| `track_interface` のエイリアス解決失敗 | L7002-7003 | `ctx.fail("'track_interface' is None!")` |

### ベースインタフェース検証

| 失敗ケース | 箇所 | 挙動 |
|---|---|---|
| `interface_name` が Loopback 系 または 無効名 | L7006-7007 | `ctx.fail("'interface_name' is not valid. Valid names [Ethernet/PortChannel/Vlan]")` |
| `interface_name` が CONFIG_DB に未存在 (INTERFACE / VLAN_INTERFACE / PORTCHANNEL_INTERFACE) | L7008-7009 | `ctx.fail("Router Interface '{}' not found")` |

### 追跡インタフェース検証

| 失敗ケース | 箇所 | 挙動 |
|---|---|---|
| `track_interface` が Loopback 系 または 無効名 | L7012-7013 | `ctx.fail("'track_interface' is not valid. Valid names [Ethernet/PortChannel/Vlan]")` |
| `track_interface` が CONFIG_DB に未存在 | L7014-7015 | `ctx.fail("Router Interface '{}' not found")` |

### 親インスタンス検証

| 失敗ケース | 箇所 | 挙動 |
|---|---|---|
| 親 VRRP インスタンス (`VRRP|<intf>|<vrid>`) が未存在 | L7017-7019 | `ctx.fail("vrrp instance {} not found on interface {}")` で永続拒絶 |

### スケール上限

| 失敗ケース | 箇所 | 挙動 |
|---|---|---|
| 同インスタンスに既に 8 トラックインタフェースが設定済み | L7037-7038 | `ctx.fail("The Vrrpv instance {} has already configured 8 track interfaces")` |

注: `priority_increment` の範囲は Click の `IntRange(10, 50)` で CLI 解析時に検査される (L6990-6991)。範囲外値はコマンド解析段階で拒絶され、DB 書き込みは発生しない。

既存の VRRP_TRACK エントリがある場合は `priority_increment` のみ更新される (冪等動作) — L7021-7026。

## remove_track_interface() 失敗パターン

| 失敗ケース | 箇所 | 挙動 |
|---|---|---|
| `interface_name` / `track_interface` のエイリアス解決失敗 | L7055-7058 | `ctx.fail("'interface_name'/'track_interface' is None!")` |
| `interface_name` が Loopback 系 または 無効名 | L7061-7062 | `ctx.fail("'interface_name' is not valid.")` |
| `interface_name` が CONFIG_DB に未存在 | L7063-7064 | `ctx.fail("Router Interface '{}' not found")` |
| `track_interface` が Loopback 系 または 無効名 | L7067-7068 | `ctx.fail("'track_interface' is not valid.")` |
| 親 VRRP インスタンスが未存在 | L7070-7072 | `ctx.fail("vrrp instance {} not found on interface {}")` |
| 対象 VRRP_TRACK エントリが未存在 | L7074-7076 | `ctx.fail("{} is not configured on the vrrp instance {}!")` |

## YANG バリデーション失敗 (gNMI / sonic-yang-mgmt 経路)

| 失敗ケース | 挙動 |
|---|---|
| `priority_increment` が 1–255 の範囲外 | YANG `uint8` 型バリデーションで reject |
| `baseifname` leafref 解決失敗 (親インスタンス未存在) | sonic-yang-mgmt が leafref エラーを返す |
| `trackifname` leafref 解決失敗 (PORT / PORTCHANNEL / VLAN 未存在) | sonic-yang-mgmt が leafref エラーを返す |

## FRR vrrpd / zebra の失敗挙動

- VRRP_TRACK が CONFIG_DB に書き込まれても FRR vrrpd が読み込む前にインタフェース状態変化が発生した場合、priority 計算は欠落する（一過性）。HLD L481-492 に記述のとおり、FRR vrrpd は起動時に CONFIG_DB を参照するが、動的な set_entry 後の通知経路は macvlanmgrd 経由ではなくプロセス再読み込みが必要な場合がある。
- `zebra` がトラックインタフェースの Up/Down 通知を vrrpd に配信できない場合 (zebra プロセス障害等)、priority 更新が停止する。DB への副次書き込みなし。

## 結論

- CLI 経路: add/remove ともに複数の段階的バリデーション (エイリアス解決 → ベース IF 確認 → トラック IF 確認 → 親インスタンス確認 → スケール確認) を経て永続拒絶 (`ctx.fail()`)。retry なし。
- YANG/gNMI 経路: leafref と uint8 型チェックが独立して動作。
- FRR 内部障害は DB 上の VRRP_TRACK エントリとは独立。STATE_DB への書き込みなし。
