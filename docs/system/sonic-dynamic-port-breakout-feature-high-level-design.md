---
title: 動的ポートブレイクアウト（dynamic port breakout・lanes / interface再構成）
description: "動的ポートブレイクアウト（dynamic port breakout・lanes / interface再構成） — 1 つの物理 cage（QSFP-DD 等）を 複数の論理 port に切り分ける / 1 つに戻す 操作を、reload 不要・稼働中の SONiC で 行えるようにする。"
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

<!-- topics-tip -->
!!! tip "Topics で読み物として読む"
    この HLD は実装詳細を含みます。機能の概念・設定・運用を読み物として読みたい場合は [Topics 14 章: Platform / Port / Optics](../topics/14-platform-port-optics/index.md) を参照。
<!-- /topics-tip -->

!!! success "裏取りステータス: code-verified"
    `sonic-utilities/config/main.py` の `breakout_cfg_file` / `_validate_interface_mode`、`sonic-buildimage/.../sonic-breakout_cfg.yang` の `BREAKOUT_CFG` スキーマで動的 breakout 実装を確認（Verifier 2026-05-10）。

# 動的ポートブレイクアウト（dynamic port breakout・lanes / interface再構成）

## 読み手が知りたいこと

1. **breakout を変えると [CONFIG_DB](../reference/glossary.md#term-config_db) / [SAI](../reference/glossary.md#term-sai) で何が起きるか**
2. **どの CLI で変更し、関連設定（[VLAN](../reference/glossary.md#term-vlan) / [LAG](../reference/glossary.md#term-lag) / [ACL](../reference/glossary.md#term-acl) / IP）はどうなるか**
3. **`platform.json` で何を制約しているか**
4. **拒否される / 一部 port が up しないときに何を見るか**
5. **`--force` は何に使うか**

## 1. 何をする機能か

1 つの物理 cage（QSFP-DD 等）を **複数の論理 port に切り分ける / 1 つに戻す** 操作を、**reload 不要・稼働中の [SONiC](../reference/glossary.md#term-sonic) で** 行えるようにする[^1]。

例: `100Gx1`（`Ethernet0`）→ `25Gx4`（`Ethernet0/1/2/3`）

達成目標:

- breakout 変更を `config interface breakout` 1 コマンドで完結
- 関連設定（PORT_CHANNEL / VLAN_MEMBER / ACL / IP / neighbor）を **依存解決** して整合的に削除
- platform 物理制約（lane / supported modes）を `platform.json` で照合

## 2. 変更フロー

```mermaid
flowchart LR
    USER[管理者] --> CLI[config interface breakout Ethernet0 4x25G]
    CLI --> VAL[platform.json と\nbreakout-cfg.json で\n組合せ妥当性検証]
    VAL --> DEPS[依存検出\nVLAN_MEMBER / PORT_CHANNEL_MEMBER\n/ ACL / IP]
    DEPS --> REMOVE[CONFIG_DB から依存削除]
    REMOVE --> PORTREM[PORT エントリ削除]
    PORTREM --> APPLY[新 PORT 追加\nlanes / speed / index 再計算]
    APPLY --> ORCH[PortsOrch / SyncD]
    ORCH --> SAI[(SAI port create/remove)]
```

主要要素[^1]:

- **`platform.json`**: 各 cage の supported breakout modes（`1x100G`/`2x50G`/`4x25G`/`4x10G` 等）
- **`hwsku.json`**: 既定 breakout
- **`BREAKOUT_CFG` テーブル**: 現状の breakout 構成
- **依存解決**: 削除対象 port を参照する設定は CLI 側 / `db_migrator` が事前削除

### `--force`

依存設定が残っている時に `--force` で依存削除と breakout 変更を一気に行う。整合性確認後の運用変更で利用。

## 3. CONFIG_DB / CLI

| Table | 説明 |
|-------|------|
| `PORT` | `lanes` / `speed` / `index` / `alias` |
| `BREAKOUT_CFG` | 現行 breakout モード |

| Command | 用途 |
|---------|------|
| `show interfaces breakout` | 利用可能 mode と現在設定 |
| `config interface breakout <port> <mode>` | breakout 変更 |
| `config interface breakout <port> <mode> -f` | force |

## 4. 制限事項と干渉する機能

- **対応 platform のみ**: `platform.json` に modes 記載が必要
- **依存設定の自動再生は無し**: 削除はするが再構築はユーザ責任
- **link 一時断**: SAI port create/remove のため link が切れる
- **fabric port** など特殊 port には適用しない
- **port-profile-init / fast-link-up**: port 起動シーケンスと整合が要る
- **media-based-port-settings**: SI 設定と連携
- **multi-asic / single-json**: per-asic で breakout を扱う場合の整合
- **CMIS / ZR**: ZR は固定 application-select で breakout 自由度低

## 5. トラブルシューティング

- **変更が拒否される** → `platform.json` の supported modes、依存設定の有無
- **一部 port だけ up しない** → 物理 lane mapping、SI 設定、[ASIC](../reference/glossary.md#term-asic) 側 lane 割当
- **関連設定が消えた** → 依存解決で削除済み。再投入が必要


### コマンド例

dynamic port breakout の状態を確認する。

```bash
show interfaces breakout current-mode
config interface breakout Ethernet0 '4x25G'
redis-cli -n 4 hgetall 'BREAKOUT_CFG|Ethernet0'
show platform summary
```

## 関連 Topics 章

- [14-platform-port-optics](../topics/14-platform-port-optics/index.md): port profile / lane / media SI / CMIS との結線
- [06-l2-vlan-lag](../topics/06-l2-vlan-lag/index.md): VLAN_MEMBER / PORT_CHANNEL_MEMBER の依存解決対象

## 制限事項

- breakout 可能なポート組合せは platform.json の `interfaces` キーに定義された範囲に限られ、[HLD](../reference/glossary.md#term-hld) 記述よりも実機サポート範囲が狭い場合がある。
- breakout 実行時は対象ポートが一時的に down し、隣接機器の [LLDP](../reference/glossary.md#term-lldp) / LAG メンバーシップが flap する点を運用で考慮する。
- 動的 breakout 中に CONFIG_DB が中間状態となるため、並行して `config save` を実行すると不整合な config が保存される。

## 引用元

[^1]: `sonic-net/SONiC` `doc/dynamic-port-breakout/sonic-dynamic-port-breakout-HLD.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: Platform / Port / Optics / PHY](../topics/14-platform-port-optics/index.md)

<!-- /topics-back-ref -->

<!-- glossary-links-injected: ec18b66e3507 -->
