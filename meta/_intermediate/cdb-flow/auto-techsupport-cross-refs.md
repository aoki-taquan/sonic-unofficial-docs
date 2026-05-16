# AUTO_TECHSUPPORT テーブル 暗黙参照スキャン (Phase C)

`docs/reference/config-db/auto-techsupport.md` の Phase C (暗黙参照) ブロック裏付け資料。

ソースは `sonic-net/sonic-utilities/scripts/coredump_gen_handler.py` と
`sonic-net/sonic-utilities/scripts/techsupport_cleanup.py`、および両者が
`from utilities_common.auto_techsupport_helper import *` で取り込む共有モジュール
`sonic-utilities/utilities_common/auto_techsupport_helper.py`。
`AUTO_TECHSUPPORT|GLOBAL` の値を起点に、これら 2 スクリプトが間接的に
読み書きする CONFIG_DB / STATE_DB のテーブルを列挙する。

## スキャン手順

```
grep -nE 'CFG_DB|STATE_DB|FEATURE|AUTO_TECHSUPPORT|TS_MAP|db\.(get|set|delete|keys|hget|connect)' \
    .cache/sonic-sources/sonic-utilities/scripts/coredump_gen_handler.py \
    .cache/sonic-sources/sonic-utilities/scripts/techsupport_cleanup.py \
    .cache/sonic-sources/sonic-utilities/utilities_common/auto_techsupport_helper.py
```

ヒットを `db.get` / `db.keys` / `db.set` / `db.delete` の用途別に分類し、
`utilities_common/auto_techsupport_helper.py:42-60` のテーブル名定数
(`CFG_DB`, `STATE_DB`, `AUTO_TS`, `FEATURE`, `TS_MAP`) と突き合わせて参照先を解決した。

## 検出された暗黙参照テーブル

### CONFIG_DB — feature 別オーバーライド (`AUTO_TECHSUPPORT_FEATURE`)

`coredump_gen_handler.py` が core 検出時に **必ず** 参照する隣接テーブル。
`AUTO_TECHSUPPORT|GLOBAL.state=enabled` でも feature 側が `enabled` でなければ
techsupport は起動しない (2 段ゲート)。

| テーブル | 参照箇所 | 用途 | evidence |
|---|---|---|---|
| `AUTO_TECHSUPPORT_FEATURE\|<container>` | `db.get(CFG_DB, FEATURE.format(self.container), CFG_STATE)` | container 単位の `state` チェック (Gate-2)。`disabled` または未設定なら起動スキップ | coredump_gen_handler.py:54-58 |
| `AUTO_TECHSUPPORT_FEATURE\|<container>` | `db.get(CFG_DB, FEATURE.format(container), COOLOFF)` | container 単位 rate-limit (`rate_limit_interval`) 取得。`ValueError` / 未設定 → `0.0` (rate-limit 無効) | auto_techsupport_helper.py:316-331 |

`container` 名は `trim_masic_suffix()` (helper.py:200-201) で `swss0` → `swss` のように
masic suffix を除去してから `FEATURE.format()` に渡される。

### CONFIG_DB — FEATURE テーブル (現状参照なし)

YANG コメントには `TODO: Leafref once the FEATURE YANG is added` とあるが、
**`coredump_gen_handler.py` / `techsupport_cleanup.py` のコード経路では
`FEATURE` テーブル (アプリケーション feature の有効化テーブル) は参照しない**。
container 名の妥当性検証は行わず、`AUTO_TECHSUPPORT_FEATURE|<container>` が
存在するか否かのみで判定する。

| テーブル | 結論 | evidence |
|---|---|---|
| `FEATURE` (アプリ feature 有効化) | 参照なし。`grep -n '"FEATURE"' coredump_gen_handler.py techsupport_cleanup.py auto_techsupport_helper.py` の hit はすべて `AUTO_TECHSUPPORT_FEATURE` キー文字列内のサブ文字列 | helper.py:14,54 (`FEATURE = "AUTO_TECHSUPPORT_FEATURE|{}"`) |

`FEATURE` テーブル本体は `hostcfgd` の `FeatureHandler` が docker サービス
on/off の起点として参照するが、auto-techsupport 経路では関与しない。
本ドキュメント (cross-refs ブロック) では「**関連 — しかし現状コードでは未参照**」として
注意書きする。

### CONFIG_DB — DEVICE_METADATA (現状参照なし)

| テーブル | 結論 | evidence |
|---|---|---|
| `DEVICE_METADATA.localhost` | 参照なし。`grep -n 'DEVICE_METADATA\|hostname\|localhost'` は 0 hit | coredump_gen_handler.py / techsupport_cleanup.py / auto_techsupport_helper.py 全行 |

`hostname` / `platform` / `mac` 等の解決は auto-techsupport 経路では行わない。
`show techsupport` (subprocess) 側が必要に応じて参照する可能性はあるが、
**CONFIG_DB レベルの暗黙参照は発生しない**。

### STATE_DB — `AUTO_TECHSUPPORT_DUMP_INFO`

両スクリプトの **副次書込先** であり、かつ **rate-limit 判定の読み出し元** でもある。
ここに書き込まれたエントリは `verify_rate_limit_intervals()` (helper.py:282-299) が
container 単位の最終 techsupport 生成時刻を引き出すために `keys + get_all` で全件走査する。

| 操作 | キー / フィールド | 参照箇所 | 用途 |
|---|---|---|---|
| `db.keys(STATE_DB, TS_MAP+"*")` | `AUTO_TECHSUPPORT_DUMP_INFO\|*` | helper.py:260 (`get_ts_map`) | container 別最終生成時刻を集計し、`rate_limit_interval` 経過判定 |
| `db.get_all(STATE_DB, ts_key)` | `timestamp` / `container_name` | helper.py:264-276 | container 名でグルーピング、`timestamp` を int 化して比較対象に |
| `db.set(STATE_DB, key, TIMESTAMP, ...)` 他 4 フィールド | `AUTO_TECHSUPPORT_DUMP_INFO\|<ts_dump>` | helper.py:302-310 (`write_to_state_db`) | 新規 techsupport 生成成功時に `timestamp` / `event_type` / `core_dump` / `container_name` を hset 相当で書込 |
| `db.delete(STATE_DB, TS_MAP + "|" + name)` | `AUTO_TECHSUPPORT_DUMP_INFO\|<name>` | techsupport_cleanup.py:13-18 (`clean_state_db_entries`) | `max_techsupport_limit` 超過で物理ファイル削除されたエントリを STATE_DB からも除去 |

`AUTO_TECHSUPPORT_DUMP_INFO` のフィールド構造は Phase F (`side-effects` ブロック) と重複するが、
**Phase C では「読み出しによる挙動依存」の側面**に焦点を当てる:

- container 側 `rate_limit_interval` > 0 のとき、本テーブルが空であれば常に「経過済」扱い (helper.py:293)
- 同一 container の `timestamp` が現在時刻に近いと techsupport 起動を抑制
- `container_name` フィールドが欠落したエントリは「グローバル枠」として集計されない

### STATE_DB — DOCKER_STATS (本スクリプトでは未参照)

`memory_threshold_check.py` (別エントリポイント) が `DOCKER_STATS|*` を参照する
ことが知られているが、`coredump_gen_handler.py` / `techsupport_cleanup.py` 経路では
読み書きしない。Phase C 対象外。

## まとめ — Phase C で本文に載せるべき関連テーブル

| テーブル | 関係 | 本文掲載判定 |
|---|---|---|
| `AUTO_TECHSUPPORT_FEATURE` | CONFIG_DB 暗黙参照 (read) — 2 段ゲート + 個別 rate-limit | **掲載** |
| `AUTO_TECHSUPPORT_DUMP_INFO` (STATE_DB) | rate-limit 判定の参照元 + 副次書込先 | **掲載** (rate-limit 観点で Phase F とは別軸) |
| `FEATURE` (アプリ feature 有効化) | 関連だが現状コードでは未参照 | **掲載** (注意書きとして) |
| `DEVICE_METADATA.localhost` | 参照なし | **不掲載** (誤解されやすい隣接テーブルとして言及のみ) |

## 範囲外 (誤解されやすい隣接)

- `FEATURE` (アプリ feature 有効化): `AUTO_TECHSUPPORT_FEATURE` と名前が似るが、
  auto-techsupport 経路では参照しない。container 名の妥当性は `AUTO_TECHSUPPORT_FEATURE|<container>` の
  存否で間接的に決まる
- `DEVICE_METADATA.localhost`: `hostname` / `platform` 等は両スクリプトに 0 hit
- `DOCKER_STATS` (STATE_DB): `memory_threshold_check.py` 経路の参照先で、本スクリプトでは未参照
