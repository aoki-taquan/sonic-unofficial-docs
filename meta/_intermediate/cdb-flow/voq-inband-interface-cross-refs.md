# VOQ_INBAND_INTERFACE — 暗黙参照調査 (Phase C)

調査対象:
- `sonic-swss/cfgmgr/intfmgr.cpp`
- `sonic-swss/cfgmgr/intfmgrd.cpp`
- `sonic-swss/cfgmgr/nbrmgr.cpp`
- `sonic-swss/orchagent/intfsorch.cpp`
- `sonic-swss/orchagent/portsorch.cpp`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-voq-inband-interface.yang`

調査日: 2026-05-18

## 依存関係一覧

### 1. DEVICE_METADATA.localhost.switch_type (VOQ ゲート)

- **参照元**: `intfmgrd` 起動時、`orchagent/main.cpp`
- **参照先**: `CONFIG_DB.DEVICE_METADATA.localhost.switch_type`
- **方向**: READ
- **内容**: `switch_type != "voq"` の場合、`orchagent` は VoQ 系処理全体をスキップする。`intfmgr.cpp` の VOQ_INBAND_INTERFACE パスも実質的に non-VOQ では無意味になる。
- **根拠**: `intfmgr.cpp:71-75` (mySwitchType), `orchagent/main.cpp`

### 2. VOQ_INBAND_INTERFACE → APP_INTF_TABLE (APPL_DB への relay)

- **参照元**: `intfmgrd` (intfmgr.cpp)
- **参照先**: `APPL_DB.APP_INTF_TABLE`
- **方向**: WRITE
- **内容**: 単一キー SET は `doIntfGeneralTask()` をバイパスし、`m_appIntfTableProducer.set()` で直接 APP_DB に relay する。`STATE_INTF_TABLE` にも `vrf=""` を即時書き込む。
- **根拠**: `intfmgr.cpp:1195-1204`

### 3. STATE_INTF_TABLE (intfmgr が書き込み、orchagent が参照)

- **参照元**: `intfmgr.cpp` (書き込み)、`intfsorch.cpp` (IP プレフィクス行の前提条件)
- **参照先**: `STATE_DB.STATE_INTF_TABLE`
- **方向**: READ/WRITE
- **内容**: `intfmgrd` が `vrf=""` を STATE_INTF_TABLE に書いた後、IP プレフィクス行 (2-key) の処理で `isIntfCreated()` が true になる。先に属性行 SET が必要。
- **根拠**: `intfmgr.cpp:1199-1200`, `intfmgr.cpp:1115`

### 4. portsorch::setVoqInbandIntf が参照するポートエントリ

- **参照元**: `orchagent/intfsorch.cpp` → `orchagent/portsorch.cpp`
- **参照先**: `portsorch` の内部ポートマップ (`getPort()`)
- **方向**: READ
- **内容**: `setVoqInbandIntf(alias, type)` は `getPort(alias, port)` でポートが存在することを確認する。ポートが未登録なら `false` を返しエントリをリトライキューに戻す。
- **根拠**: `portsorch.cpp:11121-11131`

### 5. nbrmgr が VOQ_INBAND_INTERFACE を参照 (neighbor 管理)

- **参照元**: `sonic-swss/cfgmgr/nbrmgr.cpp`
- **参照先**: `CONFIG_DB.VOQ_INBAND_INTERFACE`
- **方向**: READ
- **内容**: `nbrmgrd` は VOQ 環境 (`switch_type == "voq"`) のとき、`getVoqInbandInterfaceName()` で `VOQ_INBAND_INTERFACE` テーブルのキー一覧と `inband_type` フィールドを読み取り、リモートネイバーのカーネルルート追加に使用する。
- **根拠**: `nbrmgr.cpp:82`, `nbrmgr.cpp:524-549`

### 6. VOQ_INBAND_INTERFACE_IPPREFIX_LIST の leafref (YANG)

- **参照元**: `VOQ_INBAND_INTERFACE_IPPREFIX_LIST.name`
- **参照先**: `VOQ_INBAND_INTERFACE_LIST.name`
- **方向**: YANG leafref (READ 相当)
- **内容**: IP プレフィクス行の `name` (key) は `VOQ_INBAND_INTERFACE_LIST/name` への leafref。対応する属性行が存在しない場合 YANG バリデーションで reject。
- **根拠**: `sonic-voq-inband-interface.yang:48`
