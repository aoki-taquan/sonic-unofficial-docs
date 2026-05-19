# gnmi-counter — プラットフォーム差異調査 (Phase H)

## 調査対象
- `sonic-net/sonic-gnmi` (master)
- `pkg/bypass/bypass.go`
- `pkg/interceptors/setup.go`
- `pkg/interceptors/dpuproxy/resolver.go`
- `gnmi_server/server.go`
- `common_utils/shareMem.go`

## 結論サマリー

| 観点 | 結論 |
|------|------|
| 共有メモリ (key=7749) | 全プラットフォーム共通。SysV IPC はカーネル機能でプラットフォーム非依存 |
| `GNMI_SET_BYPASS` カウンタ | **Cisco-8102 / Cisco-8101 / Cisco-8223 専用**。他 HwSku では常に 0 |
| SmartSwitch / DPU プロキシ | RPC を DPU にルーティングするが、カウンタ増分は NPU 側 telemetryd のみ。DPU 側カウンタは独立した SHM に格納 |
| VS (仮想化環境) | 全カウンタ正常動作。バイパス条件の HwSku 判定は VS SKU で不一致となるため `GNMI_SET_BYPASS` は発生しない |

## 詳細根拠

### GNMI_SET_BYPASS — Cisco 専用バイパス

`pkg/bypass/bypass.go:33-36` に `AllowedSKUPrefixes` がハードコードされている:

```go
var AllowedSKUPrefixes = []string{
    "Cisco-8102",
    "Cisco-8101",
    "Cisco-8223",
}
```

バイパス判定 `ShouldBypass()` (`bypass.go:83-98`) は以下の 3 条件がすべて真のときのみ `GNMI_SET_BYPASS` 経路に進む:
1. gRPC メタデータ `x-sonic-ss-bypass-validation: true`
2. `checkSKU()` が `DEVICE_METADATA|localhost.hwsku` を HGet し `AllowedSKUPrefixes` に前方一致
3. 操作テーブルが `AllowedTables` に含まれる (`VNET` / `VNET_ROUTE_TUNNEL` / `VLAN_SUB_INTERFACE` / `ACL_RULE` / `BGP_PEER_RANGE`)

条件 2 により、Broadcom / Mellanox / Marvell / Barefoot 系 HwSku では `GNMI_SET_BYPASS` は **常に 0**。

### SmartSwitch / DPU 環境

`pkg/interceptors/setup.go` に DPU プロキシインターセプターが登録されており、
gRPC メタデータ `x-sonic-target-type: dpu` かつ `x-sonic-target-index: <n>` があれば
NPU の telemetryd が RPC を DPU 側 gNMI サーバーに転送する (`dpuproxy/resolver.go:66-102`)。

ただし `dpuproxy` パッケージ内に `IncCounter` / `common_utils.GNMI_*` の呼び出しは **0 件**。
転送された RPC のカウントは DPU 側 telemetryd の独立した SysV SHM に記録されるため、
NPU 側 `gnmi_dump` では DPU 経由 RPC は集計されない。

### VS / テストシム

VS (libsaivs) 環境では `DEVICE_METADATA|localhost.hwsku` が `Force10-S6000` や
`Arista-7060CX-32S` 等の非 Cisco 値となるため `checkSKU()` は常に `false` を返す。
`GNMI_SET_BYPASS` = 0 でバイパス経路は通らない。共有メモリ (SysV IPC) は Linux カーネルが
提供するため VS 上でも正常に動作する。

### SysV 共有メモリのプラットフォーム非依存性

`shareMem.go:15-17` のキー/サイズ/フラグ定数はアーキテクチャ非依存。
`syscall.SYS_SHMGET` / `SYS_SHMAT` は Linux x86_64 / arm64 で利用可能。
ただし **macOS** (darwin) では SysV SHM の動作は OS によって制限される場合があり、
SONiC の本番運用対象 (Linux) 以外でビルドする場合は `shareMem.go` の移植が必要。
