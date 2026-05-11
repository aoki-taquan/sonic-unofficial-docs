---
title: SONiC Warm Reboot（要件・順序・docker 別 warm restart）
area: system
verification: code-verified
last_verified: 2026-05-10
sources:
  - repo: sonic-net/SONiC
    path: doc/warm-reboot/SONiC_Warmboot.md
    ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
    - WARM_RESTART
  cli:
    - warm-reboot
    - config warm_restart
  yang:
    - sonic-warm-restart
---

!!! success "裏取りステータス: code-verified"
    `sonic-utilities/scripts/warm-reboot` の warm reboot script、`sonic-buildimage/.../sonic-warm-restart.yang` の `WARM_RESTART` スキーマで HLD の going-down / going-up シーケンスと整合を確認（Verifier 2026-05-10）。詳細な going down / up path は [`system-wide-warmboot.md`](system-wide-warmboot.md) を併読。

# SONiC Warm Reboot（要件・順序・docker 別 warm restart）

## 読み手が知りたいこと

1. **warm reboot とは何で、cold / fast / express とどう違うか**
2. **どこに何が保存され、何が復元されるか**（SAI dump / Redis dump）
3. **各 docker（bgp / teamd / swss / lldp / dhcp_relay）は何を準備するべきか**
4. **どの CLI で有効化・実行・確認するか**
5. **データプレーン断や reconcile 失敗のときに何を見るか**

## 1. warm reboot とは

**データプレーンを乱さずに control plane（kernel / docker）を再起動** する SONiC の機能[^1]。LibSAI が ASIC state をファイルに退避→ kexec → 復元、という流れで、上限 90 秒の制御平面ダウンを許容しつつフォワーディングは継続させる。

- 同 image / version upgrade は対象、**downgrade は対象外**
- すべての docker / SAI vendor が warm restart を実装している前提
- BGP の GR-helper や teamd の LACP 拡張 timer が peer 側に必要

cold / fast / express との関係は [11-reboot](../topics/11-reboot/index.md) を参照。詳細な going-down / up path と `SONIC_BOOT_TYPE` の扱いは [`system-wide-warmboot.md`](system-wide-warmboot.md)。

## 2. どこに何が保存されるか

| 物 | 保存先 | 役割 |
|----|--------|------|
| ASIC / SAI state | `/host/warmboot/sai-warmboot.bin` | SAI が `remove_switch()` 時に dump、`create_switch` 時に復元 |
| Redis 全体 | `/host/warmboot/dump.rdb` | APP_DB / ASIC_DB / STATE_DB を再起動後 load |
| `WARM_RESTART_TABLE:system` | STATE_DB | shutdown 進行中フラグ |

## 3. 各レイヤへの要件

### LibSAI / ASIC

- `SAI_KEY_BOOT_TYPE = 1`（warm）で起動可能（0=cold, 2=fast）
- `SAI_SWITCH_ATTR_RESTART_WARM = true` で `remove_switch()` を受けたら state を `SAI_KEY_WARM_BOOT_WRITE_FILE` に書き出す
- `create_switch` を `SAI_SWITCH_ATTR_INIT_SWITCH = true` で呼ぶと保存ファイルから復元
- callback / notification は **SAI が保持しない**。app が再 register

### syncd

- ASIC_DB / 制御 channel から warm shutdown を受けて SAI に橋渡し
- 復旧時に Redis dump と SAI dump を read
- orchagent との **init view → apply view → diff** で差分のみ SAI に流す

### アプリケーション

各 docker は自身の orch / state を warm reboot を跨いで永続化する責務を持つ:

- **bgp**: graceful restart で peer に GR-helper を促し RIB を保持
- **teamd**: LACP 拡張 timer で 90 秒間 partner にリンクを切らせない
- **swss / orchagent**: APP_DB / ASIC_DB / STATE_DB を Redis dump 保存、再起動後に SAI と diff
- **lldp**: 影響軽微（再認識）
- **dhcp_relay**: lease は server 側保持、relay 自体は無影響

## 4. state machine

```mermaid
stateDiagram-v2
    [*] --> Disabled
    Disabled --> Enabled: config warm_restart enable
    Enabled --> ShuttingDown: warm-reboot 開始
    ShuttingDown --> Booting: kexec / reboot
    Booting --> Reconciled: orchagent diff 完了
    Reconciled --> Enabled: 動作中
    Reconciled --> Failed: timeout / mismatch
    Failed --> Enabled: 手動回復
```

## 5. 設定と実行

| Command | 用途 |
|---------|------|
| `config warm_restart enable system` | warm restart 全体有効化 |
| `config warm_restart enable <docker>` | docker 別 |
| `sudo warm-reboot` | warm reboot 実施 |
| `show warm_restart` | 状態確認 |

CONFIG_DB:

| Key | 説明 |
|-----|------|
| `WARM_RESTART\|<docker>` | docker 別の `enable` / `timer` |
| `WARM_RESTART\|system` | システム全体の状態 |

## 6. トラブルシューティング

- **90s 超のデータプレーン断** → syncd warm recovery 失敗。`sai-warmboot.bin` の有無を確認
- **BGP convergence 不良** → peer の GR-helper 対応、`config bgp graceful-restart` の値
- **orchagent reconcile が永遠** → APP_DB と ASIC_DB の不一致、syncd ログ

## 関連 Topics 章

- [11-reboot](../topics/11-reboot/index.md): warm / fast / express / cold の比較と運用全体像
- [20-swss-sai-redis](../topics/20-swss-sai-redis/index.md): orchagent と SAI の init view / apply view プロトコル

## 引用元

[^1]: `sonic-net/SONiC` `doc/warm-reboot/SONiC_Warmboot.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`
