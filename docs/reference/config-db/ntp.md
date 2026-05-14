---
title: NTP テーブル群 (Phase A defaults)
description: "NTP / NTP_SERVER / NTP_KEY の各フィールドに対するコード由来の暗黙デフォルト・乖離・dead field・silent drop を網羅した Phase A 調査ページ。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-14
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-ntp.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-buildimage
    path: files/image_config/chrony/chrony.conf.j2
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-buildimage
    path: files/build_templates/init_cfg.json.j2
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-host-services
    path: scripts/hostcfgd
    ref: master
related:
  config_db:
    - NTP
    - NTP_SERVER
    - NTP_KEY
    - MGMT_VRF_CONFIG
  cli:
    - config ntp
  yang:
    - sonic-ntp
---

# NTP テーブル群 — コード由来デフォルト (Phase A)

> このページは `NTP` / `NTP_SERVER` / `NTP_KEY` 3 テーブルを横断して、YANG 定義・`init_cfg.json.j2`・`chrony.conf.j2` テンプレート・`hostcfgd` ハンドラの全行精読から得た**暗黙デフォルト**・**乖離**・**dead field**・**silent drop** を記録する。各テーブルの詳細は [`NTP (global)`](./ntp-global.md)・[`NTP_SERVER`](./ntp-server.md)・[`NTP_KEY`](./ntp-key.md) を参照。

<!-- defaults -->
## コード由来デフォルト分析

<!-- evidence:
  sonic-ntp.yang:143,149,155,161,189,195,213,219,231,255,268
  init_cfg.json.j2:210-219
  chrony.conf.j2:20-53,57-64,87-116,124-128
  chrony.keys.j2:7-18
  chronyd-starter.sh:3-16
  minigraph.py:2646
  hostcfgd:1272-1406,2512-2517
-->

### NTP|global フィールド

| フィールド | YANG default | init_cfg.json.j2 | 有効デフォルト | 分類 |
|-----------|-------------|-------------------|--------------|------|
| `authentication` | `disabled` | `"disabled"` | `disabled` | 一致 |
| `dhcp` | `enabled` | `"enabled"` | `enabled` | 一致 |
| `server_role` | `enabled` | **`"disabled"`** | **`disabled`** | **YANG-実装乖離** |
| `src_intf` | なし (任意) | `"eth0"` | `"eth0"` | build-time ハードコード |
| `vrf` | なし (任意) | `"default"` | `"default"` | build-time ハードコード |
| `admin_state` | `enabled` | `"enabled"` | `enabled` | 一致 |

#### `server_role` — YANG default=`enabled` vs init_cfg.json.j2=`"disabled"`

`sonic-ntp.yang` L155 は `default enabled` を宣言するが、`init_cfg.json.j2` L214 は `"server_role": "disabled"` を明示的に書き込む[^1]。

さらに `chrony.conf.j2` L57-63 は SmartSwitch (`DEVICE_METADATA.localhost.subtype == 'SmartSwitch'` かつ `type != 'SmartSwitchDPU'`) のときのみ `server_role` の値を参照する:

```jinja2
{% if device_metadata.subtype == 'SmartSwitch' and device_metadata.type != 'SmartSwitchDPU' -%}
{% if global.server_role == 'enabled' or global.dhcp == 'enabled' -%}
allow
binddevice bridge-midplane
{% endif -%}
{% endif -%}
```

**非 SmartSwitch では `server_role` は dead field** — フィールド値にかかわらず `chrony.conf` への影響はない。SmartSwitch では `dhcp == 'enabled'` (default) でも `allow` が追加されるため、`server_role=disabled` でも SmartSwitch は NTP server として動作する。

#### `src_intf` — YANG は任意、init_cfg が `"eth0"` を注入

YANG 上は任意の leaf-list だが、`init_cfg.json.j2` が `"eth0"` を常に設定する。`chrony.conf.j2` L87-107 は `global.src_intf` が存在する場合に `bindacqaddress <ip>` を生成し、インタフェース名の prefix でテーブルを振り分ける:

- `eth0` → `MGMT_INTERFACE`
- `Ethernet*` → `INTERFACE`
- `Loopback*` → `LOOPBACK_INTERFACE`
- `PortChannel*` → `PORTCHANNEL_INTERFACE`
- `Vlan*` → `VLAN_INTERFACE`

`src_intf` が leaf-list (複数値) でも `global.src_intf` が文字列として取り出される点に注意。hostcfgd `handle_ntp_source_intf_chg` は `src_intf` を `;` 区切りで split して比較する[^2]。

#### `vrf` — YANG は任意、init_cfg が `"default"` を注入

`init_cfg.json.j2` が `"vrf": "default"` を設定。`chronyd-starter.sh` はランタイムに:

1. `MGMT_VRF_CONFIG|vrf_global.mgmtVrfEnabled` が `"true"` かを確認
2. true なら `NTP|global.vrf` を読み、`"default"` なら default VRF で起動、それ以外 (mgmt) なら `ip vrf exec mgmt chronyd`
3. false なら常に default VRF で起動

YANG `must` 制約は DB 書き込み時のみ評価されるが、`chronyd-starter.sh` はランタイムに MGMT_VRF_CONFIG を再確認する。MGMT VRF を無効化したまま `vrf=mgmt` が DB に残ると chronyd は mgmt VRF で起動しようとして失敗する可能性がある(**経路依存乖離**)。

---

### NTP_SERVER フィールド

| フィールド | YANG default | template fallback | minigraph | 有効デフォルト | 分類 |
|-----------|-------------|-------------------|-----------|--------------|------|
| `association_type` | `server` | `\| d('server')` | - | `server` | 一致 (二重保護) |
| `iburst` | `on` | 条件付き | `"on"` 固定 | `on` | 一致。ただし潜在バグあり |
| `resolve_as` | なし (任意) | `\| d(server)` | - | server_address キー | template fallback |
| `admin_state` | `enabled` | filter による | - | `enabled` | 一致 |
| `trusted` | `no` | - | - | `no` | 一致。resolve_as 要件あり |
| `version` | `4` | - | - | `4` | 一致 |
| `key` | なし (任意) | - | - | - | authentication=disabled 時 silent drop |

#### `iburst` の潜在バグ

`chrony.conf.j2` L37 は `{% if config.iburst %}` で判定する。Jinja2/Python では文字列 `'off'` は truthy であるため、`iburst = 'off'` が DB に入っていても `iburst` オプションが `chrony.conf` に追加されてしまう[^3]。

正しくは `config.iburst == 'on'` と比較すべきところを truthy 判定しているため、**明示的に iburst=off を設定しても効かない可能性**がある。YANG が on/off enum を強制するので on/off 以外の値は入らないが、`iburst = 'off'` の場合の動作が意図と異なる。

#### `NTP_SERVER.key` — authentication=disabled 時 silent drop

`chrony.conf.j2` L30-34:

```jinja2
{% if global.authentication == 'enabled' -%}
    {% if config.key -%}
        {% set soptions = soptions ~ ' key ' ~ config.key -%}
    {% endif -%}
{% endif -%}
```

`NTP.authentication = 'disabled'` (デフォルト) のとき、`NTP_SERVER.key` に値が設定されていても `chrony.conf` の `key` オプションは生成されない。YANG バリデーションで leafref は通るが、認証なしでは鍵が使われない。

#### `NTP_SERVER.trusted` — resolve_as が必須条件

`chrony.keys.j2` L8-10:

```jinja2
{% for server in NTP_SERVER if NTP_SERVER[server].trusted == 'yes' and
                               NTP_SERVER[server].resolve_as -%}
    {% set _ = trusted_arr.append(NTP_SERVER[server].resolve_as) -%}
```

`trusted = 'yes'` でも `resolve_as` が空の場合は `trusted_str` に追加されない。YANG で `resolve_as` は任意 leaf のため、CLI や minigraph.py が `resolve_as` を設定しない場合は trusted 指定が silent drop される。

---

### NTP_KEY フィールド

| フィールド | YANG default | template参照 | 有効デフォルト | 分類 |
|-----------|-------------|-------------|--------------|------|
| `type` | `md5` | `NTP_KEY[keyid].type` (必須チェック) | `md5` | 一致。RFC 8573 非推奨 |
| `trusted` | `no` | **未参照** | `no` | **dead field** |
| `value` | なし (任意) | b64decode 必須 | - | Base64 エンコード前提 |

#### `NTP_KEY.trusted` — dead field

`chrony.keys.j2` は `NTP_KEY[keyid].trusted` を一切参照しない。trustedkey の制御は `NTP_SERVER[server].trusted` フィールドで行う。`NTP_KEY.trusted = 'yes'` を設定しても `chrony.keys` ファイルへの影響はない。

#### `NTP_KEY.value` — Base64 エンコード必須

`chrony.keys.j2` L16 は `NTP_KEY[keyid].value | b64decode` でデコードする。DB に平文を格納すると Base64 として誤ってデコードされ、chrony が誤った鍵値を使用する。CLI `config ntp authentication-key add` が Base64 エンコードを行う前提。

---

## 乖離・特殊挙動サマリ

<!-- evidence: 上記全証跡 -->

| 分類 | フィールド | 詳細 |
|------|----------|------|
| **YANG-実装乖離** | `NTP.server_role` | YANG default=`enabled`、init_cfg=`"disabled"` — 有効デフォルトは `disabled` |
| **build-time ハードコード** | `NTP.src_intf` | YANG 任意だが init_cfg が `"eth0"` を常時注入 |
| **build-time ハードコード** | `NTP.vrf` | YANG 任意だが init_cfg が `"default"` を常時注入 |
| **dead field (非SmartSwitch)** | `NTP.server_role` | 非 SmartSwitch では chrony.conf.j2 が参照しない |
| **dead field** | `NTP_KEY.trusted` | chrony.keys.j2 は NTP_KEY.trusted を未参照 |
| **silent drop** | `NTP_SERVER.key` | authentication=disabled 時は key が chrony.conf に反映されない |
| **silent drop** | `NTP_SERVER.trusted=yes` | resolve_as 未設定なら trustedkey に含まれない |
| **潜在バグ** | `NTP_SERVER.iburst` | `if config.iburst` が truthy 判定 → iburst='off' でも有効になる可能性 |
| **経路依存乖離** | `NTP.vrf` | YANG must はDB書込時のみ評価。chronyd-starter.sh はランタイムに MGMT_VRF_CONFIG を再確認 |
| **platform依存** | `NTP.server_role` / `NTP.dhcp` | SmartSwitch のみ `allow`+`binddevice` を追加 |
| **書き込み順依存** | `NTP_SERVER.key` / `NTP_KEY` | NTP_KEY 未登録時に NTP_SERVER.key を設定すると YANG leafref 拒否 |
| **Base64前提** | `NTP_KEY.value` | b64decode 必須。平文格納は誤動作 |
| **template fallback** | `NTP_SERVER.association_type` | `\| d('server')` で YANG と一致するフォールバックあり |
| **template fallback** | `NTP_SERVER.resolve_as` | `\| d(server)` でアドレスキーにフォールバック |

<!-- /defaults -->

## 関連ページ

- [CONFIG_DB: NTP (global)](./ntp-global.md)
- [CONFIG_DB: NTP_SERVER](./ntp-server.md)
- [CONFIG_DB: NTP_KEY](./ntp-key.md)
- [YANG: sonic-ntp](../yang/sonic-ntp.md)
- [CLI: config ntp](../cli/config-ntp.md)

## 引用元

[^1]: `init_cfg.json.j2` L210-219: `"NTP": {"global": {"authentication": "disabled", "dhcp": "enabled", "server_role": "disabled", "src_intf": "eth0", "admin_state": "enabled", "vrf": "default"}}`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/files/build_templates/init_cfg.json.j2#L210-L219>

[^2]: `hostcfgd` L1319: `ifs = self.cache.get('global', {}).get('src_intf', '').split(';')` — leaf-list が `;` 区切り文字列として格納される CONFIG_DB の実装依存。<https://github.com/sonic-net/sonic-host-services/blob/master/scripts/hostcfgd>

[^3]: `chrony.conf.j2` L37: `{% if config.iburst %}` — Jinja2 で文字列 `'off'` は truthy。`iburst = 'off'` のサーバも `iburst` オプションが生成される潜在的挙動。<https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/files/image_config/chrony/chrony.conf.j2#L37>
