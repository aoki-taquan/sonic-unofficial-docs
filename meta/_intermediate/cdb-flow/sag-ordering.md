# SAG — Phase B 書込み順依存スキャンノート

対象テーブル: `SAG`
Consumer: `intfmgrd` / `IntfMgr` + `orchagent` / `IntfsOrch` (`sonic-swss`) — HLD 記載
スキャン範囲: `sonic-swss-common/common/schema.h`, `SONiC/doc/sag/sag-HLD.md`, `sonic-swss` (ソースに実装が見つからないため HLD を根拠とする)
スキャン日: 2026-05-16

---

## 調査ノート

### 実装状況

`sonic-swss-common/common/schema.h:127,393` に `APP_SAG_TABLE_NAME "SAG_TABLE"` と `CFG_SAG_TABLE_NAME "SAG"` が定義されている。ただし現行 sonic-swss ソースツリー（shallow clone: sha=master, 2026-05-16）には `sagmgr.cpp` / `sagorch.cpp` 等の独立した実装ファイルが存在せず、`intfmgr.cpp` / `intfsorch.cpp` にも SAG 固有ハンドラは確認できなかった。本スキャンは HLD (`SONiC/doc/sag/sag-HLD.md` sha=49bab5b) を根拠とし、schema.h の定数を補足証跡とする。

### HLD から読み取れる CONFIG_DB 書込み順序依存

#### 1. SAG|GLOBAL → VLAN_INTERFACE の順（推奨）

HLD 記載のフロー: ユーザーが `config static-anycast-gateway mac_address add <mac>` を実行すると `SAG|GLOBAL.gateway_mac` が CONFIG_DB に書かれ、次に `config vlan static-anycast-gateway enable <vlan_id>` で `VLAN_INTERFACE|Vlan<n>.static_anycast_gateway = true` が設定される。

HLD 図の注釈: 「SAG global MAC が先に設定されている状態で VLAN インターフェースが enable になる」。これは CLI が enforce する運用順序であり、VLAN_INTERFACE が先に `static_anycast_gateway = true` に設定されても `intfmgr` / `intfsorch` が `SAG|GLOBAL.gateway_mac` を取得できなければ SAG MAC は適用されない（CPU MAC が使われる）。

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | `SAG\|GLOBAL.gateway_mac` → `VLAN_INTERFACE\|Vlan<n>.static_anycast_gateway=true` | **推奨先行** | 逆順でも runtime 再評価で最終収束するが、間欠的に CPU MAC が使われる期間が生じる（HLD 図のシーケンス参照） |
| 2 | SAG MAC 変更には `del` → `add` が必要 (CLI enforce) | **強制順序** | `config static-anycast-gateway mac_address add` は既存 MAC があれば reject。del 後に add の 2 ステップが必須 |
| 3 | SAG disable 後に MAC を del | **推奨先行** | VLAN_INTERFACE の `static_anycast_gateway=false` を先に適用することで，RIF MAC が元の CPU MAC に戻ってから SAG GLOBAL エントリを削除するのが安全。逆順だと brief period で MAC 不整合 |

#### 2. VLAN_INTERFACE の SAI RIF 更新タイミング

HLD 説明: SAG MAC が変わると `intfsorch` が VLAN_INTERFACE の RIF の `SAI_ROUTER_INTERFACE_ATTR_SRC_MAC_ADDRESS` を更新する。また IPv6 link-local アドレス由来の to-me route (RouteOrch 管理) について、MAC 変更前の link-local route を削除し新 MAC の link-local route を追加する 2 段更新が必要。

HLD の記述:
> "If the MAC address is changed between system and SAG, we need to call RouteOrch's API to delete old MAC generated IPv6 link-local to me route and then add new MAC generated IPv6 link-local to me route."

この 2 段更新はカーネル空間での arp/nd テーブル刷新も伴うため、SAG MAC 変更は一時的に IPv6 通信断が発生しうる。

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | `SAG\|GLOBAL.gateway_mac` 設定 → 各 VLAN_INTERFACE で `static_anycast_gateway=true` | 推奨先行 | 逆順は runtime 再評価で収束するが CPU MAC 使用期間が生じる |
| 2 | SAG MAC 変更: `del` → `add` の 2 ステップ | 強制順序（CLI enforce） | 同時変更不可 |
| 3 | SAG disable (`static_anycast_gateway=false`) → `SAG\|GLOBAL` del | 推奨先行 | RIF MAC 復旧後に GLOBAL エントリ削除するのが安全 |
| 4 | SAG MAC 変更時の IPv6 link-local route: 旧 route del → 新 route add | 固定順序（orchagent 内部） | RouteOrch API 呼び出しで保証、ユーザーが意識する必要なし |

---

## 証跡

- `sonic-swss-common/common/schema.h:127` `APP_SAG_TABLE_NAME "SAG_TABLE"`
- `sonic-swss-common/common/schema.h:393` `CFG_SAG_TABLE_NAME "SAG"`
- `SONiC/doc/sag/sag-HLD.md` (sha=49bab5b) — DB section, Architecture Design section
