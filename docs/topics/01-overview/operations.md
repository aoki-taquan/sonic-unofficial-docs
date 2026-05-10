---
title: 運用入口
area: topics
verification: meta
last_verified: 2026-05-10
sources:
  - docs/system/sonic-optional-feature-control-enhancement.md
  - docs/switching/control-sonic-behaviors-with-system-defaults-table.md
  - docs/architecture/reset-factory-design.md
  - docs/reference/cli/show-feature.md
  - docs/reference/config-db/system-defaults.md
---

# 運用入口

運用時の設定基盤は、日常変更、起動時の既定値、feature service の制御、復旧操作に分けて読むと判断しやすくなります。ここでは「何を確認してから変更するか」と「戻し方をどう考えるか」を中心に整理します。

## feature を有効化 / 無効化する

bgp、telemetry、snmp、lldp などの feature service は [FEATURE テーブル](../../reference/config-db/feature.md) と `hostcfgd` の制御対象です。初期の設計は [Optional Feature Control](../../system/sonic-optional-feature-control-enhancement.md) で、現在は `state`、`auto_restart`、`delayed`、scope、owner などのフィールドが加わっています。

運用では次の順に見ます。

1. [show feature](../../reference/cli/show-feature.md) で状態、設定、自動再起動を確認する。
2. `config feature` で変更する場合、対象 feature が必須 service か、遅延起動対象か、Multi-ASIC / DPU scope を持つか確認する。
3. 永続化が必要なら `config save` の要否を運用ルールに従って確認する。
4. service 起動に失敗した場合は `hostcfgd`、systemd unit、feature container のログを見る。

## system defaults を変更する

[SYSTEM_DEFAULTS](../../reference/config-db/system-defaults.md) は、従来 `DEVICE_METADATA` に溜まりがちだった「SONiC の既定挙動フラグ」を切り出すためのテーブルです。[System Defaults HLD](../../switching/control-sonic-behaviors-with-system-defaults-table.md) では、ビルド時既定値、minigraph、ランタイム書き込みの優先関係と、consumer が起動時または購読で取り込む考え方が示されています。

`SYSTEM_DEFAULTS` は名前の通り「既定値」です。ある機能の現在状態を直接操作するテーブルではなく、起動時や reload 時の振る舞いを変える入口として扱います。変更前には、そのフラグが即時反映されるのか、service restart / reload / reboot が必要なのかを個別ページで確認してください。

## reload と restart の影響を読む

`config reload` は、設定ファイルの再ロードと service restart を伴う大きな操作です。一方で、feature の enable / disable は `hostcfgd` と systemd unit 操作で局所的に完結する場合があります。GCU / `replace` はその中間で、差分だけを当てつつ必要な service だけを検証・再起動する設計です。

| 操作 | 影響範囲 | 事前確認 |
| --- | --- | --- |
| `config feature ...` | 対象 feature service | feature の scope、依存 service、auto_restart |
| `config apply-patch` | patch が触る CONFIG_DB テーブル | YANG validation、checkpoint、rollback |
| `config replace` | target config との差分 | target が完全 config か、dry-run 結果 |
| `config reload` | CONFIG_DB 全体と service 起動順 | maintenance window、保存済み config、reload lock |
| reboot / warm reboot | OS / container 全体 | reboot 章、warm restart 対応、traffic 影響 |

## factory reset は復旧操作として読む

[reset-factory](../../architecture/reset-factory-design.md) は、設定 corruption からの復旧や機材再利用前のサニタイズに使う強い操作です。`default`、`keep-basic`、`keep-all-config`、`only-config` のモードで、config、ログ・ファイル、ユーザをどこまで残すかが変わります。

日常の切り戻しには、まず GCU checkpoint / rollback、保存済み `config_db.json`、`config reload` を検討します。`reset-factory` は「設定基盤を初期状態へ戻す」操作であり、ログやユーザまで消すモードがあるため、障害解析中に安易に実行しない方がよい入口です。

## 関連ページ

- [FEATURE テーブルによるオプショナル機能制御](../../system/sonic-optional-feature-control-enhancement.md)
- [show feature サブコマンド](../../reference/cli/show-feature.md)
- [SYSTEM_DEFAULTS テーブル](../../reference/config-db/system-defaults.md)
- [SYSTEM_DEFAULTS HLD](../../switching/control-sonic-behaviors-with-system-defaults-table.md)
- [reset-factory](../../architecture/reset-factory-design.md)
