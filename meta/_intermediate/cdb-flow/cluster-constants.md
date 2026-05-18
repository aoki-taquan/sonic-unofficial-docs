# cluster フィールド — ハードコード定数調査 (Phase E)

対象: `DEVICE_METADATA|localhost.cluster` / `DEVICE_NEIGHBOR_METADATA|<device>.cluster`
調査ソース: `sonic-buildimage/src/sonic-config-engine/minigraph.py`

## 調査結果

### minigraph XML タグ名

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| XML タグ名 | `"ClusterName"` | minigraph XML からクラスタ名を読み出すタグ名。コード内にリテラルとして埋め込み | `minigraph.py:514` |
| フィールドキー名 | `"cluster"` | CONFIG_DB への書き込みキー名 (DEVICE_METADATA / DEVICE_NEIGHBOR_METADATA の両方で共通) | `minigraph.py:668, 811, 2172` |
| get() フォールバック | `""` (空文字列) | `devices[...].get('cluster', "")` の第 2 引数。DEVICE_METADATA 書き込み前の展開値。None ではなく空文字列を使用 | `minigraph.py:2170` |
| 初期値 (parse_device) | `None` | `parse_device()` 内で cluster 変数を `None` で初期化。タグが存在しない場合はこのまま返却される | `minigraph.py:493` |

### 判定条件の非対称性（コードに埋め込まれた暗黙定数）

| 箇所 | 条件式 | 意味 |
|------|--------|------|
| `DEVICE_METADATA` 書き込み判定 | `if cluster:` (truthy) | 空文字列 `""` は書き込まない。None も書き込まない | `minigraph.py:2171` |
| `DEVICE_NEIGHBOR_METADATA` 書き込み判定 | `if cluster != None:` (None check) | 空文字列 `""` は書き込む。None のみ除外 | `minigraph.py:667, 810` |

これらの条件式は定数ではなく判定パターンだが、値依存の非対称挙動を生む「コードに埋め込まれた暗黙の仕様」である。

## YANG / CONFIG_DB 側のハードコードなし

- YANG モデル (`sonic-device_metadata.yang`, `sonic-device_neighbor_metadata.yang`) に `default` 値なし
- `type string` のみで制約なし
- フィールドを参照するランタイムデーモンはなし（Phase C 調査済み）

## 結論

`cluster` フィールドに関する実質的なハードコード定数は以下の 4 点のみ:
1. XML タグ名 `"ClusterName"` (minigraph.py:514)
2. 初期値 `None` (minigraph.py:493)
3. get() フォールバック `""` (minigraph.py:2170)
4. 書き込みキー名 `"cluster"` (両テーブル共通)

ランタイム処理側にハードコード定数は存在しない（ランタイム消費デーモンがないため）。
