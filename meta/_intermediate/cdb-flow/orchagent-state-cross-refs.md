# orchagent-state — Phase C 調査証跡 (cross-table refs)

調査日: 2026-05-18  
調査対象: sonic-swss orchagent/orchdaemon.cpp, main.cpp, portsorch.cpp, fdborch.cpp, vrforch.cpp, macsecpost.cpp, sonic-swss-common/common/warm_restart.cpp

## 概要

orchagent が STATE_DB へ書き込む 5 テーブル（WARM_RESTART_TABLE / PORT_TABLE / FDB_TABLE / VRF_OBJECT_TABLE / FIPS_MACSEC_POST_TABLE）はそれぞれ異なる上流 DB を購読・参照して書き込みを行う。本ページはその暗黙的なテーブル間依存を列挙する。

## 調査ポイント別メモ

### WARM_RESTART_TABLE

- `WarmStart::checkWarmStart()` は `WARM_RESTART_TABLE|orchagent.restart_count` を自 DB から読み取ってインクリメントする（warm_restart.cpp:113-125）
- `WarmStart::setWarmStartState()` / `setDataCheckState()` は同テーブルに対する書き込み専用 API（warm_restart.cpp:223-254）
- 実質的に **自己参照**（STATE_DB 内の読み取り → 書き込み）のみ

### PORT_TABLE

- portsorch は APPL_DB の `APP_PORT_TABLE_NAME`（= "PORT_TABLE"）を購読し `PortInitDone` キーを検出して初期化完了を判定（portsorch.cpp:4613, 4350-4357）
- `PortInitDone` を portsyncd が APPL_DB に書いてから、portsorch が `initPortSupportedSpeeds/Fec()` / `initHostTxReadyState()` を経て STATE_DB `PORT_TABLE` に書く
- orchdaemon.cpp:218 で `{ APP_PORT_TABLE_NAME, portsorch_base_pri + 5 }` を Consumer 登録

### FDB_TABLE

- fdborch は APPL_DB の `APP_FDB_TABLE_NAME`（= "FDB_TABLE"）を購読（orchdaemon.cpp:227, fdborch.cpp:31-32）
- `FdbOrch::doTask()` は冒頭で `m_portsOrch->allPortsReady()` を確認し、false なら即リターン（fdborch.cpp:711, 927）
- よって STATE_DB FDB_TABLE への書き込みは APPL_DB PortInitDone + PORT_TABLE 初期化完了に **強制依存**

### VRF_OBJECT_TABLE

- vrforch は APPL_DB の `APP_VRF_TABLE_NAME`（= "VRF_TABLE"）を購読（orchdaemon.cpp:283）
- SAI `create_virtual_router` 成功後に `m_stateVrfObjectTable.hset(vrf_name, "state", "ok")` を書く（vrforch.cpp:120, 150）
- `vrfmgrd` は VRF 削除同期のために STATE_DB `VRF_OBJECT_TABLE` のエントリ消失を監視（依存方向: STATE_DB → vrfmgrd）

### FIPS_MACSEC_POST_TABLE

- orchagent `main()` が SAI switch 初期化後にMACsec POST 対応有無を SAI から取得して書き込む（main.cpp:791-793, 924）
- SAI コールバック `macsecorch.cpp:705/710/786/791` から `post_state` を更新
- CONFIG_DB / APPL_DB への明示的な依存なし。SAI の `SAI_SWITCH_ATTR_MACSEC_SUPPORTED` 取得結果に依存

### ASIC_DB (SAI 経由)

- PORT_TABLE, VRF_OBJECT_TABLE, FIPS_MACSEC_POST_TABLE はいずれも SAI 呼び出し結果を受けて書き込む
- ASIC_DB への直接購読はないが、syncd が SAI レスポンスを ASIC_DB 経由で返す構成

## 暗黙参照テーブル一覧

| 参照先 | DB | 方向 | STATE_DB テーブル | 根拠 |
|--------|-----|------|-------------------|------|
| `PORT_TABLE|PortInitDone` | APPL_DB | READ | PORT_TABLE, FDB_TABLE | portsorch.cpp:4350-4357, 4613 |
| `PORT_TABLE|PortConfigDone` | APPL_DB | READ | PORT_TABLE | portsorch.cpp:4357 |
| `FDB_TABLE|*` | APPL_DB | READ | FDB_TABLE | fdborch.cpp:31-32, orchdaemon.cpp:227 |
| `VRF_TABLE|*` | APPL_DB | READ | VRF_OBJECT_TABLE | vrforch.h:52, orchdaemon.cpp:283 |
| `WARM_RESTART_TABLE|orchagent` | STATE_DB | READ (自己) | WARM_RESTART_TABLE | warm_restart.cpp:113-125 |
| SAI `create_virtual_router` | SAI/ASIC | READ (SAI resp) | VRF_OBJECT_TABLE | vrforch.cpp:93, 120 |
| SAI `SAI_SWITCH_ATTR_MACSEC_SUPPORTED` | SAI/ASIC | READ (SAI resp) | FIPS_MACSEC_POST_TABLE | main.cpp:791-924 |
| SAI MACsec POST コールバック | SAI/ASIC | 非同期 | FIPS_MACSEC_POST_TABLE | macsecorch.cpp:705-791 |
