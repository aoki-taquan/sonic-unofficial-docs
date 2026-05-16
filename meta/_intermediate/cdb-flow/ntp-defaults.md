# NTP フィールド暗黙デフォルト調査メモ (Phase A)

調査日: 2026-05-14  
対象テーブル: CONFIG_DB `NTP` (global), `NTP_SERVER`, `NTP_KEY`

## 調査対象ファイル

- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-ntp.yang`
- `sonic-host-services/scripts/hostcfgd` (NtpCfg クラス: L1272-L1406)
- `sonic-buildimage/files/image_config/chrony/chrony.conf.j2`
- `sonic-buildimage/files/image_config/chrony/chrony.keys.j2`
- `sonic-buildimage/files/image_config/chrony/chronyd-starter.sh`
- `sonic-buildimage/files/build_templates/init_cfg.json.j2`
- `sonic-buildimage/src/sonic-config-engine/minigraph.py` (L2646)

---

## テーブル別 フィールド暗黙デフォルト

### NTP|global テーブル

#### `authentication`

**YANG default**: `disabled` (`sonic-ntp.yang:143`)  
**init_cfg.json.j2**: `"disabled"` — YANG と一致  
**chrony.conf.j2**: `global.authentication == 'enabled'` のときのみ `keyfile` ディレクティブ追加。省略時は認証なしで動作 (silent drop: keyfile なし)。  
**コード由来暗黙デフォルト**: `disabled` (YANG = init_cfg 一致、実装上も keyfile を追加しないのでデフォルト有効)

#### `dhcp`

**YANG default**: `enabled` (`sonic-ntp.yang:149`)  
**init_cfg.json.j2**: `"enabled"` — YANG と一致  
**chrony.conf.j2**: `global.server_role == 'enabled' or global.dhcp == 'enabled'` のとき SmartSwitch のみ `allow\nbinddevice bridge-midplane` を追加。通常スイッチでは dhcp=enabled でも設定変化なし (sourcedir /run/chrony-dhcp は常時)。  
**コード由来暗黙デフォルト**: `enabled` (YANG = init_cfg 一致)

#### `server_role`

**YANG default**: `enabled` (`sonic-ntp.yang:155`)  
**init_cfg.json.j2**: `"disabled"` ← **YANG との乖離** (`init_cfg.json.j2:214`)  
**chrony.conf.j2**: SmartSwitch (`device_metadata.subtype == 'SmartSwitch' and type != 'SmartSwitchDPU'`) のみ `allow\nbinddevice bridge-midplane` を追加。非 SmartSwitch では `server_role` 値に関わらず `allow` は生成されない。  
**重要**: `server_role` フィールドは非 SmartSwitch では **dead field** — テンプレート側 L57-63 がプラットフォーム条件で囲まれており、通常スイッチでは `server_role` 値は chrony.conf に反映されない。  
**コード由来暗黙デフォルト**: init_cfg.json.j2 が `"disabled"` に上書き。**YANG default `enabled` は実質無効**。

#### `src_intf`

**YANG default**: なし (任意 leaf-list)  
**init_cfg.json.j2**: `"eth0"` — ハードコード注入 (`init_cfg.json.j2:215`)  
**chrony.conf.j2 L87-107**: `global.src_intf` が存在する場合のみ `bindacqaddress` を生成。eth0 → MGMT_INTERFACE、Ethernet → INTERFACE、Loopback → LOOPBACK_INTERFACE、PortChannel → PORTCHANNEL_INTERFACE、Vlan → VLAN_INTERFACE とテーブルを切り替え。  
**コード由来暗黙デフォルト**: `"eth0"` (init_cfg.json.j2 による build-time ハードコード)。YANG は任意。

#### `vrf`

**YANG default**: なし (任意 leaf、pattern `mgmt|default` のみ)  
**init_cfg.json.j2**: `"default"` — ハードコード注入 (`init_cfg.json.j2:217`)  
**chronyd-starter.sh**: `MGMT_VRF_CONFIG|vrf_global.mgmtVrfEnabled != "true"` → `chronyd` を default VRF で起動。`vrf == "default"` でも同様に default VRF で起動。`vrf == "mgmt"` かつ mgmtVrfEnabled=true のとき `ip vrf exec mgmt chronyd`。  
**chrony.conf.j2 L109**: `not ((NTP) and NTP['global']['vrf'] == 'mgmt')` のとき bindacqaddress を出力。つまり vrf=mgmt 時は bindacqaddress を **抑制**。  
**コード由来暗黙デフォルト**: `"default"` (init_cfg.json.j2 による build-time ハードコード)。YANG は任意。

#### `admin_state`

**YANG default**: `enabled` (`sonic-ntp.yang:161`)  
**init_cfg.json.j2**: `"enabled"` — YANG と一致  
**コード由来暗黙デフォルト**: `enabled`。hostcfgd は admin_state を直接参照しない (chrony サービス全体の起動/停止は別途)。

---

### NTP_SERVER テーブル

#### `association_type`

**YANG default**: `server` (`sonic-ntp.yang:189`)  
**chrony.conf.j2 L26**: `config.association_type | d('server')` — テンプレートも `server` にフォールバック  
**コード由来暗黙デフォルト**: `server` (YANG + テンプレート両方で一致)

#### `iburst`

**YANG default**: `on` (`sonic-ntp.yang:195`)  
**minigraph.py L2646**: `{'iburst': 'on'}` を全サーバに固定設定  
**chrony.conf.j2 L37**: `if config.iburst` — 値が truthy ならオプション追加。`off` 文字列は truthy なので注意: `iburst = 'off'` でも `iburst` オプションが追加される潜在的バグ。ただし YANG が on/off enum を強制するので実害は限定的。  
**コード由来暗黙デフォルト**: `on` (YANG + minigraph 一致)

#### `resolve_as`

**YANG default**: なし (任意)  
**chrony.conf.j2 L27**: `config.resolve_as | d(server)` — 未設定時は key (server_address) にフォールバック  
**コード由来暗黙デフォルト**: server_address キー値 (テンプレートのランタイム fallback)

#### `admin_state`

**YANG default**: `enabled` (`sonic-ntp.yang:213`)  
**chrony.conf.j2 L20**: `NTP_SERVER[server].admin_state != 'disabled'` のサーバのみ出力。省略時は enabled 扱い (filterで除外されない)。  
**コード由来暗黙デフォルト**: `enabled`

#### `trusted`

**YANG default**: `no` (`sonic-ntp.yang:219`)  
**chrony.keys.j2 L8**: `NTP_SERVER[server].trusted == 'yes' and NTP_SERVER[server].resolve_as` でフィルタ。trusted が 'no' または resolve_as 未設定ならキーファイルの trusted_str に追加されない。  
**重要**: `trusted = 'yes'` のとき `resolve_as` が必須。resolve_as 未設定なら trusted=yes でも trustedkey に含まれない (silent drop)。  
**コード由来暗黙デフォルト**: `no`

#### `version`

**YANG default**: `4` (`sonic-ntp.yang:231`)  
**chrony.conf.j2 L42**: `if config.version` — 値が設定されている場合のみ `version N` オプション追加。YANG default=4 があるため通常は設定される。  
**コード由来暗黙デフォルト**: `4` (YANG)

#### `key`

**YANG default**: なし (任意、leafref NTP_KEY.id)  
**chrony.conf.j2 L30-34**: `global.authentication == 'enabled'` かつ `config.key` のときのみ `key <id>` を追加。authentication=disabled 時は key フィールドが存在しても **silent drop**。  
**コード由来暗黙デフォルト**: なし。authentication=disabled 時は dead field。

---

### NTP_KEY テーブル

#### `type`

**YANG default**: `md5` (`sonic-ntp.yang:268`)  
**chrony.keys.j2 L15**: `NTP_KEY[keyid].type and NTP_KEY[keyid].value` の両方必須。type が falsy (空) ならスキップ。  
**chrony.keys.j2 L17**: `NTP_KEY[keyid].type | upper` — MD5/SHA1/SHA256 等の大文字変換  
**コード由来暗黙デフォルト**: `md5`。md5 は RFC 8573 で非推奨。

#### `trusted`

**YANG default**: `no` (`sonic-ntp.yang:255`)  
**chrony.keys.j2 L8**: `NTP_SERVER[server].trusted == 'yes' and NTP_SERVER[server].resolve_as` でフィルタ。NTP_KEY.trusted は直接参照されない — trustedkey の判定は NTP_SERVER 側の `trusted` フィールドで行う。  
**重要**: NTP_KEY.trusted フィールドは現在の chrony.keys.j2 テンプレートでは **未参照 (dead field)**。trustedkey の制御は NTP_SERVER.trusted で行う。

#### `value`

**YANG default**: なし (必須 1..64 chars)  
**chrony.keys.j2 L15**: `NTP_KEY[keyid].value` が falsy ならスキップ (silent skip)  
**chrony.keys.j2 L16**: `NTP_KEY[keyid].value | b64decode` — Base64 デコード必須。平文を直接格納すると誤ったデコードが行われる。  
**コード由来暗黙デフォルト**: なし。value 未設定ならキーファイルに含まれない。

---

## 重要な乖離・特殊挙動まとめ

| 分類 | 対象 | 内容 |
|------|------|------|
| YANG-実装乖離 | `NTP.server_role` | YANG default=`enabled` だが init_cfg.json.j2 が `"disabled"` を注入。有効デフォルトは `disabled` |
| build-time ハードコード | `NTP.src_intf` | YANG は任意だが init_cfg.json.j2 が `"eth0"` を常に注入 |
| build-time ハードコード | `NTP.vrf` | YANG は任意だが init_cfg.json.j2 が `"default"` を常に注入 |
| dead field (非SmartSwitch) | `NTP.server_role` | SmartSwitch 以外では chrony.conf.j2 が server_role を参照しない。値は無視される |
| dead field | `NTP_KEY.trusted` | chrony.keys.j2 は NTP_KEY.trusted を未参照。trustedkey 判定は NTP_SERVER.trusted で行う |
| silent drop | `NTP_SERVER.key` | `NTP.authentication=disabled` のとき key フィールドは chrony.conf に反映されない |
| silent drop | `NTP_SERVER.trusted=yes` | `resolve_as` が未設定なら trusted=yes でも trustedkey に追加されない |
| template fallback | `NTP_SERVER.association_type` | `| d('server')` でテンプレートレベルの fallback あり (YANG と一致) |
| template fallback | `NTP_SERVER.resolve_as` | `| d(server)` でサーバアドレスにフォールバック |
| platform依存 | `NTP.server_role` + `NTP.dhcp` | SmartSwitch (`subtype==SmartSwitch` かつ `type!=SmartSwitchDPU`) のみ `allow\nbinddevice bridge-midplane` を出力 |
| VRF経路依存 | `NTP.vrf` | chronyd-starter.sh が MGMT_VRF_CONFIG.mgmtVrfEnabled をランタイムに確認してから VRF を決定。YANG must 制約は書き込み時のみ |
| 書き込み順依存 | `NTP_SERVER.key` + `NTP_KEY` | NTP_KEY を先に登録しないと leafref 制約が NTP_SERVER 書き込みを拒否 |
| iburst潜在バグ | `NTP_SERVER.iburst` | chrony.conf.j2 L37 が `if config.iburst` で truthy 判定するため、`iburst='off'` も iburst オプションを追加してしまう可能性 (Python Jinja2 で 'off' は truthy) |

## 証跡

- `sonic-ntp.yang:143,149,155,161,189,195,213,219,231,255,268`
- `init_cfg.json.j2:210-219`
- `chrony.conf.j2:20-53,57-64,87-116,124-128`
- `chrony.keys.j2:7-18`
- `chronyd-starter.sh:3-16`
- `minigraph.py:2646`
- `hostcfgd:1272-1406,2512-2517`
