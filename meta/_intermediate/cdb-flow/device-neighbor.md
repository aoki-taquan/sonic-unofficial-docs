# DEVICE_NEIGHBOR — 例外条件分析

## consumer 一覧

| consumer | 用途 | ソースパス |
|---|---|---|
| pfcwd / main.py | 外部ポート一覧として利用 | sonic-utilities/pfcwd/main.py:98,413 |
| show interfaces / __init__.py | インターフェイス一覧表示時に neighbor 情報を付与 | sonic-utilities/show/interfaces/__init__.py:316-318 |
| minigraph.py | minigraph パース時に DEVICE_NEIGHBOR テーブルを生成 | sonic-buildimage/src/sonic-config-engine/minigraph.py:2635 |
| db_migrator.py | スキーマ移行時に読み込み | sonic-utilities/scripts/db_migrator.py:766 |

## 例外条件

### minigraph: インターフェイス不在時の ignore
- minigraph.py:2635 — port_config.ini に存在しないインターフェイスが DEVICE_NEIGHBOR に含まれる場合、`Warning: ignore interface '%s' in DEVICE_NEIGHBOR as it is not in the port_config.ini` を stderr に出力してスキップ。エントリは生成されない。

### show interfaces: テーブル不在時
- show/interfaces/__init__.py:318 — `get_table("DEVICE_NEIGHBOR")` が空の場合 `"DEVICE_NEIGHBOR information is not present."` を表示して続行。エラーにはならない。

### pfcwd: 外部ポート判定
- pfcwd/main.py:413 — DEVICE_NEIGHBOR に登録されているポートキーを外部ポートとして扱う。テーブルが空の場合、pfcwd は全ポートをデフォルトで内部ポートと見なし、WD 対象から除外しない。
