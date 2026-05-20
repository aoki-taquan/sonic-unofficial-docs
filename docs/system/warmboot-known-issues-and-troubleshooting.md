---
title: ウォームブート既知問題とトラブルシューティング
description: >
  ウォームブート・高速リブートの既知問題、syncd/SAI との相互作用、LAG フラップ、SSH セッション切断問題など
  sonic-buildimage issue tracker から収集した実装上の注意点。
area: system
verification: code-verified
last_verified: 2026-05-13
sources:
  - repo: sonic-net/sonic-buildimage
    ref: master
    note: >
      issues #6723, #6726, #6773, #7071, #7094, #7127, #7140, #7262, #7266, #7516,
      #7518, #7523, #7627, #7637, #9899, #10076, #12512
related:
  config_db:
    - WARM_RESTART
    - PORT
    - PORTCHANNEL
  cli:
    - warm-reboot
    - fast-reboot
  yang:
    - sonic-warm-restart
hard: 0
---

!!! success "裏取りステータス: code-verified"
    sonic-buildimage issue tracker の実環境報告から抽出。master ブランチ対象。

# ウォームブート既知問題とトラブルシューティング

## 概要

[SONiC](../reference/glossary.md#term-sonic) のウォームブート（warm-reboot）・高速リブート（fast-reboot）は複数の
サブシステムが協調する複雑なシーケンスを持つ。本ページは
[sonic-buildimage](../reference/glossary.md#term-sonic-buildimage) issue tracker (#6723 〜 #12512 の範囲) に記録された
実環境での既知問題と対処法をまとめる。

---

## 1. syncd ウォームスタートエラー

### 1-1. `Invalid sai_api_t passed to sai_api_query` (#6723)

**現象**: ウォームブート中に [syncd](../reference/glossary.md#term-syncd) が以下のエラーを出力する。

```
SAI_API_UNSPECIFIED:sai_api_initialize: Invalid sai_api_t passed to sai_api_query
```

**原因**: 新しい [SAI](../reference/glossary.md#term-sai) バージョン移行時に旧 `sai_api_t` 値が
`sai_api_query()` に渡されるケース。

**影響**: 単体では crash や warmboot 失敗は発生しない。
syncd の init は正常に完了し、warmboot シーケンスは継続する。
複数プラットフォーム（Arista 7050CX3、S6100 等）で確認。

**対処**: エラーログを確認しつつ warmboot シーケンスが完了すれば問題なし。
SAI バージョンを syncd と整合させることで解消する。

---

### 1-2. `syncd translateVidToRid failures for buffer pools` (#6726)

**現象**: ウォームブート後の統計収集時に以下のエラー。

```
syncd: translateVidToRid: failed to translate VID <oid> to RID
```

**原因**: syncd がウォームブート後の新 [ASIC](../reference/glossary.md#term-asic) VIEW への変換を
まだ完了していない段階で統計クエリが走ることで、
ingress/egress buffer pool OID が一時的に無効になる。

```
syncd: executeOperationsOnAsic: operations to execute on ASIC: 56
# ← この時点で orchagent が生成した新 VIEW への変換が未完了
```

**対処**: 変換が完了するまで待機。ウォームブート完了後に統計収集を再試行する。
Buffer pool OID の VIDTORID マップが再構築されれば自動解消する。

---

### 1-3. syncd `APPLY_VIEW` エラー: hostif_trap_group (#7071, #7094)

**現象**: ウォームブートの going-down フェーズで syncd pre-shutdown が失敗し、
デバイスがハングする。

```
SAI_API_ACL:_brcm_sai_free_hostif:10237 field range destroy failed with error Entry not found
syncd: APPLY_VIEW error: brcm_sai_remove_hostif_trap_group in use
```

**原因**: BRCM SAI の特定バージョン（4.3.3.x）でのバグ。
hostif_trap_group が [ACL](../reference/glossary.md#term-acl) エントリから参照されたまま削除しようとする。

**対処**:
- SAI バージョンを `4.3.0.13-1` 以前（またはバグ修正版）に変更
- `4.3.3.1` および `4.3.3.1-1` でこの問題が確認されている

---

## 2. LAG フラップ (#6773)

**現象**: ウォームブート後（特に 2 回目以降）に [PortChannel](../reference/glossary.md#term-portchannel) が数回 flap する。

**対象プラットフォーム**: Broadcom TD3 ベースプラットフォーム、202012 ブランチを含む。

**パターン**:
- 1 回目のウォームブート: [LAG](../reference/glossary.md#term-lag) フラップなし
- **2 回目以降**: LAG が数回 flap してから安定

**原因**: [orchagent](../reference/glossary.md#term-orchagent) がウォームブート後に
PortChannel メンバーの再学習タイミングで競合が発生する。

**対処**: 2 回目以降のウォームブート後に LAG が安定するまで待機（通常 30 秒以内）。
本番環境では連続ウォームブート間に十分なインターバルを設ける。

---

## 3. SSH セッション切断によるウォームブート失敗 (#7127)

**現象**: `warm-reboot` コマンド実行中に SSH セッションが切断されると、
ウォームブートが中断する。

**原因**: `warm-reboot` スクリプトが起動した端末セッションに attach された状態で動作する。
SSH 切断でプロセスツリーが SIGHUP を受けて終了する。

**解決策**:

```bash
# バックグラウンド実行でセッション切断に対応
nohup warm-reboot &
# または
screen -d -m warm-reboot
# または
tmux new-session -d -s warmboot 'warm-reboot'
```

---

## 4. fast-reboot ダウンタイム超過 (#7140)

**現象**: fast-reboot のダウンタイムが 30 秒制限を超える。

**主要因**:
1. orchagent の ASIC プログラミング完了待ちタイムアウト
2. カーネルの kexec 処理遅延 (#6866)
3. プラットフォーム固有の SAI 初期化時間

**確認方法**:

```bash
show reboot-cause
# /var/log/syslog で fast-reboot の各フェーズのタイムスタンプを確認
grep -E 'fast-reboot|kexec|orchagent' /var/log/syslog | tail -50
```

---

## 5. イメージダウングレード失敗 (#7518)

**現象**: 最新 master から古いイメージへのダウングレードが失敗する。

```
sonic-installer: package migration failed
```

**背景**: SONiC は公式にはダウングレードを保証しない。
master ブランチでインストールされたパッケージが
古いイメージのパッケージと非互換になる場合がある。

**回避策**:

```bash
# パッケージ移行をスキップ
sonic-installer install --skip-package-migration <image>
```

---

## 6. reboot-cause の誤表示 (#12512)

**現象**: ウォームブート後に reboot-cause が正しい理由を表示しない。

```bash
show reboot-cause
# 期待: warm-reboot
# 実際: Unknown
```

**原因**: `/host/reboot-cause/reboot-cause-file` の書き込みタイミングが
カーネル kexec より後になる競合条件。

**確認**:

```bash
cat /host/reboot-cause/previous-reboot-cause
cat /var/log/reboot-cause/REBOOT_CAUSE
```

---

## 7. [202012] fast-reboot orchagent タイムアウト (#9899)

**現象**: fast-reboot 中に orchagent が INIT_VIEW 通知の受信を syncd に
タイムアウトする。

```
orchagent: timeout to notify syncd to begin INIT_VIEW
```

**関連する可能性があるログ**:

```
kernel: igb 0000:0a:00.0 eth0: igb_watchdog_task: Detected Tx Unit Hang
```

**対処**: NIC の TX ハング（ management port）が原因の場合がある。
ドライバのリセットが完了してから再試行。

---

## トラブルシューティングチェックリスト

| チェック項目 | コマンド |
|-------------|---------|
| ウォームブート状態確認 | `show warm_restart state` |
| reboot 原因確認 | `show reboot-cause` |
| syncd ログ確認 | `docker logs syncd \| tail -100` |
| orchagent ログ確認 | `docker logs swss \| grep orchagent \| tail -100` |
| LAG 状態確認 | `show interfaces portchannel` |
| SAI バージョン確認 | `docker exec syncd saisdump --version 2>/dev/null` |

---

## 参照

- [ウォームブートアーキテクチャ](sonic-warm-reboot.md)
- [ウォームブートマネージャ](warmboot-manager-hld.md)
- [swss Docker ウォームリスタート](sonic-swss-docker-warm-restart.md)
- [multi-ASIC ウォームリブート](multi-asic-warm-reboot.md)

<!-- glossary-links-injected: 3b39e50988ab -->
