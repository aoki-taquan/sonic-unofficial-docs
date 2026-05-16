# CABLE_LENGTH テーブル 暗黙参照スキャン (Phase C)

`docs/reference/config-db/cable-length.md` の Phase C (暗黙参照) ブロック裏付け資料。

ソースは `sonic-net/sonic-swss/cfgmgr/buffermgr.cpp` および `buffermgrdyn.cpp`。
CABLE_LENGTH テーブル変更時に `buffermgr` / `buffermgrdyn` が間接的に読み出す関連 CONFIG_DB テーブルを列挙する。

## スキャン手順

```
grep -n "PORT_TABLE\|DEVICE_METADATA\|BUFFER_POOL\|BUFFER_PROFILE\|CFG_PORT_TABLE\|CFG_DEVICE_METADATA\|CFG_BUFFER" \
    .cache/sonic-sources/sonic-swss/cfgmgr/buffermgr.cpp \
    .cache/sonic-sources/sonic-swss/cfgmgr/buffermgrdyn.cpp
```

コンストラクタ初期化・`doTask()` のルーティング・`handleCableLenTable()` / `handlePortTable()` での参照パターンを抽出。

## 検出された暗黙参照テーブル

### PORT テーブル (CONFIG_DB)

| 参照箇所 | 用途 | evidence |
|---|---|---|
| `buffermgr.cpp:23` — `m_cfgPortTable(cfgDb, CFG_PORT_TABLE_NAME)` | `speed` / `admin_status` フィールドを購読し、CABLE_LENGTH 更新後の headroom 再計算トリガとして利用 | buffermgr.cpp:23,544-560 |
| `buffermgr.cpp:544` — `table_name == CFG_PORT_TABLE_NAME` | PORT 更新イベントで `doCableTask()` に続く `doSpeedUpdateTask()` を呼び出す。port の speed が変わると cable_length と組み合わせて PG プロファイルを再選択 | buffermgr.cpp:544-565 |
| `buffermgrdyn.cpp:449` — `CFG_PORT_TABLE_NAME → handlePortTable` | `speed` / `mtu` / `admin_status` / `lanes` / `adv_speeds` / `autoneg` を取得。cable_length が既に設定済みなら `refreshPgsForPort()` を即時呼び出す | buffermgrdyn.cpp:449,2266-2415 |
| `buffermgrdyn.cpp:2353-2359` | PORT イベント処理中に `portInfo.cable_length` が空の場合、`m_cableLengths[port]` (CABLE_LENGTH テーブル由来キャッシュ) から取得して補完 | buffermgrdyn.cpp:2353-2359 |

**暗黙参照の性質**: CABLE_LENGTH 更新単体では headroom 計算に不十分で、PORT テーブルの `speed` / `mtu` / `admin_status` が揃って初めて `refreshPgsForPort()` が実行される。PORT テーブルへの暗黙依存は必須の前提条件。

### DEVICE_METADATA テーブル (CONFIG_DB)

| 参照箇所 | 用途 | evidence |
|---|---|---|
| `buffermgr.cpp:470` — `table_name == CFG_DEVICE_METADATA_TABLE_NAME` → `doBufferMetaTask()` | `buffer_model` フィールドを取得し static / dynamic モードを切り替える。`dynamic` の場合 `buffermgr` は以降の CABLE_LENGTH 処理を全スキップ | buffermgr.cpp:470-480 |
| `buffermgrdyn.cpp:41` — `m_cfgDeviceMetaDataTable(cfgDb, CFG_DEVICE_METADATA_TABLE_NAME)` | 初期化時に `m_cfgDeviceMetaDataTable.hget("localhost", "platform", m_specific_platform)` で Mellanox プラットフォーム識別子を取得。プラットフォームによって headroom Lua スクリプトが異なる | buffermgrdyn.cpp:41,87-94 |

**暗黙参照の性質**: `buffer_model=dynamic` / `static` の分岐が CABLE_LENGTH 処理経路そのものを決定する。`platform` フィールドは Mellanox 環境での headroom 計算精度に直結。

### BUFFER_POOL テーブル (CONFIG_DB)

| 参照箇所 | 用途 | evidence |
|---|---|---|
| `buffermgr.cpp:27` — `m_cfgLosslessPgPoolTable(cfgDb, CFG_BUFFER_POOL_TABLE_NAME)` | `getPgPoolMode()` (buffermgr.cpp:115) が `ingress_lossless_pool` の `mode` フィールドを取得。CABLE_LENGTH → `doSpeedUpdateTask()` → `getPgPoolMode()` の順で呼ばれる | buffermgr.cpp:27,115-123 |
| `buffermgr.cpp:481` — `table_name == CFG_BUFFER_POOL_TABLE_NAME` → `doBufferTableTask()` | BUFFER_POOL 変更を APPL_DB に転送。static モードでは CABLE_LENGTH 変更後の PG プロファイルが参照する pool が BUFFER_POOL で定義される | buffermgr.cpp:481-485 |
| `buffermgrdyn.cpp:443` — `CFG_BUFFER_POOL_TABLE_NAME → handleBufferPoolTable` | dynamic モードで BUFFER_POOL の `size` / `mode` を受け取り、SHP (Shared Headroom Pool) サイズ計算へ反映。CABLE_LENGTH 由来の PG headroom と pool 残量の整合性チェックに使用 | buffermgrdyn.cpp:443,2509-2670 |

**暗黙参照の性質**: CABLE_LENGTH から計算された headroom が実際に確保できるかどうかは BUFFER_POOL のサイズ上限に依存する。`allocateProfile()` は pool を参照して `BUFFER_PROFILE` に `pool` フィールドを設定する。

### BUFFER_PROFILE テーブル (CONFIG_DB)

| 参照箇所 | 用途 | evidence |
|---|---|---|
| `buffermgr.cpp:25` — `m_cfgBufferProfileTable(cfgDb, CFG_BUFFER_PROFILE_TABLE_NAME)` | static モードで `headroom override` プロファイルを CONFIG_DB から読み込む。CABLE_LENGTH 変更時に既存の手動設定 BUFFER_PROFILE を上書きしないよう参照する | buffermgr.cpp:25,487-492 |
| `buffermgr.cpp:248` — `// Create record in BUFFER_PROFILE table` | `doSpeedUpdateTask()` が cable_length + speed から PG プロファイル名 (`pg_lossless_<speed>_<cable>_profile`) を決定し、CONFIG_DB の BUFFER_PROFILE に書き込む | buffermgr.cpp:248 |
| `buffermgrdyn.cpp:444` — `CFG_BUFFER_PROFILE_TABLE_NAME → handleBufferProfileTable` | dynamic モードでユーザ定義の headroom override プロファイルを管理。CABLE_LENGTH 更新時に、dynamic 計算プロファイルと override プロファイルのどちらを使うか照合する | buffermgrdyn.cpp:444,2671-2860 |
| `buffermgrdyn.cpp:964-1001` — `allocateProfile()` | CABLE_LENGTH + speed + mtu + threshold から `pg_lossless_<speed>_<cable>_<mtu>_profile` を生成し APPL_DB.BUFFER_PROFILE に書き込む。BUFFER_POOL の `pool` 名を参照して profile に埋め込む | buffermgrdyn.cpp:964-1001 |

**暗黙参照の性質**: CABLE_LENGTH 更新のたびに BUFFER_PROFILE の自動生成・更新・削除が発生する。既存の手動設定プロファイルは CONFIG_DB.BUFFER_PROFILE から読み込んで照合し、dynamic 自動生成と重複しないよう管理される。

## 参照テーブル一覧サマリ

| テーブル | 参照元ファイル | 参照タイミング | 参照フィールド | 種別 |
|---|---|---|---|---|
| `PORT` | buffermgr.cpp, buffermgrdyn.cpp | CABLE_LENGTH 更新後の headroom 計算トリガ | `speed`, `mtu`, `admin_status`, `lanes`, `autoneg` | 必須前提条件 |
| `DEVICE_METADATA` | buffermgr.cpp, buffermgrdyn.cpp | 初期化時 / DEVICE_METADATA 更新時 | `buffer_model`, `platform` | 処理経路分岐 |
| `BUFFER_POOL` | buffermgr.cpp, buffermgrdyn.cpp | headroom 確保可否チェック / pool mode 取得 | `mode`, `size` | 制約チェック |
| `BUFFER_PROFILE` | buffermgr.cpp, buffermgrdyn.cpp | headroom override 照合 / profile 自動生成 | `pool`, `xon`, `xoff`, `size`, `dynamic_th` | 読み書き双方向 |
