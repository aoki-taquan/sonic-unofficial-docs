---
title: Multi-ASIC warm reboot（namespace 横断の協調 shutdown / boot）
description: "Multi-ASIC warm reboot（namespace 横断の協調 shutdown / boot） — multi-ASIC platform では各 ASIC が 独自の swss / syncd / FRR インスタンス を持つ。"
area: system
verification: code-verified
last_verified: 2026-05-10
sources:
  - repo: sonic-net/SONiC
    path: doc/warm-reboot/Multi_ASIC_warm_reboot.md
    ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
    - WARM_RESTART
  cli:
    - warm-reboot
  yang:
    - sonic-warm-restart
---

!!! warning "裏取りステータス: code-verified"
    各 namespace の swss / syncd の協調 shutdown 順序が現行スクリプトでどうなっているかは未確認。

!!! note "Verifier 注記（2026-05-10）"
    実コード裏取り: `sonic-utilities/scripts/warm-reboot` に namespace 横断の `execute_in_namespaces` ロジック（scope=all で global namespace と各 ASIC namespace に対して並列実行）を確認。multi-asic warm reboot の協調制御は本 script 経由で実装されている。

# Multi-ASIC warm reboot（namespace 横断の協調 shutdown / boot）

## 概要

multi-ASIC platform では各 ASIC が **独自の swss / syncd / FRR インスタンス** を持つ。warm reboot を成立させるには、**namespace を跨いだ協調 shutdown / boot** が必要[^1]。

ポイント:

- すべての namespace で **同時に** GR を有効化、`WARM_RESTART_TABLE` を更新する
- syncd warm shutdown は **per-namespace** に走り、`/host/warmboot/sai-warmboot.bin` 系のファイルも namespace ごとに分離する
- BGP は host namespace の `bgpcfgd` / FRR と各 asic namespace の FRR の両方で GR
- internal BGP（`BGP_INTERNAL_NEIGHBOR`）の hold time にも warm reboot を完走させるマージンを持たせる

## 動作仕様（going down 順序）

```mermaid
flowchart LR
    BGP[host BGP + asicN BGP\nGR enable] --> TEAM[teamd 全 namespace 停止]
    TEAM --> SWSS[swss@asicN 全停止\nMAC learn off / orchagent freeze]
    SWSS --> DUMP[per-namespace Redis dump]
    DUMP --> SYNCD[syncd@asicN 全 warm shutdown\nsai-warmboot.bin per-namespace]
    SYNCD --> DB[per-namespace database 停止]
    DB --> KEXEC[kexec\nSONIC_BOOT_TYPE=warm]
```

going up は逆順を namespace ごとに走らせ、orchagent compare 完了後に bgp / teamd を起動する。

## 制約と注意点[^1]

- **per-namespace の同期**: ある namespace だけ早く落ちると ASIC 間 internal BGP がフラップする
- **CPU / disk の負荷スパイク**: namespace 数 × Redis dump / syncd shutdown が同時に走るためリソースに余裕が必要
- **internal link**: shutdown 中も internal link は up のままにする（forwarding は SAI state に従う）
- **ファイル配置**: `/host/warmboot/<ns>/dump.rdb` のように namespace 識別子で分離する設計

## 関連 CLI

| Command | 用途 |
|---------|------|
| `sudo warm-reboot` | 多くは host から実行（実装が namespace を順に処理） |
| `show warm_restart` | 各 namespace の warm restart state |

## 干渉する機能

- **system-wide warmboot**: シングル ASIC 設計の上位互換。共通点が多い
- **fast-reboot**: 同じスクリプト基盤を共有
- **multi-asic single-json**: warm restart 設定を per-asic に flatten する場合の互換性
- **internal BGP**: hold timer / GR timer の整合
- **chassis VoQ**: 章レベルで別カテゴリ（chassis-wide warm reboot）。考え方は近い

## トラブルシューティング

- 全 namespace が同時に落ちず data plane が断 → script の同期 barrier 確認、`/host/warmboot/<ns>/` のファイル時刻
- internal BGP がフラップ → hold timer、GR negotiation の成功確認
- 一部 ASIC だけ syncd 復元失敗 → per-namespace `sai-warmboot.bin` の有無と vendor SAI ログ

## 引用元

[^1]: `sonic-net/SONiC` `doc/warm-reboot/Multi_ASIC_warm_reboot.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- concerns hint:
- warm-reboot スクリプトの multi-asic 対応経路の現行実装確認
- per-namespace /host/warmboot/<ns>/ ファイル配置の現行値確認
- swss@asicN / syncd@asicN の warm shutdown 順序制御の現行 systemd / docker_image_ctl 実装確認
- BGP_INTERNAL_NEIGHBOR の hold timer / GR timer の現行既定値確認
- multi-asic single-json と warm restart 設定の互換性確認
- HLD と現行 multi-asic warm reboot CI テストカバレッジの差異確認
-->
