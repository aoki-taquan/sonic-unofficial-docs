# APPL_DB FIXED_MIRROR_SESSION_TABLE (P4RT) — Phase H: プラットフォーム差

## 調査対象ソース

- `sonic-net/sonic-swss` @ `4305596156d70e9797e8a881b3d19b46de0bce0d`
  - `orchagent/mirrororch.cpp` — CONFIG_DB 側 `MirrorOrch` におけるプラットフォーム分岐 (P4RT 側との対比に使用)
    - `MirrorEntry::MirrorEntry()` L57-77 — `platform` 環境変数で GRE type を分岐 (Mellanox は `0x8949`、それ以外は `0x88be`)
    - `MirrorOrch::isHwResourcesAvailable()` L357-379 — `sai_object_type_get_availability(SAI_OBJECT_TYPE_MIRROR_SESSION)` で SAI 側枯渇/未実装を検出
    - `MirrorOrch::setUnsetPortMirror()` L811-826 — `SwitchOrch::isPortIngressMirrorSupported()` / `isPortEgressMirrorSupported()` の ASIC capability チェック
    - `MirrorOrch::activateSession()` L921-1067 — `gMySwitchType == "voq"` 分岐 (ERSPAN 時に monitor_port を recirc port に置換、DST_MAC を `gMacAddress` に置換)
    - `MirrorOrch::activateSession()` L931-938 — `SAI_MIRROR_SESSION_ATTR_TC` は queue!=0 のときだけ設定 (一部 ASIC は global TC のみ)
    - `MirrorOrch::activateSession()` L1052-1064 — `SAI_MIRROR_SESSION_ATTR_POLICER` 設定 (PolicerOrch 連携)
  - `orchagent/p4orch/mirror_session_manager.cpp` / `.h` — P4RT 側 `MirrorSessionManager` (platform 分岐なし)
- `sonic-net/sonic-sairedis` — `sai_object_type_get_availability` 実装側

## プラットフォーム識別方法

P4RT 側 `MirrorSessionManager` は **環境変数 `platform` を一切参照しない**。
GRE protocol type / IP header version / encapsulation type / session type をすべて C++ 定数としてハードコードする。
一方 CONFIG_DB 側 `MirrorOrch` は `getenv("platform")` を読み取り `MirrorEntry` コンストラクタで GRE type を分岐する。
同一 ASIC 上で CONFIG_DB 経由と P4RT 経由を併用すると、Mellanox では **GRE type の値が経路によって異なる** という discrepancy が発生する。

## 差異 1: GRE protocol type の platform 分岐 (CONFIG_DB) vs ハードコード (P4RT)

`mirrororch.cpp:65-72`:

```cpp
if (platform == MLNX_PLATFORM_SUBSTRING)
{
    greType = 0x8949;
}
else
{
    greType = 0x88be;
}
```

`mirror_session_manager.h:21`:

```cpp
constexpr uint16_t GRE_PROTOCOL_ERSPAN = 0x88be;
```

| プラットフォーム | CONFIG_DB MIRROR_SESSION (MirrorOrch) | APPL_DB FIXED_MIRROR_SESSION_TABLE (P4RT) | discrepancy |
|----------------|---------------------------------------|-------------------------------------------|-------------|
| mellanox | `gre_type = 0x8949` (デフォルト) | **`GRE_PROTOCOL_ERSPAN = 0x88be` (固定)** | あり: 同一 ASIC でも経路で GRE type が異なる |
| broadcom / barefoot / cisco-8000 / marvell-* / 他 | `gre_type = 0x88be` (デフォルト) | `GRE_PROTOCOL_ERSPAN = 0x88be` (固定) | なし |
| (CLI で `gre_type` を上書き) | 任意 16 進数値 (例 `0x88be` / `0x8949`) | 上書き不可 (APP_DB フィールドなし) | あり |

P4RT 側はそもそも `gre_type` フィールドを APP_DB スキーマに持たない (`p4orch_util.h::P4MirrorSessionAppDbEntry`)。
したがって Mellanox Spectrum で P4RT 経由の ERSPAN セッションを SAI に渡しても、ハードウェアが要求する `0x8949` ではなく標準 `0x88be` が設定される。
これは未対応もしくは silently misbehave のいずれかになり得る (実機検証は本ドキュメント範囲外)。

## 差異 2: VoQ スイッチ向け特殊処理 (P4RT 側に該当なし)

`mirrororch.cpp:592-598, 609-615, 961-973, 1037-1044, 1153-1159, 1193-1205`:

CONFIG_DB 側 `MirrorOrch` は `gMySwitchType == "voq"` かつ `session.type == MIRROR_SESSION_ERSPAN` の場合、
ERSPAN セッションの monitor_port を **recirc port** に置換し、`SAI_MIRROR_SESSION_ATTR_DST_MAC_ADDRESS` を **router MAC (`gMacAddress`)** に置換する。

| ASIC 構成 (`DEVICE_METADATA.localhost.switch_type`) | CONFIG_DB ERSPAN monitor_port | CONFIG_DB ERSPAN DST_MAC | P4RT ERSPAN monitor_port | P4RT ERSPAN DST_MAC |
|---|---|---|---|---|
| `voq` (Cisco 8000 など分散シャーシ) | **recirc port** に強制差し替え | **`gMacAddress`** (router MAC) に強制差し替え | `param/port` をそのまま (差し替えなし) | `param/dst_mac` をそのまま |
| 非 VoQ (`switch` 等) | `neighborInfo.portId` (ネクストホップ解決後) | `neighborInfo.mac` (ARP/NDP 解決済) | `param/port` (物理ポート直接指定) | `param/dst_mac` (固定指定) |

P4RT 側は VoQ シャーシ向け recirc port 経路を持たないため、`switch_type=voq` の環境で P4RT FIXED_MIRROR_SESSION_TABLE が実用的に機能するかは未定義。

## 差異 3: ASIC ingress/egress mirror capability チェック (両経路共通の SAI capability)

`mirrororch.cpp:816-826`:

```cpp
if (ingress && !m_switchOrch->isPortIngressMirrorSupported())  // → reject
if (!ingress && !m_switchOrch->isPortEgressMirrorSupported())  // → reject
```

CONFIG_DB 側はポートに mirror セッションを bind する直前に `SwitchOrch` から `SAI_SWITCH_ATTR_INGRESS_MIRROR_SESSION` / `SAI_SWITCH_ATTR_EGRESS_MIRROR_SESSION` の sai capability を照会して fail-fast する。
P4RT 側 `MirrorSessionManager` は mirror_session の作成のみで、ポートへの bind は行わない (ACL action 経由になる) ため、このチェック点は **P4RT 経路では存在しない**。

| ASIC | ingress mirror | egress mirror | P4RT に対する影響 |
|------|----------------|---------------|-------------------|
| 一般的な ASIC (broadcom / mellanox / barefoot / cisco-8000) | yes | yes | 影響なし (両方サポート) |
| egress mirror をサポートしない ASIC | yes | no | P4RT は mirror_session を作成可、ACL 側で egress 方向にバインドすると SAI 側で失敗 |

## 差異 4: SAI mirror_session リソース上限 (両経路共通)

`mirrororch.cpp:357-379` の `isHwResourcesAvailable()` は `sai_object_type_get_availability(SAI_OBJECT_TYPE_MIRROR_SESSION)` を毎回 ADD 前に呼び、`availCount == 0` なら CRM 枯渇として ADD を拒否する。
`SAI_STATUS_NOT_SUPPORTED` / `SAI_STATUS_NOT_IMPLEMENTED` を返す ASIC では「常に余裕あり」扱いになる。

P4RT 側 `mirror_session_manager.cpp::processAddRequest()` は **この事前チェックを行わない**。
SAI create_mirror_session() が枯渇エラーで失敗した時点で APPL_STATE_DB に error を返すのみ。

| ASIC | sai_object_type_get_availability(MIRROR_SESSION) | CONFIG_DB 経路の挙動 | P4RT 経路の挙動 |
|------|------------------------------------------------|---------------------|------------------|
| サポート ASIC | 正確な残り作成可能数を返す | ADD 前にチェック、`availCount=0` で reject | チェックなし、SAI create で失敗 |
| 非サポート ASIC (NOT_SUPPORTED / NOT_IMPLEMENTED) | エラー | warn ログ後 ADD 続行 | 同じく ADD 続行 |

## 差異 5: TC (Traffic Class) 属性のサポート差 (両経路共通)

`mirrororch.cpp:931-938`:

```cpp
// Some platforms don't support SAI_MIRROR_SESSION_ATTR_TC and only
// support global mirror session traffic class.
if (session.queue != 0)
{
    attr.id = SAI_MIRROR_SESSION_ATTR_TC;
    ...
}
```

CONFIG_DB 側は `queue=0` のとき `SAI_MIRROR_SESSION_ATTR_TC` を **付加しない** ことで、TC 属性非対応 ASIC との後方互換を保つ。
P4RT 側は TC フィールドを APP_DB スキーマに持たないので、常に SAI デフォルト TC で作成される (= global TC) ため互換問題は発生しない。

## 差異 6: Multi-ASIC (namespace) サポート

CONFIG_DB 側 `MirrorOrch` は namespace ごとに orchagent インスタンスが起動するため、multi-asic シャーシ (Broadcom DNX / Cisco 8000 など) では asic ごとに独立した `MIRROR_SESSION` テーブルを購読する。
P4RT 側 `MirrorSessionManager` も同様だが、APPL_DB は asic ごとの DB なので、書き込み側 (P4RT controller) が asic を選択する必要がある。
本ページ範囲では multi-asic 固有の追加分岐は **mirrororch.cpp / mirror_session_manager.cpp とも存在せず**、上位 orchagent の起動制御 (`orchdaemon.cpp`) に委ねられる。

## 差異 7: PolicerOrch 連携 (P4RT 側に該当なし)

`mirrororch.cpp:1052-1064`:

CONFIG_DB 側は `MIRROR_SESSION.policer` フィールドで CONFIG_DB `POLICER` テーブルを参照し、`PolicerOrch::getPolicerOid()` で OID を解決して `SAI_MIRROR_SESSION_ATTR_POLICER` に設定する。
P4RT 側 `FIXED_MIRROR_SESSION_TABLE` には **policer フィールドが存在しない** (`p4orch_util.h::P4MirrorSessionAppDbEntry`)。
したがって P4RT 経由 ERSPAN セッションは policer 連携不可。これは ASIC が policer 連携をサポートしていても **P4RT 経路では利用不可能** という機能差として現れる。

## 結論

`APPL_DB FIXED_MIRROR_SESSION_TABLE` (P4RT) は MirrorOrch (CONFIG_DB) と SAI mirror_session を共有するが、P4RT 側マネージャは platform 分岐コードを一切持たない。
このため Mellanox の GRE type 差・VoQ の monitor_port 置換・policer 連携が **P4RT 経路では再現されない**。
SAI レベルの ASIC capability (TC 属性、ingress/egress mirror、リソース枯渇) も CONFIG_DB 経路の事前 fail-fast に頼っているため、P4RT 経路では SAI create 失敗時に初めて検出される。
