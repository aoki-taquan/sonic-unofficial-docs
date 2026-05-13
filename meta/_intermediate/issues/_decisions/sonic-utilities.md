# sonic-net/sonic-utilities Issues — 判定記録

生成日: 2026-05-13  
対象: 26 件 (sonic-net/sonic-utilities の open issue から選定)

---

## 判定凡例

- **apply** — docs に反映（既知バグ・落とし穴・workaround・挙動の説明を追記）
- **note** — 将来の実装変更を伴うため docs に注記のみ
- **skip** — build/CI/テスト内部の問題で docs 反映対象外

---

## 判定一覧

| # | Issue | 判定 | 反映先 |
|---|-------|------|--------|
| 4535 | pfcwd interval — TypeError when PFC_WD entry missing detection_time | **apply** | `docs/reference/cli/config-pfcwd.md` |
| 4520 | PFC Watchdog allows invalid config (poll interval > detection time) | **apply** | `docs/reference/cli/config-pfcwd.md` |
| 4518 | sfputil: add lpmode/firmware show aliases | **apply** | `docs/reference/cli/show-interfaces.md` |
| 4514 | config snmptrap del/modify → SNMP docker down (systemd rate limit) | **apply** | `docs/reference/cli/config-snmp.md` |
| 4503 | show techsupport: custom filename not supported | **apply** | `docs/reference/cli/show-techsupport.md` |
| 4501 | show interfaces counters: no per-interface filter for errors/fec/rates | **apply** | `docs/reference/cli/show-interfaces.md` |
| 4487 | route_check false-positive ERR during MACSec/interface flap | **apply** | `docs/system/critical-resource-monitoring.md` |
| 4480 | val_state missing → column misalign in multi-ASIC tunnel table | **apply** | `docs/reference/cli/show-interfaces.md` |
| 4400 | show ntp: wrong VRF when NTP|global.vrf=default + mgmt VRF enabled | **apply** | `docs/reference/cli/config-ntp.md` |
| 4398 | Tab completion broken when bash-completion not installed | **apply** | `docs/reference/cli/config-ntp.md` (general CLI ops-hint) |
| 4378 | show vrf <unconfigured>: exits 0 with empty table | **apply** | `docs/reference/cli/config-vrf.md` |
| 4375 | counterpoll CLI ignores namespace when called via ip netns exec | **apply** | `docs/reference/cli/show-interfaces.md` |
| 4371 | fast-reboot/warm-reboot improperly when called as root | **apply** | `docs/system/fast-reboot-flow-improvements-hld.md` |
| 4352 | Security vulnerability reports in sonic-utilities | **skip** | セキュリティ報告窓口の案内のみ（CVE 未公開） |
| 4307 | YANG validation fails: docker_routing_config_mode set to "None" string | **apply** | `docs/reference/cli/config-vrf.md` |
| 4239 | libyang back-reference test failure (build test internal) | **skip** | ビルドテスト内部問題 |
| 4221 | PatchSorter: numeric path tokens coerced to int — KeyError on string keys | **apply** | `docs/reference/cli/sonic-cfggen.md` |
| 4144 | sonic-clear priority-group drop counters requires root unnecessarily | **apply** | `docs/reference/cli/show-priority-group.md` |
| 4139 | show bfd summary: software-BFD peers not shown (only FRR-originated) | **apply** | `docs/reference/cli/show-bfd.md` |
| 4107 | YANG validation fails for DOT1P_TO_TC_MAP|ROCE key with pipe char | **apply** | `docs/reference/cli/config-qos.md` |
| 4065 | sfputil/show transceiver shows 8 lanes for QSFP+C (should be 4) | **apply** | `docs/reference/cli/show-interfaces.md` |
| 4056 | sonic-cli-gen: multi-line YANG descriptions crash click.options | **apply** | `docs/reference/cli/sonic-cfggen.md` |
| 3978 | show mux config: column header misaligned (breaks automation) | **apply** | `docs/reference/cli/show-muxcable.md` |
| 3923 | Enable switch ingress drop monitoring by default (pending impl) | **note** | `docs/reference/cli/clear-counters.md` (運用ヒント) |
| 3897 | storm-control: CLI uses unknown-multicast but SAI uses flood (unicast+multicast) | **apply** | `docs/reference/cli/show-storm-control.md` |
| 3747 | Cannot configure IPv6 ERSPAN sessions from CLI (IPv4 only validator) | **apply** | `docs/reference/cli/config-mirror-session.md` |

---

## 詳細判定メモ

### #4535 — pfcwd interval TypeError
**問題**: `config pfcwd interval N` が、`PFC_WD|EthernetX` エントリに `detection_time` / `restoration_time` が無い場合に `TypeError: int() argument ... not 'NoneType'` でクラッシュ。`pfc_stat_history` コマンドがフィールドなしでエントリを生成するとき発生。  
**回避策**: `redis-cli` で問題エントリを手動削除してから再試行。  
**反映**: config-pfcwd.md の「よくある落とし穴」に追記。

### #4520 — PFC poll interval > detection time
**問題**: polling interval を先に大きな値に設定し、その後 detection time が小さいポートで pfcwd を有効化しても CLI は検証エラーなしで受け付ける。interval > min(detection_time) の制約が未実装。  
**反映**: config-pfcwd.md の「よくある落とし穴」に追記。

### #4518 — sfputil lpmode/firmware alias
**問題/提案**: `sfputil lpmode --help` や `sfputil firmware --help` には読み取り系コマンドが表示されない（`sfputil show lpmode` / `sfputil show fwversion` が別階層にある）。  
**反映**: show-interfaces.md のトランシーバ節に discoverability の注記を追記。

### #4514 — config snmptrap rapid restart → systemd rate limit
**問題**: `config snmptrap del` / `modify` が連続すると systemd の start rate limit に引っかかり SNMP コンテナが落ちる。`systemctl restart snmp` を毎回呼ぶ実装が原因。  
**回避策**: 操作間に最低 5 秒の間隔を空ける。落ちた場合は `systemctl reset-failed snmp && systemctl start snmp` で回復。  
**反映**: config-snmp.md の「よくある落とし穴」に追記。

### #4503 — show techsupport custom filename
**問題/提案**: ダンプは常に `/var/dump/<HOSTNAME>_YYYYMMDD_HHMMSS.tar.gz` に保存される。カスタムファイル名は未実装（enhancement request）。  
**反映**: show-techsupport.md の「制限事項」節に追記。

### #4501 — show interfaces counters subcommands missing per-interface filter
**問題**: `show interfaces counters errors`、`fec-stats`、`rates` は `-i <interface>` フィルタを受け付けない（親コマンドの `show interfaces counters -i` は受け付ける）。  
**回避策**: `show interfaces counters errors | grep Ethernet4` のように grep で絞る。  
**反映**: show-interfaces.md の「よくある落とし穴」に追記。

### #4487 — route_check false-positive during interface flap
**問題**: MACSec テスト中など BGP セッションが瞬断するタイミングで `route_check.py` が `missed_ROUTE_TABLE_routes` を誤検知し、monit が ERR を syslog に記録する。これはテスト上の問題だが、本番環境でも interface flap 直後に同様のアラートが出る可能性がある。  
**反映**: `docs/system/critical-resource-monitoring.md` の注意事項に追記。

### #4480 — val_state missing → column misalign in tunnel table
**問題**: multi-ASIC モック環境など `val_state` が返らない場合、表示行が `tunnel_header` より 1 列少なくなり、`status` カラムがずれて表示される。  
**反映**: show-interfaces.md の「既知の挙動・制限」に追記（multi-ASIC）。

### #4400 — show ntp VRF mismatch
**問題**: mgmt VRF が有効で `NTP|global.vrf = "default"` の場合、`chronyd-starter.sh` はデフォルト VRF で chrony を起動するが、`show ntp` は mgmt VRF 経由で `chronyc` を呼ぶ。VRF が食い違い「Invalid VRF name」または空出力になる。PR#3574 (chrony 移行) で混入。  
**回避策**: `ip vrf exec default chronyc tracking` で直接確認する。  
**反映**: config-ntp.md の「よくある落とし穴」に追記。

### #4398 — Tab completion broken without bash-completion package
**問題**: `sonic-utilities-data` は bash completion script を `/etc/bash_completion.d/` に置くが、`bash-completion` フレームワーク自体は `Suggests` であり `Depends` ではない。deb version pinning なしのビルドでは `bash-completion` が未インストールとなり、tab completion が全 CLI コマンドで機能しない。  
**回避策**: `sudo apt-get install bash-completion && source /etc/bash_completion` で手動インストール。  
**反映**: config-ntp.md ではなく、一般的な CLI ops-hint として config-pfcwd.md に注記追加（共通項目として）。実際の反映は show-interfaces.md の ops-hint に追記する。

### #4378 — show vrf <unconfigured> returns exit 0 with empty table
**問題**: 設定されていない VRF 名を `show vrf <vrfname>` に渡すと、空のテーブルが表示されて exit code 0 で終わる。スクリプトからの自動確認が誤動作する原因になる。  
**回避策**: `show vrf <name>` の出力行数で判定するか、`ip vrf show <name>` で確認。  
**反映**: config-vrf.md の「よくある落とし穴」に追記。

### #4375 — counterpoll ignores namespace
**問題**: `sudo ip netns exec asic0 counterpoll pg-drop disable` としても、書き換わるのは default namespace の `CONFIG_DB` であり、`CONFIG_DB0`（asic0 の DB）は更新されない。multi-ASIC で `counterpoll` 系を per-namespace で操作したい場合は `-n asic0` オプションを使う必要がある。  
**回避策**: `counterpoll pg-drop disable -n asic0` を使う。  
**反映**: show-interfaces.md の multi-ASIC 節に追記。

### #4371 — fast-reboot/warm-reboot called as root
**問題**: root ユーザーから直接 `fast-reboot` / `warm-reboot` を呼ぶと `SUDO_USER` / `XDG_SESSION_CLASS` が設定されず、warmboot/dump.rdb の生成・最終リブートアクションが誤動作する。`sudo fast-reboot` (admin ユーザー経由) でのみ正常動作。  
**回避策**: 必ず `admin` ユーザーから `sudo fast-reboot` で実行する。root シェルから直接実行しない。  
**反映**: fast-reboot-flow-improvements-hld.md の「注意」節に追記。

### #4352 — Security vulnerabilities
セキュリティ報告は非公開 (GitHub Advisory / security@lists.sonicfoundation.dev 経由)。CVE 詳細は未公開のため docs 反映対象外。

### #4307 — YANG validation fails: docker_routing_config_mode = "None" string
**問題**: `config reload` 後に `docker_routing_config_mode` フィールドが Python の `None` を str 化した `"None"` という文字列として CONFIG_DB に書かれ、YANG 検証が失敗する。minigraph.xml で該当要素が空の場合に発生。  
**回避策**: `sonic-db-cli CONFIG_DB DEL "DEVICE_METADATA|localhost" docker_routing_config_mode` で当該フィールドを削除してから再度 `config reload`。  
**反映**: config-vrf.md の「よくある落とし穴」に追記（config reload 関連）。

### #4239 — libyang back-reference test failure
ビルドテストスクリプト内部の問題 (generic_config_updater テスト)。docs 反映対象外。

### #4221 — PatchSorter numeric token coercion
**問題**: `generic_config_updater` の `PatchSorter._get_value()` が数値文字列トークン（例: `"8"`, `"7"`）を自動で `int` に変換する。CONFIG_DB の `TC_TO_QUEUE_MAP` 等はキーが文字列なので `config["8"]` は存在するが `config[8]` は存在せず KeyError / patch 適用失敗になる。  
**回避策**: `generic_config_updater` 経由でパッチを当てるのではなく、直接 `sonic-db-cli` で値を更新する。  
**反映**: sonic-cfggen.md の「既知のバグ・制限」節に追記。

### #4144 — sonic-clear priority-group drop counters requires root
**問題**: `show priority-group drop counters` は root 権限なしで動くが、`sonic-clear priority-group drop counters` は root が必須。PG drop counter のキャッシュは UID 単位なので、admin ユーザーが clear しても root のキャッシュが消えるだけで admin の表示に反映されない。  
**回避策**: `pg-drop -c clear` を使う（root 不要）、または `sudo sonic-clear priority-group drop counters` 後に `show priority-group drop counters` を root または同 UID で実行。  
**反映**: show-priority-group.md の「よくある落とし穴」に追記。

### #4139 — show bfd summary: software-BFD peers not shown
**問題**: FRR/vtysh で設定した software-BFD ピア（`BGP_NEIGHBOR` 配下でダイナミックに生成）は `BFD_SESSION_TABLE` に書かれないため `show bfd summary` に表示されない。`vtysh -c "show bfd peer"` でのみ確認できる。  
**回避策**: software-BFD の状態は `vtysh -c "show bfd peer"` で確認する。  
**反映**: show-bfd.md の「よくある落とし穴」と「データソース」節に追記。

### #4107 — YANG validation: DOT1P_TO_TC_MAP|ROCE fails pattern check
**問題**: `config reload config_db.json <explicit-file>` を実行すると `"DOT1P_TO_TC_MAP|ROCE"` のようなパイプ文字 (`|`) を含む参照値が YANG の pattern 制約（`[a-zA-Z0-9]{1}([-a-zA-Z0-9_]{0,31})`）に引っかかって失敗する。ファイル指定なしの `config reload` では YANG 検証のコードパスが異なり発生しない。  
**回避策**: `config reload -y` (引数なし) を使う。または当該フィールドの値をパイプなしの短縮名に変更する。  
**反映**: config-qos.md の「よくある落とし穴」に追記。

### #4065 — sfputil/show transceiver: 8 lanes for QSFP+C
**問題**: QSFP+C (CMIS 管理の QSFP) は物理 4 lanes なのに、`show interfaces transceiver status` / `eeprom` が lane 1-8 を表示する（lanes 5-8 は `Unknown` / `False` / 0 が並ぶ）。表示が冗長で誤解を招く。  
**反映**: show-interfaces.md の「既知の挙動」に注記追加。

### #4056 — sonic-cli-gen: multi-line YANG description crashes click
**問題**: `sonic-cli-gen generate config <yang>` で YANG フィールドの description が複数行の場合、生成 Python ファイルに `"` で囲まれた複数行文字列が展開され `SyntaxError: unterminated string literal` が発生する。該当コマンドグループ全体が import 失敗する。  
**回避策**: YANG モデルの description を1行に収める。または生成ファイルを手動で triple-quote に修正。  
**反映**: sonic-cfggen.md の「既知のバグ・制限」節に追記。

### #3978 — show mux config column header misalignment
**問題**: `show mux config` の出力でヘッダ行が本来の列位置からズレており、自動 parse (`show_and_parse`) が `port` カラムを空文字列として取得する。Ansible playbookや pytest で KeyError が発生する原因。PR#3884 で混入。  
**反映**: show-muxcable.md の「既知のバグ・制限」節に追記。

### #3923 — Enable ingress drop monitoring by default
実装待ち (enhancement request、HLD PR#1912 参照)。現時点では default で無効。  
**反映**: clear-counters.md に「現状デフォルト無効」の注記を追加。

### #3897 — storm-control: unknown-multicast vs SAI flood
**問題**: SONiC CLI は `broadcast` / `unknown-unicast` / `unknown-multicast` の 3 種類を受け付けるが、SAI の `SAI_PORT_ATTR_FLOOD_STORM_CONTROL_POLICER_ID` は unknown-unicast と unknown-multicast を一括して `flood` として扱う。`SAI_PORT_ATTR_MULTICAST_STORM_CONTROL_POLICER_ID` は registered multicast 専用。CLI の `unknown-multicast` が SAI 側でどの属性にマップされるかはベンダー実装依存の可能性がある。  
**反映**: show-storm-control.md の「注意」節に追記。

### #3747 — IPv6 ERSPAN not supported in CLI
**問題**: swss 側では IPv6 の ERSPAN (src/dst 両方 IPv6) セッションが CONFIG_DB 上でサポートされているが、CLI (`config mirror_session erspan add`) は `<src_ip>` / `<dst_ip>` を `IPv4Address` として検証するため IPv6 アドレスを渡すと `Error: fc00::1:1:1:1 is not a valid IPv4 address` で拒否される。  
**回避策**: `sonic-db-cli CONFIG_DB HSET "MIRROR_SESSION|<name>" dst_ip <ipv6> src_ip <ipv6> ...` で直接 CONFIG_DB に書き込む。  
**反映**: config-mirror-session.md の「既知のバグ・制限」節に追記。
