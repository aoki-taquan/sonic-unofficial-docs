# NTP_KEY — プラットフォーム差 (Phase H)

生成日: 2026-05-19

## 調査対象

- `sonic-host-services/scripts/hostcfgd` — `NtpCfg` クラス全体 (L1272–1406)
- `sonic-buildimage/files/image_config/chrony/chrony.keys.j2`
- `sonic-buildimage/files/image_config/chrony/chrony.conf.j2`
- `sonic-buildimage/files/image_config/chrony/chrony-config.sh`
- `sonic-buildimage/files/image_config/chrony/chronyd-starter.sh`
- `sonic-buildimage/src/sonic-config-engine/tests/data/ntp/ntp_smartswitch_dpu_interfaces.json`
- `sonic-buildimage/src/sonic-config-engine/tests/sample_output/py3/chrony_smartswitch_dpu.conf`
- `sonic-buildimage/src/sonic-config-engine/tests/sample_output/py3/chrony_smartswitch.conf`

## 結論サマリ

`NTP_KEY` テーブルの処理ロジック（`NtpCfg.ntp_srv_key_update()` / `chrony.keys.j2`）はプラットフォーム非依存。
プラットフォーム差は `NTP_SERVER` の選択・`chrony.conf` のサーバ役割設定（SmartSwitch）と VRF バインド（mgmt-vrf）に閉じており、`NTP_KEY` の鍵テーブル処理には影響しない。

## 詳細

### hostcfgd `NtpCfg` — プラットフォーム条件分岐なし

`NtpCfg.__init__` (L1278-1318) は `hwsku`・`subtype`・プラットフォーム識別子を一切参照しない。
`NtpCfg.ntp_srv_key_update()` (L1366-1406) は `NTP_KEY` 全件と `NTP_SERVER` 全件を Jinja2 テンプレートに渡すだけであり、`#ifdef` 相当の条件分岐を持たない。

grep 確認: `hostcfgd:1272-1406` 内に `hwsku`・`subtype`・`SmartSwitch`・`DPU`・`platform` の文字列ヒットなし。

### chrony.keys.j2 — プラットフォーム条件分岐なし

`chrony.keys.j2` (L1-18) は `device_metadata` / `subtype` を参照しない。
`NTP_KEY` の全件を走査して `<id> <TYPE> <decoded_value> [trusted_str]` 形式で出力するロジックはすべてのプラットフォームで同一。

### SmartSwitch (subtype=SmartSwitch, type!=SmartSwitchDPU) の影響範囲

`chrony.conf.j2:57-63` が SmartSwitch 固有の NTP サーバ機能ブロック (`allow` / `binddevice bridge-midplane`) を出力するが、これは `NTP_SERVER` の配信設定であり `NTP_KEY` テーブルの内容とは独立している。
SmartSwitch NPU でも `chrony.keys.j2` は通常の標準 NTP_KEY 処理を行い、プラットフォーム分岐なし。

### SmartSwitch DPU (type=SmartSwitchDPU) の挙動

DPU は `169.254.200.254` (midplane ブリッジ IP) を NTP_SERVER として使用する。NTP_KEY を使って midplane NTP サーバに認証付き同期をさせることは構成上可能だが、`chrony.keys.j2` はプラットフォーム分岐なしで同一処理を実行する（テストデータ: `ntp_smartswitch_dpu_interfaces.json`）。

DPU の `chrony_smartswitch_dpu.conf` サンプルでは `keyfile` 行が出力されていない（`authentication=disabled` のため）。認証を有効化すれば標準の chrony.keys 処理が走り、DPU 固有の特別処理は発生しない。

### VRF (mgmt-vrf) の影響範囲

`chronyd-starter.sh` が `NTP|global.vrf == 'mgmt'` の場合に `ip vrf exec mgmt` で chronyd を起動する。この VRF バインドは chrony プロセスレベルの設定であり、`NTP_KEY` テーブルの鍵テーブル処理とは独立。VRF 設定によって `chrony.keys` の生成内容は変化しない。

## 証跡

| 観点 | プラットフォーム差 | 根拠 |
|------|----------------|------|
| `NtpCfg.ntp_srv_key_update()` 分岐 | **なし** | `hostcfgd:1366-1406` — hwsku/subtype 参照なし |
| `chrony.keys.j2` 条件分岐 | **なし** | `chrony.keys.j2:1-18` — device_metadata 参照なし |
| SmartSwitch NPU NTP サーバ機能 | **NTP_SERVER 側に限定** | `chrony.conf.j2:57-63` — NTP_KEY テーブルに不影響 |
| SmartSwitch DPU NTP ソース | **NTP_SERVER テーブル側** | midplane IP は NTP_SERVER に登録、NTP_KEY 処理は同一 |
| VRF バインド | **NTP global / chronyd 起動時** | `chronyd-starter.sh` — chrony.keys 生成は影響なし |
