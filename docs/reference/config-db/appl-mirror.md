---
title: APPL_DB FIXED_MIRROR_SESSION_TABLE (P4RT)
description: "APPL_DB FIXED_MIRROR_SESSION_TABLE — P4RT ランタイムが書き込む ERSPAN ミラーセッション定義テーブル。MirrorSessionManager が APPL_DB を購読し SAI MIRROR_SESSION オブジェクトに変換する。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-15
sources:
  - repo: sonic-net/sonic-swss
    path: orchagent/p4orch/mirror_session_manager.h
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
  - repo: sonic-net/sonic-swss
    path: orchagent/p4orch/mirror_session_manager.cpp
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
  - repo: sonic-net/sonic-swss
    path: orchagent/p4orch/p4orch_util.h
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
  - repo: sonic-net/sonic-swss
    path: orchagent/mirrororch.cpp
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
related:
  config_db:
    - MIRROR_SESSION
  appl_db:
    - FIXED_MIRROR_SESSION_TABLE
---

# APPL_DB FIXED_MIRROR_SESSION_TABLE (P4RT)

## 概要

`APPL_DB FIXED_MIRROR_SESSION_TABLE` は [P4RT](../../reference/glossary.md#term-p4rt) ランタイムが書き込む ERSPAN ミラーセッション定義テーブル。
`p4orch` 内の `MirrorSessionManager` が [APPL_DB](../../reference/glossary.md#term-appl_db) を購読し、[SAI](../../reference/glossary.md#term-sai) MIRROR_SESSION オブジェクトに変換する[^1]。

通常の CONFIG_DB `MIRROR_SESSION` テーブルとは独立したパスであり、P4RT 経由のプログラムにのみ利用される。
セッションタイプは常に **ERSPAN (Enhanced Remote SPAN)** に固定され、GRE トンネルパラメータをすべて明示的に指定する必要がある。

## key 構造

```text
FIXED_MIRROR_SESSION_TABLE|{"match/mirror_session_id":"<id>"}
```

key は JSON 形式でエンコードされる。`<id>` は P4RT テーブルのマッチフィールド `mirror_session_id` の値。

## 主要フィールド

| フィールド | 型 | 必須 | 既定 | 説明 |
|-----------|----|------|------|------|
| `action` | string `mirror_as_ipv4_erspan` | yes | - | アクション識別子。固定値のみ受け付ける |
| `param/port` | string (物理ポート名) | yes | - | ミラーパケット送出先の物理ポート |
| `param/src_ip` | ip-address | yes | - | ERSPAN 外側 IP のソース |
| `param/dst_ip` | ip-address | yes | - | ERSPAN 外側 IP の宛先 |
| `param/src_mac` | mac-address | yes | - | ERSPAN 外側イーサネットの送信元 MAC |
| `param/dst_mac` | mac-address | yes | - | ERSPAN 外側イーサネットの宛先 MAC |
| `param/ttl` | hex uint8 | yes | - | ERSPAN 外側 IP の TTL (16 進数文字列) |
| `param/tos` | hex uint8 | yes | - | ERSPAN 外側 IP の TOS (DSCP+ECN, 16 進数文字列) |

全フィールドが必須。1 つでも欠けると `processAddRequest()` が `SWSS_RC_INVALID_PARAM` を返しセッションは作成されない[^2]。

## 制約

- `param/port` は物理ポート (`Port::Type::PHY`) のみ有効。VLAN / PortChannel は拒否される[^3]。
- `action` は `mirror_as_ipv4_erspan` のみ有効。他の値は `SWSS_RC_INVALID_PARAM`[^4]。
- APPL_DB のキー形式は JSON エンコード。パース失敗時は `SWSS_RC_INVALID_PARAM`[^4]。
- 更新時は個別フィールドを部分的に送信できる (`has_*` フラグで管理)。

<!-- defaults -->
## コード由来の暗黙デフォルト (Phase A)

<!-- evidence: sonic-swss/orchagent/p4orch/mirror_session_manager.h L20-21 / mirror_session_manager.cpp prepareSaiAttrs() L120-187 / p4orch_util.h P4MirrorSessionAppDbEntry struct L253-279 -->

| フィールド | APP_DB デフォルト | C++ 実装デフォルト | 種別 | 備考 |
|-----------|-----------------|-------------------|------|------|
| `param/ttl` | **なし (必須)** | `uint8_t ttl = 0` (struct 初期値) | 必須フィールド — デフォルト無効 | `has_ttl=false` のまま ADD 操作を行うと `SWSS_RC_INVALID_PARAM` |
| `param/tos` | **なし (必須)** | `uint8_t tos = 0` (struct 初期値) | 必須フィールド — デフォルト無効 | `has_tos=false` のまま ADD 操作を行うと `SWSS_RC_INVALID_PARAM` |
| `SAI_MIRROR_SESSION_ATTR_IPHDR_VERSION` | (APP_DB フィールドなし) | **`4`** (IPv4 固定) | ハードコード | `MIRROR_SESSION_DEFAULT_IP_HDR_VER = 4` (`mirror_session_manager.h:20`) — IPv6 ヘッダ非対応 |
| `SAI_MIRROR_SESSION_ATTR_GRE_PROTOCOL_TYPE` | (APP_DB フィールドなし) | **`0x88be`** | ハードコード | `GRE_PROTOCOL_ERSPAN = 0x88be` (`mirror_session_manager.h:21`) — 変更不可 |
| `SAI_MIRROR_SESSION_ATTR_TYPE` | (APP_DB フィールドなし) | **`SAI_MIRROR_SESSION_TYPE_ENHANCED_REMOTE`** | ハードコード | セッションタイプは ERSPAN 固定。SPAN は不可 |
| `SAI_MIRROR_SESSION_ATTR_ERSPAN_ENCAPSULATION_TYPE` | (APP_DB フィールドなし) | **`SAI_ERSPAN_ENCAPSULATION_TYPE_MIRROR_L3_GRE_TUNNEL`** | ハードコード | L3 GRE トンネルカプセル化固定 |

### 主要な discrepancy 詳細

**IP ヘッダバージョン固定 = 4 — IPv6 ERSPAN 非対応**:
`prepareSaiAttrs()` では `SAI_MIRROR_SESSION_ATTR_IPHDR_VERSION` に定数 `MIRROR_SESSION_DEFAULT_IP_HDR_VER = 4` を設定する。
`src_ip` / `dst_ip` に IPv6 アドレスを渡しても、SAI には IPv4 ヘッダバージョンが設定されるため動作しない。
P4RT ERSPAN は IPv4 outer ヘッダのみサポート。

**GRE type ハードコード = 0x88be — 設定変更不可**:
`prepareSaiAttrs()` は `SAI_MIRROR_SESSION_ATTR_GRE_PROTOCOL_TYPE` に定数 `GRE_PROTOCOL_ERSPAN = 0x88be` をハードコードする。
APP_DB に gre_type フィールドは存在せず変更できない。CONFIG_DB `MIRROR_SESSION.gre_type` (Mellanox で `0x8949`) のような platform 分岐もない。

**TOS と TTL は hex 文字列 — 0 は有効な値だが省略不可**:
`deserializeP4MirrorSessionAppDbEntry()` は TOS / TTL を `std::stoul(value, 0, 16)` で 16 進数としてパースする。
`0x00` (= 0) は有効値として受け付けられるが、フィールド自体の省略は `has_ttl=false` / `has_tos=false` のまま ADD を発行することになり `SWSS_RC_INVALID_PARAM` が返る。

<!-- /defaults -->

<!-- platform -->
## プラットフォーム差 (Phase H)

`FIXED_MIRROR_SESSION_TABLE` を処理する `MirrorSessionManager` は **`getenv("platform")` を一切参照せず**、GRE type / IP header version / encapsulation type / session type をすべて C++ 定数としてハードコードする (`mirror_session_manager.h:20-21`、`mirror_session_manager.cpp::prepareSaiAttrs()`)。
一方 CONFIG_DB 側 `MirrorOrch` は `mirrororch.cpp:65-72` で `platform == MLNX_PLATFORM_SUBSTRING` のときに GRE type を `0x8949` に切り替える等、複数のプラットフォーム / スイッチタイプ分岐を持つ。
このため同一 ASIC 上で CONFIG_DB 経路と P4RT 経路を併用すると、Mellanox 等で **経路によって SAI 属性値が異なる discrepancy** が発生する。

### P4RT 経路 vs CONFIG_DB 経路の capability 差異一覧

| capability | CONFIG_DB MIRROR_SESSION (MirrorOrch) | APPL_DB FIXED_MIRROR_SESSION_TABLE (P4RT) | evidence |
|---|---|---|---|
| **GRE protocol type** | mellanox は `0x8949`、それ以外は `0x88be` (`platform` env で分岐、`gre_type` フィールドで上書き可) | **`0x88be` ハードコード** (上書き不可) | `mirrororch.cpp:57-77` / `mirror_session_manager.h:21` |
| **IP header version** | IPv4 / IPv6 を `src_ip` / `dst_ip` のアドレスファミリで自動判定 | **`4` ハードコード** (IPv6 ERSPAN 不可) | `mirrororch.cpp:1005-1049` / `mirror_session_manager.h:20` |
| **VoQ スイッチ向け monitor_port 差し替え** | `gMySwitchType == "voq"` かつ ERSPAN のとき **recirc port** に強制差し替え | 差し替えなし (`param/port` をそのまま使用) | `mirrororch.cpp:592-598, 961-973, 1193-1205` |
| **VoQ スイッチ向け DST_MAC 差し替え** | `voq` かつ ERSPAN のとき **`gMacAddress`** に差し替え | 差し替えなし (`param/dst_mac` をそのまま使用) | `mirrororch.cpp:609-615, 1037-1044, 1153-1159` |
| **ingress/egress mirror ASIC capability** | bind 前に `SwitchOrch::isPortIngressMirrorSupported()` / `isPortEgressMirrorSupported()` で fail-fast | チェックなし (P4RT はポート bind を行わない) | `mirrororch.cpp:816-826` |
| **SAI mirror_session リソース枯渇チェック** | ADD 前に `sai_object_type_get_availability(SAI_OBJECT_TYPE_MIRROR_SESSION)` を呼ぶ | チェックなし (SAI create 失敗で初めて検出) | `mirrororch.cpp:357-379` |
| **SAI_MIRROR_SESSION_ATTR_TC サポート差** | `queue=0` のとき TC 属性を付加しない (TC 非対応 ASIC への配慮) | TC 属性そのものを APP_DB スキーマに持たず、常に SAI デフォルト | `mirrororch.cpp:931-938` |
| **Policer 連携** | `policer` フィールドで `PolicerOrch::getPolicerOid()` を解決し `SAI_MIRROR_SESSION_ATTR_POLICER` に設定 | **policer フィールド非対応** (連携不可) | `mirrororch.cpp:1052-1064` / `p4orch_util.h::P4MirrorSessionAppDbEntry` |

### プラットフォーム別 GRE type の取り扱い

| プラットフォーム | CONFIG_DB MIRROR_SESSION デフォルト | APPL_DB FIXED_MIRROR_SESSION_TABLE | 同一 ASIC で経路併用時の挙動 |
|----------------|------------------------------------|-----------------------------------|---------------------------|
| mellanox (Spectrum) | `gre_type = 0x8949` | `0x88be` 固定 | **discrepancy あり**: SAI に渡る値が経路で異なる |
| broadcom (XGS / DNX) | `gre_type = 0x88be` | `0x88be` 固定 | 一致 |
| barefoot / cisco-8000 / marvell-* / nephos / clounix / xsight | `gre_type = 0x88be` | `0x88be` 固定 | 一致 |
| (CLI で `gre_type` 明示上書き) | 任意値 | 上書き不可 | 上書き値次第で discrepancy |

### スイッチタイプ別の monitor_port / dst_mac 差し替え

| `DEVICE_METADATA.localhost.switch_type` | CONFIG_DB ERSPAN monitor_port | CONFIG_DB ERSPAN DST_MAC | P4RT FIXED_MIRROR_SESSION |
|---|---|---|---|
| `voq` (分散シャーシ — Cisco 8000 等) | **recirc port** に強制差し替え | **`gMacAddress`** (router MAC) | 差し替えなし。`switch_type=voq` で実用可否は未定義 |
| `switch` (一般スタンドアロン) | `neighborInfo.portId` (ARP/NDP 解決) | `neighborInfo.mac` | `param/port` / `param/dst_mac` をそのまま使用 |

### Multi-ASIC (namespace) サポート

`MirrorSessionManager` 自体に multi-asic 固有の分岐コードはない。multi-asic シャーシ (Broadcom DNX / Cisco 8000) では asic namespace ごとに orchagent と APPL_DB インスタンスが起動するため、P4RT controller 側で asic を選択して APPL_DB に書き込む必要がある。
namespace 間の整合性 (例: 同一 `mirror_session_id` を複数 asic に作成するか) は orchagent / SAI レベルでは強制されず、上位 P4RT controller の責務となる[^5]。

### 既知の discrepancy (重要)

- **Mellanox での GRE type 不整合**: P4RT 経由で ERSPAN セッションを作ると `0x88be` が SAI に渡るが、Mellanox Spectrum は通常 `0x8949` を期待する。CONFIG_DB 経路 (`MirrorOrch`) は `platform` env で正しく `0x8949` を選択するため、**Mellanox 上で P4RT ERSPAN を使うとハードウェアが期待しない GRE type で encap される可能性がある**。
- **IPv6 outer ヘッダ非対応**: P4RT 側は IP header version を `4` にハードコードするため、`src_ip` / `dst_ip` に IPv6 を渡しても IPv4 ヘッダバージョンが設定される。CONFIG_DB 側はアドレスファミリで自動判定する。
- **policer 連携の機能差**: CONFIG_DB 経路では `MIRROR_SESSION.policer` で rate limiter を付けられるが、P4RT 経路は policer フィールドそのものが存在せず、ASIC が policer 連携をサポートしていても **P4RT 経由では利用不可**。
- **VoQ シャーシでの monitor_port 不整合**: `switch_type=voq` 環境では CONFIG_DB 経路は ERSPAN の monitor_port を recirc port に差し替えるが、P4RT 経路は差し替えない。**P4RT FIXED_MIRROR_SESSION_TABLE は VoQ シャーシ向けに設計されていない**。

詳細は `meta/_intermediate/cdb-flow/appl-mirror-platform.md` を参照。

<!-- /platform -->

## 購読者

- `p4orch` 内の `MirrorSessionManager` (`orchagent/p4orch/mirror_session_manager.cpp`)
- CONFIG_DB `MIRROR_SESSION` テーブルの `MirrorOrch` とは独立した別経路

## 関連リファレンス

- [CONFIG_DB MIRROR_SESSION](./mirror-session.md) — 通常の SPAN/ERSPAN セッション設定 (CLI 経由)
- P4RT: `APP_P4RT_MIRROR_SESSION_TABLE_NAME = "FIXED_MIRROR_SESSION_TABLE"` (`sonic-swss-common/common/schema.h:70`)

## 確認コマンド

```bash
# APPL_DB の FIXED_MIRROR_SESSION_TABLE を確認
sonic-db-cli APPL_DB keys 'FIXED_MIRROR_SESSION_TABLE*'
sonic-db-cli APPL_DB hgetall 'FIXED_MIRROR_SESSION_TABLE|{"match/mirror_session_id":"my_session"}'
```

## 引用元

[^1]: `MirrorSessionManager` 説明: `orchagent/p4orch/mirror_session_manager.h` L69-70. <https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/orchagent/p4orch/mirror_session_manager.h#L69-L70>
[^2]: `processAddRequest()` の必須フィールドチェック: `orchagent/p4orch/mirror_session_manager.cpp` L339-363. <https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/orchagent/p4orch/mirror_session_manager.cpp#L339-L363>
[^3]: 物理ポート制約: `orchagent/p4orch/mirror_session_manager.cpp` L124-135. <https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/orchagent/p4orch/mirror_session_manager.cpp#L124-L135>
[^4]: `deserializeP4MirrorSessionAppDbEntry()`: `orchagent/p4orch/mirror_session_manager.cpp` L190-323. <https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/orchagent/p4orch/mirror_session_manager.cpp#L190-L323>
[^5]: `MirrorEntry::MirrorEntry()` での GRE type platform 分岐: `orchagent/mirrororch.cpp` L57-77. <https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/orchagent/mirrororch.cpp#L57-L77>
