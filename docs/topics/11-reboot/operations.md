---
title: Reboot 運用と障害調査
area: topics
verification: meta
last_verified: 2026-05-10
sources:
  - docs/system/reboot-cause-information-via-telemetry-agent.md
  - docs/switching/increasing-lacp-pdu-timeout-during-warm-reboot.md
  - docs/system/multi-asic-warm-reboot.md
  - docs/system/warmboot-manager-hld.md
  - docs/system/sonic-swss-docker-warm-restart.md
  - docs/system/swss-docker-warm-restart-code-reference.md
---

# Reboot 運用と障害調査

reboot 運用で重要なのは、実行前に peer と platform の前提を揃えること、実行中に warm shutdown / restore の境界を見失わないこと、実行後に原因と復元結果を確認することです。特に warm reboot は「コマンドが成功したか」だけでは不十分で、FDB/neighbor/route/LAG/BGP が期待通り戻ったかを見る必要があります。

## 失敗時の確認順

1. reboot 種別と入口を確認する。`reboot`、`fast-reboot`、`warm-reboot`、service restart のどれかで見る DB と log が変わります。
2. pre-check と終了コードを確認する。次回 image 検証、platform pre-check、FW auto-update conflict は reboot 前に失敗します。
3. warm path では pre-shutdown ACK、DB backup、syncd shutdown、SAI warm shutdown のどこで止まったかを分けます。
4. 起動後は reconciliation の完了、EOIU、neighbor/route restore、teamd/LACP restore を確認します。
5. 最後に reboot-cause 履歴を見て、想定 reboot か crash/panic/watchdog かを切り分けます。

[Reboot-cause 履歴の STATE_DB / テレメトリ公開](../../system/reboot-cause-information-via-telemetry-agent.md) は、起動時に cause を判定し、STATE_DB と telemetry へ公開する流れを説明しています。

## LACP と peer 側の時間

warm reboot では自装置だけでなく peer 側の待ち時間が結果を左右します。LAG peer が短い timeout で partner を落とすと、data plane を維持しても bundle が崩れます。[Warm-reboot 中の LACP retry count 拡張](../../switching/increasing-lacp-pdu-timeout-during-warm-reboot.md) は、LACP PDU の拡張により warm reboot 中の retry count を増やす設計です。

BGP も同様に Graceful Restart と timer が前提です。warm reboot を有効化しても、peer が GR を許容しなければ L3 adjacency は維持されません。

## multi-ASIC warm reboot

multi-ASIC では、namespace ごとに service、DB、ASIC が分かれます。warm reboot は default namespace だけで完結せず、ASIC namespace 群の shutdown / boot 順序、除外指定、DB backup、peer 影響を合わせて扱います。詳細は [Multi-ASIC warm reboot](../../system/multi-asic-warm-reboot.md) を参照します。

運用上は、対象 ASIC を絞った reboot とシステム全体 reboot を混同しないことが重要です。`-m` のような除外指定を使う場合は、残す ASIC と落とす ASIC の依存関係を確認します。

## Warmboot Manager と SWSS warm restart

Warmboot Manager は、複数 component の shutdown orchestration と reconciliation を統一する設計です。4 phase の shutdown orchestration、component state、race condition の扱いを確認する入口は [Warmboot Manager](../../system/warmboot-manager-hld.md) です。

SWSS docker warm restart は service lifecycle の代表例です。restore、pre/post validation、sync up、失敗時 fallback を順に見ます。仕様は [SWSS docker warm restart](../../system/sonic-swss-docker-warm-restart.md)、開発時の実装メモは [SWSS docker の Warm Restart 実装メモ](../../system/swss-docker-warm-restart-code-reference.md) に分かれています。

## 関連ページ

- [Reboot-cause 履歴の STATE_DB / テレメトリ公開](../../system/reboot-cause-information-via-telemetry-agent.md)
- [Warm-reboot 中の LACP retry count 拡張](../../switching/increasing-lacp-pdu-timeout-during-warm-reboot.md)
- [Multi-ASIC warm reboot](../../system/multi-asic-warm-reboot.md)
- [Warmboot Manager](../../system/warmboot-manager-hld.md)
- [SWSS docker warm restart](../../system/sonic-swss-docker-warm-restart.md)
- [SWSS docker の Warm Restart 実装メモ](../../system/swss-docker-warm-restart-code-reference.md)
