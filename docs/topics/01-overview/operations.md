---
title: 運用入口
description: 運用入口 — 運用時の設定基盤は、日常変更、起動時の既定値、feature service の制御、復旧操作に分けて読むと判断しやすくなります。ここでは「何を確認してから変更するか」と「戻し方をどう考えるか」を中心に整理します。
area: topics
verification: meta
last_verified: 2026-05-10
sources:
- docs/system/sonic-optional-feature-control-enhancement.md
- docs/switching/control-sonic-behaviors-with-system-defaults-table.md
- docs/architecture/reset-factory-design.md
- docs/reference/cli/show-feature.md
- docs/reference/config-db/system-defaults.md
related:
  cli:
  - show feature
  - config vnet
  - config bgp
  - show bgp
  - config vxlan
  config_db:
  - SYSTEM_DEFAULTS
  - FEATURE
  - VNET
  - DEVICE_METADATA
  - BGP_PEER_GROUP_AF
  - BGP_GLOBALS_AF_NETWORK
  - BGP_GLOBALS_AF_AGGREGATE_ADDR
  yang:
  - sonic-vnet
  - sonic-bgp-monitor
  - sonic-bgp-peergroup
  - sonic-bgp-peerrange
  - sonic-bgp-global
  - sonic-bgp-bbr
  - sonic-bgp-aggregate-address
---

# 運用入口

運用時の設定基盤は、日常変更、起動時の既定値、feature service の制御、復旧操作に分けて読むと判断しやすくなります。ここでは「何を確認してから変更するか」と「戻し方をどう考えるか」を中心に整理します。

## feature を有効化 / 無効化する

bgp、telemetry、snmp、lldp などの feature service は [FEATURE テーブル](../../reference/config-db/feature.md) と `hostcfgd` の制御対象です。初期の設計は [Optional Feature Control](../../system/sonic-optional-feature-control-enhancement.md) で、現在は `state`、`auto_restart`、`delayed`、scope、owner などのフィールドが加わっています。

運用では次の順に見ます。

1. [show feature](../../reference/cli/show-feature.md) で状態、設定、自動再起動を確認する。
2. `config feature` で変更する場合、対象 feature が必須 service か、遅延起動対象か、Multi-ASIC / [DPU](../../reference/glossary.md#term-dpu) scope を持つか確認する。
3. 永続化が必要なら `config save` の要否を運用ルールに従って確認する。
4. service 起動に失敗した場合は `hostcfgd`、systemd unit、feature container のログを見る。

## system defaults を変更する

[SYSTEM_DEFAULTS](../../reference/config-db/system-defaults.md) は、従来 `DEVICE_METADATA` に溜まりがちだった「SONiC の既定挙動フラグ」を切り出すためのテーブルです。[System Defaults HLD](../../switching/control-sonic-behaviors-with-system-defaults-table.md) では、ビルド時既定値、minigraph、ランタイム書き込みの優先関係と、consumer が起動時または購読で取り込む考え方が示されています。

`SYSTEM_DEFAULTS` は名前の通り「既定値」です。ある機能の現在状態を直接操作するテーブルではなく、起動時や reload 時の振る舞いを変える入口として扱います。変更前には、そのフラグが即時反映されるのか、service restart / reload / reboot が必要なのかを個別ページで確認してください。

## reload と restart の影響を読む

`config reload` は、設定ファイルの再ロードと service restart を伴う大きな操作です。一方で、feature の enable / disable は `hostcfgd` と systemd unit 操作で局所的に完結する場合があります。[GCU](../../reference/glossary.md#term-gcu) / `replace` はその中間で、差分だけを当てつつ必要な service だけを検証・再起動する設計です。

| 操作 | 影響範囲 | 事前確認 |
| --- | --- | --- |
| `config feature ...` | 対象 feature service | feature の scope、依存 service、auto_restart |
| `config apply-patch` | patch が触る [CONFIG_DB](../../reference/glossary.md#term-config_db) テーブル | [YANG](../../reference/glossary.md#term-yang) validation、checkpoint、rollback |
| `config replace` | target config との差分 | target が完全 config か、dry-run 結果 |
| `config reload` | CONFIG_DB 全体と service 起動順 | maintenance window、保存済み config、reload lock |
| reboot / warm reboot | OS / container 全体 | reboot 章、warm restart 対応、traffic 影響 |

## factory reset は復旧操作として読む

[reset-factory](../../architecture/reset-factory-design.md) は、設定 corruption からの復旧や機材再利用前のサニタイズに使う強い操作です。`default`、`keep-basic`、`keep-all-config`、`only-config` のモードで、config、ログ・ファイル、ユーザをどこまで残すかが変わります。

日常の切り戻しには、まず GCU checkpoint / rollback、保存済み `config_db.json`、`config reload` を検討します。`reset-factory` は「設定基盤を初期状態へ戻す」操作であり、ログやユーザまで消すモードがあるため、障害解析中に安易に実行しない方がよい入口です。

## show feature の出力サンプル

実装上、`show feature status` は CONFIG_DB の `FEATURE` テーブルと [STATE_DB](../../reference/glossary.md#term-state_db) の `FEATURE|<name>` を結合して表示します。標準構成では次の通り、`State`、`AutoRestart`、`SetOwner` の 3 カラムが出ます。

```text
Feature     State           AutoRestart     SetOwner
----------  --------------  --------------  ----------
bgp         enabled         enabled         local
database    always_enabled  always_enabled  local
dhcp_relay  enabled         enabled         kube
lldp        enabled         enabled         kube
nat         enabled         enabled         local
pmon        enabled         enabled         kube
radv        enabled         enabled         kube
restapi     disabled        enabled         local
sflow       disabled        enabled         local
snmp        enabled         enabled         kube
swss        enabled         enabled         local
syncd       enabled         enabled         local
teamd       enabled         enabled         local
telemetry   enabled         enabled         kube
```

remote management が有効な構成では追加で `SystemState`、`UpdateTime`、`ContainerId`、`Version`、`CurrentOwner`、`RemoteState` が出ます。

```text
Feature   State    AutoRestart  SystemState  UpdateTime           ContainerId   Version       SetOwner  CurrentOwner  RemoteState
--------  -------  -----------  -----------  -------------------  ------------  ------------  --------  ------------  -----------
snmp      enabled  enabled      up           2020-11-12 23:32:56  aaaabbbbcccc  20201230.100  kube      kube          kube
```

カラムの意味:

- `State` は CONFIG_DB の `FEATURE|<name>:state`。`enabled` / `disabled` / `always_enabled` / `always_disabled` を取り得ます。`always_*` は build-time fix で `config feature` から変更できません。
- `AutoRestart` は systemd unit が落ちた時に `hostcfgd` が再起動するかの方針です。
- `SystemState` は STATE_DB が示す現在状態。`up` 以外（`down` / 空）は service が立ち上がっていないことを疑います。
- `SetOwner` は `local`（host）か `kube`（kubernetes-managed）の指定で、`CurrentOwner` がそれと一致しなければ kube join 中などの過渡状態です。

## 異常検出パターン

| 観測値 | 疑う状態 | 一次切り分け |
|---|---|---|
| `State=enabled` だが `SystemState=down` | container 起動失敗、依存 service 未起動、image 不一致 | `systemctl status <feature>`、`docker ps -a`、`journalctl -u <feature>` |
| `AutoRestart=enabled` で繰り返し再起動 | container 内部の crash loop | `docker logs <container>`、`/var/log/syslog` の `Main process exited` 連続発生 |
| `delayed=True` の feature が起動しない | `delayed-` timer 単位の起動順、または前提 service 失敗 | `systemctl list-timers`、`<feature>-delayed.timer` を確認 |
| `SetOwner=kube` で `CurrentOwner=local` | kube join 未完了、または kube image pull 失敗 | `show feature config` で `version` 表示、`docker images` で kube tag 有無 |
| `config save` 後も次回 reboot で消える | `/etc/sonic/config_db.json` への書き込み失敗、または read-only FS | `ls -l /etc/sonic/`、`mount` で rw 確認 |

## 典型的なログサンプル

`hostcfgd` は feature の enable/disable と AutoRestart 反映を担当します。`/var/log/syslog` には次のような行が出ます。

```text
hostcfgd: Feature 'bgp' is enabled and started
hostcfgd: Feature 'snmp' is disabled and stopped
hostcfgd: Feature 'telemetry' restart policy set to 'enabled'
hostcfgd: Feature 'lldp' state transition disabled->enabled
```

`systemctl status bgp` の異常時には次のようなテイルが付きます。

```text
bgp.service: Main process exited, code=exited, status=1/FAILURE
bgp.service: Failed with result 'exit-code'.
Stopped BGP container.
bgp.service: Scheduled restart job, restart counter is at 5.
```

`docker logs bgp` で container 側の [zebra](../../reference/glossary.md#term-zebra)/bgpd 立ち上げに失敗している場合は別途 [BGP](../../reference/glossary.md#term-bgp) 章を参照します。

## 対応コマンド早見表

| 目的 | コマンド |
|---|---|
| feature 一覧 | `show feature status` |
| 設定だけ確認 | `show feature config` |
| 個別 feature 切替 | `config feature state <name> enabled\|disabled` |
| AutoRestart 切替 | `config feature autorestart <name> enabled\|disabled` |
| owner 切替 | `config feature owner <name> local\|kube` |
| service 再起動 | `systemctl restart <feature>` |
| systemd unit 状態 | `systemctl status <feature>` |
| container 状態 | `docker ps`、`docker logs <container>` |
| 設定保存 | `config save -y` |
| 設定再適用 | `config reload -y` |
| 差分適用 | `config apply-patch <patch.json>` |
| target で置換 | `config replace <target.json>` |
| 工場初期化 | `sonic-installer set-default <image>` ／ `sudo reset-factory` |

## 関連 CONFIG_DB / STATE_DB

- `CONFIG_DB:FEATURE|<name>` — `state`、`auto_restart`、`delayed`、`high_mem_alert`、`set_owner`、`support_syslog_rate_limit`、`has_global_scope`、`has_per_asic_scope`、`has_per_dpu_scope` を保持。
- `CONFIG_DB:SYSTEM_DEFAULTS|<flag>` — 起動時の既定挙動フラグ。`tunnel_qos_remap`、`synchronous_mode`、`mac_expiry_for_dualtor` 等。
- `STATE_DB:FEATURE|<name>` — `system_state`、`update_time`、`container_id`、`container_version`、`current_owner`、`remote_state`。
- `STATE_DB:DEVICE_METADATA|localhost` — 起動時のマシン状態（hwsku、platform、type）の確認用。

## 横断参照

- BGP service が起動しない場合: [BGP 章 運用](../02-bgp/operations.md) の neighbor / [orchagent](../../reference/glossary.md#term-orchagent) 切り分け。
- [VXLAN](../../reference/glossary.md#term-vxlan) / [VNET](../../reference/glossary.md#term-vnet) 関連 service の前提: [Overlay 章 運用](../03-vxlan-evpn/operations.md)。
- L2 service（[teamd](../../reference/glossary.md#term-teamd-teamsyncd-teammgrd)、swss）の連動失敗: [L2 章 運用](../06-l2-vlan-lag/operations.md)。
- Dual-ToR 構成での feature 順序（mux、[linkmgrd](../../reference/glossary.md#term-linkmgrd)、telemetry）: [Dual-ToR 章 運用](../05-dual-tor/operations.md)。

## 追加の show 出力例

`show feature config` は CONFIG_DB の `FEATURE` テーブルだけを抜粋表示し、起動時挙動を確認できます。

```text
Feature     State           AutoRestart     Delayed  HighMemAlert  SetOwner
----------  --------------  --------------  -------  ------------  --------
bgp         enabled         enabled         False    disabled      local
dhcp_relay  enabled         enabled         True     disabled      kube
lldp        enabled         enabled         False    disabled      kube
snmp        enabled         enabled         False    disabled      kube
telemetry   enabled         enabled         True     disabled      kube
```

`Delayed=True` は systemd の `*-delayed.timer` 経由で遅延起動される feature です。boot 直後に `up` にならないことが正常仕様の場合があるため、`systemctl list-timers '*-delayed.timer'` で次回起動予定時刻を併せて確認します。

```text
NEXT                          LEFT     LAST  PASSED  UNIT                 ACTIVATES
Mon 2026-05-11 12:05:43 UTC   2min     n/a   n/a     telemetry-delayed.timer   telemetry-delayed.service
Mon 2026-05-11 12:08:00 UTC   4min     n/a   n/a     dhcp_relay-delayed.timer  dhcp_relay-delayed.service
```

## 典型的な運用シナリオ

1. **新規 feature 有効化** — `config feature state <name> enabled` 後に `show feature status` で `SystemState=up` を確認し、当該 container の `docker ps` を見ます。`enabled` だが `down` のまま停滞する場合は `systemctl status <feature>` の Main process exit を見ます。
2. **設定差分の慎重な適用** — `config apply-patch` で patch を適用する前に `config checkpoint <name>` を取り、失敗時に `config rollback <name>` で戻せる状態を作ります。GCU は YANG 検証を通すため、`config replace` よりも安全側です。
3. **kube 管理への移行** — `SetOwner` を `kube` に切り替えた直後は `CurrentOwner` が `local` のまま残るのが正常で、kube join 後に一致します。長時間一致しない場合は kube image pull と `acms` connectivity を疑います。
4. **緊急時の reload と reboot 判断** — service 個別 restart で復旧する見込みがあるなら `systemctl restart <feature>` で局所化します。CONFIG_DB の不整合が広範な場合のみ `config reload -y`、kernel / image 自体の問題なら `fast-reboot` または `reboot` を選びます。
5. **factory reset の決断** — `config reload` でも復旧しない設定 corruption、または機材払い出し前のサニタイズ用途でのみ `reset-factory` を選びます。本番投入機ではログとユーザを残すモードを選び、データ消失を最小化します。

## 関連ページ

- [FEATURE テーブルによるオプショナル機能制御](../../system/sonic-optional-feature-control-enhancement.md)
- [show feature サブコマンド](../../reference/cli/show-feature.md)
- [SYSTEM_DEFAULTS テーブル](../../reference/config-db/system-defaults.md)
- [SYSTEM_DEFAULTS HLD](../../switching/control-sonic-behaviors-with-system-defaults-table.md)
- [reset-factory](../../architecture/reset-factory-design.md)

<!-- glossary-links-injected: c7663e102d50 -->
