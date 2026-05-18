# VRRP — Phase E: ハードコード定数スキャンノート

生成日: 2026-05-18 (chore/q67-f-batch212-next)

対象テーブル: `VRRP` / `VRRP6` / `VRRP_TRACK` / `VRRP6_TRACK`
Consumer: `macvlanmgrd` (BGP コンテナ), `vrrpsyncd` (SWSS コンテナ)
スキャン範囲: `sonic-utilities/config/main.py` (L6880–7640), `SONiC/doc/vrrp/VRRP_Adaptation_HLD.md` (CONFIG_DB schema, RFC 定数)

---

## 1. スケール上限リテラル (config/main.py)

CONFIG_DB / YANG に宣言されておらず、CLI ハンドラ内のリテラルとしてのみ存在する上限値。

| 定数 / リテラル | 値 | 対象テーブル | 失敗メッセージ | ソース |
|---|---|---|---|---|
| システム全体 VRRP インスタンス上限 | `254` | `VRRP` | `"Has already configured 254 vrrp instances"` | `config/main.py:6915` |
| インタフェースあたり VRRP インスタンス上限 | `16` | `VRRP` | `"{intf} has already configured 16 vrrp instances!"` | `config/main.py:6924` |
| インスタンスあたり VIP 上限 (IPv4) | `4` | `VRRP` | `"The vrrp instance {} has already configured 4 IP addresses"` | `config/main.py:6908-6909` |
| システム全体 VRRP6 インスタンス上限 | `254` | `VRRP6` | `"Has already configured 254 vrrp instances!"` | `config/main.py:7231` |
| インタフェースあたり VRRP6 インスタンス上限 | `16` | `VRRP6` | `"{intf} has already configured 16 vrrp instances!"` | `config/main.py:7240` |
| インスタンスあたり VIP 上限 (IPv6) | `4` | `VRRP6` | `"The vrrp instance {} has already configured 4 IPv6 addresses"` | `config/main.py:7327` |
| インスタンスあたりトラックインタフェース上限 | `8` | `VRRP_TRACK` | `"The Vrrpv instance {} has already configured 8 track interfaces"` | `config/main.py:7038` |

> YANG `max-elements` は `VRRP_LIST` / `VRRP6_LIST` ともに `128` (`sonic-vrrp.yang` L45, L188)。CLI 側の上限 `254` と乖離しているが、CLI 検査が先に発火するため YANG の `128` は実効的に到達しない。

---

## 2. フィールドデフォルト (YANG スキーマ由来)

`sonic-vrrp.yang` に宣言された `default` 文。CLI が省略時の代入値として使用する。

| フィールド | YANG default | 対象テーブル | ソース |
|---|---|---|---|
| `priority` | `100` | `VRRP` / `VRRP6` | `sonic-vrrp.yang` L106, L224 |
| `adv_interval` | `1` (秒) | `VRRP` / `VRRP6` | `sonic-vrrp.yang` L112, L230 |

> `version`, `pre_empt`, `use_v2_checksum` の YANG デフォルトは宣言なし。HLD の説明 (`version` デフォルト = VRRPv3、`pre_empt` デフォルト = True) はコードコメントレベルの記述であり、macvlanmgrd 側での fallback が実際の適用源と推定される。

---

## 3. プロトコル RFC 定数 (HLD 由来)

FRR `vrrpd` / `macvlanmgrd` が VRRP 動作のためにハードコードする RFC 5798 由来の定数。CONFIG_DB には現れない。

| 定数 | 値 | 説明 | ソース |
|---|---|---|---|
| IPv4 仮想 MAC プレフィクス | `00:00:5e:00:01:<vrid>` | VRID ごとに VMAC を一意に決定 (RFC 5798) | HLD L169, sonic-vrrp.yang L118 |
| IPv6 仮想 MAC プレフィクス | `00:00:5e:00:02:<vrid>` | IPv6 VRID 用 VMAC | HLD L171 |
| VRRP IPv4 マルチキャストアドレス | `224.0.0.18` | Advertisement パケットの宛先 | HLD L177 |
| VRRP IPv6 マルチキャストアドレス | `ff02::12` (FF02::02/64) | IPv6 Advertisement の宛先 | HLD L177 |
| IP プロトコル番号 | `112` | VRRP パケットの IP プロトコル TYPE | HLD L177 |
| Linux カーネル最小バージョン | `5.1` | macvlan protodown サポート要件 | HLD L199-200 |

---

## 4. macvlan デバイス命名規則 (HLD / macvlanmgrd 由来)

macvlanmgrd が Linux カーネルに作成する macvlan デバイスの名前プレフィクス。CONFIG_DB には記録されない。

| 規則 | 値 | 説明 | ソース |
|---|---|---|---|
| IPv4 macvlan 名プレフィクス | `Vrrp4-` | `ip link add Vrrp4-<intf>-<vrid> ...` | HLD Container セクション L221 |
| IPv6 macvlan 名プレフィクス | `Vrrp6-` | `ip link add Vrrp6-<intf>-<vrid> ...` | HLD Container セクション L221 |
| macvlan タイプ | `bridge` | macvlan デバイスの mode 指定 | HLD L117-120 |
| macvlan addrgenmode | `random` | link local 生成を MAC ではなくランダムにする | HLD L117-120 |

---

## 順序依存サマリ

| # | 定数 | 区分 | 備考 |
|---|------|------|------|
| 1 | スケール上限 (254/16/4/8) | CLI ハードコード | YANG `max-elements 128` と乖離あり |
| 2 | `priority` default=100, `adv_interval` default=1 | YANG デフォルト | CONFIG_DB 省略時に YANG が適用 |
| 3 | VMAC プレフィクス / マルチキャストアドレス / IP proto 112 | RFC 5798 ハードコード | DB 管理外 |
| 4 | `Vrrp4-` / `Vrrp6-` macvlan 名 | macvlanmgrd 内部 | vrrpsyncd がこのプレフィクスで inotify 監視 |
