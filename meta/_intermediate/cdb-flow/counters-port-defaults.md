# counters-port Phase A — implicit defaults (code-derived)

Generated: 2026-05-14  
Target doc: docs/reference/config-db/counters-port.md

## Field-by-field analysis

### ポーリング間隔のハードコードデフォルト

COUNTERS_DB は CONFIG_DB テーブルではなく COUNTERS_DB に書かれる runtime データだが、
ポーリング間隔は `portsorch.cpp` にハードコードされており、`FLEX_COUNTER_TABLE|PORT`
の `POLL_INTERVAL` が未設定の場合にこの値が syncd に投入される。

| 検出種類 | 詳細 |
|---------|------|
| ハードコード固定値 | `PORT_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS = 1000` (portsorch.cpp:87) → PORT / WRED_ECN_PORT グループのデフォルト間隔 |
| ハードコード固定値 | `PORT_RATE_FLEX_COUNTER_POLLING_INTERVAL_MS = "1000"` (portsorch.h:41) → rate プラグイン（port_rates.lua）の呼び出し間隔 |
| ハードコード固定値 | `PG_DROP_FLEX_STAT_COUNTER_POLL_MSECS = "10000"` (portsorch.h:40) → PG_DROP グループのデフォルト間隔 |
| CLI ソフトデフォルトとの一致 | counterpoll show が PORT に "default (1000)" と表示するのと偶然一致。YANG / CLI の `default` 宣言はなし |
| ビルド時書き込み | init_cfg.json.j2 が `FLEX_COUNTER_TABLE|PORT: {FLEX_COUNTER_STATUS: enable}` を書くが `POLL_INTERVAL` は書かない。orchagent ハードコード値 1000ms が実効値になる |

### FLEX_COUNTER_STATUS 依存の収集有無

| 検出種類 | 詳細 |
|---------|------|
| コード由来デフォルト | `m_port_counter_enabled = false`（flexcounterorch.h:66）。起動直後は PORT カウンタ収集ゼロ |
| ビルド時書き込み | init_cfg.json.j2 が起動時に `FLEX_COUNTER_STATUS: enable` を書き込み → 通常起動では有効 |
| allPortsReady 依存 | enable 受信時に `gPortsOrch->allPortsReady()` が false だと doTask 早期 return。ポート ready 後に一括適用（書込み順依存） |

### PHY ポート限定の暗黙フィルタ

| 検出種類 | 詳細 |
|---------|------|
| コード由来デフォルト | `m_type != Port::Type::PHY` を除外 (portsorch.cpp:9113-9117)。LAG / VLAN / CPU ポートは COUNTERS_PORT_NAME_MAP に登録されない。COUNTERS_DB エントリも生成されない |

### SAI フィールド未サポート時の暗黙 STATUS_NA

| 検出種類 | 詳細 |
|---------|------|
| YANG default 外 fallback | portstat.py `get_counters()` で SAI フィールドが COUNTERS:<oid> に存在しない場合、`fields[pos] = STATUS_NA` ('N/A') に fallback (portstat.py:350) |
| WRED dead consumer | STATE_DB の `PORT_COUNTER_CAPABILITIES|WRED_ECN_PORT_WRED_*_DROP_COUNTER` が "true" でないと WRED カウンタは counter_bucket_dict から除外。portstat.py:297-329 |
| プラットフォーム依存 | FEC bin カウンタ (S0-S15) は ASIC が FEC をサポートしない場合 N/A |

### gearbox 別 DB への分岐

| 検出種類 | 詳細 |
|---------|------|
| 経路依存乖離 | gearbox 有効環境では `GB_COUNTERS_DB` に別途カウンタを書き込む（m_gearboxEnabled && m_gb_counter_db）。通常の COUNTERS_DB とは独立した DB インデックス。portstat.py は GB_COUNTERS_DB を直接参照しない |

### WRED カウンタの追加有効化要件

| 検出種類 | 詳細 |
|---------|------|
| 前提条件依存 | `WRED_ECN_PORT` が enable でも `STATE_DB|PORT_COUNTER_CAPABILITIES|WRED_ECN_PORT_WRED_*_DROP_COUNTER` が "true" でなければ SAI ポーリング対象から除外（portstat.py:297-329）。エラー通知なし |

## 検出された discrepancy / 暗黙挙動まとめ

1. **ポーリング間隔の二重管理**: `POLL_INTERVAL` を CONFIG_DB に書かなかった場合、orchagent ハードコード (1000ms) と CLI ソフトデフォルト (1000ms) が偶然一致しているだけ。PORT_BUFFER_DROP は CLI 許容下限 30000ms に対しハードコードは異なるため注意。
2. **WRED カウンタの silent skip**: STATE_DB 能力フラグが "true" でない場合、`WRED_ECN_PORT` を enable にしても収集されない。エラー通知なし。
3. **LAG / VLAN ポートの除外**: COUNTERS_PORT_NAME_MAP に登録されないため、portstat.py で LAG インターフェースを指定しても表示が出ない（LAG 専用の COUNTERS_LAG_NAME_MAP が別途存在）。
4. **gearbox の二重 DB**: GB_COUNTERS_DB に書かれたカウンタは portstat.py の通常パスでは参照されない。gearbox 統計を見るには別途専用コマンドが必要。

## 書き込み経路サマリ

| 経路 | 対象 | 詳細 |
|------|------|------|
| portsorch init | COUNTERS_PORT_NAME_MAP | ポート名→OID マッピング書き込み |
| syncd FlexCounter (PORT) | COUNTERS:<oid> | SAI 統計を 1000ms ごとにポーリング |
| syncd Lua プラグイン (port_rates.lua) | RATES:<oid> | BPS / PPS / UTIL 計算・書き込み (1000ms) |
| syncd Lua プラグイン (port_flr.lua) | RATES:<oid>.FEC_* | FLR / BER 計算 |
| portsorch port add | COUNTERS_PORT_NAME_MAP | 新ポート追加時に追記 |
| portsorch port remove | COUNTERS_PORT_NAME_MAP | ポート削除時に削除 |
