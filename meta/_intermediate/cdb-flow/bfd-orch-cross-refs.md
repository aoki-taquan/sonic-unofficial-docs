# BFD_SESSION (bfdorch) — 暗黙参照 (cross-table refs) 調査メモ

## 調査対象

`docs/reference/config-db/bfd-orch.md` Phase C 追加分。
`BFD_SESSION` (APPL_DB `BFD_SESSION_TABLE`) は SONiC yang-models に schema 未定義のため leafref は存在しない。
`sonic-swss/orchagent/bfdorch.cpp` を精読し、外部テーブル・外部 Orch・外部リソースへの依存を網羅した。

## ソースファイル精読

| ファイル | 役割 |
|---------|------|
| `sonic-swss/orchagent/bfdorch.cpp` | `BfdOrch::doTask()` / `create_bfd_session()` / `remove_bfd_session()` / `handleTsaStateChange()` |
| `sonic-swss/orchagent/bfdorch.h` | `BfdOrch` / `BgpGlobalStateOrch` クラス宣言 |

## YANG leafref

`BFD_SESSION` には対応する YANG schema が存在しない（2026-05 時点）。全参照は実装レベルの暗黙参照。

## 暗黙参照 (実装レベル)

### 1. PORT テーブル (interface 経路、hardware lookup 無効時)

- **参照先テーブル**: `PORT`
- **参照方向**: 読み取り（Port オブジェクト解決 + SAI port OID 取得）
- **条件**: key の `<interface>` が `"default"` 以外（= hardware lookup 無効 = `SAI_BFD_SESSION_ATTR_HW_LOOKUP_VALID=false`）
- **参照元**: `bfdorch.cpp` L482–520 (`gPortsOrch->getPort(alias, port)` + `port.m_port_id` + `port.m_mac`)
- **意味**:
  - `gPortsOrch->getPort(alias, port)` が false（PORT エントリ不在）→ `"Failed to locate port"` ERROR + `return false` → セッション作成失敗（リトライ対象）
  - 取得した `port.m_port_id` を `SAI_BFD_SESSION_ATTR_PORT` に、`port.m_mac` を `SAI_BFD_SESSION_ATTR_SRC_MAC_ADDRESS` に投入
  - PortsOrch 初期化が未完了のうちに BFD_SESSION が来た場合は `getPort()` が false を返し、`it++` で再試行待ち
- **追加制約**: 同時に `dst_mac` が必須（未指定 → `"destination MAC address required when hardware lookup not valid"` エラー）、`vrf_name == "default"` も必須（vrf!=default → `"vrf is not supported when hardware lookup not valid"` エラー）

### 2. VRF テーブル (vrf 経路、hardware lookup 有効時)

- **参照先テーブル**: `VRF`
- **参照方向**: 読み取り（VRFOrch 経由で SAI virtual_router OID 取得）
- **条件**: key の `<vrf>` が `"default"` 以外、かつ `<interface> == "default"`（hardware lookup 有効経路）
- **参照元**: `bfdorch.cpp` L530–541 (`gDirectory.get<VRFOrch*>()->getVRFid(vrf_name)`)
- **意味**:
  - `vrf_name == "default"` の場合は extern `gVirtualRouterId`（default VRF の SAI OID）を使う
  - `vrf_name != "default"` の場合は `VRFOrch::getVRFid(vrf_name)` で VRF テーブルから OID を引く。VRF 未作成なら 0 が返り SAI 作成失敗の可能性
  - 投入先 SAI attribute: `SAI_BFD_SESSION_ATTR_VIRTUAL_ROUTER`
- **追加制約**: hardware lookup 無効経路（`interface != "default"`）では vrf!=default は拒否される

### 3. BGP_DEVICE_GLOBAL テーブル (TSA + use_software_bfd フラグ)

- **参照先テーブル**: `BGP_DEVICE_GLOBAL` (CONFIG_DB) / STATE_DB 派生
- **参照方向**: 読み取り（`BgpGlobalStateOrch` 経由）
- **条件**: 全 `doTask()` 呼び出しで参照（毎回先頭で取得）
- **参照元**:
  - `bfdorch.cpp` L114–121 (`gDirectory.get<BgpGlobalStateOrch*>()->getTsaState()` + `getSoftwareBfd()`)
  - `BgpGlobalStateOrch::doTask()` L793–840（`tsa_enabled` フィールド購読）
  - `BgpGlobalStateOrch::offload_supported()` L755–791（起動時 1 回のみ評価し `bfd_offload` を確定 → `getSoftwareBfd()` は `!bfd_offload` を返す）
- **意味**:
  - `tsa_enabled == true` + `shutdown_bfd_during_tsa == "true"` のセッションは作成スキップ + Down 通知（後で TSA 解除 → `handleTsaStateChange()` で `bfd_session_cache` から復元作成）
  - `use_software_bfd == true` → SAI を呼ばず STATE_DB `SOFTWARE_BFD_SESSION_TABLE` に転記して終了。本テーブルの全フィールドは FRR `bgpcfgd/BfdMgr` 側でデフォルト再評価される
  - `use_software_bfd` の判定は **bfdorch 起動時 1 回のみ** であり、動的切替には swss 再起動が必要

### 4. NEXTHOP / RouteOrch (逆参照 — 監視対象としての BFD_SESSION)

- **参照先テーブル**: なし（bfdorch 自体は NEXTHOP / ROUTE テーブルを参照しない）
- **逆参照方向**: `BFD_SESSION` は他 Orch（`StaticRouteBfd`、`VxlanTunnelOrch` の monitoring、`NhgOrch` の bfd-monitor next-hop）から **作成元** として参照される
- **参照元 (逆)**:
  - `bfdorch.cpp` L569–572, L257–260 — セッション状態変化時に `SUBJECT_TYPE_BFD_SESSION_STATE_CHANGE` で `BfdUpdate` を publish
  - subscriber 例: `nhgorch.cpp` (next-hop group の BFD-monitored member の up/down 判定), `routeorch.cpp` (`BFD_SESSION` 状態に応じた static route 切替), `vxlanmgr` / `tunnel_decap_orch.cpp`
- **意味**:
  - bfdorch は publisher、NEXTHOP / NHG 系 Orch は subscriber。FRR bgpcfgd の `BfdMgr` も dynamic next-hop の BFD 状態を SOFTWARE_BFD_SESSION_TABLE 経由で取得
  - BFD_SESSION エントリの key (`<vrf>:<interface>:<peer_ip>`) はそのまま next-hop の (vrf, intf, ip) と一致するため、subscriber 側は key マッチで対応 next-hop を特定する
- **注意**: この方向は CONFIG_DB の `STATIC_ROUTE_BFD` / `NEXTHOP_GROUP_MEMBER` などが作成主体になるため、`docs/reference/config-db/bfd-session.md` (CONFIG_DB 側) の暗黙参照と重複しないよう、ここでは bfdorch が publish する subject としてのみ扱う

### 5. STATE_DB / ASIC_DB (Orch 間連動)

- **参照先**: STATE_DB `BFD_SESSION_TABLE` / STATE_DB `SOFTWARE_BFD_SESSION_TABLE` / ASIC_DB `NOTIFICATIONS` channel
- **参照方向**: 書き込み（STATE_DB）+ 購読（NotificationConsumer）
- **条件**: 常時
- **参照元**: `bfdorch.cpp` L63–86, L252, L544–567, L629
- **意味**:
  - 起動時に STATE_DB `BFD_SESSION_TABLE` および `SOFTWARE_BFD_SESSION_TABLE` を全削除（クリーン起動）
  - SAI セッション作成成功 → STATE_DB `BFD_SESSION_TABLE|<vrf>|<interface>|<peer_ip>` に `state=Down` + 確定値（local_discriminator, type, local_addr, tx_interval, rx_interval, multiplier, multihop）を書く
  - SAI からの `bfd_session_state_change` 通知（ASIC_DB `NOTIFICATIONS`）を購読し、`state` フィールドを更新
- **意味（cross-table）**: これは「暗黙参照」というより同一 Orch の状態管理だが、`docs/reference/config-db/bfd-state.md` との往復関係を成立させる

## 参照関係サマリ

```
BFD_SESSION (CONFIG_DB → APPL_DB BFD_SESSION_TABLE)
  ├─ [暗黙] PORT.name                    (alias != "default" 時、PortsOrch::getPort → m_port_id, m_mac)
  ├─ [暗黙] VRF.name                     (vrf != "default" かつ alias == "default" 時、VRFOrch::getVRFid)
  ├─ [暗黙] BGP_DEVICE_GLOBAL            (TSA enabled / use_software_bfd フラグ — BgpGlobalStateOrch 経由)
  ├─ [逆参照、publish] NEXTHOP / NHG     (BfdUpdate notification → nhgorch / routeorch / vxlanmgr が購読)
  └─ [書込] STATE_DB BFD_SESSION_TABLE / SOFTWARE_BFD_SESSION_TABLE / ASIC_DB NOTIFICATIONS
```

## evidence

- `bfdorch.cpp`: L114–121 (BGP_DEVICE_GLOBAL 参照), L133–139, L182–188 (use_software_bfd 分岐), L155–178 (TSA 連動), L482–520 (PORT 参照), L530–541 (VRF 参照), L569–572 (NEXTHOP 逆参照 publish), L252–260 (state notification 配信), L63–86 (STATE_DB クリーン起動)
- `bfdorch.h`: `BfdOrch` / `BgpGlobalStateOrch` クラス宣言、`bfd_session_map` / `bfd_session_cache` / `bfd_session_lookup` 内部状態

## 備考

- `aclorch.cpp` のような `getRedirectObjectId()` の多段フォールバック解決はなく、依存先は key の `<vrf>` と `<interface>` の値で 1 対 1 に決まる
- NEXTHOP の方向は **逆参照**（subscribe）であり、bfdorch.cpp 内には `NEXTHOP` という文字列も `NeighOrch` / `RouteOrch` へのフィールド読み取りも存在しないことを明示しておく
