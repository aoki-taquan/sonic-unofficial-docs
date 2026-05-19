# dhcpv4-relay — Phase H: プラットフォーム差

## DualToR (`DEVICE_METADATA.subtype = "DualToR"`)

`dhcp4relay_mgr` が `DEVICE_METADATA|localhost` の `subtype` フィールドを購読し、`"DualToR"` を検出すると `m_config.is_dualTor = true` をセットする（`dhcp4relay_mgr.cpp:231-232`）。

この状態では以下の強制的なプラットフォーム差が発生する：

1. **source_interface の強制上書き**: `dhcp4relay.cpp:263-267` で `interface_config.source_interface = "Loopback0"` に固定される。`DHCPV4_RELAY` テーブルの `source_interface` フィールドに別の値を設定していても**無視**される。
2. **link_selection の自動 enable**: `dhcp4relay.cpp:521` で `m_config.is_dualTor || config->link_selection_opt == "enable"` の条件のため、`link_selection = disable` の設定値に関わらず RFC 3527 Link Selection Sub-option が付与される。

## SmartSwitch (`DEVICE_METADATA.subtype = "SmartSwitch"`)

`dhcp4relay_mgr.cpp:241-249` で `is_SmartSwitch = true` がセットされ、`MID_PLANE_BRIDGE|GLOBAL.bridge` からミッドプレーンブリッジ名を取得する。

以下の挙動差が発生する：

1. **OPTION82 Remote-ID MAC**: `dhcp4relay.cpp:509-517` で `is_SmartSwitch == true` かつ midplane bridge の MAC が取得できた場合、OPTION82 SUBOPT_REMOTE_ID に**ホスト MAC ではなく midplane bridge の MAC** が使用される。
2. **DPU インタフェースの VLAN マッピング**: `dhcp4relay.cpp:1001-1003` で `dpu` プレフィックスを持つインタフェースからのパケットは midplane bridge 名を VLAN キーとして扱う。`VLAN` テーブルではなく `DPUS` テーブルを通じて管理される DPU に転送されるパケットが正しく処理される。

## 通常プラットフォーム（差なし）

ASIC 種別（Broadcom / Mellanox / Marvell 等）、multi-ASIC 構成、VOQ chassis については DHCPV4_RELAY は SAI 非経由（Linux カーネルレイヤ）であるため、ASICプラットフォームの差は発生しない。

| 観点 | 結果 | 根拠 |
|------|------|------|
| ASIC 種別 | 影響なし | SAI 非経由 |
| multi-ASIC / namespace | 影響なし | DHCPv4 relay は CPU-side Linux ネットワークスタックで動作 |
| DualToR | `source_interface` 強制 + `link_selection` 自動 enable | `dhcp4relay.cpp:263-267`, `dhcp4relay.cpp:521` |
| SmartSwitch | OPTION82 Remote-ID MAC が midplane bridge MAC に切替 | `dhcp4relay.cpp:509-517` |

## Evidence

- `sonic-dhcp-relay/dhcp4relay/src/dhcp4relay_mgr.cpp:231-232` — `is_dualTor` セット
- `sonic-dhcp-relay/dhcp4relay/src/dhcp4relay_mgr.cpp:241-249` — `is_SmartSwitch` セット + midplane bridge 取得
- `sonic-dhcp-relay/dhcp4relay/src/dhcp4relay.cpp:263-267` — DualToR 時の `source_interface = "Loopback0"` 強制
- `sonic-dhcp-relay/dhcp4relay/src/dhcp4relay.cpp:509-517` — SmartSwitch 時の OPTION82 Remote-ID MAC 切替
- `sonic-dhcp-relay/dhcp4relay/src/dhcp4relay.cpp:521` — `is_dualTor` による link_selection 自動 enable
- `sonic-dhcp-relay/dhcp4relay/src/dhcp4relay.cpp:1001-1003` — SmartSwitch DPU インタフェースの midplane bridge マッピング
