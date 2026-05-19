# FIPS — Phase F 副次 DB 書込 (調査メモ)

対象ページ: `docs/reference/config-db/fips.md`
調査日: 2026-05-19
調査者: batch-q67-f

## 調査ソース

- `sonic-host-services/scripts/hostcfgd` (`FipsCfg` クラス, L1753-1846)
- STATE_DB 書込: hostcfgd L1792 (`state_db_conn.hset('FIPS_STATS|state', 'config_datetime', ...)`)
- APPL_DB / COUNTERS_DB / ASIC_DB 参照: grep して 0 ヒット確認

## 調査結果

`FipsCfg.update()` が CONFIG_DB `FIPS|global` の変更を処理した際に副次的に書き込む DB エントリは STATE_DB `FIPS_STATS|state` のみ。

| 副次 DB | キー | フィールド | 書込タイミング | evidence |
|---------|------|-----------|---------------|----------|
| STATE_DB | `FIPS_STATS\|state` | `config_datetime` | `update()` 呼出ごとに `datetime.utcnow().isoformat()` を書込む | hostcfgd:1792 |

その他の DB (APPL_DB / COUNTERS_DB / ASIC_DB / FLEX_COUNTER_DB) への書込はなし。

## APPL_DB 非経由の根拠

`FipsCfg` クラス (L1753-1846) 内に `ProducerStateTable` / `Table` の `set(` / `hset` 呼出はなく、APPL_DB への変更は行わない。FIPS 設定はホスト OS レベル (OpenSSL/kernel) の変更であり SAI 非経由。

## STATE_DB 書込の用途

`FIPS_STATS|state.config_datetime` は `restart()` メソッドが `/etc/fips/fips_enable` の mtime と比較して「既に再起動済みかどうか」を判定するために使う (hostcfgd:1821-1823)。二重再起動防止機構として機能する。
