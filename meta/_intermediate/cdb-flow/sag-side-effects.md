# SAG テーブル — 副次処理 (Phase F) 調査証跡

## 調査日時
2026-05-18

## 調査対象
`CONFIG_DB: SAG|GLOBAL` の SET / DEL 操作が、SAG 自身のスキーマ外のリソース・テーブル・カーネル状態に与える副次的影響

## ソース
- `SONiC/doc/sag/sag-HLD.md` (sha=49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06) §High-Level Design §Testing
- `sonic-swss/orchagent/intfsorch.cpp` — SAG 専用ファイル非存在を確認。IntfsOrch 内で処理される設計
- `sonic-swss/cfgmgr/intfmgr.cpp` — IntfMgr 内 SAG ハンドラ組み込みの設計

## 検出された副次処理

### 1. IPv6 link-local to-me route の再設定（RouteOrch 経由）

HLD §High-Level Design:

> "In IPv6 link-local address management, the system MAC generated IPv6 link-local to me route is added by RouteOrch in its initialization.
> If the MAC address is changed between system and SAG, we need to call RouteOrch's API to delete old MAC generated IPv6 link-local to-me route and then add new MAC generated IPv6 link-local to-me route."

**トリガー**: `SAG|GLOBAL.gateway_mac` が SET/DEL されることで、VLAN インターフェースの MAC が system CPU MAC と SAG MAC の間で切り替わる。

**副次処理の内容**:
- `IntfsOrch` が `RouteOrch::addIpPrefix()` / `RouteOrch::delIpPrefix()` 相当の API を呼び出す
- 旧 MAC 由来の IPv6 link-local (`fe80::/10`) IP2ME route をまず削除
- 新 MAC 由来の IPv6 link-local IP2ME route を追加
- この 2 ステップ操作により、切替期間中は当該 VLAN インターフェース宛ての IPv6 link-local 通信が一時断となる

### 2. RIF の SAI 属性変更（SAI_ROUTER_INTERFACE_ATTR_SRC_MAC_ADDRESS）

HLD §sonic-swss:

> "The VLAN interface will use static anycast gateway MAC address to replace CPU MAC address if static anycast gateway MAC address is specified and it's enabled on the VLAN interface."

`IntfsOrch` は `SAG_TABLE|GLOBAL.gateway_mac` を受けて、`static_anycast_gateway=true` な全 VLAN インターフェースの SAI RIF の `SAI_ROUTER_INTERFACE_ATTR_SRC_MAC_ADDRESS` を変更する。これは SAG テーブル本来の役割だが、ASIC 内 RIF リソース変更という副次的なハードウェア状態変化を引き起こす。

### 3. カーネルインターフェース MAC アドレス変更

HLD §Testing System Test Cases:

> "Verify that VLAN interface can be created with SAG MAC address in kernel."
> "Verify the VLAN interface's MAC change to CPU MAC address in kernel" (SAG disable 時)

SAG の enable/disable に連動して、VLAN インターフェースのカーネル側 MAC アドレス (`ip link set dev VlanXXX address ...` 相当) が変更される。これにより ARP テーブルの再解決がホスト側で必要になる。

### 4. CRM (Critical Resource Monitor) — ルーターインターフェースリソース影響

HLD §Restrictions/Limitations:

> "For the router interfaces resources, it's the same as other IP address configure on the interface, and it can be monitored by CRM."

SAG 有効化は新規 SAI RIF を作成するわけではない（既存 RIF の MAC を変更するだけ）が、RIF 属性変更は CRM が追跡するルーターインターフェースリソースの消費に影響しない。ただし、CRM の router-interface カウンタが参照する状態と一致していることが前提。

## 副次処理サマリ

| 副次処理 | トリガー | 影響範囲 | 可逆性 |
|---------|---------|---------|--------|
| IPv6 link-local to-me route の del → add (RouteOrch 経由) | `SAG|GLOBAL` SET / DEL / MAC 変更 | VLAN インターフェース毎に 1 エントリ | 可逆（SAG disable で旧 route 復旧） |
| ASIC RIF の MAC 変更 (`SAI_ROUTER_INTERFACE_ATTR_SRC_MAC_ADDRESS`) | `SAG_TABLE|GLOBAL` SET / DEL | 対象 VLAN インターフェースの SAI RIF 全件 | 可逆（SAG disable で CPU MAC に戻る） |
| カーネル VLAN IF の MAC 変更 | `SAG|GLOBAL` SET / DEL | Linux カーネルのインターフェース状態 | 可逆 |

## 結論

SAG テーブルの primary 副次処理は **IPv6 link-local to-me route の RouteOrch 経由再設定**と**ASIC RIF の MAC 変更**の 2 点。これらは SAG 機能の本質であるが、SAG|GLOBAL の操作がトリガーとなって APPL_DB・SAI・カーネル状態の複数レイヤーに波及する副次的影響として記述できる。

sonic-swss master に sagmgr.cpp / sagorch.cpp の独立実装が存在しないため、コードレベルの詳細は HLD 記載設計 + IntfsOrch/IntfMgr の共通パターンに基づく推定。
