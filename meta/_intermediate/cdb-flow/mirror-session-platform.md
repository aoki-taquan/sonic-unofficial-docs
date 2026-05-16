# MIRROR_SESSION — Phase H: プラットフォーム差

## 調査対象ソース

- `sonic-net/sonic-swss`
  - `orchagent/mirrororch.cpp`
    - `MirrorEntry::MirrorEntry()` L57-77 — `platform` 環境変数で GRE type を分岐
    - `MirrorOrch::MirrorOrch()` L79-110 — `SAI_SWITCH_ATTR_QOS_MAX_NUMBER_OF_TRAFFIC_CLASSES` で ASIC TC 数を取得
    - `MirrorOrch::isHwResourcesAvailable()` L357-379 — `sai_object_type_get_availability(SAI_OBJECT_TYPE_MIRROR_SESSION)` で ASIC リソース照会
    - `MirrorOrch::setUnsetPortMirror()` L811-826 — `SwitchOrch::isPortIngressMirrorSupported()` / `isPortEgressMirrorSupported()` による ASIC capability チェック
    - `MirrorOrch::activateSession()` L921-1067 — `gMySwitchType == "voq"` 分岐 + VLAN nexthop 分岐 + TC 属性スキップ

---

## プラットフォーム識別方法

`MirrorOrch` は以下 2 種のプラットフォーム識別を行う。

1. **`getenv("platform")`** (L395) — `MirrorEntry` コンストラクタに渡し、GRE protocol type を分岐。`DEVICE_METADATA|localhost|platform` を `sonic-cfggen` が起動スクリプト経由で環境変数として注入する。CONFIG_DB への直接アクセスではなく、コンテナ起動時 one-shot。
2. **`gMySwitchType`** — `DEVICE_METADATA|localhost|switch_type` 由来のグローバル変数。VoQ (Cisco 8000 等の分散シャーシ) 向け特殊処理に使用。

---

## 差異 1: GRE protocol type — Mellanox vs それ以外

`mirrororch.cpp:57-77`:

```cpp
MirrorEntry::MirrorEntry(const string& platform) :
        dscp(8), ttl(255), queue(0), ...
{
    if (platform == MLNX_PLATFORM_SUBSTRING)
        greType = 0x8949;
    else
        greType = 0x88be;
}
```

| プラットフォーム | `gre_type` 省略時のデフォルト | SAI 属性 | 備考 |
|---|---|---|---|
| **Mellanox (Spectrum)** | `0x8949` | `SAI_MIRROR_SESSION_ATTR_GRE_PROTOCOL_TYPE = 0x8949` | YANG default `0x88be` と乖離 |
| Broadcom / Barefoot / Cisco-8000 / Marvell / 他 | `0x88be` | `SAI_MIRROR_SESSION_ATTR_GRE_PROTOCOL_TYPE = 0x88be` | YANG default と一致 |

CLI で `gre_type` を明示指定した場合はその値を優先するため、上書きにより Mellanox でも `0x88be` を設定可能。ただし Mellanox Spectrum ASIC が `0x88be` を受け付けるかはベンダー実装次第。

---

## 差異 2: ASIC TC (Traffic Class) サポート差 — queue=0 の SAI_MIRROR_SESSION_ATTR_TC スキップ

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

- `queue = 0`（デフォルト）のとき `SAI_MIRROR_SESSION_ATTR_TC` は SAI に渡さない。一部 ASIC が `SAI_MIRROR_SESSION_ATTR_TC` を非対応のため、設定を省略することで後方互換を保つ。
- `queue != 0` を指定した場合のみ TC 属性を push するため、実際に TC 分離が機能するかは ASIC 実装に依存する。

| `queue` 値 | SAI_MIRROR_SESSION_ATTR_TC | 挙動 |
|---|---|---|
| `0` (デフォルト) | **設定しない** | ASIC の global TC を使用 (TC 非対応 ASIC でも動作) |
| `1〜m_maxNumTC-1` | 設定あり | ASIC が対応していれば TC 分離で mirror 転送 |
| `>= m_maxNumTC` | 設定不可 | `createEntry()` で `task_invalid_entry` |

`m_maxNumTC` は起動時 `SAI_SWITCH_ATTR_QOS_MAX_NUMBER_OF_TRAFFIC_CLASSES` で取得。失敗時は `MIRROR_SESSION_DEFAULT_NUM_TC = 255` にフォールバック (バリデーション実質無効化)。

---

## 差異 3: ASIC ingress / egress mirror capability チェック

`mirrororch.cpp:816-826`:

```cpp
if (ingress && !m_switchOrch->isPortIngressMirrorSupported())
{
    SWSS_LOG_ERROR("Port ingress mirror is not supported by the ASIC");
    return false;
}
if (!ingress && !m_switchOrch->isPortEgressMirrorSupported())
{
    SWSS_LOG_ERROR("Port egress mirror is not supported by the ASIC");
    return false;
}
```

`src_port` を指定した SPAN/ERSPAN セッションをポートに bind する直前に `SwitchOrch` が SAI から取得した ASIC capability を照会する。

| ASIC | ingress mirror (RX) | egress mirror (TX) | direction=BOTH |
|---|---|---|---|
| 一般的な ASIC (Broadcom, Mellanox, Barefoot, Cisco-8000) | サポート | サポート | サポート |
| ingress のみの ASIC (一部ホワイトボックス) | サポート | **非対応 → bind 拒否** | TX 方向が拒否される |
| egress のみの ASIC | **非対応 → bind 拒否** | サポート | RX 方向が拒否される |

セッション自体（SAI mirror_session オブジェクト）は capability に関わらず作成されるが、`configurePortMirrorSession()` (src_port bind) のみが拒否される。

---

## 差異 4: ERSPAN SAI mirror_session attr マトリクス (SPAN vs ERSPAN)

| SAI 属性 | SPAN (SAI_MIRROR_SESSION_TYPE_LOCAL) | ERSPAN (SAI_MIRROR_SESSION_TYPE_ENHANCED_REMOTE) |
|---|---|---|
| `SAI_MIRROR_SESSION_ATTR_TYPE` | `SAI_MIRROR_SESSION_TYPE_LOCAL` | `SAI_MIRROR_SESSION_TYPE_ENHANCED_REMOTE` |
| `SAI_MIRROR_SESSION_ATTR_MONITOR_PORT` | `dst_port` の OID | nexthop 解決済みポート (VoQ: recirc port) |
| `SAI_MIRROR_SESSION_ATTR_TC` | queue!=0 時のみ | queue!=0 時のみ |
| `SAI_MIRROR_SESSION_ATTR_ERSPAN_ENCAPSULATION_TYPE` | (なし) | `SAI_ERSPAN_ENCAPSULATION_TYPE_MIRROR_L3_GRE_TUNNEL` |
| `SAI_MIRROR_SESSION_ATTR_IPHDR_VERSION` | (なし) | `4` (IPv4) or `6` (IPv6) |
| `SAI_MIRROR_SESSION_ATTR_TOS` | (なし) | `dscp << 2` (DSCP 6bit + ECN 2bit = 8bit) |
| `SAI_MIRROR_SESSION_ATTR_TTL` | (なし) | `ttl` (デフォルト 255) |
| `SAI_MIRROR_SESSION_ATTR_SRC_IP_ADDRESS` | (なし) | `src_ip` |
| `SAI_MIRROR_SESSION_ATTR_DST_IP_ADDRESS` | (なし) | `dst_ip` |
| `SAI_MIRROR_SESSION_ATTR_SRC_MAC_ADDRESS` | (なし) | `gMacAddress` (router MAC) |
| `SAI_MIRROR_SESSION_ATTR_DST_MAC_ADDRESS` | (なし) | `neighborInfo.mac` (VoQ: `gMacAddress`) |
| `SAI_MIRROR_SESSION_ATTR_GRE_PROTOCOL_TYPE` | (なし) | `greType` (Mellanox: `0x8949` / 他: `0x88be`) |
| `SAI_MIRROR_SESSION_ATTR_POLICER` | policer 指定時のみ | policer 指定時のみ |
| `SAI_MIRROR_SESSION_ATTR_VLAN_HEADER_VALID` | (なし) | VLAN nexthop 時のみ `true` |
| `SAI_MIRROR_SESSION_ATTR_VLAN_TPID` | (なし) | VLAN nexthop 時のみ `ETH_P_8021Q` |
| `SAI_MIRROR_SESSION_ATTR_VLAN_ID` | (なし) | VLAN nexthop 時のみ |
| `SAI_MIRROR_SESSION_ATTR_VLAN_PRI` | (なし) | VLAN nexthop 時のみ `0` |
| `SAI_MIRROR_SESSION_ATTR_VLAN_CFI` | (なし) | VLAN nexthop 時のみ `0` |

---

## 差異 5: VoQ スイッチ向け特殊処理

`mirrororch.cpp:961-973, 1037-1044`:

ERSPAN セッションかつ `gMySwitchType == "voq"` の場合に以下の差し替えが行われる。

| SAI 属性 | 非 VoQ | VoQ (Cisco 8000 等) |
|---|---|---|
| `SAI_MIRROR_SESSION_ATTR_MONITOR_PORT` | nexthop 解決済みポート OID | **recirc port OID** (recirc 取得失敗なら `activateSession()` が `false` 返却) |
| `SAI_MIRROR_SESSION_ATTR_DST_MAC_ADDRESS` | `neighborInfo.mac` (ARP/NDP 解決済み) | **`gMacAddress`** (router MAC を強制使用) |

SPAN セッションには VoQ 分岐なし（SPAN は dst_port に直接送出するため）。

---

## 差異 6: SAI mirror_session リソース上限 (isHwResourcesAvailable)

`mirrororch.cpp:357-379`:

```cpp
sai_status_t status = sai_object_type_get_availability(
    gSwitchId, SAI_OBJECT_TYPE_MIRROR_SESSION, 0, nullptr, &availCount
);
```

| ASIC 挙動 | `isHwResourcesAvailable()` 結果 | セッション ADD への影響 |
|---|---|---|
| 残余 session 数を正確に返す | `availCount > 0` なら `true` | 上限超過時に `task_failed` (事前 fail-fast) |
| `SAI_STATUS_NOT_SUPPORTED` / `NOT_IMPLEMENTED` を返す | `true` (スキップ) | warn ログを出して ADD 続行 |
| その他 SAI エラー | `parseHandleSaiStatusFailure` | SAI エラーハンドラに委ねる |

`SAI_STATUS_NOT_SUPPORTED` の ASIC では CRM チェックが実質無効化される。

---

## まとめ: プラットフォーム別挙動マトリクス

| プラットフォーム / 条件 | gre_type デフォルト | SAI_MIRROR_SESSION_ATTR_TC | ingress/egress capability | VoQ 特殊処理 | CRM チェック |
|---|---|---|---|---|---|
| **Mellanox (Spectrum)** | `0x8949` | queue!=0 時のみ付加 | 通常サポート | なし | ASIC 依存 |
| **Broadcom** | `0x88be` | queue!=0 時のみ付加 | 通常サポート | なし | ASIC 依存 |
| **Cisco-8000 (VoQ)** | `0x88be` | queue!=0 時のみ付加 | 通常サポート | **recirc port + router MAC** | ASIC 依存 |
| TC 非対応 ASIC (任意) | プラットフォーム依存 | **付加しない (`queue=0`)** | 通常サポート | なし | ASIC 依存 |
| CRM 非対応 ASIC (任意) | プラットフォーム依存 | queue!=0 時のみ付加 | 通常サポート | なし | **スキップ (warn)** |
