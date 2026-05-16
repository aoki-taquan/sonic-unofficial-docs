# BREAKOUT_CFG — Phase B 書込み順依存スキャンノート

対象テーブル: `BREAKOUT_CFG`
Consumer: `ConfigMgmt.breakOutPort()` (`sonic-utilities/config/config_mgmt.py`)、`PortsOrch` (`sonic-swss/orchagent/portsorch.cpp`)
スキャン範囲: `config_mgmt.py` `breakOutPort()` / `_deletePorts()` / `_addPorts()` / `_shutdownIntf()` / `_verifyAsicDB()` 全行精読、`portsorch.cpp` PORT_CONFIG_RECEIVED 処理 / `onWarmBootEnd()` / `m_isWarmRestoreStage` フロー、`config/main.py` `breakout()` CLI handler 全行精読

---

## 検出した順序依存・タイミング依存

### 1. PORT shutdown → ASIC DB 削除確認 → PORT 再作成（3 フェーズ厳守）

- `ConfigMgmt.breakOutPort()` (config_mgmt.py L414-462) は以下の順序で処理を実行する:
  1. `_shutdownIntf(delPorts)` — 削除対象ポートに `admin_status: down` を CONFIG_DB へ書き込む
  2. `writeConfigDB(delConfigToLoad)` — ポート削除設定を CONFIG_DB へ書き込む
  3. `_verifyAsicDB(ports=delPorts, timeout=MAX_WAIT=60)` — ASIC DB からポートが消えるまで最大 60 秒ポーリング
  4. `writeConfigDB(addConfigtoLoad)` — 新ポートの追加設定を CONFIG_DB へ書き込む
- **順序依存**: ステップ 1（shutdown）をスキップして削除すると、ポートがトラフィックを転送中に SAI レベルで削除が試みられ、ASIC エラーになる。ステップ 3（ASIC DB 確認）の前にステップ 4（追加）を実行すると、レーン競合により新ポート生成が失敗する。
- evidence: `config_mgmt.py L451-460`

### 2. 依存テーブル（VLAN_MEMBER / ACL / BUFFER / QUEUE）の削除順序

- `_deletePorts()` (config_mgmt.py L466-530) は YANG データツリー上でポートの xpath 依存を解析し、依存ノード（VLAN_MEMBER、ACL_TABLE ポートリスト等）を**ポート削除前に先に削除**する (`sy.deleteNode(dep)` → `sy.deleteNode(port)` の順序)。
- `--force-remove-dependencies` フラグが指定された場合のみ依存を強制削除する。未指定の場合は依存が存在すると処理中断し、依存一覧を出力する。
- `port_breakout_config_db.json` (`/etc/sonic/port_breakout_config_db.json`) に定義されたデフォルト設定には **ACL_TABLE**（`DPB_ACL_TBL_1`、`DPB_ACL_TBL_2`）と **VLAN_MEMBER** が含まれ、breakout 後に `_addPorts()` → `_mergeConfigs()` で自動再注入される。
- **順序依存**: VLAN_MEMBER・ACL テーブルの ACL ポートリストは、PORT 削除**前**にクリアされなければ YANG バリデーション失敗になる。新ポート生成後の再注入（`_mergeConfigs`）は PORT 追加が ASIC DB に反映された後でないと ACL/VLAN 設定が実ポートに紐付かない。
- evidence: `config_mgmt.py L480-520`, `port_breakout_config_db.json`（`sonic-buildimage/platform/vs/docker-sonic-vs/`）

### 3. buffer 設定が完了するまでポート処理が保留（portsorch 側）

- `portsorch.cpp L4779-4788`: PORT テーブルの doTask 処理中に `gBufferOrch->isPortReady(pCfg.key)` を確認し、buffer 設定未完了のポートは `m_pendingPortSet` に積んで次サイクルまでリトライを保留する。
- `m_initDone && m_pendingPortSet.empty()` が `true` になるまで `allPortsReady()` は `false` を返す (portsorch.cpp L1687)。
- **順序依存**: breakout で新ポートを PORT テーブルへ追加する場合、対応する `BUFFER_PG`・`BUFFER_QUEUE` 設定が CONFIG_DB に書き込まれるまで orchagent 側でポートが「準備完了」と見なされない。buffer 設定を後から追加すると、その間 PORT は pending 状態のままになる。
- evidence: `portsorch.cpp L4779-4788`, `portsorch.cpp L1687`

### 4. warm reboot 時の postPortInit スキップと onWarmBootEnd() 完了待ち

- `m_isWarmRestoreStage` フラグ (portsorch.cpp L753) が `true`（warm reboot 中）の場合、`initPortsBulk()` 内で `postPortInit()` が**スキップ**される (portsorch.cpp L4076-4078)。
- `postPortInit()` には SAI カウンタ登録、serdes 設定、FEC 設定など PORT 有効化に必要な後処理が含まれる。
- `onWarmBootEnd()` (portsorch.cpp L6424-6440) が呼ばれて `m_isWarmRestoreStage = false` になった後、`refreshPortStatus()` と全 PHY ポートへの `postPortInit()` が実行される。
- **順序依存**: warm reboot フロー中に breakout 変更を含む `config reload` を行う場合、`onWarmBootEnd()` が完了するまで新ポートの `postPortInit()` は走らない。warm reboot 完了前に breakout 設定変更を注入すると、ポートが partial init 状態（lane 割り当てのみ）で停留するリスクがある。warm reboot と breakout 変更は**同一リロードサイクルで同時実施しない**ことを推奨。
- evidence: `portsorch.cpp L753`, `portsorch.cpp L4076-4078`, `portsorch.cpp L6424-6440`

### 5. `loadDefConfig` による BUFFER / QUEUE カウンタの再注入タイミング

- `_addPorts(loadDefConfig=True)` (config_mgmt.py L533) は `_getDefaultConfig(ports)` で `/etc/sonic/port_breakout_config_db.json` から ACL/VLAN/INTERFACE 設定を取得し、`_mergeConfigs()` で新ポートの設定に合流させる (config_mgmt.py L553-572)。
- `--load-predefined-config` フラグが未指定の場合は `loadDefConfig=True` がデフォルト (config/main.py L5461)。
- **順序依存**: `port_breakout_config_db.json` が存在しない・空の場合、`_getDefaultConfig()` は空 dict を返すが例外を発生させないため、ACL/VLAN のデフォルト再注入がサイレントにスキップされる。その後、手動で ACL_TABLE / VLAN_MEMBER を再設定する必要がある。
- evidence: `config_mgmt.py L731-753`, `config/main.py L5461`

### 6. BREAKOUT_CFG への最終書き込みは PORT 再構成完了後

- `config/main.py` の `breakout()` CLI handler は `breakout_Ports()` 呼び出しが成功した**後に**（L5548 以降）`config_db.set_entry("BREAKOUT_CFG", interface_name, {'brkout_mode': target_brkout_mode})` を実行する (config/main.py L5553)。
- **順序依存**: `BREAKOUT_CFG` 自体はフローの**最後**に更新される。PORT テーブルの再構成失敗時は `BREAKOUT_CFG` は旧モードのまま残る。このため `BREAKOUT_CFG.brkout_mode` は「現在 ASIC で有効なモード」の信頼できる reflection となる（中間失敗が隠蔽されない）。
- **注意点**: `breakout_Ports()` が Exception で失敗した場合（portsorch タイムアウト等）、PORT テーブルが中途半端に再構成されても `BREAKOUT_CFG` は旧モードのまま残り、実 ASIC 状態と乖離する可能性がある。
- evidence: `config/main.py L5545-5553`

---

## 順序まとめ（推奨実施順）

```
1. VLAN_MEMBER / ACL_TABLE の依存ポートを事前に除去（または --force-remove-dependencies 使用）
2. PORT admin_status: down（_shutdownIntf が自動実施）
3. PORT テーブルから旧ポートエントリを削除（writeConfigDB delConfigToLoad）
4. ASIC DB でポート消滅を確認（_verifyAsicDB、最大 60 秒待機）
5. PORT テーブルへ新ポートエントリを追加（writeConfigDB addConfigtoLoad）
6. BUFFER_PG / BUFFER_QUEUE が CONFIG_DB に存在する → portsorch が isPortReady を解除
7. ACL_TABLE / VLAN_MEMBER を新ポートで再注入（loadDefConfig=True により自動）
8. BREAKOUT_CFG.brkout_mode を target_brkout_mode に更新（最後）
```

warm reboot 中は breakout 変更を行わない。onWarmBootEnd() 完了後に実施する。
