# VXLAN_TUNNEL — Phase A: Implicit Defaults & Code-derived Behaviors

## Field enumeration

| フィールド | YANG 型 | 必須 | YANG default |
|-----------|---------|------|-------------|
| `name` (key) | string | ✅ | なし |
| `src_ip` | inet:ip-address | - | なし |
| `dst_ip` | inet:ip-address | - | なし |
| `ttl_mode` | string (uniform\|pipe) | - | なし |

---

## コード由来の暗黙デフォルト / fallback

### 1. `ttl_mode` — NOT_SET (SAI 属性未設定)

**根拠**: `vxlanorch.cpp:1617`
```cpp
VxlanTunnelTTLMode ttl_mode = VxlanTunnelTTLMode::NOT_SET;
if (attr_names.find("ttl_mode") != attr_names.end()) { ... }
```

**根拠**: `vxlanorch.h:142-146`
```cpp
enum class VxlanTunnelTTLMode { NOT_SET, PIPE, UNIFORM };
```

**根拠**: `vxlanorch.cpp:372-383` create_tunnel()
```cpp
if (decap_ttl_mode == VxlanTunnelTTLMode::PIPE) {
    // SAI_TUNNEL_ATTR_DECAP_TTL_MODE = SAI_TUNNEL_TTL_MODE_PIPE_MODEL
} else if (decap_ttl_mode == VxlanTunnelTTLMode::UNIFORM) {
    // SAI_TUNNEL_ATTR_DECAP_TTL_MODE = SAI_TUNNEL_TTL_MODE_UNIFORM_MODEL
}
// NOT_SET の場合は SAI_TUNNEL_ATTR_DECAP_TTL_MODE を設定しない
```

**結論**: `ttl_mode` 省略時は `SAI_TUNNEL_ATTR_DECAP_TTL_MODE` が SAI に渡されない。SAI 実装依存のデフォルト (通常 PIPE または UNIFORM) が適用される。YANG にデフォルト値の定義なし、orchagent も fallback を明示しない — **プラットフォーム依存の silent default**。

---

### 2. `dst_ip` 省略 — P2MP モード (SAI_TUNNEL_PEER_MODE_P2MP)

**根拠**: `vxlanorch.cpp:1598-1605`
```cpp
if (attr_names.find("dst_ip") == attr_names.end()) {
    if (src_ip.isV4()) dst_ip = IpAddress("0.0.0.0");
    else               dst_ip = IpAddress("::");
}
```

**根拠**: `vxlanorch.cpp:356-370`
```cpp
if ((dst_ip != nullptr) && p2p) {
    attr.id = SAI_TUNNEL_ATTR_PEER_MODE; attr.value.s32 = SAI_TUNNEL_PEER_MODE_P2P;
    attr.id = SAI_TUNNEL_ATTR_ENCAP_DST_IP; ...
} else {
    attr.id = SAI_TUNNEL_ATTR_PEER_MODE; attr.value.s32 = SAI_TUNNEL_PEER_MODE_P2MP;
}
```

さらに `VxlanTunnel::createTunnelHw()` で `p2p = (src_creation_ == TNL_CREATION_SRC_EVPN)? true:false`。
CLI 経由 (`TNL_CREATION_SRC_CLI`) では `dst_ip` が 0.0.0.0 のときは `p2p=false` となり P2MP になる。

**結論**: `dst_ip` 省略 → ゼロ IP に置換 → `SAI_TUNNEL_PEER_MODE_P2MP`。EVPN 用 VTEP として動作。

---

### 3. `src_ip` 省略 — `isTunnelActive()` が false を返してマップ処理がブロック

**根拠**: `vxlanmgr.cpp:1318`
```cpp
if (m_vxlanTunnelCache[vxlanTunnelName].m_sourceIp == "NULL") return false;
```

**根拠**: `vxlanmgr.cpp:420-421`
```cpp
tuncache.m_sourceIp = "NULL";
// src_ip フィールドが存在するときのみ上書きされる
```

**結論**: `src_ip` が CONFIG_DB エントリに存在しない場合、キャッシュの `m_sourceIp` は `"NULL"` のまま。`isTunnelActive()` は false を返し、後続の `VXLAN_TUNNEL_MAP` 処理が永遠にサスペンドされる (**dead-consumer / silent drop 経路**)。
CLI の `config vxlan add` は `src_ip` を必須引数として要求するため、この状態は直接 DB 書き込みでのみ発生しうる。

---

### 4. `src_ip` — SAI_TUNNEL_ATTR_ENCAP_SRC_IP への反映

**根拠**: `vxlanorch.cpp:347-353`
```cpp
if (src_ip != nullptr) {
    attr.id = SAI_TUNNEL_ATTR_ENCAP_SRC_IP;
    attr.value.ipaddr = *src_ip;
    tunnel_attrs.push_back(attr);
}
```

`src_ip` が IpAddress として parse されたときのみ SAI に設定される。NULL ポインタの場合は属性ごと省略 → SAI 実装依存。

---

### 5. `encap_ttl` — SAI_TUNNEL_ATTR_ENCAP_TTL_VAL (CONFIG_DB には存在しない)

**根拠**: `vxlanorch.cpp:385-394`
```cpp
if (encap_ttl != 0) {
    attr.id = SAI_TUNNEL_ATTR_ENCAP_TTL_MODE; attr.value.s32 = SAI_TUNNEL_TTL_MODE_PIPE_MODEL;
    attr.id = SAI_TUNNEL_ATTR_ENCAP_TTL_VAL; attr.value.u8 = encap_ttl;
}
```

`createTunnelHw()` の呼び出し元が `encap_ttl=0` を渡せば属性は省略。CONFIG_DB の `VXLAN_TUNNEL` テーブルに `encap_ttl` フィールドは YANG に存在しない — **dead field / ハードコード 0 (省略)**。

---

### 6. vxlanmgrd の `dstport 4789` ハードコード

**根拠**: `vxlanmgr.cpp:67`
```cpp
cmd << " dstport 4789";
```

`VXLAN_TUNNEL` テーブルに UDP ポート設定フィールドはなく、VTEP netdevice の dstport は常に **4789 固定**。

---

### 7. `nolearning` ハードコード (EVPN netdevice)

**根拠**: `vxlanmgr.cpp:1015`
```cpp
link_add_cmd = ... + " nolearning " + " dstport 4789 ";
```

`createVxlanNetdevice()` で作成する EVPN netdevice は常に `nolearning` フラグ付き。CONFIG_DB に制御フィールドなし — **暗黙ハードコード**。EVPN NVO が登録済みの場合はさらに `bridge link set dev ... learning off` が追加される (`vxlanmgr.cpp:1046-1049`)。

---

### 8. CLI: `config vxlan add` は `dst_ip` / `ttl_mode` を書かない

**根拠**: `sonic-utilities/config/vxlan.py:47`
```python
fvs = {'src_ip': src_ip}
config_db.set_entry('VXLAN_TUNNEL', vxlan_name, fvs)
```

CLI は `src_ip` のみを書き込む。`dst_ip` と `ttl_mode` は常に省略 → EVPN P2MP / SAI-default TTL mode が暗黙的に適用される。

---

### 9. YANG-実装 discrepancy: `ttl_mode` YANG reject vs. 実装エラーログ

YANG `pattern "uniform|pipe"` は Yang バリデーション層で reject するが、orchagent は独自に文字列比較して invalid の場合 `SWSS_LOG_ERROR` で戻る (`vxlanorch.cpp:1631`)。二重バリデーション経路が存在する — 互いの挙動は等価だが、管理面バイパス時には orchagent 側のみが作動する。

---

### 10. 経路依存乖離: 書込み順依存

`VXLAN_TUNNEL` が存在しない状態で `VXLAN_TUNNEL_MAP` が先に書かれると、`isTunnelActive()` が false を返し MAP 処理がサスペンドされる。その後 `VXLAN_TUNNEL` が書かれても vxlanmgrd がリトライするまで MAP は処理されない（`toSync` キューのポーリング間隔次第）。

---

## 要約テーブル

| フィールド | デフォルト/挙動 | 分類 |
|-----------|---------------|------|
| `ttl_mode` 省略 | SAI_TUNNEL_ATTR_DECAP_TTL_MODE 未設定 → プラットフォーム依存 | プラットフォーム依存 silent default |
| `dst_ip` 省略 | 0.0.0.0 / `::` に置換、SAI P2MP モード | 暗黙フォールバック |
| `src_ip` 省略 (直接 DB 書き込み) | `isTunnelActive()=false`、MAP 永遠サスペンド | dead-consumer / silent drop |
| `encap_ttl` | CONFIG_DB に存在しない、常に 0 → SAI 属性省略 | YANG 未定義フィールド / dead field |
| UDP dstport | 4789 ハードコード | ハードコード |
| learning | `nolearning` ハードコード | ハードコード |
| CLI `dst_ip`/`ttl_mode` | 常に省略 | 書込み元依存 |
| 書込み順 | MAP が TUNNEL より先の場合サスペンド | 書込み順依存 |
