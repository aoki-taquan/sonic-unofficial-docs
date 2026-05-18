# BREAKOUT_CFG (DPB) — Phase B 書込み順依存スキャンノート

対象テーブル: `BREAKOUT_CFG`
Consumer: `config interface breakout` CLI (`sonic-utilities/config/main.py`) → `ConfigMgmtDPB` (`config/config_mgmt.py`)
スキャン範囲: `breakout()` CLI コマンド, `ConfigMgmtDPB.breakOutPort()`, `_deletePorts()`, `_addPorts()`, `_shutdownIntf()`, `_verifyAsicDB()`, `dvs_port.py:remove_port()` 全行精読

---

## 検出した順序依存・タイミング依存

### 1. BREAKOUT_CFG が PORT より先行必須（読込フェーズ）

`breakout()` (main.py:5479) は breakout コマンド実行直後に `config_db.get_table('BREAKOUT_CFG')` を呼ぶ。テーブルが空の場合は即 Abort する。

- `BREAKOUT_CFG` エントリは起動時に `sonic-cfggen` が `hwsku.json` の `default_brkout_mode` を元に書き込む（portconfig.py:parse_breakout_mode）。
- **順序依存**: `BREAKOUT_CFG` が CONFIG_DB に存在しない場合、`config interface breakout` コマンドは「`[ERROR] BREAKOUT_CFG table is NOT present in CONFIG DB`」を返して失敗する（main.py:5481）。
- `PORT` テーブルの存在に先行して `BREAKOUT_CFG` の整合性が確認される。
- evidence: `main.py:5479-5486`, `portconfig.py:37-38,475-478`, `sonic-cfggen:402-404`

### 2. port 削除フェーズ（CONFIG_DB書込み）の前に依存テーブルが先に削除される

`ConfigMgmtDPB.breakOutPort()` (config_mgmt.py:414) の内部シーケンス:

1. `_deletePorts()` — Yang ツリーで依存テーブル（VLAN_MEMBER, ACL_TABLE, BUFFER_PG, BUFFER_QUEUE, INTERFACE, CABLE_LENGTH 等）を検出・削除しメモリ上で configDiff を生成
2. `_shutdownIntf()` — 削除対象ポートを `admin_status: down` に設定（CONFIG_DB に書込み）
3. `writeConfigDB(delConfigToLoad)` — ポートと依存設定を CONFIG_DB から削除
4. `_verifyAsicDB()` — ASIC_DB でポート削除完了を確認（最大 60 秒ポーリング）
5. `writeConfigDB(addConfigtoLoad)` — 新ポートを CONFIG_DB に追加

**強制順序**: 依存テーブル削除 → ポート shutdown → ポート CONFIG_DB 削除 → ASIC_DB 確認 → 新ポート CONFIG_DB 追加。いずれかのステップが失敗すると後続は実行されない。
- evidence: `config_mgmt.py:450-460`

### 3. ASIC_DB ポート削除確認（_verifyAsicDB）が新ポート追加の先行条件

`_verifyAsicDB()` (config_mgmt.py:377) は削除対象ポートが ASIC_DB から消えるまで最大 60 秒待機する。タイムアウトした場合は例外を投げて新ポートの CONFIG_DB 書込みは行われない。

- **順序依存**: `orchagent`（`portsorch`）が CONFIG_DB の PORT DEL を処理して SAI 経由で ASIC からポートを削除し、結果を ASIC_DB に反映するまで、新ポートは CONFIG_DB に書き込まれない。
- この待機なしに新ポートを書くと、旧ポートの OID が ASIC に残ったまま同レーンへの再割当が起きる可能性がある。
- evidence: `config_mgmt.py:377-412`, `config_mgmt.py:458-460`

### 4. CABLE_LENGTH / BUFFER_PG / BUFFER_QUEUE の事前削除

DPB テストコード `dvs_port.py:remove_port()` (dvs_port.py:55-68) は以下の順序でポートを削除する:

```
DEL CABLE_LENGTH|AZURE|<port>
DEL BUFFER_PG|<port>|*
DEL BUFFER_QUEUE|<port>|*
DEL BREAKOUT_CFG|<port>
DEL INTERFACE|<port>
DEL PORT|<port>
```

`--force-remove-dependencies` オプション有効時は CLI が Yang ツリー経由でこれらを自動削除するが、手動操作や直接 DB 書込みの場合は**この順序で依存テーブルを先に DEL しなければ YANG バリデーションエラー**が発生する。
- evidence: `dvs_port.py:55-68`, `config_mgmt.py:503-514`

### 5. BREAKOUT_CFG の最終更新は PORT 再構成後（書込み順の末尾）

`breakout()` (main.py:5548-5554) は `breakout_Ports()` が成功した後に限り `config_db.set_entry("BREAKOUT_CFG", interface_name, {'brkout_mode': target_brkout_mode})` を呼ぶ。

- **順序依存**: `BREAKOUT_CFG` の `brkout_mode` 更新は PORT テーブル再構成と ASIC_DB 確認の**後**。失敗時は `BREAKOUT_CFG` は旧モードを保持したままになり、次回 `breakout` コマンドは旧モードを起点として差分計算する。
- evidence: `main.py:5548-5556`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | `BREAKOUT_CFG` エントリ存在確認 → `PORT` 操作 | 先行必須 | 起動時 `sonic-cfggen` が自動生成。手動投入時は `BREAKOUT_CFG` を先に書く |
| 2 | 依存テーブル削除 → ポート shutdown → CONFIG_DB 削除 | 強制順序 (`ConfigMgmtDPB`) | `--force-remove-dependencies` で自動。手動時は依存テーブルを先に DEL |
| 3 | ASIC_DB ポート削除確認 → 新ポート CONFIG_DB 追加 | 強制先行 (最大 60 秒待機) | タイムアウト時は中断。syncd / orchagent の応答性に依存 |
| 4 | `CABLE_LENGTH` / `BUFFER_PG` / `BUFFER_QUEUE` DEL → `PORT` DEL | 推奨先行（YANG 依存） | `--force` で自動削除。なければ YANG バリデーションエラー |
| 5 | PORT 再構成 + ASIC_DB 確認 → `BREAKOUT_CFG` brkout_mode 更新 | 強制後続（成功時のみ更新） | 失敗時は旧モード保持のまま。再実行可能 |
