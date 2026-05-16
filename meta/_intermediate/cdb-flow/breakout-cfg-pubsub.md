# BREAKOUT_CFG テーブル — 通信メカニズム (Phase G) 解析メモ

対象: `CONFIG_DB` の `BREAKOUT_CFG` テーブル。Dynamic Port Breakout (DPB) における CLI 起動経路と PORT 変更を契機とした orchagent 連鎖を記録する。

## 1. BREAKOUT_CFG の直接 Subscribe 者: なし

`BREAKOUT_CFG` テーブルを直接 Subscribe するデーモンは存在しない。
`grep -r "BREAKOUT_CFG" sonic-swss/orchagent/` でヒットなし（`portsorch.cpp` 含む）。

CONFIG_DB の `BREAKOUT_CFG` は **CLI が読み書きするだけ** で、ランタイムデーモンが keyspace 通知をポーリングする設計ではない。

## 2. CLI 起動経路（Producer ロール）

```
operator
  → config interface breakout <port> <mode>
      sonic-utilities/config/main.py L5465 (interface_breakout())
        ↓ CONFIG_DB.get_table('BREAKOUT_CFG')     # L5479 — 現状 mode 読み取り
        ↓ _validate_interface_mode()               # L5491 — platform.json との照合
        ↓ ConfigMgmt.breakOutPort()               # L5544 — config_mgmt.py L451
            ↓ _shutdownIntf(delPorts)             # admin_status: down
            ↓ writeConfigDB(delConfigToLoad)      # PORT エントリ削除 → CONFIG_DB
            ↓ _verifyAsicDB(timeout=60s)          # ASIC_DB ポーリング確認
            ↓ writeConfigDB(addConfigToLoad)      # PORT エントリ追加 → CONFIG_DB
        ↓ CONFIG_DB.set_entry("BREAKOUT_CFG", port, {'brkout_mode': mode})  # L5554
```

- `writeConfigDB()` は内部で `ConfigDBConnector.set_entry()` → Redis `HSET` を呼ぶ。
- `BREAKOUT_CFG` への書き込みは **PORT 再構成成功後のみ**（失敗時は旧値を保持）。

## 3. PORT 変更を契機とした orchagent 連鎖（間接 Subscribe）

CLI が `PORT` テーブルを変更すると以下の Subscribe チェーンが起動する:

### 3-1. portsyncd → APPL_DB[APP_PORT_TABLE_NAME]

```
CONFIG_DB[PORT|*]
  → portsyncd (sonic-swss/portsyncd/portsyncd.cpp L91,179-214)
      handlePortConfigFromConfigDB()
        Table cfgDb(CFG_PORT_TABLE_NAME).getKeys()
        ProducerStateTable p(&appl_db, APP_PORT_TABLE_NAME).set(k, attrs)  # L207
        notifyPortConfigDone() → p.set("PortConfigDone", ...)               # L176
```

- `portsyncd` は CONFIG_DB[PORT] を **起動時一括読み取り**し、APPL_DB[PORT_TABLE] へ ProducerStateTable で転送する。
- DPB の `writeConfigDB()` 呼び出し後、`portsyncd` は PORT エントリの追加・削除を APPL_DB へ反映する。

### 3-2. PortsOrch (orchagent) — APPL_DB[APP_PORT_TABLE_NAME] 消費

```
APPL_DB[APP_PORT_TABLE_NAME]
  → PortsOrch (sonic-swss/orchagent/portsorch.cpp)
      コンストラクタ: Orch(db, tableNames)  # L723-724
        tableNames = {APP_PORT_TABLE_NAME, portsorch_base_pri+5}  # orchdaemon.cpp L218
      orchdaemon select() loop (orchdaemon.cpp L500)
        Consumer::drain() → PortsOrch::doPortTask()  # portsorch.cpp L4555
          key == "PortConfigDone" → setPortConfigState(PORT_CONFIG_RECEIVED)  # L4598
          key == "PortInitDone"   → PORT_CONFIG_DONE 状態へ移行               # L4617
          通常 PORT エントリ → addPortBulk() / removePortBulk()               # L4744,4762
            gBufferOrch->isPortReady(pCfg.key) チェック                       # L4779
```

`PortsOrch` は `ConsumerStateTable` ではなく `Orch(db, tableNames)` 基底クラスの `addConsumer()` が生成する `ConsumerStateTable(APPL_DB, APP_PORT_TABLE_NAME)` で APPL_DB を購読する（`orch.cpp` の標準 wiring）。

### 3-3. BufferOrch — PORT 準備判定（gBufferOrch->isPortReady）

```
PortsOrch::doPortTask()
  → gBufferOrch->isPortReady(port_name)  # portsorch.cpp L4779
      bufferorch.cpp L254-273
        m_port_ready_list_ref に port_name があれば m_ready_list を確認
        BUFFER_PG / BUFFER_QUEUE エントリが揃うと true を返す
```

- DPB で新ポートが追加された場合、`isPortReady()` が `true` になるまで `doPortTask()` はそのポートを `m_pendingPortSet` に保留する（L4779-4784）。
- `platform.json` 由来の BUFFER_PG / BUFFER_QUEUE が CONFIG_DB に書き込まれ BufferOrch が処理完了してから、portsorch が新ポートの SAI 登録を行う。

### 3-4. SAI 呼び出し（PortsOrch → SAI）

```
PortsOrch::addPortBulk()  # L1248
  → sai_port_api->create_port_bulk()  or
  → sai_port_api->create_port()
      SAI_PORT_ATTR_HW_LANE_LIST, SAI_PORT_ATTR_SPEED, ...
      (削除時: sai_port_api->remove_port())
```

## 4. Subscribe パターンまとめ

| 区間 | 方式 | チャンネル |
|------|------|-----------|
| CLI → CONFIG_DB[BREAKOUT_CFG] | Redis `HSET` (直接書き込み) | — |
| CLI → CONFIG_DB[PORT] | Redis `HSET` (`writeConfigDB`) | — |
| CONFIG_DB[PORT] → portsyncd | 起動時一括読み取り (getKeys) | — |
| portsyncd → APPL_DB[PORT_TABLE] | `ProducerStateTable::set()` | APPL_DB channel |
| APPL_DB[PORT_TABLE] → PortsOrch | `ConsumerStateTable` (keyspace) | `__keyspace@appl_db__:PORT_TABLE\|*` |
| PortsOrch → BufferOrch | 関数呼び出し `gBufferOrch->isPortReady()` | — |
| PortsOrch → SAI | SAI API 直接呼び出し | — |

**BREAKOUT_CFG を直接 Subscribe するデーモンは存在しない。** CONFIG_DB[PORT] の増減が間接トリガーとなって portsyncd → portsorch → bufferorch → SAI の連鎖が起動する。

## 5. APPL_DB / STATE_DB 書き込み有無

| DB | 書き込み | 備考 |
|----|---------|------|
| APPL_DB[PORT_TABLE] | **あり** (portsyncd 経由) | portsorch が消費 |
| STATE_DB[PORT_TABLE] | **あり** (portsorch 経由) | `m_portStateTable` (`portsorch.cpp L725`) |
| APPL_DB[BREAKOUT_CFG] | なし | BREAKOUT_CFG は APPL_DB に存在しない |

## 6. keyspace 通知パターン（PortsOrch 視点）

| Redis 通知 | PortsOrch 受信 |
|-----------|---------------|
| `__keyspace@appl_db_id__:PORT_TABLE\|Ethernet0` `hset` | `doPortTask()` で SET イベント処理 |
| `__keyspace@appl_db_id__:PORT_TABLE\|Ethernet0` `del` | `doPortTask()` で DEL イベント（removePortBulk） |
| `__keyspace@appl_db_id__:PORT_TABLE\|PortConfigDone` `hset` | `setPortConfigState(PORT_CONFIG_RECEIVED)` |
| `__keyspace@appl_db_id__:PORT_TABLE\|PortInitDone` `hset` | PORT_CONFIG_DONE 状態へ移行 |

## 7. 参考行番号

- `sonic-utilities/config/main.py`: L5465-5554 (`interface_breakout` 全体)
- `sonic-swss/portsyncd/portsyncd.cpp`: L71, L91, L176-177, L179-214
- `sonic-swss/orchagent/orchdaemon.cpp`: L217-232 (`ports_tables` / `PortsOrch` 生成)
- `sonic-swss/orchagent/portsorch.cpp`: L723-724 (コンストラクタ), L4555-4604 (`doPortTask`), L4779-4788 (`isPortReady` チェック), L1248 (`addPortBulk`)
- `sonic-swss/orchagent/bufferorch.cpp`: L254-273 (`isPortReady`)
