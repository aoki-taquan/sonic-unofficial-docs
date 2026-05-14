# mux-cable — Direction A 書き込み入り口

テーブル: `MUX_CABLE`

## 調査ファイル

- sonic-utilities/config/muxcable.py

## 結果サマリ


<!-- entry-points -->
## 書き込み入り口 (Direction A)

MUX_CABLE テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - `config muxcable mode ...` / `config muxcable prbs ...` — `config/muxcable.py` が `set_entry('MUX_CABLE', port, fvs)` を呼ぶ (sonic-utilities/config/muxcable.py:278)

### minigraph / sonic-cfggen

minigraph.py に MUX_CABLE 生成なし — 通常 minigraph から配信されない

### REST / gNMI

sonic-mgmt-common の MUX_CABLE トランスフォーマーなし

### db_migrator

db_migrator.py での MUX_CABLE マイグレーションなし

### ビルド時デフォルト (build-time default)

`init_cfg.json.j2` に MUX_CABLE エントリなし

### ハードコードデフォルト / ランタイム注入

`sonic-platform-daemons/ycabled` が `y_cable_table_helper.py` で MUX_CABLE を読み取り、デーモン内部で状態値を更新するケースあり

### 死活・デッドコード

なし
<!-- /entry-points -->

