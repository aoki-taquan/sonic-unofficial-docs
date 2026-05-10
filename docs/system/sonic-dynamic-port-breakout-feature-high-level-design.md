---
title: 動的ポートブレイクアウト（dynamic port breakout・lanes / interface再構成）
area: system
verification: code-verified
last_verified: 2026-05-10
sources:
  - repo: sonic-net/SONiC
    path: doc/dynamic-port-breakout/sonic-dynamic-port-breakout-HLD.md
    ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
    - PORT
    - BREAKOUT_CFG
  cli:
    - config interface breakout
    - show interfaces breakout
  yang:
    - sonic-port
---

!!! warning "裏取りステータス: code-verified"
    PortConfigDoneOrch / PortBreakoutOrch（仮称）の現行 master 取り込み、依存 CONFIG_DB の cleanup ロジックは未確認。

!!! note "Verifier 注記（2026-05-10）"
    実コード裏取り: `sonic-utilities/config/main.py` の `breakout_cfg_file` / `_validate_interface_mode` 経路で動的 breakout 実装を確認。yang は `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-breakout_cfg.yang` に CONFIG_DB BREAKOUT_CFG スキーマを確認。

# 動的ポートブレイクアウト（dynamic port breakout・lanes / interface再構成）

## 概要

1 つの物理 cage（QSFP-DD 等）を **複数の論理 port に切り分けたり 1 つに戻したりする** 操作を、**reload 不要・実行中の SONiC で** 行えるようにする機能[^1]。

例: 100Gx1（`Ethernet0`）→ 25Gx4（`Ethernet0/1/2/3`）

主目的:

- breakout 変更を `config interface breakout` 1 コマンドで完結
- 関連設定（PORT_CHANNEL、VLAN_MEMBER、ACL、IP、neighbor 等）を **依存解決** して整合的に削除/再生
- platform 側の物理制約（lane count / supported modes）を `platform.json` で照合

## 動作仕様

```mermaid
flowchart LR
    USER[管理者] --> CLI[config interface breakout Ethernet0 4x25G]
    CLI --> VAL[platform.json と\nbreakout-cfg.json で\n組合せ妥当性検証]
    VAL --> DEPS[依存設定の検出\n(VLAN_MEMBER / PORT_CHANNEL_MEMBER / ACL / IP)]
    DEPS --> REMOVE[CONFIG_DB から該当 port の依存を削除]
    REMOVE --> PORTREM[PORT エントリを削除]
    PORTREM --> APPLY[新 PORT エントリ追加\n(lanes / speed / index 再計算)]
    APPLY --> ORCH[PortsOrch / SyncD]
    ORCH --> SAI[(SAI port create/remove)]
```

主要要素[^1]:

- **`platform.json`**: 各 cage の supported breakout modes（例: `1x100G`, `2x50G`, `4x25G`, `4x10G`）
- **`hwsku.json`**: 既定 breakout
- **`BREAKOUT_CFG` テーブル**: 現状の breakout 構成
- **依存解決**: 削除対象 port を参照する設定を CLI 側 / `db_migrator` が事前に削除

### 「force」オプション

依存設定が残っている時に `--force` で強制的に依存削除と breakout 変更を一気に行う。整合性確認後の運用変更で利用。

## 関連 CONFIG_DB

| Table | 説明 |
|-------|------|
| `PORT` | `lanes` / `speed` / `index` / `alias` |
| `BREAKOUT_CFG` | 現行 breakout モード |

## 関連 CLI

| Command | 用途 |
|---------|------|
| `show interfaces breakout` | 利用可能 mode と現在設定 |
| `config interface breakout <port> <mode>` | breakout 変更 |
| `config interface breakout <port> <mode> -f` | force |

## 制限事項

- **対応 platform のみ**: `platform.json` に modes が記載されていなければ操作不可
- **依存設定の自動再生は無し**: 削除はするが再構築はユーザ責任
- **link 一時断**: 該当 port は SAI port create/remove のため link が切れる
- **fabric port** など特殊 port には適用しない

## 干渉する機能

- **port-profile-init / fast-link-up**: port 起動シーケンスとの整合
- **media-based-port-settings**: SI 設定との連携
- **multi-asic / single-json**: per-asic で breakout を扱う場合の整合
- **CMIS / ZR**: ZR は固定 application-select で breakout 自由度が下がる

## トラブルシューティング

- 変更が拒否される → `platform.json` の supported modes、依存設定の有無
- 一部 port だけ up しない → 物理 lane mapping、SI 設定、ASIC 側 lane 割当
- 関連設定が消えた → 依存解決で削除されている。再投入が必要

## 引用元

[^1]: `sonic-net/SONiC` `doc/dynamic-port-breakout/sonic-dynamic-port-breakout-HLD.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- concerns hint:
- config interface breakout / show interfaces breakout の sonic-utilities への取り込みと依存解決ロジック確認
- platform.json supported breakout modes の現行 platform 別記述確認
- BREAKOUT_CFG スキーマと sonic-yang-models 取り込み確認
- PortsOrch の dynamic port create / remove 経路の現行実装確認
- VLAN_MEMBER / PORT_CHANNEL_MEMBER / ACL_RULE / INTERFACE 等の依存削除自動化の現行範囲確認
- multi-asic / CMIS application-select との整合の現行実装確認
-->
