# DPB (BREAKOUT_CFG) — Phase D failure-behavior 調査メモ

## 調査対象

- `sonic-net/sonic-utilities` : `config/main.py`, `config/config_mgmt.py`
- `sonic-net/sonic-buildimage` : `src/sonic-config-engine/portconfig.py`

## 失敗シナリオと CONFIG_DB / BREAKOUT_CFG への影響

### シナリオ 1: BREAKOUT_CFG テーブル不在

`main.py:5479-5482`: `config_db.get_table('BREAKOUT_CFG')` が空を返した場合、
`[ERROR] BREAKOUT_CFG table is NOT present in CONFIG DB` を表示して `raise click.Abort()`。
CONFIG_DB は一切変更されない。

### シナリオ 2: 対象ポートが BREAKOUT_CFG に不在

`main.py:5484-5486`: `interface_name not in cur_brkout_dict.keys()` の場合、
`[ERROR] {interface} interface is NOT present in BREAKOUT_CFG table of CONFIG DB` で Abort。
CONFIG_DB 変更なし。

### シナリオ 3: 依存テーブルが存在 (force なし)

`config_mgmt.py:497-499`: `_deletePorts()` が依存を検出し `force=False` の場合、
`return configToLoad, deps, False` で失敗。`breakOutPort()` が `return deps, ret` して
`breakout_Ports()` が `sys.exit(1)` する。CONFIG_DB は変更されない（メモリ操作のみで失敗）。

### シナリオ 4: _deletePorts() 例外

`config_mgmt.py:525-529`: YANG ツリー操作中に例外が発生した場合、
`return configToLoad, deps, False` で失敗。CONFIG_DB は変更されない（まだ writeConfigDB 前）。

### シナリオ 5: _verifyAsicDB タイムアウト（60 秒）

`config_mgmt.py:377-410`: syncd/orchagent の応答遅延で 60 秒待機後に
`raise Exception("Ports are present in ASIC DB after 60 secs")`。
この時点では:
- `_shutdownIntf()` 実行済み（PORT.admin_status=down が CONFIG_DB に書き込まれている）
- `writeConfigDB(delConfigToLoad)` 実行済み（旧ポートが CONFIG_DB から削除済み）
- `writeConfigDB(addConfigtoLoad)` は未実行（新ポートは CONFIG_DB に存在しない）
- `BREAKOUT_CFG.brkout_mode` は未更新（旧モードのまま）

**→ 部分的な CONFIG_DB 不整合状態**: 旧ポートが削除され新ポートが追加されていない半端な状態が
残る。BREAKOUT_CFG は旧モードを保持する。手動リカバリが必要。

### シナリオ 6: _addPorts() 失敗

`config_mgmt.py:438-443`: `_addPorts()` が False を返した場合、`return None, ret`。
ただしこの時点では `_shutdownIntf()` と `writeConfigDB(delConfigToLoad)` は未実行のため
CONFIG_DB 変更なし（シナリオ 4 同様の早期失敗）。

### シナリオ 7: BREAKOUT_CFG 更新時エラー

`main.py:5553-5556`: `config_db.set_entry("BREAKOUT_CFG", ...)` で `ValueError` の場合、
`ctx.fail("Invalid ConfigDB. Error: ...")` を表示して終了。
この時点では PORT 再構成は完了済みのため、CONFIG_DB と BREAKOUT_CFG の不整合が残る。
（新モードで動作しているが BREAKOUT_CFG は旧モード表示のまま）

## evidence ファイルリスト

- `sonic-utilities/config/main.py`: L5479-5486, L5544-5556
- `sonic-utilities/config/config_mgmt.py`: L377-412, L432-466, L468-531, L533-600
