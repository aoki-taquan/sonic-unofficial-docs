# Phase A: LLDP フィールド暗黙デフォルト調査

## 調査対象ソース

- `sonic-buildimage/dockers/docker-lldp/lldpmgrd` (Python daemon)
- `sonic-buildimage/dockers/docker-lldp/lldpd.conf.j2` (起動時 config 生成)
- `sonic-buildimage/dockers/docker-lldp/lldpdSysDescr.conf.j2` (sysDescr 生成)
- `sonic-buildimage/dockers/docker-lldp/start.sh` (コンテナ起動スクリプト)
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-lldp.yang` (YANG 定義)

---

## LLDP|GLOBAL フィールド別暗黙デフォルト

### `hello_time`
- YANG default: `30` (秒)
- 実装: `lldpd.conf.j2` は hello_time を直接 inject しない。lldpd 自体のデフォルト = 30 秒。
- **乖離なし**: YANG default = lldpd ハードコード default = 30 秒。
- LLDP|GLOBAL エントリが存在しない場合も lldpd は 30 秒で起動する。
- hello_time が YANG range 外（0 以下）の場合は lldpd が無視してデフォルト継続動作。YANG バリデーション有効環境では mgmt-framework 経由で SET が拒否される（CLI パスでは python コード側でエラーにはならないが lldpd 側で無視）。

### `multiplier`
- YANG default: `4`
- 実装: `lldpmgrd` も `lldpd.conf.j2` も multiplier を lldpcli/conf へ inject しない。
- **dead field に近い**: CONFIG_DB に書けるが lldpd への反映パスがコード上に存在しない。lldpd 自体のデフォルト hold-multiplier = 4 で一致するが、変更しても lldpd に伝わらない。

### `system_name`
- YANG default: なし（省略可能）
- 実装: `lldpmgrd` は `DEVICE_METADATA|localhost` の `chassis_hostname` または `hostname` を読んで `lldpcli configure system hostname <name>` を実行する。LLDP|GLOBAL の `system_name` フィールドは **直接読まれない**。
- **dead field**: `LLDP|GLOBAL.system_name` は YANG に存在するが lldpmgrd の consumer コードに読み取りパスなし。実際のシステム名は DEVICE_METADATA.hostname 由来。

### `system_description`
- YANG default: なし
- 実装: `lldpdSysDescr.conf.j2` がビルド時に `SONiC Software Version: SONiC.{{ build_version }} - HwSku: {{ hwsku }} - Distribution: Debian {{ debian_version }} - Kernel: {{ kernel_version }}` 形式のシステム説明を生成し `/etc/lldpd.conf` に書き込む。
- **ハードコード固定値**: CONFIG_DB の `system_description` を書いても lldpmgrd はこれを lldpcli へ渡さない。実際の system description は起動時の j2 展開でハードコードされる。

### `supp_mgmt_address_tlv`
- YANG default: `false`（= Management Address TLV を送信する）
- 実装: `lldpmgrd` はこのフィールドを読まない。
- **dead field**: CONFIG_DB への書き込みは lldpd に伝わらない。Management IP は `MGMT_INTERFACE` テーブル経由で `lldpd.conf.j2` および `lldpmgrd.update_mgmt_addr()` が制御する別パス。

### `supp_system_capabilities_tlv`
- YANG default: `false`
- 実装: `lldpmgrd` はこのフィールドを読まない。
- **dead field**: lldpd への反映パスなし。

### `enabled` (grouping lldp_mode_config)
- YANG default: `true`
- 実装: `lldpmgrd` は `LLDP|GLOBAL` の `enabled` フィールドを読まない。
- **dead field at GLOBAL level**: GLOBAL の enabled は lldpd の起動/停止を制御しない。ポート単位（LLDP_PORT）の enabled についても lldpmgrd は読まない（lldp-syncd が別途処理する可能性あり）。

### `mode` (LLDP|GLOBAL)
- YANG default: なし（optional leaf）
- 実装: `lldpmgrd` は `LLDP|GLOBAL.mode` を読まない。lldpcli への mode 設定パスはグローバルレベルでは存在しない。
- **dead field at GLOBAL level**: 未設定時 lldpd のデフォルトは双方向 (tx_and_rx)。

---

## LLDP_PORT|<ifname> フィールド別

### `enabled`
- YANG default: `true`
- 実装: `lldpmgrd` は LLDP_PORT テーブルを購読しない。PORT (APP_DB) の oper_status を監視してポートが up になったときのみ lldpcli configure ports を実行。enabled フィールドは読まない。
- **dead field**: lldp-syncd が代わりに処理している可能性があるが、lldpmgrd コードには反映パスなし。

### `mode` (LLDP_PORT)
- YANG default: なし
- 実装: `lldpmgrd` は LLDP_PORT の mode を読まない。dead field と同様。

---

## 起動時ハードコード固定値（lldpd.conf.j2 由来）

| 設定 | ソース | 値 |
|------|--------|----|
| portidsubtype (eth0) | MGMT_PORT.alias または "eth0" | `local <alias>` / `local eth0` |
| system ip management pattern | MGMT_INTERFACE の IPv4 優先（IPv4 なければ IPv6） | 動的 |
| hostname | DEVICE_METADATA.localhost.hostname | 動的 |
| portidsubtype (global) | ハードコード | `ifname` |
| system description | lldpdSysDescr.conf.j2 展開 | `SONiC Software Version: ...` 固定形式 |
| 起動時 pause | ハードコード | lldpmgrd が resume するまで LLDP PDU 送信停止 |

---

## lldpmgrd が実際に読む外部情報

| テーブル | フィールド | 用途 |
|---------|-----------|------|
| `DEVICE_METADATA|localhost` | `chassis_hostname`, `hostname` | lldpcli configure system hostname |
| `MGMT_INTERFACE|<name>|<prefix>` | key の IP アドレス部分 | lldpcli configure system ip management pattern |
| `APP_DB PORT` | `oper_status` | ポートが up のときのみ lldpcli configure ports 実行 |
| `CONFIG_DB PORT` | `alias`, `description` | lldpcli configure ports <ifname> lldp portidsubtype local <alias> description <desc> |

---

## 発見した discrepancy / 暗黙挙動サマリ

| フィールド | 種類 | 内容 |
|-----------|------|------|
| `multiplier` | dead field + lldpd 暗黙固定値 | CONFIG_DB に書いても lldpd 反映パスなし。lldpd デフォルト 4 で動作 |
| `system_name` | dead field | DEVICE_METADATA.hostname が実際に使われる |
| `system_description` | ハードコード固定値 | 起動時 j2 展開による固定フォーマット。CONFIG_DB 値は無視 |
| `supp_mgmt_address_tlv` | dead field | 反映パスなし |
| `supp_system_capabilities_tlv` | dead field | 反映パスなし |
| `LLDP|GLOBAL.enabled` | dead field | lldpmgrd 非購読 |
| `LLDP|GLOBAL.mode` | dead field | lldpmgrd 非購読 |
| `LLDP_PORT.enabled` | dead field (lldpmgrd 経由) | lldpmgrd は LLDP_PORT 未購読 |
| `LLDP_PORT.mode` | dead field (lldpmgrd 経由) | lldpmgrd は LLDP_PORT 未購読 |
| `hello_time` 0/負 | silent fallback | YANG range 外: lldpd が 30 秒デフォルトで継続動作 |
| `LLDP|GLOBAL` 未存在 | implicit reset | lldpd デフォルト (hello=30s, tx_and_rx) で起動 |
| ポート起動順依存 | 書込み順依存 | PORT.oper_status=up になるまで lldpcli configure ports がキューイング (RETRY_LIMIT=5, timeout=300s) |
