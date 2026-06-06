---
title: Reboot / warm restart の設定
description: OS reboot と service warm restart の使い分け、warm restart の有効化・timer 設定・blocking
  mode の運用手順を、sonic-utilities の CLI 実装と sonic-swss の daemon default に基づいて整理する。
area: topics
verification: code-verified
last_verified: 2026-06-06
sources:
- repo: sonic-net/sonic-utilities
  path: config/main.py
  ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
- repo: sonic-net/sonic-utilities
  path: show/warm_restart.py
  ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
- repo: sonic-net/sonic-swss
  path: neighsyncd/neighsync.h
  ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
- repo: sonic-net/sonic-swss
  path: fpmsyncd/fpmsyncd.cpp
  ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
related:
  cli:
  - show warm_restart
  - config warm_restart
  - reboot
  - fast-reboot
  - warm-reboot
  config_db:
  - FEATURE
  - WARM_RESTART
  yang:
  - sonic-warm-restart
---

# Reboot / warm restart の設定

設定で最初に分けるのは、OS 全体の reboot を実行するのか、service warm restart を許可するのかです。`reboot`、`fast-reboot`、`warm-reboot` は実行コマンドであり、`config warm_restart` は module ごとの warm restart capability と timer を設定します。

## シナリオ 1: warm reboot を初めて使えるようにする

「box の OS upgrade を data plane 無停止でやりたい」のが大抵の目的。box ごとに有効化する手順は次のとおり。

```bash
# 1. system レベルで warm restart を有効化
config warm_restart enable

# 2. 主要 module を warm 対応にする
config warm_restart enable swss
config warm_restart enable bgp
config warm_restart enable teamd

# 3. timer を実環境に合わせて延ばす (chassis や大規模 FIB ほど長く)
#    daemon 側の組み込みデフォルトは neighsyncd=5s, fpmsyncd=120s で、
#    teamsyncd は明示デフォルトを持たない[^timer-defaults]。明示的に設定するのが安全。
config warm_restart neighsyncd_timer 120   # 1..9999
config warm_restart bgp_timer        180   # 1..3600
config warm_restart teamsyncd_timer  60    # 1..3600
config warm_restart bgp_eoiu enable

# 4. 設定保存 (warm boot script は永続設定を期待する)
config save -y
```

[CONFIG_DB](../../reference/glossary.md#term-config_db):

```json
{
  "WARM_RESTART": {
    "system": {"enable":"true"},
    "swss":   {"enable":"true","neighsyncd_timer":"120"},
    "bgp":    {"enable":"true","bgp_timer":"180","bgp_eoiu":"true"},
    "teamd":  {"enable":"true","teamsyncd_timer":"60"}
  }
}
```

確認:

```bash
$ show warm_restart config
name              enable    timer_name           timer_duration    eoiu_enable
----------------  --------  -------------------  ----------------  -------------
system            true
swss              true      neighsyncd_timer     120
bgp               true      bgp_timer            180               true
teamd             true      teamsyncd_timer      60

$ show warm_restart state
name              restore_count  state
----------------  -------------  --------
orchagent         0              reconciled
neighsyncd        0              reconciled
bgp               0              reconciled
teamsyncd         0              reconciled
```

`state` が `reconciled` で揃っていれば次回 `warm-reboot` は data plane 無停止で抜けられる目安になります。

## シナリオ 2: 実際に warm-reboot を実行する

事前 check、実行、復帰確認まで。

```bash
# 事前: 次の image を確認
sudo sonic-installer list
sudo sonic-installer verify-next-image

# 事前: 隣接の BGP graceful restart capability を確認
vtysh -c 'show ip bgp neighbors 10.0.0.1' | grep -A2 'Graceful Restart'

# 事前: 全 FRR daemon が helper として動く準備
docker exec bgp vtysh -c 'show bgp memory' | tail -5

# 実行 (warm-reboot)
sudo warm-reboot
```

復帰直後の確認:

```bash
$ show reboot-cause
Cause: warm-reboot
Time:  Mon May 11 03:25:11 UTC 2026
User:  admin

$ show warm_restart state
name              restore_count  state
orchagent         1              reconciled
bgp               1              reconciled
teamsyncd         1              reconciled

$ show ip bgp summary | grep -c Established
12   # 期待値
```

`restore_count` がインクリメントされていて、全 module が `reconciled` に到達していれば warm-reboot は成功。`state` が `restored` のまま止まる module があれば、timer 超過で reconciliation が間に合っていません。

## シナリオ 3: blocking mode で自動化する

自動運用 (CI、orchestrator) から呼ぶときは blocking mode で進捗・失敗を呼び出し元に返す方が扱いやすい。

```bash
# 非対話、進捗を stdout に出しつつ完了まで戻ってこない
sudo reboot -b -v

# /etc/sonic/reboot.conf で default 動作を指定可能
cat /etc/sonic/reboot.conf
# blocking=yes
# verbose=yes
# timeout=600
```

`-b` を付けると reboot script が systemd 側の停止進行を待ち、終了コードで失敗を表現します。詳細は [`reboot` コマンドの blocking mode](../../system/reboot-support-blockingmode-in-sonic.md) を参照。

## OS reboot の入口

通常 reboot は `reboot`、短時間 reboot は `fast-reboot`、data plane 継続を狙う reboot は `warm-reboot` を使います。`warm-reboot` は実装上 `fast-reboot` script への symlink で、script 名により warm mode に分岐します。オプションや終了コードの詳細は [reboot / fast-reboot / warm-reboot コマンド](../../reference/cli/reboot-fast-warm.md) を参照します。

運用上は次の順に確認します。

1. 次回 boot image が `sonic-installer verify-next-image` で通るか。
2. platform-specific `platform_reboot_pre_check` がある場合に失敗しないか。
3. warm reboot では pre-shutdown ACK、DB backup、peer 側 graceful behavior が揃っているか。
4. multi-[ASIC](../../reference/glossary.md#term-asic) では対象 ASIC の除外や namespace 反映が意図通りか。

## warm restart を有効化する

`config warm_restart enable` は、module 単位または system 単位で warm restart を有効化します。module を省略すると `system` が対象です。module 指定時は CONFIG_DB の `FEATURE` に存在する feature 名が前提になります。

代表的な対象は `swss`、`bgp`、`teamd` です。timer は復元待ちの上限として働くため、単に長くすれば良いものではありません。長すぎる timer は障害検知を遅らせ、短すぎる timer は正常な reconciliation を失敗扱いにします。CLI の具体的な項目は [config warm_restart サブコマンド](../../reference/cli/config-warm_restart.md) を見ます。

## timer 設定の読み方

| timer | 主な対象 | 何を待つか |
|---|---|---|
| `neighsyncd_timer` | `swss` | neighbor restore / sync を待つ |
| `bgp_timer` | `bgp` | [BGP](../../reference/glossary.md#term-bgp) graceful restart と EOIU 周辺の完了を待つ |
| `teamsyncd_timer` | `teamd` | [LAG](../../reference/glossary.md#term-lag)/team state の復元を待つ |
| `bgp_eoiu` | `bgp` | EOIU の扱いを切り替える |

multi-ASIC では namespace 指定の有無で反映先が変わります。single-ASIC の感覚で default namespace だけを見ていると、ASIC namespace 側の warm restart state を見落とします。

## blocking mode を使う場面

通常の `reboot` は非 blocking で呼び出し元に戻る設計でしたが、blocking mode では reboot script が systemd 側の停止進行を待ち、進捗や失敗を呼び出し元に返しやすくします。自動運用から reboot を実行し、pre-check や停止処理の失敗をその場で扱いたい場合に有用です。

blocking mode の詳細は [`reboot` コマンドの blocking mode](../../system/reboot-support-blockingmode-in-sonic.md) にあります。`-b` と `reboot.conf` の関係、verbose 出力、タイムアウトの扱いを確認します。

## よくある設定エラーと対処

| 症状 | 典型的な原因 | 対処 |
|---|---|---|
| `warm-reboot: command not found` | warm-reboot symlink が存在しない (古い image) | `which fast-reboot` で実体を確認、`sudo ln -s fast-reboot /usr/local/bin/warm-reboot` |
| warm-reboot 後 `state` が `restored` のまま reconcile しない | timer が短すぎて FIB 復元が間に合わない | `bgp_timer` / `neighsyncd_timer` を 2 倍に延ばして再試行 |
| warm-reboot 中に BGP session が flap する | peer 側 GR helper が無効 / 未交渉 | peer 側で `bgp graceful-restart` を有効化、`show ip bgp neighbors` で Restart Time が見えるか確認 |
| `sonic-installer verify-next-image` 失敗 | image hash / signature mismatch、disk 不足 | image を再ダウンロード、`/host` の空きを確認 |
| fast-reboot は通るが warm-reboot だけ失敗 | swss / [teamd](../../reference/glossary.md#term-teamd-teamsyncd-teammgrd) の warm capability が未 enable | `config warm_restart enable swss teamd` を確認 |
| multi-ASIC で 一部 ASIC namespace だけ reconcile しない | namespace 別の WARM_RESTART 設定漏れ | `sudo config warm_restart enable -n asic0 swss` 等で個別に設定 |
| `reboot.conf` を書いたのに blocking にならない | `-b` 未指定、`reboot.conf` の文法誤り | `reboot.conf` を最小形式に戻して再試行、または明示的に `reboot -b` |
| warm-reboot 後 [LACP](../../reference/glossary.md#term-lacp) partner が timeout で外す | `teamsyncd_timer` が短い、peer の lacp_short_timeout 設定 | `teamsyncd_timer` を 90s 以上、peer 側を long timeout に |

## 関連リファレンス

- [reboot / fast-reboot / warm-reboot コマンド](../../reference/cli/reboot-fast-warm.md)
- [config warm_restart サブコマンド](../../reference/cli/config-warm_restart.md)
- [`reboot` コマンドの blocking mode](../../system/reboot-support-blockingmode-in-sonic.md)
- CONFIG_DB: `WARM_RESTART` table
- 同章の [concept](concept.md) / [architecture](architecture.md) / [operations](operations.md) / [upgrade](upgrade.md)

## 引用元

[^timer-defaults]: `neighsyncd` の warm restart 待機時間のコンパイル時 default は `DEFAULT_NEIGHSYNC_WARMSTART_TIMER = 5` 秒で、CONFIG_DB の `WARM_RESTART|swss/neighsyncd_timer` で上書きされる（[sonic-net/sonic-swss `neighsyncd/neighsync.h` L10](https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/neighsyncd/neighsync.h#L10) と [`neighsyncd/neighsync.cpp` L30](https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/neighsyncd/neighsync.cpp#L30)）。`fpmsyncd` 側は `DEFAULT_ROUTING_RESTART_INTERVAL = 120` 秒で（[`fpmsyncd/fpmsyncd.cpp` L46, L160-164](https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/fpmsyncd/fpmsyncd.cpp#L46)）、これが `WARM_RESTART|bgp/bgp_timer` 未設定時の待機時間となる。`teamsyncd` には明示的なコンパイル時 default 値が無く、`config warm_restart teamsyncd_timer` 未設定時は CONFIG_DB に値が無い状態で `AppRestartAssist` が呼ばれる。timer の許容 range は [YANG](../../reference/glossary.md#term-yang) (`sonic-warm-restart`) と `config/main.py` の双方で `neighsyncd_timer: 1..9999` / `bgp_timer: 1..3600` / `teamsyncd_timer: 1..3600` に強制される（[sonic-net/sonic-utilities `config/main.py` L4015-L4078](https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/config/main.py#L4015-L4078)）。

<!-- evidence:
source: sonic-net/sonic-utilities/show/warm_restart.py#L176-L177 (sha: 39732bceb8bdefe706518ab40623bbbba6ff33b9)
excerpt: |
  header = ['name', 'enable', 'timer_name', 'timer_duration', 'eoiu_enable']
  click.echo(tabulate(tablelize(keys, data, enable_table_keys, prefix), header))
reasoning: 本ページの `show warm_restart config` 出力例は 5 列 (name / enable / timer_name / timer_duration / eoiu_enable) を反映している。
-->

<!-- evidence-rendered:start -->
??? note "📋 検証エビデンス: sonic-net/sonic-utilities/show/warm_restart.py#L176-L177 (sha: 39732bceb8bdefe706518ab40623bbbba6ff33b9)"

    **出典**:

    `sonic-net/sonic-utilities/show/warm_restart.py#L176-L177 (sha: 39732bceb8bdefe706518ab40623bbbba6ff33b9)`

    **抜粋**:

    ```text
    header = ['name', 'enable', 'timer_name', 'timer_duration', 'eoiu_enable']
    click.echo(tabulate(tablelize(keys, data, enable_table_keys, prefix), header))
    ```

    **判断根拠**: 本ページの `show warm_restart config` 出力例は 5 列 (name / enable / timer_name / timer_duration / eoiu_enable) を反映している。

<!-- evidence-rendered:end -->

<!-- evidence:
source: sonic-net/sonic-utilities/config/main.py#L3938-L4096 (sha: 39732bceb8bdefe706518ab40623bbbba6ff33b9)
excerpt: |
  @config.group(cls=clicommon.AbbreviationGroup, name='warm_restart')
  ... warm_restart_enable / disable / neighsyncd_timer / bgp_timer / teamsyncd_timer / bgp_eoiu
reasoning: 本ページで列挙する `config warm_restart enable|disable|neighsyncd_timer|bgp_timer|teamsyncd_timer|bgp_eoiu` の各サブコマンドは sonic-utilities の click group `warm_restart` 配下に実在し、CONFIG_DB `WARM_RESTART` table に書き込む。
-->

<!-- evidence-rendered:start -->
??? note "📋 検証エビデンス: sonic-net/sonic-utilities/config/main.py#L3938-L4096 (sha: 39732bceb8bdefe706518ab40623bbbba6ff33b9)"

    **出典**:

    `sonic-net/sonic-utilities/config/main.py#L3938-L4096 (sha: 39732bceb8bdefe706518ab40623bbbba6ff33b9)`

    **抜粋**:

    ```text
    @config.group(cls=clicommon.AbbreviationGroup, name='warm_restart')
    ... warm_restart_enable / disable / neighsyncd_timer / bgp_timer / teamsyncd_timer / bgp_eoiu
    ```

    **判断根拠**: 本ページで列挙する `config warm_restart enable|disable|neighsyncd_timer|bgp_timer|teamsyncd_timer|bgp_eoiu` の各サブコマンドは sonic-utilities の click group `warm_restart` 配下に実在し、CONFIG_DB `WARM_RESTART` table に書き込む。

<!-- evidence-rendered:end -->

<!-- glossary-links-injected: d5320e852f7a -->
