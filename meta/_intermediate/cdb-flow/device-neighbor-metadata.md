# DEVICE_NEIGHBOR_METADATA — 例外条件分析

## consumer 一覧

| consumer | 用途 | ソースパス |
|---|---|---|
| bgpcfgd / managers_bgp.py | BGP ピア生成時に neighbor metadata を参照 | sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py:140,220-224 |
| pfcwd / main.py | PFC watchdog が外部ポートを DEVICE_NEIGHBOR 経由で取得し、neighbor metadata を参照 | sonic-utilities/pfcwd/main.py:102 |

## 例外条件

### bgpcfgd: DEVICE_NEIGHBOR_METADATA 未取得時
- managers_bgp.py:220-222 — BGP ピア追加時に `DEVICE_NEIGHBOR_METADATA` が directory に存在しない (= まだ読み込まれていない) 場合、`log_info("DEVICE_NEIGHBOR_METADATA is not ready for neighbor...")` を出力して `return False` で処理を延期。再試行待ちとなる。
- managers_bgp.py:140 — `deps.append(...)` により依存関係として登録されているため、テーブルが到着した時点で再処理が行われる。

### pfcwd: neighbor name 欠落
- pfcwd/main.py:102 — `candidates[port]['name']` で DEVICE_NEIGHBOR_METADATA を参照するが、name フィールド欠落時は KeyError が発生。エラーハンドリングは特に定義されておらず、pfcwd の起動シーケンスが中断する。
