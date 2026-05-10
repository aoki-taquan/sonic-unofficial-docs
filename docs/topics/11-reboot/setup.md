---
title: Reboot / warm restart の設定
area: topics
verification: meta
last_verified: 2026-05-10
sources:
  - docs/reference/cli/reboot-fast-warm.md
  - docs/reference/cli/config-warm_restart.md
  - docs/system/reboot-support-blockingmode-in-sonic.md
---

# Reboot / warm restart の設定

設定で最初に分けるのは、OS 全体の reboot を実行するのか、service warm restart を許可するのかです。`reboot`、`fast-reboot`、`warm-reboot` は実行コマンドであり、`config warm_restart` は module ごとの warm restart capability と timer を設定します。

## OS reboot の入口

通常 reboot は `reboot`、短時間 reboot は `fast-reboot`、data plane 継続を狙う reboot は `warm-reboot` を使います。`warm-reboot` は実装上 `fast-reboot` script への symlink で、script 名により warm mode に分岐します。オプションや終了コードの詳細は [reboot / fast-reboot / warm-reboot コマンド](../../reference/cli/reboot-fast-warm.md) を参照します。

運用上は次の順に確認します。

1. 次回 boot image が `sonic-installer verify-next-image` で通るか。
2. platform-specific `platform_reboot_pre_check` がある場合に失敗しないか。
3. warm reboot では pre-shutdown ACK、DB backup、peer 側 graceful behavior が揃っているか。
4. multi-ASIC では対象 ASIC の除外や namespace 反映が意図通りか。

## warm restart を有効化する

`config warm_restart enable` は、module 単位または system 単位で warm restart を有効化します。module を省略すると `system` が対象です。module 指定時は CONFIG_DB の `FEATURE` に存在する feature 名が前提になります。

代表的な対象は `swss`、`bgp`、`teamd` です。timer は復元待ちの上限として働くため、単に長くすれば良いものではありません。長すぎる timer は障害検知を遅らせ、短すぎる timer は正常な reconciliation を失敗扱いにします。CLI の具体的な項目は [config warm_restart サブコマンド](../../reference/cli/config-warm_restart.md) を見ます。

## timer 設定の読み方

| timer | 主な対象 | 何を待つか |
|---|---|---|
| `neighsyncd_timer` | `swss` | neighbor restore / sync を待つ |
| `bgp_timer` | `bgp` | BGP graceful restart と EOIU 周辺の完了を待つ |
| `teamsyncd_timer` | `teamd` | LAG/team state の復元を待つ |
| `bgp_eoiu` | `bgp` | EOIU の扱いを切り替える |

multi-ASIC では namespace 指定の有無で反映先が変わります。single-ASIC の感覚で default namespace だけを見ていると、ASIC namespace 側の warm restart state を見落とします。

## blocking mode を使う場面

通常の `reboot` は非 blocking で呼び出し元に戻る設計でしたが、blocking mode では reboot script が systemd 側の停止進行を待ち、進捗や失敗を呼び出し元に返しやすくします。自動運用から reboot を実行し、pre-check や停止処理の失敗をその場で扱いたい場合に有用です。

blocking mode の詳細は [`reboot` コマンドの blocking mode](../../system/reboot-support-blockingmode-in-sonic.md) にあります。`-b` と `reboot.conf` の関係、verbose 出力、タイムアウトの扱いを確認します。

## 関連ページ

- [reboot / fast-reboot / warm-reboot コマンド](../../reference/cli/reboot-fast-warm.md)
- [config warm_restart サブコマンド](../../reference/cli/config-warm_restart.md)
- [`reboot` コマンドの blocking mode](../../system/reboot-support-blockingmode-in-sonic.md)
