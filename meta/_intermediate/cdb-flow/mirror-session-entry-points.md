# mirror-session — Direction A 書き込み入り口

テーブル: `MIRROR_SESSION`

## 調査ファイル

- sonic-utilities/config/main.py

## 結果サマリ


<!-- entry-points -->
## 書き込み入り口 (Direction A)

MIRROR_SESSION テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - `config mirror_session add ...` / `config mirror_session remove ...` — `config/main.py` が `set_entry('MIRROR_SESSION', ...)` を呼ぶ (sonic-utilities/config/main.py:3242, 3311, 3368, 3413)

### minigraph / sonic-cfggen

minigraph.py に MIRROR_SESSION 生成コードはあるがコメントアウト済み (sonic-buildimage/src/sonic-config-engine/minigraph.py:2721)

### REST / gNMI

sonic-mgmt-common の MIRROR_SESSION トランスフォーマーなし — REST/gNMI 書き込みは未実装

### db_migrator

db_migrator.py での MIRROR_SESSION マイグレーションなし

### ビルド時デフォルト (build-time default)

`init_cfg.json.j2` に MIRROR_SESSION エントリなし

### ハードコードデフォルト / ランタイム注入

なし

### 死活・デッドコード

minigraph 経路は実質デッドコード (コメントアウト)
<!-- /entry-points -->

