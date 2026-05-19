# fabric-port — Phase H platform (intermediate)

slug: fabric-port
phase: platform
source: sonic-swss/orchagent/fabricportsorch.cpp, sonic-swss/orchagent/main.cpp, sonic-buildimage/src/sonic-config-engine/portconfig.py, sonic-buildimage/device/*/fabric_port_config.ini

## プラットフォーム依存性の概要

`FABRIC_PORT` テーブルのプラットフォーム依存は 3 つの経路で顕在化する:
1. `switch_type` (`voq` / `fabric`) による FabricPortsOrch の動作差
2. `fabric_port_config.ini` の列定義（`forceUnisolateStatus` 列の有無）
3. FlexCounter 収集フラグ（`fabricPortStatEnabled` / `fabricQueueStatEnabled`）の設定差

## switch_type による動作差

`gMySwitchType` は `DEVICE_METADATA.switch_type` から読み取られる。
- `voq`: OrchDaemon + FabricPortsOrch（fabricPortStatEnabled=true, fabricQueueStatEnabled=false）
- `fabric`: FabricOrchDaemon（fabricPortStatEnabled=true, fabricQueueStatEnabled=true がデフォルト）
- それ以外: FabricPortsOrch は起動しない

## 実機 fabric_port_config.ini 一覧

platforms 別ポート数と対応フィールド:
- Arista 7800R3 48CQM2 LC: Fabric0-111, lanes 0-111, isolateStatus + forceUnisolateStatus
- Arista 7800R3A 36D2 LC: Fabric0-191, lanes 0-191, isolateStatus + forceUnisolateStatus
- Nokia IXR7250E 36x400G: Fabric0-191, lanes 0-191, isolateStatus + forceUnisolateStatus
- SONiC-VM (virtual): Fabric0-16, lanes 0-16, isolateStatus のみ（forceUnisolateStatus 列なし）

evidence: portconfig.py:125-168, device/arista/*, device/nokia/*, device/virtual/*
