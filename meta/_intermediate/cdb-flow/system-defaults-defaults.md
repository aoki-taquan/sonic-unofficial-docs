# SYSTEM_DEFAULTS フィールド暗黙デフォルト調査メモ

調査日: 2026-05-16  
対象テーブル: CONFIG_DB `SYSTEM_DEFAULTS`

## 調査対象ファイル

- `sonic-buildimage/files/build_templates/init_cfg.json.j2` (ビルド時 SYSTEM_DEFAULTS エントリ生成)
- `sonic-buildimage/src/sonic-config-engine/config_samples.py` (SmartSwitch DPU プロファイル時の補完)
- `sonic-utilities/scripts/db_migrator.py` (DEVICE_METADATA.synchronous_mode の補完 — SYSTEM_DEFAULTS 直接ではないが関連)
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-system-defaults.yang` (status enum)

SHA: sonic-buildimage `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`、sonic-utilities `39732bceb8bdefe706518ab40623bbbba6ff33b9`。

---

## フィールド別 暗黙デフォルト

### `status` (admin_mode) — YANG enum、コード fallback は "absent = disabled"

`sonic-system-defaults.yang` (L16-) は `SYSTEM_DEFAULTS_LIST` の `status` を `admin_mode` typedef (enum `enabled`/`disabled`) として宣言。YANG 側に `default` 宣言は無く、`status` 不在 → 各機能コードが「エントリ不在=disabled」として扱う runtime fallback に依存する。

```yang
container SYSTEM_DEFAULTS {
    list SYSTEM_DEFAULTS_LIST {
        ...
        leaf status { type admin_mode; }
    }
}
```

`config_samples.py:160-161` でも:

```python
if "SYSTEM_DEFAULTS" not in data:
    data["SYSTEM_DEFAULTS"] = {}
```

→ minigraph に SYSTEM_DEFAULTS が無いケースで空 dict を補完。

---

### `mux_tunnel_egress_acl` (Dual-ToR mux ACL)

**コード由来デフォルト**: プラットフォーム条件分岐

`init_cfg.json.j2:188-197`:

```jinja2
"SYSTEM_DEFAULTS" : {
{%- if include_mux == "y" %}
    "mux_tunnel_egress_acl": {
{%- if sonic_asic_platform == "mellanox" %}
        "status": "enabled"
{% else %}
        "status": "disabled"
{% endif %}
    }
{% endif %}
}
```

- `include_mux == "y"` のビルドでのみ生成。それ以外はエントリ自体が無い。
- Mellanox: `enabled`、それ以外 (Broadcom など): `disabled` が build-time に焼き込まれる。

---

### `synchronous_mode` (orchagent SAI 同期実行)

**コード由来デフォルト**: P4RT 連携ビルド時のみ DEVICE_METADATA に注入 (SYSTEM_DEFAULTS には注入されない)

`init_cfg.json.j2:5` (DEVICE_METADATA セクション内):

```jinja2
{%- if include_p4rt == "y" %}"synchronous_mode":"enable",{% endif %}
```

- **重要**: `synchronous_mode` は実コード上 `DEVICE_METADATA|localhost` に書かれる（SYSTEM_DEFAULTS ではない）。本テーブル文中の「代表値」は概念的な紹介で、実装は DEVICE_METADATA 側。
- ビルド時 `include_p4rt != "y"` のときキー不在 → orchagent は非同期モードで起動。
- `db_migrator.py:670-677` で旧 image からのアップグレード時に `metadata['synchronous_mode']` を `device_metadata_data.get("synchronous_mode")` (config_src デフォルト) で補完する。

---

### `dhcp_server` (組み込み DHCP サーバ)

**コード由来デフォルト**: ビルド時 features list に追加されるが、対象は FEATURE テーブル

`init_cfg.json.j2:77`:

```jinja2
{%- if include_dhcp_server == "y" %}{% do features.append(("dhcp_server", "disabled", false, "enabled")) %}{% endif %}
```

- `include_dhcp_server == "y"` ビルド時に FEATURE テーブルへ `state=disabled` で登録。SYSTEM_DEFAULTS 経由ではなく FEATURE 経由。
- 概念紹介として SYSTEM_DEFAULTS 文中に併記されているが、実コードでは FEATURE テーブルの管掌。

---

### `software_bfd` (DPU プロファイルのみ)

**コード由来デフォルト**: SmartSwitch DPU プロファイル生成時に `enabled` を強制

`config_samples.py:186-188`:

```python
data["SYSTEM_DEFAULTS"]["software_bfd"] = {
    "status": "enabled"
}
```

`generate_smartswitch_dpu` プロファイル (config_samples.py:155-) 経由でのみ作られる。通常スイッチには付かない。

---

### `polaris` (Pensando hwsku のみ)

**コード由来デフォルト**: Pensando hwsku 時に `enabled`

`config_samples.py:179-184`:

```python
if "pensando" in data['DEVICE_METADATA']['localhost']['hwsku'].lower():
    data['SYSTEM_DEFAULTS'] = {
        "polaris": {
            "status": "enabled"
        }
    }
```

- Pensando DPU 向け SmartSwitch プロファイル時に SYSTEM_DEFAULTS 全体を polaris 単体エントリで上書き（直前の `software_bfd` も後段で再追加される）。

---

### `tunnel_qos_remap` — ビルド時注入なし、ランタイム参照のみ

`init_cfg.json.j2` / `config_samples.py` のいずれにも `tunnel_qos_remap` の自動生成コードは無い。`muxorch` (sonic-swss) が起動時に `SYSTEM_DEFAULTS|tunnel_qos_remap` のエントリ有無と `status` を確認するのみで、不在時は QoS remap を行わない (= 概念的 `disabled` 扱い)。コード由来のデフォルトは「エントリ不在」。

---

## 要約表

| `<name>` エントリ | コード由来デフォルト | 注入源 |
|------------------|---------------------|-------|
| `mux_tunnel_egress_acl` | Mellanox: `enabled` / 他: `disabled` (`include_mux=y` ビルド時のみ) | `init_cfg.json.j2:188-197` |
| `software_bfd` | `enabled` (SmartSwitch DPU プロファイルのみ) | `config_samples.py:186-188` |
| `polaris` | `enabled` (Pensando hwsku のみ) | `config_samples.py:179-184` |
| `tunnel_qos_remap` | エントリ不在 = `disabled` 扱い (ビルド注入なし) | runtime fallback (muxorch) |
| `synchronous_mode` | 実体は `DEVICE_METADATA` 側。`include_p4rt=y` ビルド時に `"enable"` | `init_cfg.json.j2:5` |
| `dhcp_server` | 実体は `FEATURE` 側。`include_dhcp_server=y` ビルド時に登録 | `init_cfg.json.j2:77` |
| `status` 全般 | YANG `default` 無し。コードは「エントリ不在 = disabled」として扱う | `sonic-system-defaults.yang`、各 daemon |

---

## 証拠リンク

- `sonic-buildimage/files/build_templates/init_cfg.json.j2:5, 77, 188-197` (`9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`)
- `sonic-buildimage/src/sonic-config-engine/config_samples.py:160-188`
- `sonic-utilities/scripts/db_migrator.py:670-677` (`39732bceb8bdefe706518ab40623bbbba6ff33b9`)
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-system-defaults.yang:16-` (`admin_mode` enum、`default` 宣言なし)
