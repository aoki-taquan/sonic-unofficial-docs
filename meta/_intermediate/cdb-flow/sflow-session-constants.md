# SFLOW_SESSION — Phase E: 定数・マジックナンバー調査

調査日: 2026-05-17
対象ファイル:
- `sonic-swss/cfgmgr/sflowmgr.h`
- `sonic-swss/cfgmgr/sflowmgr.cpp`
- `sonic-swss/orchagent/sfloworch.cpp`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-sflow.yang`

## sflowmgr.h — マクロ定数

| 定数名 | 値 | 用途 |
|-------|----|------|
| `ERROR_SPEED` | `"error"` | ポートが `m_sflowPortConfMap` に未登録の場合に返す速度センチネル値。APP_DB に `sample_rate=error` として書き込まれると SflowOrch 側で rate=0 として解釈されスキップされる（`sfloworch.cpp:275-281`）。 |
| `NA_SPEED` | `"N/A"` | oper_speed が STATE_DB からまだ到着していない状態を示すセンチネル値。`oper_speed == NA_SPEED` の間は cfg_speed (PORT テーブルの speed) をサンプリングレートに使用する（`sflowmgr.cpp:396-400`）。 |

## sflowmgr.cpp — ハードコード初期値（コンストラクタ）

| 変数 | 初期値 | コード箇所 | 意味 |
|------|--------|-----------|------|
| `m_intfAllConf` | `true` | `sflowmgr.cpp:18` | 全ポートデフォルト有効状態。初期値 true = 全ポートに対してグローバルセッションを適用する |
| `m_gEnable` | `false` | `sflowmgr.cpp:19` | グローバル admin_state。初期値 false = sFlow 全体が無効 |
| `m_gDirection` | `"rx"` | `sflowmgr.cpp:20` | グローバルサンプリング方向デフォルト。YANG `sample_direction` default "rx" と一致 |
| `m_intfAllDir` | `"rx"` | `sflowmgr.cpp:21` | SFLOW_SESSION\|all のデフォルト方向。全ポートへの方向フォールバックとして使用 |

## sflowmgr.cpp — ハードコードリテラル（処理中）

| 箇所 | 値 | コード | 意味 |
|------|----|----|------|
| `sflowCheckAndFillValues()` | `"up"` | `sflowmgr.cpp:365` | `admin_state` 未指定ポートへのデフォルト注入値 |
| `sflowCheckAndFillValues()` | `"rx"` (via `m_gDirection`) | `sflowmgr.cpp:377` | `sample_direction` 未指定ポートへのデフォルト注入値 |
| `doTask()` — CFG_SFLOW_TABLE_NAME | `"rx"` | `sflowmgr.cpp:435` | SFLOW グローバルテーブル処理時のローカル変数初期値。admin_state/sample_direction が見つからない場合のフォールバック |
| `sflowGetGlobalInfo()` | `"up"` | `sflowmgr.cpp:277` | グローバル設定から APP_DB へ書き込む際の admin_state ハードコード値 |

## sfloworch.cpp — ハードコード初期値

| 変数 | 初期値 | コード箇所 | 意味 |
|------|--------|-----------|------|
| `m_sflowStatus` | `false` | `sfloworch.cpp:17` | SflowOrch 起動時は sFlow 無効。APP_SFLOW_TABLE の SET イベントで true に変わる |
| `dir` (doTask ローカル) | `"rx"` | `sfloworch.cpp:387` | SET 処理時のサンプリング方向ローカル変数初期値 |
| `rate` (doTask ローカル) | `0` | `sfloworch.cpp:386` | SET 処理時のサンプリングレートローカル変数初期値。rate==0 は無効値として新規ポートをスキップする条件に使われる |

## YANG 制約 (sonic-sflow.yang)

| フィールド | 制約 | YANG 箇所 |
|-----------|------|----------|
| `sample_rate` | `uint32 range "256..8388608"` | `sonic-sflow.yang:127-130` |
| `sample_rate` | `must "../port != 'all'"` — `SFLOW_SESSION\|all` キーには sample_rate を定義できない | `sonic-sflow.yang:126` |
| `admin_state` (SFLOW_SESSION) | `default up` | `sonic-sflow.yang:121` |
| `sample_direction` (SFLOW_SESSION) | `default "rx"` | `sonic-sflow.yang:137` |
| `SFLOW_COLLECTOR` | `max-elements 2` — コレクタは最大 2 個まで | `sonic-sflow.yang:62` |
| SFLOW_COLLECTOR `collector_port` | `default 6343` — sFlow デフォルトポート | `sonic-sflow.yang:81` |

## センチネル値の伝播パス

```
findSamplingRate() が ERROR_SPEED("error") を返す
  ↓
APP_SFLOW_SESSION_TABLE に sample_rate="error" が書き込まれる
  ↓  (sflowmgr.cpp:392 -- APP_DB に書いてしまう)
SflowOrch::sflowExtractInfo() が "error" を検出
  ↓  (sfloworch.cpp:275-281)
rate = 0 に変換
  ↓
doTask() の if(rate == 0) { it++; continue } でスキップ
  ↓  (sfloworch.cpp:410-415)
SAI 設定まで到達しない
```

## まとめ

- `ERROR_SPEED="error"` と `NA_SPEED="N/A"` が sflowmgrd の内部センチネル。前者は APP_DB まで伝播してサンプリングレートを「無効」にする唯一の信号。
- `m_gEnable=false`, `m_intfAllConf=true`, `m_gDirection="rx"`, `m_intfAllDir="rx"` がコンストラクタ時点の初期状態。
- YANG で `sample_rate` は `[256..8388608]`、`SFLOW_SESSION|all` には sample_rate を持てない（must 制約）。
- コレクタは最大 2 個（`max-elements 2`）、デフォルトポートは `6343`。
