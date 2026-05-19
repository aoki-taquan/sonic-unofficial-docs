# gNMI 内部リクエストカウンタ — Phase H プラットフォーム差異調査

## 調査元

- `sonic-gnmi/pkg/bypass/bypass.go` (master)
- `sonic-gnmi/gnmi_server/server.go` (master)
- `sonic-gnmi/common_utils/shareMem.go` (master)

## 概要

gNMI 内部カウンタは SysV 共有メモリ（key=7749）に格納されるため、
ASIC / SAI capability によるプラットフォーム差異は存在しない。
ただし `GNMI_SET_BYPASS` カウンタの増分は **Cisco 特定 HwSku** でのみ発生するという
明示的なプラットフォーム依存が `pkg/bypass/bypass.go` に実装されている。

## GNMI_SET_BYPASS の Cisco 専用制限

`bypass.go:33-37`:

```go
var AllowedSKUPrefixes = []string{
    "Cisco-8102",
    "Cisco-8101",
    "Cisco-8223",
}
```

`checkSKU()` が `DEVICE_METADATA|localhost.hwsku` を CONFIG_DB から読み取り、
上記いずれかのプレフィクスで始まる場合のみ bypass 高速パスが有効になる。

非 Cisco プラットフォーム（Broadcom XGS、Mellanox Spectrum、Virtual Switch 等）では
`checkSKU()` が false を返すため bypass パスは通らず、`GNMI_SET_BYPASS` は常に 0。

## プラットフォーム別カウンタ挙動

| カウンタ | Cisco 8101/8102/8223 | その他プラットフォーム |
|---|---|---|
| `GNMI_SET_BYPASS` | bypass 条件が満たされれば増分 | 常に 0 |
| 他の全カウンタ | 通常通り増分 | 通常通り増分 |

bypass の追加条件: (1) gRPC メタデータ `x-sonic-ss-bypass-validation: true`、
(2) 対象テーブルが `VNET` / `VNET_ROUTE_TUNNEL` / `VLAN_SUB_INTERFACE` / `ACL_RULE` /
`BGP_PEER_RANGE` のいずれか、の 3 条件すべてが揃った場合のみ増分。

## SysV 共有メモリのプラットフォーム中立性

`shareMem.go` の SysV IPC キー `7749`、メモリサイズ `1024`、フラグ `0x380` はハードコード定数であり、
プラットフォームによる分岐はない。`gnmi_dump` コマンドも同様に全プラットフォームで同一動作。

## Virtual Switch (VS) での挙動

VS プラットフォームでは `telemetryd` は通常起動し、全カウンタは通常通り動作する。
ただし `checkSKU()` で hwsku が `vs` と返るため bypass パスは無効。
`GNMI_SET_BYPASS` は常に 0。

## SmartSwitch / DPU 環境

`pkg/interceptors/dpuproxy/` は DPU へのリクエスト転送を担うが、
カウンタ (`GNMI_GET` / `GNMI_SET` 等) は NPU 側 `telemetryd` で増分される。
DPU 側のカウンタは別インスタンスの共有メモリに格納される（独立）。
