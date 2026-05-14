# WRED_PROFILE — 書き込み入り口 (Direction A)

## 探索サマリー

| ソース種別 | 有無 | 概要 |
|---|---|---|
| CLI (sonic-utilities) | あり | `config qos reload` 経由でテンプレートから生成 |
| config qos clear | あり | WRED_PROFILE テーブル全削除 |
| minigraph | なし | WRED_PROFILE は minigraph で生成しない |
| REST/gNMI | なし | sonic-mgmt-common translib に WRED_PROFILE 対応なし |
| db_migrator | あり | `QUEUE.wred_profile` の ABNF 形式除去 (間接) |
| build-time (j2) | あり | `qos_config.j2` で `AZURE_LOSSLESS` プロファイル自動生成 |
| hard-coded defaults | なし | |
| runtime injection | なし | orchagent は読み取り側 |

---

## CLI — config qos reload

ソース: `sonic-utilities/config/main.py:3666-3755`

`config qos reload` コマンドで実行:

1. `_clear_qos()` (L895-940) で WRED_PROFILE テーブルを全削除
   ```python
   config_db.delete_table("WRED_PROFILE")
   ```
2. プラットフォーム固有の `qos.json.j2` テンプレートを `sonic-cfggen` で展開し `--write-to-db` で CONFIG_DB に書き込む
3. テンプレートには `WRED_PROFILE` セクションが含まれ、`AZURE_LOSSLESS` 等のプロファイルが生成される

**対象 DB**: CONFIG_DB

---

## CLI — config qos clear

ソース: `sonic-utilities/config/main.py:895-915`

`_clear_qos()` の `QOS_TABLE_NAMES` リストに `'WRED_PROFILE'` が含まれており、`config qos clear` で WRED_PROFILE テーブルが全削除される。

```python
config_db.delete_table("WRED_PROFILE")
```

---

## build-time (qos_config.j2)

ソース: `sonic-buildimage/files/build_templates/qos_config.j2:486-506`

`generate_wred_profiles` マクロが未定義の場合、デフォルトの `AZURE_LOSSLESS` プロファイルを生成:

```json
"WRED_PROFILE": {
    "AZURE_LOSSLESS": {
        "wred_green_enable": "true",
        "wred_yellow_enable": "true",
        "wred_red_enable": "true",
        "ecn": "ecn_all",
        "green_max_threshold": "2097152",
        "green_min_threshold": "1048576",
        "yellow_max_threshold": "2097152",
        "yellow_min_threshold": "1048576",
        "red_max_threshold": "2097152",
        "red_min_threshold": "1048576",
        "green_drop_probability": "5",
        "yellow_drop_probability": "5",
        "red_drop_probability": "5"
    }
}
```

プラットフォームが `generate_wred_profiles` マクロを定義している場合は、そちらが優先されプラットフォーム固有の WRED_PROFILE を生成する (L486-487)。

このテンプレートは `sonic-cfggen` による `config qos reload` または初回 firstboot 時に CONFIG_DB へ書き込まれる。

---

## db_migrator

ソース: `sonic-utilities/scripts/db_migrator.py:574-585`

直接的な WRED_PROFILE テーブル変更は行わない。ただし QUEUE テーブルの `wred_profile` フィールド値のフォーマットを変換する:

- 旧形式: `|AZURE_LOSSLESS|` (ABNF leafref 形式)
- 新形式: `AZURE_LOSSLESS` (プレーン文字列)

```python
qos_table_list = [
    ('QUEUE', ['scheduler', 'wred_profile']),
    ...
]
migrate_qos_db_fieldval_reference_remove(qos_table_list, ...)
```

これは WRED_PROFILE テーブル自体ではなく、参照側 (QUEUE) の値フォーマット変換。

---

## minigraph

なし。WRED_PROFILE は minigraph.py で生成しない。

---

## REST / gNMI

なし。`sonic-mgmt-common/translib/` に WRED_PROFILE 対応の App が存在しない (WRED 関連の Go ファイルが見当たらず)。

OpenConfig QoS YANG モデルへの translib 実装が未完のため、REST/gNMI 経由での WRED_PROFILE 書き込みは現時点では非サポート。

---

## hard-coded デフォルト

なし。WRED_PROFILE のデフォルト値は YANG の `default` 宣言および qos_config.j2 テンプレートで定義され、コード内のハードコードではない。

---

## 死活 (runtime injection)

`orchagent` の `QosOrch` は WRED_PROFILE を購読するのみ（読み取り側）。orchagent 自身が WRED_PROFILE へ書き込むケースはない。

---

## エビデンス grep カバレッジ

| ソース | パス | hit |
|---|---|---|
| config/main.py | `WRED_PROFILE` (QOS_TABLE_NAMES) | 1 |
| config/main.py | `qos reload` (template→db) | 間接 (3666-3755) |
| qos_config.j2 | `WRED_PROFILE` | 1 (L489) |
| db_migrator.py | `wred_profile` (QUEUE 側) | 1 (L575) |
| minigraph.py | WRED_PROFILE | 0 |
| translib/*.go | WRED_PROFILE | 0 |
