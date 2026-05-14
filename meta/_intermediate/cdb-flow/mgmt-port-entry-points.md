# mgmt-port — Direction A 書き込み入り口

テーブル: `MGMT_PORT`

## 調査ファイル



## 結果サマリ


<!-- entry-points -->
## 書き込み入り口 (Direction A)

MGMT_PORT テーブルへの書き込みが発生するコード経路を網羅的に調査した結果。

### CLI

  - `config interface mgmt ...` — なし (管理ポートは通常 minigraph/sonic-cfggen で投入)

### minigraph / sonic-cfggen

**minigraph.py** `parse_device_desc_xml()` が管理インターフェース名と速度を抽出し `results['MGMT_PORT']` に投入 (sonic-buildimage/src/sonic-config-engine/minigraph.py:2281–2296)

### REST / gNMI

sonic-mgmt-common の MGMT_PORT トランスフォーマーなし — REST/gNMI 書き込みは未実装

### db_migrator

db_migrator.py での MGMT_PORT マイグレーションなし

### ビルド時デフォルト (build-time default)

`files/build_templates/init_cfg.json.j2` に MGMT_PORT エントリなし (JSON 手動定義 or minigraph 由来)

### ハードコードデフォルト / ランタイム注入

なし

### 死活・デッドコード

MGMT_PORT へのプログラム書き込みは minigraph 経由が唯一の実装経路
<!-- /entry-points -->

