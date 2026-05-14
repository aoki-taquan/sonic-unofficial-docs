# Phase 9 — evidence precision verification report

## 対象ページ

1. device-metadata (tier_high)
2. acl-rule (tier_mid)
3. acl-table (tier_mid)
4. wred-profile (tier_mid)

## 確認 evidence 行数

| ページ | 確認行数 | 修正行数 | 正しかった行数 |
|--------|---------|---------|--------------|
| device-metadata | 52 | 5 | 47 |
| acl-rule | 28 | 1 | 27 |
| acl-table | 18 | 0 | 18 |
| wred-profile | 8 | 0 | 8 |
| **合計** | **106** | **6** | **100** |

## 修正内容 (前→後)

### 修正1: device-metadata — SpineRouter tuple position 誤読

- 行: `type` 値別挙動 SpineRouter 行
- 原因: init_cfg.json.j2 の features tuple `(name, state, delayed, autorestart)` の position 2 を `has_per_asic_scope` と誤解釈
- 前: `pmon の has_per_asic_scope=False 設定 (SpineRouter は per-ASIC scope なし)`
- 後: `pmon の delayed=False 設定 (SpineRouter は pmon を遅延起動しない)`

### 修正2: device-metadata — derivation table 同根修正

- 行: Phase 6 派生表の SpineRouter → pmon 行
- 前: `pmon has_per_asic_scope = False`
- 後: `pmon delayed = False (pmon を遅延起動しない)`

### 修正3: device-metadata — DualToR pmon デーモン名誤記

- 行: subtype 値別挙動 DualToR 行
- 原因: docker-pmon.supervisord.conf.j2:157 を確認; 実際に起動するのは `ycabled` であり `mux_manager` は存在しない
- 前: `pmon で mux_manager 起動`
- 後: `pmon で ycabled 起動`

### 修正4: device-metadata — async_swss_rec disabled の else 節誤記

- 行: async_swss_rec 値別挙動 disabled 行
- 原因: orchagent.sh:66-68 に else 節が存在しないのに "(else 節)" と記載
- 前: `swss.rec を同期書き込み | orchagent.sh:66 (else 節)`
- 後: `-A フラグを付加しない → swss.rec を同期書き込み (デフォルト動作、else 節なし) | orchagent.sh:66-68`

### 修正5: device-metadata — suppress-fib-pending disabled の evidence 行誤解釈

- 行: suppress-fib-pending 値別挙動 disabled 行
- 原因: line 278 は "ルートを即座に通知" する箇所ではなく runtime の suppress 無効化トランジション処理
- 前: `fpmsyncd.cpp:278 でルートを即座に通知`
- 後: 起動時の未分岐 (`fpmsyncd.cpp:113-114`) + ランタイム無効化トランジション (`fpmsyncd.cpp:291-300`)

### 修正6: acl-rule — aclorch.h ANY の行番号誤記

- 行: IP_TYPE 値別挙動 ANY 行
- 原因: IP_TYPE_ANY は aclorch.h:98 に定義されているが line 100 と誤記
- 前: `aclorch.h:100`
- 後: `aclorch.h:98`

## 確認して正しかった代表例

- qosorch.cpp:37-44 の ecn_map 全 8 値マッピング ✓
- aclorch.cpp:145-147 の aclPacketActionLookup (FORWARD/DROP/COPY) ✓
- acltable.h:26-42 の TABLE_TYPE_* 定義 ✓
- fpmsyncd.cpp:113-114 の suppressionEnabled check ✓
- managers_bgp.py:502 の suppress-fib-pending FRR コマンド ✓
- bgpd.main.conf.j2:20,27 の disagg_t2/disagg_rh lowercase 比較 ✓
