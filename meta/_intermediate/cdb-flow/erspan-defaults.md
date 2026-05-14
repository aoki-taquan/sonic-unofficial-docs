# MIRROR_SESSION ERSPAN 種別 Phase A: コード由来の暗黙デフォルト

**対象**: `docs/reference/config-db/erspan.md`
**調査日**: 2026-05-14
**evidence**: `sonic-swss/orchagent/mirrororch.cpp`, `sonic-swss/orchagent/mirrororch.h`, `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-mirror-session.yang`

---

## 調査スコープ

`MIRROR_SESSION` テーブルのうち `type=ERSPAN` に限定した暗黙デフォルト・コード由来挙動の調査。SPAN 共通フィールド（`src_port`, `direction`, `policer`）も ERSPAN 経路での挙動を対象とする。

---

## フィールド別デフォルト・暗黙挙動マトリクス

### MirrorEntry コンストラクタの初期値 (`mirrororch.cpp:57-77`)

```cpp
MirrorEntry::MirrorEntry(const string& platform) :
        status(false),
        dscp(8),
        ttl(255),
        queue(0),
        sessionId(0),
        refCount(0)
{
    if (platform == MLNX_PLATFORM_SUBSTRING)
        greType = 0x8949;
    else
        greType = 0x88be;
    ...
}
```

### ERSPAN フィールド別詳細

| フィールド | YANG default | C++ 初期値 | CONFIG_DB 省略時の実挙動 | 種別 |
|-----------|-------------|------------|--------------------------|------|
| `type` | `ERSPAN` | `""` (空文字) | `entry.type == MIRROR_SESSION_SPAN` は false → ERSPAN 経路（RouteOrch attach）に落ちる。YANG default が実質有効 | YANG default 一致（C++ 空文字だが条件分岐で ERSPAN 扱い） |
| `gre_type` | `0x88be` | `0x88be` (非 Mellanox) / `0x8949` (Mellanox) | **Mellanox プラットフォームでは YANG default (0x88be) より `0x8949` が優先される** | プラットフォーム依存 discrepancy |
| `dscp` | なし | `8` (hardcode) | CONFIG_DB に `dscp` がなくても SAI に TOS=`8<<2=32` (DSCP 8 = CS1 相当) が渡る | ハードコード fallback — YANG に default 記載なし |
| `ttl` | なし | `255` (hardcode) | CONFIG_DB に `ttl` がなくても SAI に TTL=255 が渡る | ハードコード fallback — YANG に default 記載なし |
| `queue` | なし | `0` (hardcode) | `queue=0` のとき `SAI_MIRROR_SESSION_ATTR_TC` を SAI に push しない（line 933: `if (session.queue != 0)`）。プラットフォーム global TC を使用 | ハードコード + SAI attr silent omit |
| `src_ip` | なし | 未初期化（IpAddress デフォルト） | `src_ip` 省略 + `dst_ip` 省略の場合は ip family 比較をスキップ（`src_ip_initialized && dst_ip_initialized` が false のため）。`SAI_MIRROR_SESSION_ATTR_SRC_IP_ADDRESS` には 0.0.0.0 相当が渡り ASIC が drop する | dead field 相当（YANG when 制約で ERSPAN 必須だが orchagent は non-fatal で処理） |
| `dst_ip` | なし | 未初期化（IpAddress デフォルト）| 同上。YANG では ERSPAN 時必須だが orchagent は type チェックなしで `m_routeOrch->attach(this, entry.dstIp)` を呼ぶ | 書込み順依存—YANG は拒否するが DB 直書き時は orchagent 任せ |
| `direction` | `BOTH` | `""` (空文字) | `configurePortMirrorSession()` で `direction==""` はどの enum にもマッチしない → src_port 指定があっても RX/TX mirror が silent drop | YANG-実装 discrepancy（YANG は `BOTH` default だが DB 省略時に orchagent は空文字で処理） |
| `policer` | なし | `""` (空文字) | 未指定時は PolicerOrch 参照なし（任意フィールド） | 正常 |
| `src_port` | なし | `""` (空文字) | 未指定時は `configurePortMirrorSession()` 内 tokenize が空リスト → src_port 設定スキップ | 正常（任意） |
| `m_maxNumTC` | — | SAI 取得失敗時 `255` (hardcode) | SAI が TC 数を返さない場合、`queue >= m_maxNumTC` のバリデーションが実質無効化（255 以上の uint8 は存在しない） | ハードコード fallback |
| `VLAN_PRI` / `VLAN_CFI` | — | `0` / `0` (マクロ hardcode) | ERSPAN nexthop が VLAN ポート経由の場合、VLAN outer header に PRI=0, CFI=0 が固定付与 | ハードコード — CONFIG_DB から変更不可 |
| `SAI_ERSPAN_ENCAPSULATION_TYPE` | — | `SAI_ERSPAN_ENCAPSULATION_TYPE_MIRROR_L3_GRE_TUNNEL` (hardcode) | ERSPAN カプセル化タイプは GRE トンネル固定。CONFIG_DB からは変更不可 | ハードコード |
| `SAI_MIRROR_SESSION_ATTR_SRC_MAC_ADDRESS` | — | `gMacAddress` (ルータ MAC) | ERSPAN outer header の src MAC はルータ MAC 固定。CONFIG_DB から指定不可 | ハードコード |
| `SAI_MIRROR_SESSION_ATTR_DST_MAC_ADDRESS` | — | neighbor MAC (通常) / gMacAddress (voq) | ERSPAN dst MAC は nexthop neighbor の解決済み MAC。voq switch では router MAC 固定 | プラットフォーム依存 + 動的解決 |

---

## 重要な discrepancy 詳細

### 1. `gre_type`: Mellanox では YANG default (0x88be) と異なる（最重要）

```cpp
// mirrororch.cpp:65-72
if (platform == MLNX_PLATFORM_SUBSTRING)
    greType = 0x8949;
else
    greType = 0x88be;
```

YANG は `default 0x88be` を記載。Mellanox プラットフォームでは `gre_type` を省略すると `0x8949`（ERSPAN Type III / Broadcom 互換）が使われる。対向コレクタが `0x88be`（Cisco）期待の場合、ミラーパケットが parse 不能になる。

### 2. `dscp` = 8: YANG に default なし、コードで CS1 相当を暗黙付与

YANG の `dscp` leaf に `default` 文なし（`sonic-mirror-session.yang:115-125`）。コードでは `dscp=8`（CS1）が `8<<2=32` として TOS フィールドに付与される。CONFIG_DB に `dscp` を書かない運用者は外側 GRE パケットに DSCP CS1 が付与されることを認識しにくい。

### 3. `ttl` = 255: YANG に default なし、コードで最大値を暗黙付与

YANG の `ttl` leaf に `default` 文なし（`sonic-mirror-session.yang:127-136`）。コードでは `ttl=255` がデフォルトであり、ERSPAN パケットが TTL 255 で送出される。ループ / ECMP 経路での TTL 消費が意図通りかを確認する必要がある。

### 4. `queue = 0`: `SAI_MIRROR_SESSION_ATTR_TC` を SAI に push しない

```cpp
// mirrororch.cpp:933-938
if (session.queue != 0)
{
    attr.id = SAI_MIRROR_SESSION_ATTR_TC;
    attr.value.u8 = session.queue;
    attrs.push_back(attr);
}
```

`queue=0` のとき TC 属性を SAI に送らない。コメント「Some platforms don't support SAI_MIRROR_SESSION_ATTR_TC」。プラットフォームの global mirror TC が使用される。`queue` の YANG 記載は「ERSPAN Queue」だが、実際は SPAN にも適用される。

### 5. `direction` = 空文字: src_port があっても silent drop

```cpp
// mirrororch.cpp:897, 906
if (session.direction == MIRROR_RX_DIRECTION || session.direction == MIRROR_BOTH_DIRECTION)
    setUnsetPortMirror(port, true, set, session.sessionId);
if (session.direction == MIRROR_TX_DIRECTION || session.direction == MIRROR_BOTH_DIRECTION)
    setUnsetPortMirror(port, false, set, session.sessionId);
```

CONFIG_DB に `direction` が存在しない場合 `direction=""` → どの条件にもマッチしない → src_port ポートにミラーセッションが attach されない。CLI (`config mirror_session add`) は `src_port` 指定時に `direction` を自動補完するが、REST API / 直接 DB 操作では補完なし。

### 6. ERSPAN 開始タイミング: RouteOrch callback 依存

`createEntry()` → `m_routeOrch->attach(this, entry.dstIp)` → RouteOrch callback → `updateSession()` → `activateSession()`。dst_ip のルート解決まで SESSION は **inactive** のまま。解決まで数 ms〜数十 ms。静的ルートがなければ永久に inactive。

### 7. voq switch での dst MAC / monitor port 変更

```cpp
// mirrororch.cpp:1037-1044
if ((gMySwitchType == "voq") && (session.type == MIRROR_SESSION_ERSPAN))
    memcpy(attr.value.mac, gMacAddress.getMac(), sizeof(sai_mac_t));
else
    memcpy(attr.value.mac, session.neighborInfo.mac.getMac(), sizeof(sai_mac_t));
```

voq switch では dst MAC がルータ MAC に固定され、monitor port も recirc port に置換される。CONFIG_DB の dst_ip 指定と実際の ERSPAN パケット経路が大きく異なる。

---

## dead field / dead consumer 調査

- `MIRROR_SESSION_DST_MAC_ADDRESS`, `MIRROR_SESSION_MONITOR_PORT`, `MIRROR_SESSION_ROUTE_PREFIX`, `MIRROR_SESSION_NEXT_HOP_IP`, `MIRROR_SESSION_VLAN_ID`: これらは CONFIG_DB フィールドではなく **STATE_DB** `MIRROR_SESSION_TABLE` に書き込まれる内部フィールド。CONFIG_DB の `createEntry()` parse ループには存在しない。dead field ではなく用途の違い。
- minigraph.py の MIRROR_SESSION コードはコメントアウト済みでデッドコード（`minigraph.py:2721`）。
- REST / gNMI の MIRROR_SESSION トランスフォーマーは未実装 → REST 経由の書き込みは不可。

---

## 書込み順依存

- `policer` 指定時、policer が CONFIG_DB に存在しなければ `task_need_retry` → policer 追加後に自動再処理。順序依存あり。
- ERSPAN: `dst_ip` のルート解決が完了するまで inactive → route 追加後に RouteOrch callback → activateSession()。
- `src_ip`/`dst_ip` は YANG `when` 制約で `type=ERSPAN` のときのみ有効。CLI は type 確認後に書くが、DB 直書きでは type と ip を同時または type 先に書く必要あり（orchagent は `createEntry()` で一括処理するため順序は不要だが、YANG バリデーション段階では必要）。

---

## evidence ソース行

| 知見 | ファイル | 行 |
|------|---------|-----|
| `dscp=8`, `ttl=255`, `queue=0` コンストラクタ | `mirrororch.cpp` | 57-63 |
| `greType` platform 分岐 (Mellanox 0x8949) | `mirrororch.cpp` | 65-72 |
| `queue != 0` 条件で TC push | `mirrororch.cpp` | 933-938 |
| `SAI_ERSPAN_ENCAPSULATION_TYPE_MIRROR_L3_GRE_TUNNEL` hardcode | `mirrororch.cpp` | 1005-1007 |
| IPHDR_VERSION: dstIp.isV4() で 4 or 6 | `mirrororch.cpp` | 1009-1011 |
| TOS = `dscp << 2` | `mirrororch.cpp` | 1015-1017 |
| src MAC = gMacAddress hardcode | `mirrororch.cpp` | 1031-1033 |
| dst MAC: neighbor MAC / voq=gMacAddress | `mirrororch.cpp` | 1035-1045 |
| `direction` 空文字 silent drop | `mirrororch.cpp` | 897, 906 |
| VLAN_PRI/CFI = 0 hardcode | `mirrororch.cpp` | 996-1001 |
| m_maxNumTC = 255 fallback | `mirrororch.cpp` | 100-104 |
| voq recirc port | `mirrororch.cpp` | 961-975 |
| YANG `direction default "BOTH"` | `sonic-mirror-session.yang` | 170 |
| YANG `gre_type default 0x88be` | `sonic-mirror-session.yang` | 110 |
| YANG `type default "ERSPAN"` | `sonic-mirror-session.yang` | 74 |
| YANG `dscp` に default なし | `sonic-mirror-session.yang` | 115-125 |
| YANG `ttl` に default なし | `sonic-mirror-session.yang` | 127-136 |
| YANG `queue` に default なし | `sonic-mirror-session.yang` | 139-143 |
