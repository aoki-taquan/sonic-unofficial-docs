# device-metadata — Phase H: プラットフォーム差分 (switch_type / subtype / ASIC_VENDOR / sub_role 分岐)

## 調査目的

`DEVICE_METADATA|localhost` の以下フィールドが「どの ASIC ベンダ / スイッチタイプ / サブロールか」に応じて
挙動を変えるコードパスを網羅する。

- `switch_type` (`npu`/`voq`/`fabric`/`chassis-packet`/`dpu`/`dummy-sup`) — 既存セクションの補強
- `subtype` (`DualToR`/`SmartSwitch`/`Supervisor`/`UpstreamLC`/`DownstreamLC`) — 既存補強
- `ASIC_VENDOR` 変数 (= ビルド時 `sonic_asic_platform`: `mellanox`/`broadcom`/`barefoot`/`cisco-8000` 等)
- `sub_role` (`FrontEnd`/`BackEnd`/`Fabric`) — multi-ASIC chassisの ASIC ロール

## ASIC_VENDOR の伝搬経路

```
ビルド時: sonic_asic_platform 変数 (build/make/config.mk)
    ↓
docker_image_ctl.j2:792  -e ASIC_VENDOR={{ sonic_asic_platform }}  (swss コンテナのみ)
    ↓
docker-orchagent コンテナ環境変数 ASIC_VENDOR
    ↓
docker-init.j2:13  -a '{"ASIC_VENDOR":"${ASIC_VENDOR:-unknown}"}'  → sonic-cfggen に渡す
    ↓
ipinip.json.j2, switch.json.j2 など J2 テンプレートで参照可能
```

orchagent.sh 側では `ASIC_VENDOR` ではなく `asic_type` (swss_vars.j2:2 で出力) を
`platform` 変数として参照する。
- `platform = MLNX_PLATFORM_SUBSTRING ("mellanox")`
- `platform = BRCM_PLATFORM_SUBSTRING ("broadcom")`
- `platform = BFN_PLATFORM_SUBSTRING  ("barefoot")`
- `platform = CISCO_8000_PLATFORM_SUBSTRING ("cisco-8000")`
- `platform = MRVL_TL_PLATFORM_SUBSTRING / MRVL_PRST_PLATFORM_SUBSTRING / CLX_PLATFORM_SUBSTRING / NPS_PLATFORM_SUBSTRING`

定義: sonic-swss/orchagent/orch.h:42-48

## 分岐表

### 1. ASIC_VENDOR (ipinip.json.j2) — IPinIP DSCP モード

| 条件 | `dscp_mode` | evidence |
|------|-------------|---------|
| `ASIC_VENDOR` に `"broadcom"` を含む かつ `type == 'LeafRouter'` (is_broadcom_t1) | `"pipe"` | sonic-buildimage/dockers/docker-orchagent/ipinip.json.j2:12-13,98-100 |
| `ASIC_VENDOR` に `"broadcom"` を含む かつ LeafRouter 以外 | `"uniform"` | ipinip.json.j2:97-102 |
| `ASIC_VENDOR` が broadcom 以外 (Mellanox 等) | `"pipe"` + `decap_dscp_to_tc_map: "AZURE"` (AZURE QoS map 存在時) | ipinip.json.j2:103-108 |

### 2. platform (orchdaemon.cpp) — PFC Watchdog Handler の選択

| platform 値 | PfcWd Handler | portStatIds の差異 | evidence |
|-------------|--------------|-------------------|---------|
| `mellanox` / `vs` | `PfcWdZeroBufferHandler`, `PfcWdLossyHandler` | `SAI_PORT_STAT_PFC_*_RX_PAUSE_DURATION_US` (microsecond) | orchdaemon.cpp:635-672 |
| `marvell-teralynx` / `marvell-prestera` / `centec` / `barefoot` / `nephos` | `PfcWdZeroBufferHandler`/`PfcWdAclHandler` + `PfcWdLossyHandler` | `SAI_PORT_STAT_PFC_*_RX_PAUSE_DURATION` (無単位) | orchdaemon.cpp:674-731 |
| `broadcom` | `PfcWdDlrHandler` (pfcDlrInit=true 時) or `PfcWdAclHandler` + `PfcWdLossyHandler` | `SAI_PORT_STAT_PFC_*_ON2OFF_RX_PKTS` を追加 | orchdaemon.cpp:733-803 |
| `cisco-8000` | `PfcWdSwOrch` with Cisco-specific stat IDs | `SAI_PORT_STAT_PFC_*_RX_PKTS` のみ | orchdaemon.cpp:804-860 |
| その他 / 未設定 | PfcWd なし | — | orchdaemon.cpp:635-860 |

### 3. platform (orchdaemon.cpp) — DTel (Dataplane Telemetry) 初期化

| platform 値 | DTelOrch 初期化 | evidence |
|-------------|----------------|---------|
| `barefoot` / `vs` | `DTelOrch` を初期化 (`initialize_dtel = true`) | orchdaemon.cpp:503-524 |
| それ以外 | DTelOrch 不使用 | orchdaemon.cpp:503 |

### 4. subtype (orchdaemon.cpp) — SmartSwitch DashEniFwdOrch

| `subtype` 値 | 追加 Orch | evidence |
|-------------|----------|---------|
| `SmartSwitch` | `DashEniFwdOrch` を `m_orchList` に追加 | sonic-swss/orchagent/orchdaemon.cpp:613-618 |
| それ以外 | `DashEniFwdOrch` なし | — |

### 5. switch_type (orchdaemon.cpp) — FabricOrchDaemon vs OrchDaemon

| `switch_type` 値 | 起動する OrchDaemon クラス | evidence |
|----------------|--------------------------|---------|
| `fabric` | `FabricOrchDaemon` (orchdaemon.cpp:1283) — 通常の OrchDaemon とは別クラス | sonic-swss/orchagent/main.cpp:1009 |
| それ以外 | 通常 `OrchDaemon` | sonic-swss/orchagent/main.cpp:1002-1009 |

### 6. switch_type (orchagent.sh) — pop batch size

| `LOCALHOST_SWITCHTYPE` 値 | `-b` フラグ値 | evidence |
|--------------------------|-------------|---------|
| `chassis-packet` | `128` (リンク通知ルートチャーン用) | sonic-buildimage/dockers/docker-orchagent/orchagent.sh:23-25 |
| `dpu` | `65536` (大量オブジェクト対応) | orchagent.sh:26-28 |
| それ以外 | `1024` (デフォルト) | orchagent.sh:29-31 |

### 7. sub_role (startup_tsa_tsb.py) — TSA 設定スキップ

| `sub_role` 値 | 挙動 | evidence |
|-------------|------|---------|
| `FrontEnd` | multi-ASIC 構成時、TSA enabled かどうかを確認して TSA コマンドを実行 | sonic-buildimage/files/scripts/startup_tsa_tsb.py:53-56 |
| `BackEnd` / `Fabric` / その他 | multi-ASIC 時は TSA 設定をスキップ（FrontEnd のみカウント） | startup_tsa_tsb.py:53-57 |

### 8. sub_role (ipinip.json.j2) — loopback interface リスト選択

| `sub_role` 値 | loopback interface 集合 | evidence |
|-------------|----------------------|---------|
| `FrontEnd` または `BackEnd` | `['Loopback0', 'Loopback4096']` — chassis 内部通信用 Loopback4096 を含む | ipinip.json.j2:22-24 |
| それ以外 (npu 通常モード等) | `['Loopback0', 'Loopback2', 'Loopback3']` — 通常のルーティング loopback | ipinip.json.j2:25-26 |

### 9. switch_type + SWITCH_TYPE (docker-init.j2) — arp_update 起動条件

| 条件 | arp_update 起動 | evidence |
|------|----------------|---------|
| VLAN テーブルが存在する OR `SWITCH_TYPE == "chassis-packet"` | `arp_update.conf` を `/etc/supervisor/conf.d/` にコピー → 起動 | sonic-buildimage/dockers/docker-orchagent/docker-init.j2:38-40 |
| それ以外 | arp_update 不起動 | docker-init.j2:38-40 |

### 10. subtype (docker-init.j2) — tunnel_packet_handler 起動

| `subtype` 値 | 挙動 | evidence |
|-------------|------|---------|
| `DualToR` | `tunnel_packet_handler.conf` を `/etc/supervisor/conf.d/` にコピー → `tunnel_packet_handler.py` 起動 | sonic-buildimage/dockers/docker-orchagent/docker-init.j2:42-44 |
| それ以外 | tunnel_packet_handler 不起動 | docker-init.j2:42-44 |

### 11. switch_type + type (switch.json.j2) — SWITCH_TABLE hash seed / ordered_ecmp

| 条件 | SWITCH_TABLE パラメータ | evidence |
|------|-----------------------|---------|
| `switch_type != "dpu"` | `ecmp_hash_seed`, `lag_hash_seed`, `fdb_aging_time: 600` を設定 | switch.json.j2:35-38 |
| `switch_type == "dpu"` | 上記 3 フィールドを生成しない | switch.json.j2:35 |
| `switch_type != "chassis-packet"` かつ `switch_type != "dpu"` | `ecmp_hash_offset`, `lag_hash_offset` を設定 | switch.json.j2:39-41 |
| `type` に `"LeafRouter"` を含む | `ordered_ecmp: "true"` | switch.json.j2:44-46 |
| それ以外 | `ordered_ecmp: "false"` | switch.json.j2:47 |

## asic_id の動的更新 (SmartSwitch Chassis)

`docker-init.j2:53-67` で `IS_SUPERVISOR=/etc/sonic/chassisdb.conf` が存在する場合、
`CHASSIS_STATE_DB.CHASSIS_FABRIC_ASIC_TABLE|asic{N}` から PCI アドレスを取得し、
CONFIG_DB の `DEVICE_METADATA|localhost.asic_id` を `sonic-db-cli` 経由で動的に更新する。
これは `DEVICE_METADATA` への **runtime 書き込みが orchagent 自身以外から発生する** 唯一のケース。

evidence: sonic-buildimage/dockers/docker-orchagent/docker-init.j2:53-67

## swss_vars.j2 から orchagent へのプラットフォーム情報伝搬

swss_vars.j2 は CONFIG_DB の `DEVICE_METADATA.localhost` から以下を抽出し、JSON で orchagent.sh に渡す:

| JSON フィールド | 取得元 | orchagent での利用 |
|---------------|-------|-----------------|
| `asic_type` | ビルド時変数 `asic_type` | `platform` 変数 → orchdaemon.cpp PfcWd 分岐 |
| `asic_id` | `DEVICE_METADATA.localhost.asic_id` | `-i <asic_id>` フラグ |
| `synchronous_mode` | `DEVICE_METADATA.localhost.synchronous_mode` | `-s` フラグ (enable 時) |
| `switch_type` | `DEVICE_METADATA.localhost.switch_type` | `LOCALHOST_SWITCHTYPE` → `-b` バッチサイズ分岐 |
| `dual_tor` | `type == ToRRouter AND subtype == DualToR` | 将来利用 |

evidence: sonic-buildimage/files/build_templates/swss_vars.j2

## 12. switch_type 分岐: SAI スイッチ起動属性 (sonic-swss/orchagent/main.cpp)

`getCfgSwitchType()` (main.cpp:242) が `DEVICE_METADATA|localhost.switch_type` を読み出し `gMySwitchType` に設定する。未設定/不明な値は `"switch"` として扱う。

| `switch_type` | SAI 起動属性セット | 必須フィールド | evidence |
|--------------|-----------------|-------------|---------|
| `voq` | `SAI_SWITCH_ATTR_TYPE = SAI_SWITCH_TYPE_VOQ` + `SWITCH_ID` + `MAX_SYSTEM_CORES` + `SYSTEM_PORT_CONFIG_LIST` | `switch_id`, `max_cores`, `hostname`, `asic_name` | sonic-swss/orchagent/main.cpp:694-721 |
| `fabric` | `SAI_SWITCH_ATTR_TYPE = SAI_SWITCH_TYPE_FABRIC` + `SWITCH_ID`; MAC 設定スキップ | `switch_id` (未設定なら exit) | main.cpp:738-770 |
| `dpu` | `DpuOrchDaemon` + `DPU_APPL_DB` + `DPU_APPL_STATE_DB` 接続 | — | main.cpp:990-994 |
| `npu`/`switch`/未設定 | 通常 `OrchDaemon`; `SAI_SWITCH_ATTR_TYPE` 未設定 (SAI デフォルト = NPU) | — | main.cpp:997-999 |

### voq 起動時の必須フィールド検証 (main.cpp:305-363)

`getSystemPortConfigList()` が以下を順次検証; いずれかが不正なら voq SAI 作成をスキップ (orchagent 終了):
`switch_id` (≥0 整数) → `max_cores` (≥1) → `hostname` (非空) → `asic_name` (非空)

## 13. switch_type 分岐: SAI sync タイムアウト (main.cpp:809-848)

| `switch_type` | タイムアウト倍率 |
|--------------|--------------|
| `voq` / `chassis-packet` / `dpu` | × 5 |
| `fabric` | × 10 |
| `npu` / その他 | × 1 |

SWITCH 作成完了後にデフォルト値へ戻す。ASAN 有効時はさらに × 2。

## 14. buffer_model → BUFFER_POOL.mode → SAI 属性 (bufferorch.cpp:474-487)

| `BUFFER_POOL.mode` | SAI 属性値 | evidence |
|-------------------|-----------|---------|
| `"dynamic"` | `SAI_BUFFER_POOL_THRESHOLD_MODE_DYNAMIC` | bufferorch.cpp:474-476; bufferorch.h:22 |
| `"static"` | `SAI_BUFFER_POOL_THRESHOLD_MODE_STATIC` | bufferorch.cpp:478-480; bufferorch.h:23 |
| それ以外 | `task_invalid_entry` エラー | bufferorch.cpp:484 |

`mode` は create-only 属性のためプール作成後は変更不可 (bufferorch.cpp:469-471 でスキップ)。

## 15. platform 分岐: saihelper — INIT_VIEW 前後タイムアウト (saihelper.cpp:423-467)

| platform | INIT_VIEW 前 | INIT_VIEW 後 |
|----------|------------|------------|
| `mellanox` / `xsight` / `marvell-prestera` | 拡張値 (`SAI_REDIS_SYNC_OPERATION_RESPONSE_TIMEOUT`) | — |
| `mellanox` / `xsight` のみ | 上記 | デフォルト値に復元 |
| それ以外 | 変更なし | 変更なし |

## 注記

- `ASIC_VENDOR` は **ビルド時定数** で、CONFIG_DB フィールドではない。`DEVICE_METADATA` に `asic_vendor` フィールドは存在しない。ただし orchestration レイヤ（J2 テンプレート）で `DEVICE_METADATA.localhost` と組み合わせて分岐するため、実質的に `type`/`sub_role`/`switch_type` の補助変数として機能する。
- `platform` (asic_type) も同様にビルド時決定値であり、orchdaemon.cpp が `getenv("platform")` で参照する。
- `sub_role` は minigraph.py で `chassis_type` / `voq switch_type` / `card_type` から導出され (Phase 6 derivation 表参照)、CONFIG_DB に永続化された後、startup_tsa_tsb.py や ipinip.json.j2 で参照される。
- `switch_type = "voq"` 時は `switch_id`/`max_cores`/`hostname`/`asic_name` の 4 フィールドが実質必須 (未設定で orchagent 起動失敗)。
- `switch_type = "fabric"` 時は `switch_id` が必須 (main.cpp:763 で exit)。MAC アドレス設定は fabric では不要 (main.cpp:675)。
