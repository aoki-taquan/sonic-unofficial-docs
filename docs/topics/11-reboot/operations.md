---
title: Reboot 運用と障害調査
description: Reboot 運用と障害調査 — 実行前に peer と platform の前提を揃え、実行中は warm shutdown / restore の境界を見失わず、実行後は reboot-cause と reconciliation 状態を確認するための切り分け手順をまとめる。
area: topics
verification: code-verified
last_verified: 2026-06-06
sources:
- repo: sonic-net/sonic-utilities
  path: scripts/reboot
  ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
- repo: sonic-net/sonic-utilities
  path: show/reboot_cause.py
  ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
- repo: sonic-net/sonic-swss
  path: fpmsyncd/fpmsyncd.cpp
  ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
- repo: sonic-net/sonic-swss
  path: doc/swss-schema.md
  ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
related:
  cli:
  - show reboot-cause
  - show warm_restart
  - show interfaces portchannel
  - show techsupport
  - show version
  config_db:
  - WARM_RESTART
  - BGP_NEIGHBOR
  yang:
  - sonic-warm-restart
---

# Reboot 運用と障害調査

reboot 運用で重要なのは、実行前に peer と platform の前提を揃えること、実行中に warm shutdown / restore の境界を見失わないこと、実行後に原因と復元結果を確認することです。特に warm reboot は「コマンドが成功したか」だけでは不十分で、[FDB](../../reference/glossary.md#term-fdb)/neighbor/route/[LAG](../../reference/glossary.md#term-lag)/[BGP](../../reference/glossary.md#term-bgp) が期待通り戻ったかを見る必要があります。

## 失敗時の確認順

1. reboot 種別と入口を確認する。`reboot`、`fast-reboot`、`warm-reboot`、service restart のどれかで見る DB と log が変わります。
2. pre-check と終了コードを確認する。次回 image 検証、platform pre-check、FW auto-update conflict は reboot 前に失敗します。
3. warm path では pre-shutdown ACK、DB backup、[syncd](../../reference/glossary.md#term-syncd) shutdown、[SAI](../../reference/glossary.md#term-sai) warm shutdown のどこで止まったかを分けます。
4. 起動後は reconciliation の完了、EOIU、neighbor/route restore、[teamd](../../reference/glossary.md#term-teamd-teamsyncd-teammgrd)/[LACP](../../reference/glossary.md#term-lacp) restore を確認します。
5. 最後に reboot-cause 履歴を見て、想定 reboot か crash/panic/watchdog かを切り分けます。

[Reboot-cause 履歴の STATE_DB / テレメトリ公開](../../system/reboot-cause-information-via-telemetry-agent.md) は、起動時に cause を判定し、[STATE_DB](../../reference/glossary.md#term-state_db) と telemetry へ公開する流れを説明しています。

```text
admin@sonic:~$ show reboot-cause
User issued 'warm-reboot' command [User: admin, Time: Mon May 10 11:00:01 UTC 2026]

admin@sonic:~$ show reboot-cause history
Name                 Cause       Time                            User    Comment
-------------------  ----------  ------------------------------  ------  -------
2026_05_10_11_00_01  warm-reboot Mon May 10 11:00:01 UTC 2026    admin   N/A
2026_05_09_03_22_45  Kernel Panic Sun May  9 03:22:45 UTC 2026   N/A     N/A
2026_05_08_19_10_00  Power Loss  Sat May  8 19:10:00 UTC 2026    N/A     N/A
```

`Kernel Panic` / `Watchdog` / `Power Loss` / `Hardware - reason` のいずれかが出ている場合は計画外で、`/host/reboot-cause/` 配下のテキストファイルと vmcore (kdump 有効時) を一次資料として保全します。

```bash
ls /host/reboot-cause/
cat /host/reboot-cause/reboot-cause.txt
cat /host/reboot-cause/previous-reboot-cause.json
```

<!-- evidence:
source: sonic-net/sonic-utilities/scripts/reboot#L14 (sha: 39732bceb8bdefe706518ab40623bbbba6ff33b9)
excerpt: |
  REBOOT_CAUSE_FILE="/host/reboot-cause/reboot-cause.txt"
reasoning: reboot / fast-reboot / soft-reboot のいずれの wrapper script も /host/reboot-cause/reboot-cause.txt を最新 cause の生ファイルとして書き出す。
-->

<!-- evidence-rendered:start -->
??? note "📋 検証エビデンス: sonic-net/sonic-utilities/scripts/reboot#L14 (sha: 39732bceb8bdefe706518ab40623bbbba6ff33b9)"

    **出典**:

    `sonic-net/sonic-utilities/scripts/reboot#L14 (sha: 39732bceb8bdefe706518ab40623bbbba6ff33b9)`

    **抜粋**:

    ```text
    REBOOT_CAUSE_FILE="/host/reboot-cause/reboot-cause.txt"
    ```

    **判断根拠**: reboot / fast-reboot / soft-reboot のいずれの wrapper script も /host/reboot-cause/reboot-cause.txt を最新 cause の生ファイルとして書き出す。

<!-- evidence-rendered:end -->

<!-- evidence:
source: sonic-net/sonic-utilities/show/reboot_cause.py#L13-L23 (sha: 39732bceb8bdefe706518ab40623bbbba6ff33b9)
excerpt: |
  PREVIOUS_REBOOT_CAUSE_FILE_PATH = "/host/reboot-cause/previous-reboot-cause.json"
  ...
  if os.path.exists(PREVIOUS_REBOOT_CAUSE_FILE_PATH):
      with open(PREVIOUS_REBOOT_CAUSE_FILE_PATH) as prev_reboot_cause_file:
reasoning: show reboot-cause は前回 cause を /host/reboot-cause/previous-reboot-cause.json から JSON として読み込む。
-->

<!-- evidence-rendered:start -->
??? note "📋 検証エビデンス: sonic-net/sonic-utilities/show/reboot_cause.py#L13-L23 (sha: 39732bceb8bdefe706518ab40623bbbba6ff33b9)"

    **出典**:

    `sonic-net/sonic-utilities/show/reboot_cause.py#L13-L23 (sha: 39732bceb8bdefe706518ab40623bbbba6ff33b9)`

    **抜粋**:

    ```text
    PREVIOUS_REBOOT_CAUSE_FILE_PATH = "/host/reboot-cause/previous-reboot-cause.json"
    ...
    if os.path.exists(PREVIOUS_REBOOT_CAUSE_FILE_PATH):
        with open(PREVIOUS_REBOOT_CAUSE_FILE_PATH) as prev_reboot_cause_file:
    ```

    **判断根拠**: show reboot-cause は前回 cause を /host/reboot-cause/previous-reboot-cause.json から JSON として読み込む。

<!-- evidence-rendered:end -->

## LACP と peer 側の時間

warm reboot では自装置だけでなく peer 側の待ち時間が結果を左右します。LAG peer が短い timeout で partner を落とすと、data plane を維持しても bundle が崩れます。[Warm-reboot 中の LACP retry count 拡張](../../switching/increasing-lacp-pdu-timeout-during-warm-reboot.md) は、LACP PDU の拡張により warm reboot 中の retry count を増やす設計です。

BGP も同様に [Graceful Restart](../../reference/glossary.md#term-graceful-restart) と timer が前提です。warm reboot を有効化しても、peer が GR を許容しなければ L3 adjacency は維持されません。

```text
sw01# show bgp neighbors 10.0.0.1 graceful-restart
BGP neighbor is 10.0.0.1
  Local GR Mode : Helper*
  Remote GR Mode: Restart
  R bit: True
  Configured Restart Time(sec): 240
  Received Restart Time(sec): 240
  ...
```

`Remote GR Mode` が `Disable` の peer は warm reboot 中に session を落とす可能性が高いので、対象から外すか peer 側設定を変えます。

```text
admin@sonic:~$ show warm_restart config
name        enable    timer_name             timer_duration
----------  --------  ---------------------  --------------
swss        true                             -
bgp         true      bgp_timer              180
teamd       true      teamsyncd_timer         30
```

LACP の retry 拡張は teamd 側のオプション化されており、warm reboot 中だけ retry を増やします。同 [HLD](../../reference/glossary.md#term-hld) のシーケンス図と [CONFIG_DB](../../reference/glossary.md#term-config_db) の `WARM_RESTART_TABLE` を併せて読みます。

## multi-ASIC warm reboot

multi-[ASIC](../../reference/glossary.md#term-asic) では、namespace ごとに service、DB、ASIC が分かれます。warm reboot は default namespace だけで完結せず、ASIC namespace 群の shutdown / boot 順序、除外指定、DB backup、peer 影響を合わせて扱います。詳細は [Multi-ASIC warm reboot](../../system/multi-asic-warm-reboot.md) を参照します。

運用上は、対象 ASIC を絞った reboot とシステム全体 reboot を混同しないことが重要です。`-m` のような除外指定を使う場合は、残す ASIC と落とす ASIC の依存関係を確認します。

## Warmboot Manager と SWSS warm restart

Warmboot Manager は、複数 component の shutdown orchestration と reconciliation を統一する設計です。4 phase の shutdown orchestration、component state、race condition の扱いを確認する入口は [Warmboot Manager](../../system/warmboot-manager-hld.md) です。

SWSS docker warm restart は service lifecycle の代表例です。restore、pre/post validation、sync up、失敗時 fallback を順に見ます。仕様は [SWSS docker warm restart](../../system/sonic-swss-docker-warm-restart.md)、開発時の実装メモは [SWSS docker の Warm Restart 実装メモ](../../system/swss-docker-warm-restart-code-reference.md) に分かれています。

### Warm reboot 実行ログの例

```text
admin@sonic:~$ sudo warm-reboot
Starting warm-reboot...
Stopping bgp service...
Pre-shutdown BGP ... [OK]
Saving config to /etc/sonic/config_db.json
Backing up Redis to /host/warmboot/redis_db.json
Stopping syncd service ... [OK]
Stopping swss service ... [OK]
SAI warm shutdown ... [OK]
Rebooting...
```

起動後の reconciliation 完了は次で確認します。

```text
admin@sonic:~$ show warm_restart state
name              restore_count  state
----------------  -------------  ----------
neighsyncd                    1  reconciled
bgp                           1  reconciled
teamsyncd                     1  reconciled
fdbsyncd                      1  reconciled
natsyncd                      1  reconciled
```

`reconciled` 以外（`restored`, `init`, `disabled`）の component が残る場合、その component の syslog を見ます。`reconciled` まで届かないと EOIU (End-of-Initial-Update) が出ず、後続の clean up が走らないため、route や neighbor の幽霊が残ることがあります。

```text
May 10 11:01:08 sw01 INFO swss#bgpcfgd: BGP reached reconciled state
May 10 11:01:09 sw01 INFO swss#orchagent: EOIU received from all components
```

<!-- evidence:
source: sonic-net/sonic-swss/fpmsyncd/fpmsyncd.cpp#L49-L61 (sha: 4305596156d70e9797e8a881b3d19b46de0bce0d)
excerpt: |
  // Wait 3 seconds after detecting EOIU reached state
  const uint32_t DEFAULT_EOIU_HOLD_INTERVAL = 3;
  ...
  bgpStateTable.hget("IPv4|eoiu", "state", value);
reasoning: fpmsyncd は STATE_DB の BGP_STATE_TABLE|<family>|eoiu を hget して reached を待つ。EOIU は警告文どおり後続 clean-up の前提となる同期点である。
-->

<!-- evidence-rendered:start -->
??? note "📋 検証エビデンス: sonic-net/sonic-swss/fpmsyncd/fpmsyncd.cpp#L49-L61 (sha: 4305596156d70e9797e8a881b3d19b46de0bce0d)"

    **出典**:

    `sonic-net/sonic-swss/fpmsyncd/fpmsyncd.cpp#L49-L61 (sha: 4305596156d70e9797e8a881b3d19b46de0bce0d)`

    **抜粋**:

    ```text
    // Wait 3 seconds after detecting EOIU reached state
    const uint32_t DEFAULT_EOIU_HOLD_INTERVAL = 3;
    ...
    bgpStateTable.hget("IPv4|eoiu", "state", value);
    ```

    **判断根拠**: fpmsyncd は STATE_DB の BGP_STATE_TABLE|<family>|eoiu を hget して reached を待つ。EOIU は警告文どおり後続 clean-up の前提となる同期点である。

<!-- evidence-rendered:end -->

<!-- evidence:
source: sonic-net/sonic-swss/doc/swss-schema.md#L1159-L1162 (sha: 4305596156d70e9797e8a881b3d19b46de0bce0d)
excerpt: |
  key             = BGP_STATE_TABLE|family|eoiu             ; family = "IPv4" / "IPv6"  ; address family.
  state           = "unknown" / "reached" / "consumed"         ; unknown: eoiu state not fetched yet.
                                                               ; reached: bgp eoiu done.
reasoning: EOIU 状態は STATE_DB の BGP_STATE_TABLE で公開され、reconciliation 完了判定に使われる。
-->

<!-- evidence-rendered:start -->
??? note "📋 検証エビデンス: sonic-net/sonic-swss/doc/swss-schema.md#L1159-L1162 (sha: 4305596156d70e9797e8a881b3d19b46de0bce0d)"

    **出典**:

    `sonic-net/sonic-swss/doc/swss-schema.md#L1159-L1162 (sha: 4305596156d70e9797e8a881b3d19b46de0bce0d)`

    **抜粋**:

    ```text
    key             = BGP_STATE_TABLE|family|eoiu             ; family = "IPv4" / "IPv6"  ; address family.
    state           = "unknown" / "reached" / "consumed"         ; unknown: eoiu state not fetched yet.
                                                                 ; reached: bgp eoiu done.
    ```

    **判断根拠**: EOIU 状態は STATE_DB の BGP_STATE_TABLE で公開され、reconciliation 完了判定に使われる。

<!-- evidence-rendered:end -->

## reboot 種別の使い分け早見表

| 種別 | data plane | control plane | 想定停止時間 | 主用途 |
|------|------------|---------------|--------------|--------|
| `reboot` (cold) | 完全停止 | 完全停止 | 分単位 | image 更新、kernel 更新 |
| `fast-reboot` | 完全停止 (短時間) | 完全停止 | 30s〜 | image 更新で warm 不可なとき |
| `warm-reboot` | 維持 | 短時間停止 | 数秒 (data plane 影響なし) | minor update / patch |
| `config reload -y` | 維持 | swss 系のみ再起動 | 数秒 | 設定全面適用 |
| `systemctl restart bgp` | 維持 | 該当サービスのみ | サブ秒〜数秒 | サービス単位 |

## 対応コマンド早見表

| 症状 | コマンド | 補足 |
|------|---------|------|
| 突然 reboot した | `show reboot-cause history` | `/host/reboot-cause/` も保全 |
| warm-reboot 後 BGP が落ちた | `show bgp neighbors X graceful-restart` | peer 側 GR 設定 |
| warm-reboot 後 LAG が崩れた | `show interfaces portchannel` + teamd log | LACP retry 拡張 / peer timeout |
| reconciliation が終わらない | `show warm_restart state` | 該当 component の syslog |
| ASIC namespace だけ再起動したい | `warm-reboot -m <namespace>` | multi-ASIC HLD 参照 |
| panic を保全したい | `show kdump status` | 章 [09](../09-telemetry-snmp/operations.md) |
| reconciliation log | `grep -i reconcil /var/log/syslog` | syslog から一括確認 |
| 直近 cause の生ファイル | `cat /host/reboot-cause/reboot-cause.txt` | `/host/reboot-cause/` 配下 |
| 前回 cause（JSON） | `cat /host/reboot-cause/previous-reboot-cause.json` | 前回 cause 詳細 |

## CONFIG_DB / STATE_DB 関連 key

| 項目 | DB | Key |
|------|-----|-----|
| warm-restart enable | `CONFIG_DB` | `WARM_RESTART\|<service>` |
| warm-restart timer | `CONFIG_DB` | `WARM_RESTART\|<service>` (timer field) |
| 各 component の state | `STATE_DB` | `WARM_RESTART_TABLE\|<key>` |
| reboot-cause 履歴 | `STATE_DB` | `REBOOT_CAUSE\|<timestamp>` |
| 直近 cause (file) | n/a | `/host/reboot-cause/reboot-cause.txt` |

## 関連章

- 章 [09 telemetry / SNMP / observability](../09-telemetry-snmp/operations.md) — techsupport / kdump / system-health
- 章 [10 gNMI / OpenConfig](../10-gnmi-openconfig/operations.md) — save-on-set と再起動を跨ぐ永続化
- 章 [02 BGP](../02-bgp/operations.md) — BGP Graceful Restart の運用

## 異常検出パターン

| 観測 | 疑う状態 | 一次切り分け |
|---|---|---|
| `show reboot-cause` が `Unknown` | `/host/reboot-cause/` の更新失敗、または初回 boot | ファイル mtime、`determine-reboot-cause.service` の journal |
| warm-reboot 後 `restore_count` が 0 | warm path に入らず cold boot した | `/var/log/syslog` の warm-reboot 実行ログ、`pre-shutdown` 失敗 |
| reconciliation が `restored` で止まる | EOIU 未受領、または依存 service 未起動 | 該当 component の syslog、`show warm_restart state` の他 component |
| warm-reboot 中に LAG が落ちる | LACP retry 拡張未対応、peer 側 timeout 短 | teamd ログ、peer 側 LACP rate |
| warm-reboot 中に BGP session が落ちる | peer の Graceful Restart が `Disable` | `show bgp neighbor X graceful-restart` の `Remote GR Mode` |
| `Kernel Panic` 直後の boot で kdump が無い | kdump 無効、または `/var/crash/` 空き不足 | `show kdump status`、`/var/crash/` 容量 |
| fast-reboot 後 BGP neighbor が `never` | image 切替で config drift、または `config_db.json` 破損 | `config_db.json` の `BGP_NEIGHBOR`、`bgpcfgd` ログ |

## 典型的な運用シナリオ

1. **計画 warm-reboot（minor update）** — `show warm_restart config` で対象 service が enable で timer が適切か確認 → peer の Graceful Restart 設定確認 → `sudo warm-reboot` → 起動後 `show warm_restart state` が全て `reconciled` を確認。
2. **計画外の Kernel Panic 解析** — `/host/reboot-cause/previous-reboot-cause.json` と `/var/crash/` の vmcore を保全 → `show techsupport` で全 log 収集 → `dmesg` で MCE / OOM / driver oops を確認。
3. **multi-ASIC で一部 ASIC のみ再起動** — 対象 namespace を特定 → `warm-reboot -m <namespace>` または該当 namespace の `swss`/`syncd` を `systemctl restart` → 残り ASIC が影響を受けていないことを `show interfaces counters` の連続性で確認。
4. **fast-reboot で image 切替** — `sonic-installer set-default <image>` → `fast-reboot` → 起動後 `show version` で image を確認 → BGP/LAG/route 件数が事前メモと合っているかを確認。
5. **reboot 履歴の定期点検** — `show reboot-cause history` を週次で確認し、`Watchdog` / `Hardware - reason` が一度でも出ていれば platform team に escalate、`Kernel Panic` が複数回なら同 stack trace を比較。

## 関連ページ

- [Reboot-cause 履歴の STATE_DB / テレメトリ公開](../../system/reboot-cause-information-via-telemetry-agent.md)
- [Warm-reboot 中の LACP retry count 拡張](../../switching/increasing-lacp-pdu-timeout-during-warm-reboot.md)
- [Multi-ASIC warm reboot](../../system/multi-asic-warm-reboot.md)
- [Warmboot Manager](../../system/warmboot-manager-hld.md)
- [SWSS docker warm restart](../../system/sonic-swss-docker-warm-restart.md)
- [SWSS docker の Warm Restart 実装メモ](../../system/swss-docker-warm-restart-code-reference.md)

<!-- glossary-links-injected: c006405759d8 -->
