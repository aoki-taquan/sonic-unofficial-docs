# MIRROR_SESSION Phase A: コード由来の暗黙デフォルト

**対象**: `docs/reference/config-db/mirror-session.md`
**調査日**: 2026-05-14
**evidence**: `sonic-swss/orchagent/mirrororch.cpp`, `sonic-swss/orchagent/mirrororch.h`, `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-mirror-session.yang`

---

## フィールド別デフォルト・暗黙挙動マトリクス

### フィールド列挙と初期化経路

`MirrorEntry` 構造体 (`mirrororch.h:32-65`) と コンストラクタ (`mirrororch.cpp:57-77`) によるC++初期化:

```
status   = false   (C++ init)
dscp     = 8       (コンストラクタ hardcode)
ttl      = 255     (コンストラクタ hardcode)
queue    = 0       (コンストラクタ hardcode)
sessionId= 0       (C++ init)
refCount = 0       (C++ init)
greType  = 0x8949 (Mellanox) or 0x88be (その他)  (platform 条件分岐)
direction= ""      (string デフォルト空文字)
type     = ""      (string デフォルト空文字)
policer  = ""      (string デフォルト空文字)
src_port = ""      (string デフォルト空文字)
dst_port = ""      (string デフォルト空文字)
```

### field ごとの詳細

| フィールド | YANG default | C++ 初期値 | CONFIG_DB 省略時の実挙動 | 種別 |
|-----------|-------------|------------|--------------------------|------|
| `type` | `ERSPAN` | `""` (空文字) | `entry.type == MIRROR_SESSION_SPAN` は false → ERSPAN 経路 (RouteOrch attach)。YANG default が有効 | YANG default 一致 |
| `gre_type` | `0x88be` | `0x88be` (非 Mellanox) / `0x8949` (Mellanox) | **Mellanox プラットフォームでは YANG default (0x88be) より `0x8949` が優先される** | プラットフォーム依存 discrepancy |
| `dscp` | (なし) | `8` (hardcode) | CONFIG_DB に `dscp` がなくても SAI に DSCP=8 (CS1) が渡る。TOS = `8 << 2 = 32` | ハードコード fallback |
| `ttl` | (なし) | `255` (hardcode) | CONFIG_DB に `ttl` がなくても SAI に TTL=255 が渡る | ハードコード fallback |
| `queue` | (なし) | `0` (hardcode) | `queue=0` のとき `SAI_MIRROR_SESSION_ATTR_TC` は **SAI に push されない** (line 933: `if (session.queue != 0)`)。プラットフォーム global TC を使用 | ハードコード + silent drop of SAI attr |
| `direction` | `BOTH` | `""` (空文字) | `configurePortMirrorSession()` で `direction == "RX"`, `"TX"`, `"BOTH"` のいずれにもマッチしない → src_port が指定されていても **RX/TX ともに setUnsetPortMirror が呼ばれない** (silent drop) | YANG-実装 discrepancy (YANG は BOTH default だが、YANG から CONFIG_DB に書かれない場合 orchagent は空文字で処理) |
| `policer` | (なし) | `""` (空文字) | policer 未指定時は PolicerOrch 呼び出しなし | 正常 (任意フィールド) |
| `src_port` | (なし) | `""` (空文字) | src_port 未指定時は `configurePortMirrorSession()` の tokenize が空 → src_port 設定をスキップ | 正常 (任意フィールド) |
| `dst_port` | (なし) | `""` (空文字) | SPAN 時に dst_port 未指定: `activateSession` は呼ばれない (SPAN + dst_port.empty() → ERSPAN 経路へ落ちる) | 経路依存乖離 |
| `m_maxNumTC` | - | SAI 取得失敗時 `255` (hardcode) | SAI が TC 数を返さない場合、queue バリデーションが実質無効化 | ハードコード fallback |
| `VLAN_PRI` / `VLAN_CFI` | - | `0` / `0` (hardcode マクロ) | ERSPAN nexthop が VLAN ポート経由の場合、VLAN outer header に PRI=0, CFI=0 が固定で付与 | ハードコード |

---

## 重要な discrepancy 詳細

### 1. `direction` = 空文字: silent drop (最重要)

**経路**: CONFIG_DB `direction` フィールドなし → `MirrorEntry.direction = ""` → `configurePortMirrorSession()`:

```cpp
// mirrororch.cpp:897, 906
if (session.direction == MIRROR_RX_DIRECTION || session.direction == MIRROR_BOTH_DIRECTION)
    setUnsetPortMirror(port, true, set, session.sessionId);   // RX mirror
if (session.direction == MIRROR_TX_DIRECTION || session.direction == MIRROR_BOTH_DIRECTION)
    setUnsetPortMirror(port, false, set, session.sessionId);  // TX mirror
```

`direction=""` はどの条件にもマッチしない → **src_port が設定されていてもミラーリングが起動しない**。

**ただし CLI は自動補完する**: `gather_session_info()` (sonic-utilities `config/main.py:3207-3208`) は `src_port` が指定されていれば `direction` 省略を `"both"` に補完して CONFIG_DB へ書き込む。`src_port` なし + `direction` なしの場合のみ `direction` キーが CONFIG_DB に存在しない。その場合は `src_port` もないので実害なし。

**実害が出るケース**: REST API や直接 DB 操作で `src_port` をセットしつつ `direction` を省略した場合、orchagent は `direction=""` のまま処理し src_port ミラーリングが silent drop になる。

### 2. `greType`: Mellanox では YANG default と異なる

```cpp
// mirrororch.cpp:65-72
if (platform == MLNX_PLATFORM_SUBSTRING)
    greType = 0x8949;
else
    greType = 0x88be;
```

YANG は `default 0x88be` を記載しているが、Mellanox では `0x8949` が暗黙適用される。運用者が `gre_type` を省略した場合、プラットフォームによって異なる GRE type が使用される。

### 3. `dscp` = 8: YANG に default なし、コードで CS1 相当

YANG の `dscp` leaf に `default` 文なし。しかしコードでは `dscp=8` (DSCP 8 = CS1) が SAI TOS として `8<<2=32` で渡る。外側 GRE パケットに DSCP CS1 が付与されることを運用者が意識していないと、QoS ポリシーとの乖離が生じる。

### 4. `queue=0`: SAI_MIRROR_SESSION_ATTR_TC を push しない

```cpp
// mirrororch.cpp:933-938
if (session.queue != 0)
{
    attr.id = SAI_MIRROR_SESSION_ATTR_TC;
    attr.value.u8 = session.queue;
    attrs.push_back(attr);
}
```

`queue=0` のとき `SAI_MIRROR_SESSION_ATTR_TC` は SAI に送らない。コメントに「Some platforms don't support SAI_MIRROR_SESSION_ATTR_TC」とある。プラットフォームによって global TC が使われる。

---

## dead consumer / dead field 調査

- `MIRROR_SESSION_DST_MAC_ADDRESS`, `MIRROR_SESSION_VLAN_ID`, `MIRROR_SESSION_ROUTE_PREFIX`, `MIRROR_SESSION_NEXT_HOP_IP`, `MIRROR_SESSION_MONITOR_PORT`: これらは CONFIG_DB フィールドではなく **STATE_DB (MIRROR_SESSION_TABLE) に書き込まれる** 内部フィールド名。CONFIG_DB の `createEntry()` の parse ループには現れない。dead field ではなく用途の違い。
- minigraph.py の MIRROR_SESSION コードはコメントアウト済みでデッドコード。

---

## 書込み順依存

- `policer` が CONFIG_DB 書き込み時点で未存在 → `task_need_retry` でキュー保留 → policer 追加後に自動再処理。順序依存あり。
- ERSPAN: `createEntry()` が `m_routeOrch->attach()` → RouteOrch callback → `updateSession()` → `activateSession()` の非同期チェーン。route 解決まで inactive。

---

## evidence ソース行

| 知見 | ファイル | 行 |
|------|---------|-----|
| `dscp=8`, `ttl=255`, `queue=0` コンストラクタ | `mirrororch.cpp` | 57-63 |
| `greType` platform 分岐 | `mirrororch.cpp` | 65-72 |
| `queue != 0` 条件で TC push | `mirrororch.cpp` | 933-938 |
| `direction` 空文字 silent drop | `mirrororch.cpp` | 897, 906 |
| VLAN_PRI/CFI = 0 hardcode | `mirrororch.cpp` | 996-1001 |
| m_maxNumTC = 255 fallback | `mirrororch.cpp` | 100-104 |
| YANG `direction default "BOTH"` | `sonic-mirror-session.yang` | 170 |
| YANG `gre_type default 0x88be` | `sonic-mirror-session.yang` | 110 |
| YANG `type default "ERSPAN"` | `sonic-mirror-session.yang` | 74 |
| YANG `dscp` に default なし | `sonic-mirror-session.yang` | 115-125 |
| YANG `ttl` に default なし | `sonic-mirror-session.yang` | 127-136 |
| YANG `queue` に default なし | `sonic-mirror-session.yang` | 139-143 |
