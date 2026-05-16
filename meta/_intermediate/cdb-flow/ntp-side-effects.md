# NTP テーブル群 — 副次 DB 書込・ファイル書込 (Phase F)

ソース: `sonic-host-services/scripts/hostcfgd`, `sonic-buildimage/files/image_config/chrony/`

対象テーブル: `CONFIG_DB / NTP`, `CONFIG_DB / NTP_SERVER`, `CONFIG_DB / NTP_KEY`

## スキャン結果

### APPL_DB / STATE_DB への副次書込

**0 件。** NTP 処理系は APPL_DB / STATE_DB への書込を一切行わない。

NTP ステータス（同期状態・到達性）は STATE_DB にも書き込まれない。
観測手段は `chronyc tracking` / `chronyc sources` コマンドのみ。

---

## ファイルシステム書込

### `/etc/chrony/chrony.conf`

**書込経路 (ブート時):**

```
config-setup.service
  → ExecStartPre: chrony-config.sh
    → sonic-cfggen -d -t /usr/share/sonic/templates/chrony.conf.j2
      >/etc/chrony/chrony.conf
```

`chrony-config.sh:9` が `sonic-cfggen` を呼び出し、`chrony.conf.j2` テンプレートを
CONFIG_DB 全体をコンテキストとしてレンダリングし `/etc/chrony/chrony.conf` へ上書き書込する。

**書込経路 (ランタイム):**

NTP テーブルへの変更は hostcfgd の `NtpCfg` ハンドラが検出し、
`systemctl restart chrony` を発行する。chrony サービスの `ExecStartPre` として
`chrony-config.sh` が再実行されるため、サービス再起動のたびに `/etc/chrony/chrony.conf`
が再生成される。

```
CONFIG_DB 変更 (NTP / NTP_SERVER / NTP_KEY)
  → hostcfgd NtpCfg.handler()
    → ntp_global_update() / ntp_srv_key_update()
      → run_cmd(['systemctl', 'restart', 'chrony'])
        → chrony.service ExecStartPre: chrony-config.sh
          → /etc/chrony/chrony.conf 上書き生成
```

生成内容の変化点 (CONFIG_DB フィールドと出力の対応):

| CONFIG_DB フィールド | chrony.conf への影響 |
|---------------------|---------------------|
| `NTP_SERVER.<addr>.admin_state == 'disabled'` | そのサーバ行を除外 |
| `NTP_SERVER.<addr>.association_type` | `server` / `pool` ディレクティブ切替 |
| `NTP_SERVER.<addr>.iburst` | `iburst` オプション追加 (truthy 判定バグあり) |
| `NTP_SERVER.<addr>.version` | `version N` オプション追加 |
| `NTP_SERVER.<addr>.key` | `key N` オプション追加 (authentication=enabled 時のみ) |
| `NTP.global.authentication == 'enabled'` | `keyfile /etc/chrony/chrony.keys` ディレクティブ追加 |
| `NTP.global.src_intf` | `bindacqaddress <ip>` ディレクティブ追加 (vrf!=mgmt 時) |
| `NTP.global.server_role` / `dhcp` | SmartSwitch のみ `allow` + `binddevice bridge-midplane` 追加 |

証拠: `chrony.conf.j2:9,20,30-34,37,43,53,58-64,87-116,124-128`
(`sonic-buildimage/files/image_config/chrony/chrony.conf.j2`)

---

### `/etc/chrony/chrony.keys`

**書込経路 (ブート時):**

```
config-setup.service
  → ExecStartPre: chrony-config.sh
    → sonic-cfggen -d -t /usr/share/sonic/templates/chrony.keys.j2
      >/etc/chrony/chrony.keys
    → chmod o-r /etc/chrony/chrony.keys   # world-read 削除
```

`chrony-config.sh:10-11` が `chrony.keys.j2` をレンダリングして `/etc/chrony/chrony.keys`
へ書込み、`chmod o-r` でパーミッション制限を適用する。

**書込経路 (ランタイム):** `/etc/chrony/chrony.conf` と同様に chrony 再起動の
`ExecStartPre` として再生成される。

生成内容の変化点:

| CONFIG_DB フィールド | chrony.keys への影響 |
|---------------------|---------------------|
| `NTP_KEY.<id>.type` | 鍵タイプ (`md5` 等) |
| `NTP_KEY.<id>.value` | Base64 デコード済み鍵値 |
| `NTP_SERVER.<addr>.trusted == 'yes'` かつ `resolve_as` 存在 | `trustedkey <id>` ディレクティブに追加 |
| `NTP_KEY.<id>.trusted` | **未参照 (dead field)** |

証拠: `chrony.keys.j2:7-18`
(`sonic-buildimage/files/image_config/chrony/chrony.keys.j2`)

---

## systemd 経路

### chrony.service (override.conf)

```
/etc/systemd/system/chrony.service.d/override.conf

[Unit]
Requires=config-setup.service
After=config-setup.service
After=interfaces-config.service
BindsTo=sonic.target
After=sonic.target

[Service]
ExecStartPre=!/usr/bin/chrony-config.sh     # chrony.conf / chrony.keys 生成
ExecStart=
ExecStart=!/usr/local/sbin/chronyd-starter.sh  # VRF 判定して chronyd 起動
```

`chronyd-starter.sh` は `ExecStart` として VRF 設定を参照して chrony デーモンを起動する:

1. `sonic-db-cli CONFIG_DB HGET "MGMT_VRF_CONFIG|vrf_global" "mgmtVrfEnabled"` を確認
2. `true` かつ `NTP|global.vrf != "default"` → `ip vrf exec mgmt /usr/sbin/chronyd`
3. それ以外 → `/usr/sbin/chronyd`

証拠: `chronyd-starter.sh:1-16`, `override.conf:9-11`

### hostcfgd のトリガー

| メソッド | トリガーテーブル | 発行コマンド |
|---------|--------------|------------|
| `ntp_global_update()` | `NTP\|global` | `systemctl restart chrony` |
| `ntp_srv_key_update()` | `NTP_SERVER\|*`, `NTP_KEY\|*` | `systemctl restart chrony` |
| `handle_ntp_source_intf_chg()` | LOOPBACK_INTERFACE 変更（src_intf 一致時） | `systemctl restart chrony` |
| MGMT_VRF_CONFIG 変更ハンドラ | `MGMT_VRF_CONFIG\|vrf_global` | `systemctl stop chrony` + `systemctl start chrony` |

証拠: `hostcfgd:1280,1325,1357,1398,1660-1662`

---

## まとめ

| 副次書込先 | 操作 | 条件 |
|-----------|------|------|
| `/etc/chrony/chrony.conf` | 上書き生成 | ブート時 (ExecStartPre) + ランタイム chrony 再起動のたび |
| `/etc/chrony/chrony.keys` | 上書き生成 + `chmod o-r` | 同上 |
| APPL_DB | なし | - |
| STATE_DB | なし | - |
| COUNTERS_DB | なし | - |
