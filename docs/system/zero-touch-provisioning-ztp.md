---
title: Zero Touch Provisioning（ZTP・DHCP option / plugin / state machine）
area: system
verification: code-verified
last_verified: 2026-05-10
sources:
  - repo: sonic-net/SONiC
    path: doc/ztp/ztp.md
    ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
    - ZTP
  cli:
    - ztp
    - show ztp
  yang:
    - sonic-ztp
---

!!! warning "裏取りステータス: code-verified / 大規模 HLD"
    HLD は 119KB。本ページは ZTP の architecturally distinctive な要素（DHCP option ベースのトリガ、plugin section モデル、state machine）に絞る。各 plugin 仕様の網羅は HLD 本文を参照。

!!! note "Verifier 注記（2026-05-10）"
    実コード裏取り: `sonic-buildimage/src/sonic-ztp` に ZTP daemon 実装が存在することを確認。`SONiC/doc/ztp` に上流 HLD があり、本ページの DHCP option / plugin / state machine 記述は実装と整合する。

# Zero Touch Provisioning（ZTP・DHCP option / plugin / state machine）

## 概要

ZTP は **箱出し直後の SONiC を、DHCP オプションで指示された ZTP JSON を取得・順次適用して自動構成する** 仕組み[^1]。狙いは:

- 工場出荷後の手動初期構成を不要にする
- 機種・ロケーションごとの構成を ZTP server 側で集中管理
- 失敗時に再試行・状態確認が可能な state machine を提供

## トリガと取得経路

```mermaid
flowchart LR
    BOOT[初回 boot\nconfig_db.json なし] --> DHCP[DHCP discover\nmgmt interface]
    DHCP --> SRV[(DHCP server)]
    SRV -->|option 67 / 239 / 225 等| ZTPCFG[ZTP JSON URL]
    ZTPCFG --> FETCH[ztp daemon\nfetch via HTTP/HTTPS/TFTP]
    FETCH --> EXEC[plugin runner\nsection 単位で順次実行]
    EXEC --> STATE[/var/lib/ztp/ztp_state\n state machine]
    STATE --> APPLY[config / firmware / image / scripts 適用]
```

主要点[^1]:

- **トリガ**: `/etc/sonic/config_db.json` が存在しない（or ztp 強制）状態で boot
- **DHCP option**: ZTP JSON URL を伝える option 番号は platform / 環境設定に従う（option 67 / 225 / 239 等）
- **transport**: HTTP / HTTPS / TFTP / FTP / file
- **plugin model**: ZTP JSON は **section の集合**。各 section は plugin 種別と引数を持ち、順番に走る

## plugin section の例

| section type | 役割 |
|--------------|------|
| `configdb-json` | `/etc/sonic/config_db.json` の取得 / 適用 |
| `connectivity-check` | ネットワーク到達性確認 |
| `firmware` | platform component firmware 更新 |
| `download` | 任意ファイル DL |
| `graphservice` (minigraph) | 旧来の minigraph 取得 |
| `provisioning-script` | 任意スクリプトの実行 |
| `plugin` | ベンダー / 拡張 plugin |

各 section は **`reboot-on-success` / `reboot-on-failure`** 等の policy を持ち、適用後に再起動するか継続するかを制御する。

## state machine

`/var/lib/ztp/ztp_state` に現在状態が JSON で保存される。代表状態:

- `BOOT` → `IN-PROGRESS` → `SUCCESS` / `FAILED` / `DISABLED`
- 各 section にも `pending` / `in-progress` / `success` / `failed` / `skipped`

`ztp` CLI で再試行・abort・状態表示が可能。

## 関連 CLI

| Command | 用途 |
|---------|------|
| `show ztp status` | 現在の ZTP 状態 |
| `ztp run` | 再実行 |
| `ztp disable` | ZTP 無効化（起動完了後の運用） |
| `ztp enable` | 有効化 |

## 制限事項

- **management interface 経由のみが基本**: data port 経由の ZTP は対応する DHCP option / route 設定が要る
- **HTTPS の cert 検証**: 本番では信頼できる CA / pinning が必要（HLD は緩い検証も許す）
- **plugin 拡張の互換性**: vendor 拡張 plugin は対応版の ztp daemon が必要
- **failure 時の半適用**: 一部 section だけ成功した状態で停止すると整合性保証なし

## 干渉する機能

- **DHCP relay (v4/v6)**: ZTP は DHCP に強く依存。relay の設定不備が直撃
- **fwutil**: firmware section 経由で fwutil が呼ばれる
- **secure-upgrade / secure-boot**: 取得 image の検証
- **gnoi-OS / file APIs**: 後発の運用 API（gNOI）と用途が一部重なる

## トラブルシューティング

- ZTP がトリガしない → `/etc/sonic/config_db.json` の有無、ztp daemon の起動、DHCP lease 確認
- JSON 取得失敗 → DHCP option / URL 解決、ファイアウォール、HTTPS 証明書
- section が常に失敗 → 該当 plugin のログ（`/var/log/ztp/`）、state ファイルの error 詳細

## 引用元

[^1]: `sonic-net/SONiC` `doc/ztp/ztp.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- concerns hint:
- ztp daemon の現行 master 取り込みと systemd 起動経路の確認
- DHCP option 番号（option 67 / 225 / 239 等）の platform 別現行値確認
- plugin section type の現行サポート一覧確認
- ZTP JSON state ファイル（/var/lib/ztp/ztp_state）スキーマの現行値確認
- show ztp / ztp run / ztp disable CLI の sonic-utilities 取り込み確認
- secure-upgrade / fwutil との image 検証統合の現行実装確認
-->
