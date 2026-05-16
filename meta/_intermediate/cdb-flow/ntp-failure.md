# NTP — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-15 (chore/q67-f-phaseD-ntp)

<!-- failure -->
## Phase D: 失敗挙動マトリクス

ソース:
- `sonic-net/sonic-host-services/scripts/hostcfgd` (ref: master, NtpCfg L1272-1406, MgmtVrfCfg L1650-1669)
- `sonic-net/sonic-buildimage/files/image_config/chrony/chronyd-starter.sh` (ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd)
- `sonic-net/sonic-buildimage/files/image_config/chrony/chrony.conf.j2` (同 ref)
- `sonic-net/sonic-buildimage/files/image_config/chrony/chrony.keys.j2` (同 ref)

### hostcfgd NtpCfg ハンドラの失敗経路

| 失敗条件 | 検出箇所 | 結果 | STATE_DB ステータス | evidence |
|---|---|---|---|---|
| `systemctl restart chrony` 失敗 (`handle_ntp_source_intf_chg`) | `hostcfgd:1324-1328` | `LOG_ERR` → `return`（キャッシュ更新なし・再試行なし） | なし | `hostcfgd:1326-1329` |
| `systemctl restart chrony` 失敗 (`ntp_global_update`) | `hostcfgd:1356-1361` | `LOG_ERR` → `return`（キャッシュ更新なし・config_db 変更は適用済み） | なし | `hostcfgd:1358-1361` |
| `systemctl restart chrony` 失敗 (`ntp_srv_key_update`) | `hostcfgd:1397-1402` | `LOG_ERR` → `return`（キャッシュ更新なし＝次回変更時に再処理される） | なし | `hostcfgd:1399-1402` |
| `key != 'global'` または変更なし (`ntp_global_update`) | `hostcfgd:1344-1346` | `LOG_NOTICE: Nothing to update` → `return`（no-op・正常） | なし | `hostcfgd:1344-1346` |
| サーバ・鍵ともに変更なし (`ntp_srv_key_update`) | `hostcfgd:1383-1386` | `LOG_NOTICE: Nothing to update` → `return`（no-op・正常） | なし | `hostcfgd:1383-1386` |
| `src_intf` に対応するサーバが未設定 (`handle_ntp_source_intf_chg`) | `hostcfgd:1315-1316` | `return`（何も行わない、サーバ登録後に反映） | なし | `hostcfgd:1315-1316` |
| 変更 `intf_name` が `src_intf` に含まれない | `hostcfgd:1319-1321` | `return`（スキップ・正常） | なし | `hostcfgd:1319-1321` |
| `systemctl stop chrony` または `restart interfaces-config` 失敗（MGMT_VRF_CONFIG 変更時） | `hostcfgd:1659-1665` | `CalledProcessError` → `LOG_ERR` → `return`（mgmt_vrf_enabled キャッシュ未更新） | なし | `hostcfgd:1663-1666` |

### キャッシュ不整合リスク（経路依存乖離）

`ntp_global_update` は `systemctl restart chrony` **失敗時にキャッシュを更新しない**（L1364 の `self.cache[key] = data` は `try` ブロック外だが、`return` で到達しない）。
ただし CONFIG_DB の値は既に変更されているため、次回の同フィールド変更がキャッシュ差分なしと誤判定する可能性がある（`cache.get('global') == data` が true になれば no-op となる）。

`ntp_srv_key_update` は失敗時にキャッシュ更新をスキップするため、次回変更イベント発生時に再処理が保証される（差分が残るため）。

### chrony.conf.j2 / chrony.keys.j2 テンプレートの失敗経路

| 失敗条件 | 検出箇所 | 結果 | evidence |
|---|---|---|---|
| `NTP_SERVER[server].admin_state == 'disabled'` | `chrony.conf.j2:20` | そのサーバを `chrony.conf` から除外（サイレント除去） | `chrony.conf.j2:20` |
| `NTP_KEY[keyid].type` が falsy (空) | `chrony.keys.j2:15` | そのキーをキーファイルからスキップ（サイレントスキップ） | `chrony.keys.j2:15` |
| `NTP_KEY[keyid].value` が falsy (空) | `chrony.keys.j2:15` | そのキーをキーファイルからスキップ（サイレントスキップ） | `chrony.keys.j2:15` |
| `NTP_KEY[keyid].value` が正しい Base64 でない | `chrony.keys.j2:16` | `b64decode` が不正文字を無視してデコード → 誤った鍵値を chrony.keys に書き込む（サイレント誤動作） | `chrony.keys.j2:16` |
| `NTP_SERVER[server].trusted == 'yes'` かつ `resolve_as` 未設定 | `chrony.keys.j2:8-10` | `trusted_str` に追加されない（サイレントドロップ） | `chrony.keys.j2:8-10` |
| `global.authentication != 'enabled'` のとき `NTP_SERVER.key` が設定されている | `chrony.conf.j2:30-34` | `key` オプションが生成されない（サイレントドロップ） | `chrony.conf.j2:30-34` |
| `NTP.authentication == 'enabled'` だが `NTP_KEY` が空 | `chrony.conf.j2:124-128` | `keyfile` ディレクティブは追加されるが chrony.keys が空 → chrony が認証エラーで起動失敗する可能性 | `chrony.conf.j2:124-128`, `chrony.keys.j2:15-18` |
| `config.iburst == 'off'` (Jinja2 truthy) | `chrony.conf.j2:37` | `iburst` オプションが生成される（意図に反する潜在バグ） | `chrony.conf.j2:37` |
| `association_type == 'pool'` のとき `resolve_as` に FQDN 以外を設定 | `chrony.conf.j2:49-51` | `resolve_as = server`（アドレスキー）に強制上書き。pool のカスタム解決先は無視 | `chrony.conf.j2:49-51` |

### chronyd-starter.sh の失敗経路

| 失敗条件 | 検出箇所 | 結果 | evidence |
|---|---|---|---|
| `sonic-db-cli` が `MGMT_VRF_CONFIG|vrf_global.mgmtVrfEnabled` 読み取りに失敗 | `chronyd-starter.sh:3` | `VRF_ENABLED` が空 → `else` 分岐に落ちて default VRF で起動（安全フォールバック） | `chronyd-starter.sh:3-16` |
| `sonic-db-cli` が `NTP|global.vrf` 読み取りに失敗 | `chronyd-starter.sh:5` | `VRF_CONFIGURED` が空 → `else` 分岐で `mgmt` VRF 起動（`mgmtVrfEnabled=true` かつ vrf 読み取り失敗の場合は意図せず mgmt VRF で起動） | `chronyd-starter.sh:5-11` |
| `mgmtVrfEnabled=true` かつ `vrf` フィールドが `default` でも `mgmt` でもない | `chronyd-starter.sh:6` | `vrf != 'default'` → mgmt VRF で起動（YANG `pattern mgmt|default` の制約が DB 書き込み時のみ有効なため、旧データが残存する場合あり） | `chronyd-starter.sh:5-11` |
| `ip vrf exec mgmt` が失敗（mgmt VRF 未設定） | `chronyd-starter.sh:11` | `exec` が失敗 → chrony サービスが起動しない（サービス障害） | `chronyd-starter.sh:11` |

### STATE_DB ステータスの非存在

NTP 処理は `hostcfgd` + テンプレートエンジン（`chrony.conf.j2` / `chrony.keys.j2`）のパイプラインで完結するため、**STATE_DB への NTP ステータス書き込みは存在しない**。失敗検知は `journalctl -u chrony` および `/var/log/syslog` の `NtpCfg: Failed to restart chrony service` ログのみで行う。

### グレップカバレッジ

| 項目 | hit 数 | 証跡 |
|---|---|---|
| `LOG_ERR.*Failed to restart chrony` | 3 | `hostcfgd:1327, 1359, 1400` |
| `LOG_ERR.*Failed to restart management vrf` | 1 | `hostcfgd:1664` |
| `LOG_NOTICE.*Nothing to update` | 2 | `hostcfgd:1345, 1385` |
| `CHRONY_RESTART` 呼び出し | 3 | `hostcfgd:1325, 1357, 1398` |
| `exec chronyd` (chronyd-starter.sh) | 2 | `chronyd-starter.sh:8, 11` |
| `b64decode` | 1 | `chrony.keys.j2:16` |
| `admin_state != 'disabled'` | 1 | `chrony.conf.j2:20` |

<!-- /failure -->
