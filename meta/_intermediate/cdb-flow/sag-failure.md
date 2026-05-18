# SAG — 失敗挙動調査 (Phase D)

調査日: 2026-05-18
調査者: Claude (batch #6)
対象: `docs/reference/config-db/sag.md`

## 調査方針

`SAG|GLOBAL` テーブルの実装は sonic-swss master に独立ファイル (`sagmgr.cpp` / `sagorch.cpp`) が存在せず、
HLD (`SONiC/doc/sag/sag-HLD.md`, sha=49bab5b) 記載の通り `intfmgrd` / `IntfsOrch` に組み込まれる設計。
コード確認: `sonic-swss-common/common/schema.h:127,393` に定数のみ存在 (`APP_SAG_TABLE_NAME`, `CFG_SAG_TABLE_NAME`)。
`sonic-swss/cfgmgr/intfmgr.cpp` および `sonic-swss/orchagent/intfsorch.cpp` に SAG 処理の grep hit なし (2026-05-18 確認)。

→ 本フェーズは HLD 記載のアーキテクチャ + intfmgrd/IntfsOrch の一般的な失敗挙動モデルに基づく推定。

## 書込みパス

```
CONFIG_DB: SAG|GLOBAL (SET/DEL)
  └─ intfmgrd が SubscriberStateTable で購読
       └─ APPL_DB: SAG_TABLE|GLOBAL に転送 (ProducerStateTable)
            └─ IntfsOrch が ConsumerStateTable で消費
                 └─ SAI: sai_router_intf_api set_attribute(SAI_ROUTER_INTERFACE_ATTR_SRC_MAC_ADDRESS)
```

## 失敗箇所別分析

### 1. CONFIG_DB 書込み段階 (CLI 側バリデーション)

| 失敗条件 | 挙動 | 証跡 |
|---|---|---|
| `gateway_mac` が不正 MAC 形式 | YANG `type yang:mac-address` で sonic-cfggen レベルでの reject (DB に書かれない) | HLD §YANG model, `sonic-static-anycast-gateway.yang` |
| `SAG\|GLOBAL` に `gateway_mac` が既存の状態で `config static-anycast-gateway mac_address add` | CLI が reject ("MAC address already configured, delete first") | HLD §CLI: "It doesn't allow to change SAG MAC via this command" |

### 2. intfmgrd → APPL_DB 転送段階

intfmgrd は SONiC 標準の `cfgmgr` パターンを採用する。

| 失敗条件 | 挙動 | 証跡 |
|---|---|---|
| `SAG\|GLOBAL.gateway_mac` 不在時に `VLAN_INTERFACE.static_anycast_gateway=true` を受信 | intfmgrd は `gateway_mac` を取得できず、システム MAC をそのまま使用して APPL_DB に転送。`SAG\|GLOBAL` が後から追加された時点で再評価・収束 | HLD §Architecture: runtime re-evaluation 記載 |
| Redis (CONFIG_DB) 切断中の SubscriberStateTable | intfmgrd プロセスが Redis 例外で abort → swss コンテナが `critical_processes` 設定に従って再起動 | SONiC cfgmgr 共通パターン |
| Redis (APPL_DB) 切断中の ProducerStateTable | 同上 (write 失敗 → abort → コンテナ再起動) | SONiC cfgmgr 共通パターン |

### 3. IntfsOrch → SAI 設定段階

| 失敗条件 | 挙動 | 証跡 |
|---|---|---|
| `sai_router_intf_api->set_attribute(SAI_ROUTER_INTERFACE_ATTR_SRC_MAC_ADDRESS)` 失敗 | IntfsOrch は SAI エラーを `SWSS_LOG_ERROR` ログ出力。retry 有無はコード未確認 (HLD に明記なし)。APPL_DB のエントリはそのまま残る | HLD §sonic-swss 説明 |
| SAG を適用すべき VLAN_INTERFACE が未作成の状態で `SAG_TABLE\|GLOBAL` を受信 | IntfsOrch は VLAN RIF が存在しないため SAI 設定不可。`VLAN_INTERFACE` 作成時に再評価 | HLD §Architecture (ordering dependency) |
| MAC 変更中 (del → add の間) に VLAN_INTERFACE が SAG_TABLE を参照 | RIF がシステム MAC に一時回帰する (HLD §High-Level Design 記載) | HLD §sonic-swss |

### 4. IPv6 link-local route 更新段階

| 失敗条件 | 挙動 | 証跡 |
|---|---|---|
| `RouteOrch` API での旧 link-local route DEL 失敗 | 旧 MAC 由来の route が残存し、IPv6 link-local 通信が期待通りに切り替わらない可能性 | HLD §IPv6 link-local address management |
| `RouteOrch` API での新 link-local route ADD 失敗 | 新 MAC への link-local route が存在せず、IPv6 パケットが CPU trap されない | HLD §IPv6 link-local address management |

## まとめ

- CLI 段階での MAC 形式チェック / 重複チェックは enforced。DB には不正値が書かれない。
- intfmgrd / IntfsOrch の Redis 例外はプロセス abort → swss コンテナ再起動で自己回復 (SONiC 共通パターン)。
- `SAG\|GLOBAL` 欠如状態での `VLAN_INTERFACE.static_anycast_gateway=true` 設定はサイレント degradation (CPU MAC 使用) で最終収束。
- HLD-only のため、SAI 失敗時の retry / 恒久スキップ分岐はコード確認不可。
