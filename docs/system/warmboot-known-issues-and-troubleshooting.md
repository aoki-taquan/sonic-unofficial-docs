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
      issues #6723, #6726, #6773, #6866, #7071, #7094, #7127, #7140, #7518, #9899, #12512
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
---

!!! success "裏取りステータス: code-verified"
    sonic-buildimage issue tracker の実環境報告から抽出。master ブランチ対象。

# ウォームブート既知問題とトラブルシューティング

## 概要

[SONiC](../reference/glossary.md#term-sonic) のウォームブート（warm-reboot）・高速リブート（fast-reboot）は複数の
サブシステムが協調する複雑なシーケンスを持つ。本ページは
[sonic-buildimage](../reference/glossary.md#term-sonic-buildimage) issue tracker に記録された
実環境での既知問題と対処法をまとめる（取り上げる issue は #6723, #6726, #6773, #6866, #7071, #7094, #7127, #7140, #7518, #9899, #12512）。

---

## 1. syncd ウォームスタートエラー

ウォームリスタートの状態は `WARM_RESTART` [CONFIG_DB](../reference/glossary.md#term-config_db) テーブルで制御され、その
スキーマは `sonic-warm-restart.yang` に定義されている[^yang]。

<!-- evidence:
source: sonic-net/sonic-buildimage/src/sonic-yang-models/yang-models/sonic-warm-restart.yang#L1-L5 (sha: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd)
excerpt: |
  module sonic-warm-restart  {
      namespace "http://github.com/sonic-net/sonic-warm-restart";
reasoning: >
  現行 master に sonic-warm-restart.yang が存在し WARM_RESTART テーブルのスキーマを
  定義していることを確認。本ページが扱うウォームリスタート機構の実装裏取り。
-->

<!-- evidence-rendered:start -->
??? note "📋 検証エビデンス: sonic-net/sonic-buildimage/src/sonic-yang-models/yang-models/sonic-warm-restart.yang#L1-L5 (sha: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd)"

    **出典**:

    `sonic-net/sonic-buildimage/src/sonic-yang-models/yang-models/sonic-warm-restart.yang#L1-L5 (sha: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd)`

    **抜粋**:

    ```text
    module sonic-warm-restart  {
        namespace "http://github.com/sonic-net/sonic-warm-restart";
    ```

    **判断根拠**: 現行 master に sonic-warm-restart.yang が存在し WARM_RESTART テーブルのスキーマを 定義していることを確認。本ページが扱うウォームリスタート機構の実装裏取り。

<!-- evidence-rendered:end -->

### 1-1. `Invalid sai_api_t passed to sai_api_query` (#6723)[^6723]

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

**現行 master での状況**: SAI 連携バグはベンダー SAI 実装に依存するため、SONiC 側コードでの普遍的な
fix は導入されていない。`syncd` の warm-restart シーケンス自体は今も `sonic-sairedis` 側で維持
されている。報告当時の 202012 系プラットフォームでの再現に対しては SAI ヘッダ更新で解消ずみの旨が
コメントで報告されている。

---

### 1-2. `syncd translateVidToRid failures for buffer pools` (#6726)[^6726]

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

**現行 master での状況**: VIDTORID マップ再構築のタイミング問題はウォーム/ファストリブートに本質的な
過渡状態であり、master でも `warm_restart` 終了通知（`WARM_RESTART_TABLE` の `state` 列）を待って
から外部監視を走らせる運用が引き続き推奨される。

---

### 1-3. syncd `APPLY_VIEW` エラー: hostif_trap_group (#7071, #7094)[^7071][^7094]

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

**現行 master での状況**: BRCM SAI 側のバグであり SONiC リポジトリでは fix を持たない。
master では Broadcom が同梱する SAI のバージョンが進んでおり、4.3.3.x 系の固有問題としては
事実上クローズ扱いだが、同等の APPLY_VIEW 障害の再発時には SAI 側 changelog の確認が必須。

---

## 2. LAG フラップ (#6773)[^6773]

**現象**: ウォームブート後（特に 2 回目以降）に [PortChannel](../reference/glossary.md#term-portchannel) が数回 flap する。

**対象プラットフォーム**: Broadcom TD3 ベースプラットフォーム、202012 ブランチを含む。

**パターン**:
- 1 回目のウォームブート: [LAG](../reference/glossary.md#term-lag) フラップなし
- **2 回目以降**: LAG が数回 flap してから安定

**原因**: [orchagent](../reference/glossary.md#term-orchagent) がウォームブート後に
PortChannel メンバーの再学習タイミングで競合が発生する。

**対処**: 2 回目以降のウォームブート後に LAG が安定するまで待機（通常 30 秒以内）。
本番環境では連続ウォームブート間に十分なインターバルを設ける。

**現行 master での状況**: TD3 固有の PortChannel 再収束タイミング問題は、[teamd](../reference/glossary.md#term-teamd-teamsyncd-teammgrd)/orchagent の
warm-restart 再同期手順が継続して維持されており、master でも連続ウォームブート間隔は
WARM_RESTART_TABLE の各コンポーネント `state` が `reconciled` になるのを待つ運用が安全。

---

## 3. SSH セッション切断によるウォームブート失敗 (#7127)[^7127]

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

**現行 master での状況**: `scripts/warm-reboot` は今も bash スクリプトで、warm-reboot / fast-reboot
の分岐後に `trap clear_boot EXIT HUP INT QUIT TERM KILL ABRT ALRM` を仕掛けて中断時には
`clear_boot` (kexec -u / warm_restart disable / WARM_DIR の redis スナップショット退避) でロール
バックを試みる。kexec 直前に至った段階で初めて `trap '' EXIT HUP INT QUIT TERM KILL ABRT ALRM`
へ差し替え、最終クリティカル区間ではシグナルを無視する設計になっている[^warmreboot-trap]。
いずれにせよスクリプト全体が前段で SIGHUP を受けると中断 (clear_boot 経由でロールバック) するため、
SSH 経由実行時は `nohup` / `screen` / `tmux` での detach が推奨される。

<!-- evidence:
source: sonic-net/sonic-utilities/scripts/warm-reboot#L947,L962,L1151-L1152 (sha: 39732bceb8bdefe706518ab40623bbbba6ff33b9)
excerpt: |
  trap clear_boot EXIT HUP INT QUIT TERM KILL ABRT ALRM
  ...
  # disable trap-handlers which were set before
  trap '' EXIT HUP INT QUIT TERM KILL ABRT ALRM
reasoning: >
  前段では clear_boot による中断クリーンアップ trap が掛かっており、kexec 直前で初めて
  空 trap に差し替えられる二段構造であることを実コードで確認。
-->

<!-- evidence-rendered:start -->
??? note "📋 検証エビデンス: sonic-net/sonic-utilities/scripts/warm-reboot#L947,L962,L1151-L1152 (sha: 39732bceb8bdefe706518ab40623bbbba6ff33b9)"

    **出典**:

    `sonic-net/sonic-utilities/scripts/warm-reboot#L947,L962,L1151-L1152 (sha: 39732bceb8bdefe706518ab40623bbbba6ff33b9)`

    **抜粋**:

    ```text
    trap clear_boot EXIT HUP INT QUIT TERM KILL ABRT ALRM
    ...
    # disable trap-handlers which were set before
    trap '' EXIT HUP INT QUIT TERM KILL ABRT ALRM
    ```

    **判断根拠**: 前段では clear_boot による中断クリーンアップ trap が掛かっており、kexec 直前で初めて 空 trap に差し替えられる二段構造であることを実コードで確認。

<!-- evidence-rendered:end -->

---

## 4. fast-reboot ダウンタイム超過 (#7140)[^7140]

**現象**: fast-reboot のダウンタイムが 30 秒制限を超える。

**主要因**:
1. orchagent の ASIC プログラミング完了待ちタイムアウト
2. カーネルの kexec 処理遅延 (#6866)[^6866]
3. プラットフォーム固有の SAI 初期化時間

**確認方法**:

```bash
show reboot-cause
# /var/log/syslog で fast-reboot の各フェーズのタイムスタンプを確認
grep -E 'fast-reboot|kexec|orchagent' /var/log/syslog | tail -50
```

**現行 master での状況**: fast-reboot のダウンタイム上限はプラットフォーム依存で、SONiC 側に汎用的な
30 秒保証はもともと存在しない（30 秒は当時の目標値）。master でも `fast-reboot` スクリプトと
`syncd`/`orchagent` の連携シーケンスは継続的に調整されており、ダウンタイム測定はプラットフォーム
ごとに個別検証が必要。

---

## 5. イメージダウングレード失敗 (#7518)[^7518]

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

**現行 master での状況**: `--skip-package-migration` オプションは現行 master の
`sonic_installer/main.py` でも有効で[^skip-pkg-mig]、対象 bootloader が package migration をサポート
しない場合は自動的に skip される実装になっている。

---

## 6. reboot-cause の誤表示 (#12512)[^12512]

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

**現行 master での状況**: `/host/reboot-cause/previous-reboot-cause` は現行 master の各プラット
フォーム `sonic_platform/chassis.py` でも参照されているパスである。reboot-cause 競合の根本対策は
issue で議論中だが、`show reboot-cause history` で過去ログを参照する運用は引き続き有効。

---

## 7. [202012] fast-reboot orchagent タイムアウト (#9899)[^9899]

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

**現行 master での状況**: 報告は 202012 ブランチが対象。master は orchagent/syncd 間の
INIT_VIEW 通知シーケンスが継続的に改善されており、同等のタイムアウトを観測した場合は
NIC ドライバ（igb 等）の TX hang 警告の有無を併せて確認する手順が引き続き有効。

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

## 引用元

各項目の一次情報は sonic-buildimage の issue tracker。ウォームリスタート機構の実装は `sonic-net/sonic-buildimage` (sha `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`) で裏取りした。

[^yang]: `src/sonic-yang-models/yang-models/sonic-warm-restart.yang`、`sonic-net/sonic-buildimage` (sha `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`)。`WARM_RESTART` テーブルのスキーマ定義。
[^6723]: [sonic-buildimage #6723](https://github.com/sonic-net/sonic-buildimage/issues/6723) — warmboot 中の syncd `Invalid sai_api_t passed to sai_api_query`。
[^6726]: [sonic-buildimage #6726](https://github.com/sonic-net/sonic-buildimage/issues/6726) — buffer pool の `translateVidToRid` 失敗。
[^7071]: [sonic-buildimage #7071](https://github.com/sonic-net/sonic-buildimage/issues/7071) — syncd `APPLY_VIEW` の hostif_trap_group 削除失敗。
[^7094]: [sonic-buildimage #7094](https://github.com/sonic-net/sonic-buildimage/issues/7094) — 上記 hostif_trap_group 問題の関連報告。
[^6773]: [sonic-buildimage #6773](https://github.com/sonic-net/sonic-buildimage/issues/6773) — ウォームブート後（2 回目以降）の LAG フラップ。
[^7127]: [sonic-buildimage #7127](https://github.com/sonic-net/sonic-buildimage/issues/7127) — SSH セッション切断による warm-reboot 中断。
[^7140]: [sonic-buildimage #7140](https://github.com/sonic-net/sonic-buildimage/issues/7140) — fast-reboot のダウンタイムが 30 秒制限を超える件。
[^6866]: [sonic-buildimage #6866](https://github.com/sonic-net/sonic-buildimage/issues/6866) — fast-reboot のダウンタイムに寄与するカーネル kexec 処理遅延。
[^7518]: [sonic-buildimage #7518](https://github.com/sonic-net/sonic-buildimage/issues/7518) — 最新 master から旧イメージへのダウングレード失敗。
[^12512]: [sonic-buildimage #12512](https://github.com/sonic-net/sonic-buildimage/issues/12512) — ウォームブート後の reboot-cause 誤表示。
[^9899]: [sonic-buildimage #9899](https://github.com/sonic-net/sonic-buildimage/issues/9899) — [202012] fast-reboot 中の orchagent INIT_VIEW タイムアウト。
[^warmreboot-trap]: `scripts/warm-reboot`（`sonic-net/sonic-utilities` sha `39732bceb8bdefe706518ab40623bbbba6ff33b9`）。L947 / L962 で `trap clear_boot EXIT HUP INT QUIT TERM KILL ABRT ALRM` (fast-reboot / warm-reboot 分岐時)、L1152 で kexec 直前に `trap '' EXIT HUP INT QUIT TERM KILL ABRT ALRM` に差し替え。`clear_boot()` は L339 に定義され `kexec -u` / `config warm_restart disable` / WARM_DIR redis スナップショット退避を行う。
[^skip-pkg-mig]: `sonic_installer/main.py` の `install` コマンドにおける `--skip-package-migration` オプション定義（`sonic-net/sonic-utilities`）。

<!-- glossary-links-injected: 9165fb6adb46 -->
