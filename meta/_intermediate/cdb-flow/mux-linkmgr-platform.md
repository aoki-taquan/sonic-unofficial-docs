# MUX_LINKMGR — Phase H: プラットフォーム差 (Active-Standby vs Active-Active / SmartSwitch DPU)

## 調査対象ソース

- `sonic-net/sonic-linkmgrd` (最新 HEAD)
- `src/DbInterface.cpp` — `processMuxLinkmgrConfigNotifiction()` (L1120–1215)
- `src/MuxManager.cpp` — `setUseWellKnownMacActiveActive()` / `updatePortCableType()` / `getMuxPortPtrOrThrow()` / `processSrcMac()` / `addOrUpdateMuxPort()` / `addOrUpdateMuxPortSoCAddress()`
- `src/MuxPort.cpp` — `handleProbeMuxState()` / `handleMuxConfig()` / `probeMuxState()`
- `src/common/MuxConfig.h` — `mUseWellKnownMacActiveActive` / `mEnableUseTorMac`
- `src/link_prober/LinkProberStateMachineActiveActive.h` / `LinkProberStateMachineActiveStandby.h`

## プラットフォーム識別方法

linkmgrd では ASIC ベンダー名（broadcom/mellanox 等）を参照しない。代わりに **ケーブルタイプ** (`PortCableType`) でプラットフォームプロファイルを分岐する。

`MuxManager::updatePortCableType()` (`MuxManager.cpp:245`) が `MUX_CABLE` テーブルの `cable_type` フィールドを読み取り `PortCableType` を決定する:

```
cableType == "active-standby"  →  PortCableType::ActiveStandby  (DualToR 標準)
cableType == "active-active"   →  PortCableType::ActiveActive   (Y-cable Active-Active)
それ以外                        →  ActiveStandby にフォールバック (ログ: MUXLOGERROR)
```

SmartSwitch DPU 環境については linkmgrd の直接的な DPU 検出コードは存在しない。DPU ポートは `MUX_CABLE` に登録されず、linkmgrd 自体が対象外となる（`docker-mux` は DualToR 専用デーモン）。

## 差異 1: StateMachine の種別 (PortCableType による分岐)

`MuxPort::MuxPort()` コンストラクタ (`MuxPort.cpp:60-90`) で `PortCableType` に応じて異なる StateMachine インスタンスを生成する:

| PortCableType | StateMachine | ICMP Prober クラス |
|--------------|--------------|-------------------|
| `ActiveActive` | `link_manager::ActiveActiveStateMachine` | `LinkProberStateMachineActiveActive` |
| `ActiveStandby` | `link_manager::ActiveStandbyStateMachine` | `LinkProberStateMachineActiveStandby` |

- **Active-Standby**: ToR が排他的にアクティブ。peer ToR がスタンバイ。Timed Oscillation でアクティブ ToR を定期切替。
- **Active-Active**: 両 ToR が同時にアクティブ（各ポート独立）。NiC (Y-cable SmartNiC) が内部でトラフィックを振り分ける。障害時は `failure` 状態遷移あり (`MuxPort.cpp:304`)。

## 差異 2: `use_well_known_mac` フィールドの有効性

`DbInterface.cpp:1142-1143`:
```cpp
} else if (f == "use_well_known_mac") {
    mMuxManagerPtr->setUseWellKnownMacActiveActive(v == "enable");
```

| PortCableType | `use_well_known_mac` の効果 |
|--------------|---------------------------|
| **ActiveActive** | `MuxConfig::mUseWellKnownMacActiveActive` を設定。ポート初期化時に well-known MAC を server MAC として使用するか制御 (`MuxManager.cpp:505`) |
| **ActiveStandby** | `setUseWellKnownMacActiveActive()` は呼ばれるが `getMuxPortPtrOrThrow()` 内の分岐 (`MuxManager.cpp:501`) が `ActiveActive` 専用のため実質無効 |

- **注意**: YANG enum は `enabled`/`disabled` だが、コードは `v == "enable"` で比較（末尾 `d` 不一致）。ActiveActive 環境でも YANG どおり `enabled` を書くと常に `false` として扱われる（実装バグ）。

## 差異 3: SoC IP アドレス処理

`MuxManager::addOrUpdateMuxPortSoCAddress()` (`MuxManager.cpp:208`):

| PortCableType | SoC IP 処理 |
|--------------|------------|
| **ActiveActive** | SoC (NiC/SmartNiC) の IPv4 アドレスを linkmgrd 内部に登録し、gRPC 疎通確認に使用 |
| **ActiveStandby** | 処理スキップ（`if (portCableType == ActiveActive)` ガードで弾かれる） |

`MuxManager::addOrUpdateMuxPort()` (`MuxManager.cpp:185`) では逆に:

| PortCableType | Blade/Server IP 処理 |
|--------------|---------------------|
| **ActiveStandby** | Server IPv4 アドレスを `handleBladeIpv4AddressUpdate()` で登録 (ICMP probe 宛先) |
| **ActiveActive** | スキップ（SoC IP を使うため Server IP は不要） |

## 差異 4: MUX 状態プローブ方法

`MuxPort::probeMuxState()` (`MuxPort.cpp:444`):

| PortCableType | プローブ手段 |
|--------------|------------|
| **ActiveActive** | `probeForwardingState()` — gRPC / xcvrd 経由でフォワーディング状態を照会 |
| **ActiveStandby** | `probeMuxState()` — i2c 経由で MUX ハードウェア状態を照会 |

- ActiveActive の `failure` 状態は gRPC 接続障害時に発生 (`MuxPort.cpp:304`)。ActiveStandby には `failure` 遷移なし。

## 差異 5: `detach` モードのサポート

`MuxPort::handleMuxConfig()` (`MuxPort.cpp:362-367`):

| PortCableType | `config=detach` |
|--------------|----------------|
| **ActiveActive** | `Detached` モードに遷移（両 ToR が passive となり NiC がスタンドアロン動作） |
| **ActiveStandby** | `detach` は非対応。MUXLOGWARNING を出して `return`（設定無視） |

## 差異 6: Link Failure Detection タイプ / Prober タイプ

`MuxManager::updateLinkFailureDetectionState()` / `updateProberType()` (`MuxManager.cpp:270-298`):

| PortCableType | 対応 |
|--------------|------|
| **ActiveActive** | `updateLinkFailureDetectionState()` / `updateProberType()` が実行される |
| **ActiveStandby** | 両関数は `if (portCableType == ActiveActive)` ガードで処理スキップ |

## 差異 7: TIMED_OSCILLATION の意味論的差異

`TIMED_OSCILLATION` container (`oscillation_enabled` / `interval_sec`) は linkmgrd の設定ハンドラで両タイプ共通に処理される (`DbInterface.cpp:1185-1213`)。ただし意味論が異なる:

| PortCableType | Timed Oscillation の意味 |
|--------------|------------------------|
| **ActiveStandby** | 定期的にアクティブ ToR を切り替えるタイマー機構。負荷分散・ウォームレジリエンス目的 |
| **ActiveActive** | 両 ToR が常時アクティブのため「切替」の概念がない。`oscillation_enabled=true` は設定可能だが効果は限定的（Active-Active StateMachine 内での扱いは別途実装依存） |

## 差異 8: SmartSwitch DPU との関係

linkmgrd は **DualToR 専用デーモン** であり、SmartSwitch DPU のポートは直接対象外:

- `docker-mux` (linkmgrd) は `feature: subtype=="DualToR"` 環境のみ起動。SmartSwitch (`subtype=="SmartSwitch"`) では起動しない。
- SmartSwitch の DPU ポートは `MUX_CABLE` テーブルに登録されず、`MUX_LINKMGR` テーブルも参照されない。
- ただし **Active-Active ケーブルタイプは SmartNiC (Y-cable) 搭載の DualToR で使用**されるものであり、DPU (SmartSwitch の Data Processing Unit) とは別概念である点に注意。

## スキャン証跡

| ファイル | 確認箇所 |
|---------|---------|
| `src/DbInterface.cpp` | L1120–1215 `processMuxLinkmgrConfigNotifiction()` 全行 |
| `src/MuxManager.cpp` | L60–68 `setUseWellKnownMacActiveActive()`, L185–222 `addOrUpdateMuxPort*`, L245–262 `updatePortCableType()`, L270–298 `updateLinkFailureDetectionState/updateProberType()`, L470–523 `getMuxPortCableType/getMuxPortPtrOrThrow()` |
| `src/MuxPort.cpp` | L60–90 コンストラクタ, L295–319 `handleProbeMuxState()`, L351–368 `handleMuxConfig()`, L440–456 `probeMuxState()` |
| `src/common/MuxConfig.h` | L487–510 メンバ初期化子確認 |
