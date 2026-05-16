# NTP|global フィールド暗黙デフォルト調査メモ

調査日: 2026-05-15
対象テーブル: CONFIG_DB `NTP|global`

## 調査対象ファイル

- `sonic-host-services/scripts/hostcfgd` (`NtpCfg` クラス: `load`, `ntp_global_update`, `handle_ntp_source_intf_chg`, `ntp_srv_key_update`)
- `sonic-buildimage/files/image_config/chrony/chrony.conf.j2` (NTP デーモン設定テンプレ — SONiC は ntpd ではなく chrony を採用、`ntp.conf.j2` は廃止)
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-ntp.yang` (`container global`)

---

## テーブル構造

```
NTP|global
```

key は `global` 固定 (singleton)。

---

## フィールド別 暗黙デフォルト

### `src_intf`

**YANG default**: なし (leaf-list / ordered-by user)

**コード由来 fallback**:

- `NtpCfg.handle_ntp_source_intf_chg()` (hostcfgd:1319): `self.cache.get('global', {}).get('src_intf', '').split(';')` — 未設定時は空文字 → 空リスト → 何もしない。
- `chrony.conf.j2:86-107`: `ns.source_intf = ""` 初期化、`global.src_intf` が truthy のときのみ `bindacqaddress` を発行。未設定なら `bindacqaddress` 行は出力されず、カーネル経路選択に委ねる (テンプレ内コメント: "otherwise, rely on the kernel to route packets as needed").

**実効デフォルト (未設定時)**: 送信元 IP は OS の経路選択に従う。`bindacqaddress` 未発行。

---

### `vrf`

**YANG default**: なし (`pattern "mgmt|default"`)

**コード由来 fallback**:

- `NtpCfg.ntp_global_update()` (hostcfgd:1351-1353): `old_vrf = self.cache.get(key, {}).get('vrf')` — 未設定時は `None` を許容 (例外なし、差分検知のみ)。
- `chrony.conf.j2:109`: `{% if not ((NTP) and NTP['global']['vrf'] == 'mgmt') -%}` — `vrf` が未設定または `'default'` のときに `bindacqaddress` 行を出力。`vrf == 'mgmt'` のときは `bindacqaddress` をスキップして `interface` ベースの bind に依存。

**実効デフォルト (未設定時)**: default VRF 扱い。`bindacqaddress` は `src_intf` に従って出力される。

---

### `authentication`

**YANG default**: `disabled`

```yang
# sonic-ntp.yang:141-145
leaf authentication {
    type stypes:admin_mode;
    default disabled;
}
```

**コード由来 fallback**: `chrony.conf.j2:30,124` — `{% if global.authentication == 'enabled' %}` チェック。未設定なら falsy 扱いで `keyfile /etc/chrony/chrony.keys` 行と `key <N>` オプションを出力しない。

**実効デフォルト**: `disabled` (NTP 認証無効、`NTP_KEY` を読まない)。

**chrony.conf マッピング**: `keyfile` / `key` server option。

---

### `dhcp`

**YANG default**: `enabled`

```yang
# sonic-ntp.yang:147-151
leaf dhcp {
    type stypes:admin_mode;
    default enabled;
}
```

**コード由来 fallback**: `chrony.conf.j2:60` — `{% if global.server_role == 'enabled' or global.dhcp == 'enabled' -%}` (SmartSwitch 限定)。テンプレ末尾の `sourcedir /run/chrony-dhcp` は `dhcp` の値に関わらず常に出力 (chrony.conf.j2:118-119) — DHCP NTP の取り込みは `dhcp` enabled 時にディレクトリ経由で有効化される設計。

**実効デフォルト**: `enabled` (DHCP 配布 NTP サーバを優先採用)。

---

### `server_role`

**YANG default**: `enabled`

```yang
# sonic-ntp.yang:153-157
leaf server_role {
    type stypes:admin_mode;
    default enabled;
}
```

**コード由来 fallback**: `chrony.conf.j2:58-64` — SmartSwitch かつ NPU 側 (`device_metadata.type != 'SmartSwitchDPU'`) のときのみ `allow` / `binddevice bridge-midplane` を出力。通常スイッチでは `server_role` の値はテンプレ内で参照されない。

**実効デフォルト**: `enabled` (ただし通常スイッチでは chrony.conf に反映されない — SmartSwitch NPU 限定で `allow` を発行)。

---

### `admin_state`

**YANG default**: `enabled`

```yang
# sonic-ntp.yang:159-163
leaf admin_state {
    type stypes:admin_mode;
    default enabled;
}
```

**コード由来 fallback**: `chrony.conf.j2` 内に `admin_state` の参照なし。`hostcfgd` の `NtpCfg` も `admin_state` を分岐に使わない (`ntp_global_update` は全フィールド差分で chrony を restart するのみ)。

**実効デフォルト**: `enabled` (chrony は常に起動)。`admin_state=disabled` を設定しても chrony.conf 再生成 + restart は行うが、chrony 自体は停止しない設計 (admin_state はテンプレ未参照)。

---

## chrony.conf.j2 テンプレフォールバック (NTP_SERVER 関連、参考)

`NTP|global` 自体ではないが、`global.authentication` / `global.vrf` と連動する `NTP_SERVER` 側のテンプレ既定値も `ntp_global` ハンドラ経路で評価されるため列挙する。

- `association_type | d('server')` (chrony.conf.j2:26) — 未設定時 `server` ディレクティブ。
- `resolve_as | d(server)` (chrony.conf.j2:27) — 未設定時はサーバ名そのまま (= key 値) を resolve_as に使う。

---

## 要約表

| フィールド | YANG default | コード由来 fallback | 実効デフォルト (未設定時) | chrony.conf 反映 |
|-----------|-------------|-------------------|------------------------|----------------|
| `src_intf` | なし | `split(';')` 空配列 / テンプレ `ns.source_intf=""` | `bindacqaddress` 未発行 → カーネル経路選択 | `bindacqaddress <IP>` 行 (vrf!=mgmt のみ) |
| `vrf` | なし | テンプレ `if vrf == 'mgmt'` 分岐のみ | default VRF 扱い、`bindacqaddress` 出力 | (条件分岐) |
| `authentication` | `disabled` | テンプレ `if authentication == 'enabled'` | `disabled` (`keyfile` / `key` 行なし) | `keyfile /etc/chrony/chrony.keys`, `key <N>` |
| `dhcp` | `enabled` | テンプレ `sourcedir /run/chrony-dhcp` 常時出力 | `enabled` (DHCP NTP 採用) | (SmartSwitch のみ `allow` に影響) |
| `server_role` | `enabled` | SmartSwitch NPU 限定で参照 | `enabled` (通常スイッチでは無影響) | `allow` / `binddevice bridge-midplane` (SmartSwitch のみ) |
| `admin_state` | `enabled` | テンプレ参照なし | `enabled` (chrony 常時起動) | 反映なし |

---

## 特記事項

1. **`ntp.conf.j2` は実在しない**: 公開ドキュメントや旧 HLD で `ntp.conf` と表記されているが、現行 master では chrony を採用しており実テンプレは `chrony.conf.j2`。`hostcfgd` のコメント (`CHRONY_RESTART = ['systemctl', 'restart', 'chrony']`) もこれを裏付ける。

2. **`admin_state` の死活**: YANG default `enabled` だがテンプレ未参照のため、`admin_state=disabled` を CONFIG_DB に書いても chrony は停止しない。`ntp_global_update` は他フィールド変更と同様に chrony を restart するだけで、機能的 OFF にはならない (sonic-host-services 側で `admin_state` を扱う死活トリガが存在しない)。

3. **`trusted_key` フィールドは NTP|global に存在しない**: YANG `container global` の leaf は `src_intf` / `vrf` / `authentication` / `dhcp` / `server_role` / `admin_state` の 6 つのみ。`trusted` は `NTP_SERVER` / `NTP_KEY` 側の leaf (default `no`)。Task F の「trusted_key」既定値は `NTP_KEY|<id>:trusted=no` を指すと解釈し、`NTP|global` ページでは扱わない (別ページ `ntp-key.md` 管轄)。

4. **`interface` ディレクティブ**: 既存ページの handler-branching 表に「`interface eth0` を追加」とあるが、現行 chrony.conf.j2 は `interface` ディレクティブを発行せず、`bindacqaddress` で送信元 IP を縛る方式。`vrf == 'mgmt'` のときは `bindacqaddress` をスキップしてカーネル mgmt VRF の routing に委ねる。handler-branching の文言は将来の修正候補だが本 Phase A の対象外。

5. **差分検知**: `ntp_global_update()` (hostcfgd:1344) は `self.cache.get('global', {}) == data` で完全一致時は no-op。`ntp_srv_key_update()` も同様 (hostcfgd:1383-1386)。

---

## 証拠リンク

- `sonic-host-services` `scripts/hostcfgd:1272-1401` — `NtpCfg` クラス全体
- `sonic-buildimage` `files/image_config/chrony/chrony.conf.j2` — chrony テンプレ (ntp.conf.j2 後継)
- `sonic-buildimage:9ea932ec` `src/sonic-yang-models/yang-models/sonic-ntp.yang:91-165` — `container global` YANG defaults
