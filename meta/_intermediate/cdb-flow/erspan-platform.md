# ERSPAN (CONFIG_DB MIRROR_SESSION) — Phase H: プラットフォーム差

## 調査対象ソース

- `sonic-net/sonic-swss` @ `4305596156d70e9797e8a881b3d19b46de0bce0d`
  - `orchagent/mirrororch.cpp`
    - `MirrorEntry::MirrorEntry()` L57-77 — `platform` 環境変数で GRE type を分岐
    - `MirrorOrch::isHwResourcesAvailable()` L357-379 — SAI session 枯渇 / 未サポート検出
    - `MirrorOrch::setUnsetPortMirror()` L817-826 — Ingress/Egress mirror ASIC capability チェック
    - `MirrorOrch::activateSession()` L931-938 — TC (queue) 設定: 一部 ASIC は global TC のみ
    - `MirrorOrch::activateSession()` L961-969 — VoQ: ERSPAN monitor port を recirc port に置換
    - `MirrorOrch::activateSession()` L1037-1041 — VoQ: ERSPAN DST MAC を gMacAddress (router mac) に置換
  - `orchagent/orch.h` L42 — `MLNX_PLATFORM_SUBSTRING = "mellanox"`

## 差異 1: GRE protocol type の Mellanox 分岐

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

`platform` は `MirrorOrch::addEntry()` (L395) で `getenv("platform")` から取得される。完全一致比較 (`== "mellanox"`)。

| プラットフォーム | デフォルト `gre_type` | YANG `default` | 状態 |
|----------------|----------------------|----------------|------|
| mellanox | `0x8949` (ERSPAN Type III / Broadcom 互換) | `0x88be` | YANG と乖離 |
| その他全て | `0x88be` (ERSPAN Type II / Cisco 準拠) | `0x88be` | 一致 |

## 差異 2: TC (Traffic Class) 属性のプラットフォーム非対応

`mirrororch.cpp:931-938`:

```cpp
// Some platforms don't support SAI_MIRROR_SESSION_ATTR_TC and only
// support global mirror session traffic class.
if (session.queue != 0)
{
    attr.id = SAI_MIRROR_SESSION_ATTR_TC;
    attr.value.u8 = session.queue;
    attrs.push_back(attr);
}
```

`queue=0`（省略時デフォルト）のときは `SAI_MIRROR_SESSION_ATTR_TC` を SAI に送信しない。プラットフォームの global mirror session TC が使われる。`queue >= 1` の場合のみ TC 属性を push するが、SAI 未対応 ASIC では `sai_mirror_api->create_mirror_session()` がエラーを返す可能性がある。

## 差異 3: VoQ シャーシ — monitor port と DST MAC の置換

VoQ シャーシ (`gMySwitchType == "voq"`) + ERSPAN 組み合わせで 2 箇所のフィールドが自動置換される。

### monitor port: recirc port に置換

通常 ERSPAN では `SAI_MIRROR_SESSION_ATTR_MONITOR_PORT` に宛先の物理ポート OID を設定するが、VoQ では `getRecircPort(recirc_port, Port::Role::Rec)` で取得した recirc port OID を使用する (`mirrororch.cpp:961-969`)。

### DST MAC: gMacAddress (router MAC) に置換

通常 ERSPAN では NEP 解決済みの隣接 MAC を DST MAC に使用するが、VoQ では `gMacAddress`（スイッチの router MAC）を設定する (`mirrororch.cpp:1037-1041`)。VoQ シャーシでは宛先 IP への L3 転送はチャーシスファブリック側が担当するため、GRE パケットの outer MAC は router MAC で十分。

## 差異 4: ハードウェアリソース可用性の SAI 依存

`MirrorOrch::isHwResourcesAvailable()` (L357-379) が `sai_object_type_get_availability(SAI_OBJECT_TYPE_MIRROR_SESSION)` を呼ぶ。

- SAI が `SAI_STATUS_NOT_SUPPORTED` / `SAI_STATUS_NOT_IMPLEMENTED` を返す場合: ログ警告を出して `true`（利用可能）として扱う — リソース上限監視を省略
- AvailCount が 0 の場合: `createEntry()` 内で early return し `task_need_retry` を返す
- AvailCount > 0 の場合: 通常フロー継続

## 差異 5: Ingress / Egress mirror ASIC capability チェック

`setUnsetPortMirror()` (L817-826) で `SwitchOrch::isPortIngressMirrorSupported()` / `isPortEgressMirrorSupported()` を確認。Ingress mirror 非対応 ASIC では ingress 方向の mirror 設定が SAI エラーなしに静かに失敗（エラーログのみ）。
