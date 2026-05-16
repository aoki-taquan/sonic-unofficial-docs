# TUNNEL_ENCAP_TABLE (FIXED_TUNNEL_TABLE / P4RT GRE Encap) — Phase A: Implicit Defaults & Code-derived Behaviors

## 対象テーブル

`APPL_DB: P4RT_TABLE:FIXED_TUNNEL_TABLE:<json_key>`

- `APP_P4RT_TUNNEL_TABLE_NAME = "FIXED_TUNNEL_TABLE"` (schema.h:72)
- 管理ロール: `GreTunnelManager` (`sonic-swss/orchagent/p4orch/gre_tunnel_manager.cpp`)
- P4RT controller が書き込み → orchagent が SAI GRE トンネル (IP-in-IP GRE encap) を作成

---

## フィールド列挙

| フィールド | 型 | 必須 | YANG/スキーマ default |
|-----------|-----|------|----------------------|
| `tunnel_id` (key: match フィールド) | string | ✅ | なし |
| `action` | string (`mark_for_p2p_tunnel_encap`) | ✅ | なし |
| `param/router_interface_id` | string (RIF ID) | ✅ | なし |
| `param/encap_src_ip` | IPアドレス | ✅ | なし (0.0.0.0 が parse デフォルト) |
| `param/encap_dst_ip` | IPアドレス | ✅ | なし (0.0.0.0 が parse デフォルト) |
| `controller_metadata` | string | - | 無視される |

---

## コード由来の暗黙デフォルト / fallback

### 1. `action` — `mark_for_p2p_tunnel_encap` 固定

**根拠**: `p4orch_util.h:111`
```cpp
constexpr char *kTunnelAction = "mark_for_p2p_tunnel_encap";
```

**根拠**: `gre_tunnel_manager.cpp:83-87`
```cpp
if (app_db_entry.action_str != p4orch::kTunnelAction) {
    return ReturnCode(StatusCode::SWSS_RC_INVALID_PARAM)
           << "Invalid action " << QuotedVar(app_db_entry.action_str)
           << " of GRE Tunnel App DB entry";
}
```

**結論**: `action` は `"mark_for_p2p_tunnel_encap"` のみ受け入れる。他の文字列は `SWSS_RC_INVALID_PARAM` エラー。**デフォルト値なし・固定必須値**。

---

### 2. `encap_src_ip` / `encap_dst_ip` — デシリアライズ初期値 0.0.0.0

**根拠**: `gre_tunnel_manager.cpp:325-327`
```cpp
P4GreTunnelAppDbEntry app_db_entry = {};
app_db_entry.encap_src_ip = swss::IpAddress("0.0.0.0");
app_db_entry.encap_dst_ip = swss::IpAddress("0.0.0.0");
```

**根拠**: `gre_tunnel_manager.cpp:93-101` (バリデーション)
```cpp
if (app_db_entry.encap_src_ip.isZero()) {
    return ReturnCode(StatusCode::SWSS_RC_INVALID_PARAM)
           << QuotedVar(prependParamField(p4orch::kEncapSrcIp))
           << " field is missing in table entry";
}
if (app_db_entry.encap_dst_ip.isZero()) {
    return ReturnCode(StatusCode::SWSS_RC_INVALID_PARAM)
           << QuotedVar(prependParamField(p4orch::kEncapDstIp))
           << " field is missing in table entry";
}
```

**結論**: パースの技術的デフォルトは 0.0.0.0 だが、バリデーションで `isZero()` チェックにより **事実上必須**。省略すると `SWSS_RC_INVALID_PARAM` エラー。

---

### 3. SAI トンネルタイプ — `SAI_TUNNEL_TYPE_IPINIP_GRE` ハードコード

**根拠**: `gre_tunnel_manager.cpp:41-43`
```cpp
tunnel_attr.id = SAI_TUNNEL_ATTR_TYPE;
tunnel_attr.value.s32 = SAI_TUNNEL_TYPE_IPINIP_GRE;
tunnel_attrs.push_back(tunnel_attr);
```

**結論**: テーブルエントリ記述にトンネル種別フィールドはなく、常に `SAI_TUNNEL_TYPE_IPINIP_GRE` に固定される。CONFIG_DB / APPL_DB 側に設定フィールドなし — **ハードコードデフォルト**。

---

### 4. SAI ピアモード — `SAI_TUNNEL_PEER_MODE_P2P` ハードコード

**根拠**: `gre_tunnel_manager.cpp:45-47`
```cpp
tunnel_attr.id = SAI_TUNNEL_ATTR_PEER_MODE;
tunnel_attr.value.s32 = SAI_TUNNEL_PEER_MODE_P2P;
tunnel_attrs.push_back(tunnel_attr);
```

**結論**: P4 GRE encap は常に P2P モード。`kTunnelAction = "mark_for_p2p_tunnel_encap"` の `p2p` という語もこれを示す。DB フィールドとして公開されない — **ハードコードデフォルト**。

---

### 5. `overlay_if_oid` — `gUnderlayIfId` (グローバルループバック RIF) を流用

**根拠**: `gre_tunnel_manager.cpp:419-420`
```cpp
// Use gUnderlayIfId, a shared global loopback rif, for encap tunnels
entries[i].overlay_if_oid = gUnderlayIfId;
```

**結論**: `SAI_TUNNEL_ATTR_OVERLAY_INTERFACE` は SAI 必須属性だが、P4 GRE encap は専用オーバーレイ RIF を持たず、グローバルアンダーレイ RIF (`gUnderlayIfId`) を代替使用する — **ハードコード流用 (TODO コメントで将来修正予定と明記)**。

---

### 6. `neighbor_id` — `encap_dst_ip` と等値にハードコード

**根拠**: `gre_tunnel_manager.cpp:402-406`
```cpp
entries.push_back(P4GreTunnelEntry(
    gre_tunnel_entries[i].tunnel_id,
    gre_tunnel_entries[i].router_interface_id,
    gre_tunnel_entries[i].encap_src_ip, gre_tunnel_entries[i].encap_dst_ip,
    gre_tunnel_entries[i].encap_dst_ip));  // neighbor_id = encap_dst_ip
```

**根拠**: `gre_tunnel_manager.h:44` コメント
```cpp
// neighbor_id is required to be equal to encap_dst_ip by BRCM.
```

**結論**: BRCM SAI の要件から `neighbor_id` は `encap_dst_ip` と同値に設定される。DB にフィールドとして公開されない — **BRCM SAI 互換ハードコード**。

---

### 7. GRE トンネルの Update 非対応

**根拠**: `gre_tunnel_manager.cpp:279-283`
```cpp
status = ReturnCode(StatusCode::SWSS_RC_UNIMPLEMENTED)
         << "Currently GRE tunnel doesn't support update by SAI."
         << "GRE tunnel key " << QuotedVar(tunnel_key);
```

**根拠**: `gre_tunnel_manager.cpp:544-546`
```cpp
LOG_ERROR_AND_RETURN(
    ReturnCode(StatusCode::SWSS_RC_UNIMPLEMENTED)
    << "Currently GRE tunnel doesn't support update by SAI.");
```

**結論**: 既存エントリへの `SET` (update) は `SWSS_RC_UNIMPLEMENTED` エラー。変更するには DEL → SET が必要。

---

### 8. `controller_metadata` フィールドの無視

**根拠**: `gre_tunnel_manager.cpp:371-375`
```cpp
else if (field != p4orch::kControllerMetadata)
{
    return ReturnCode(StatusCode::SWSS_RC_INVALID_PARAM)
           << "Unexpected field " << QuotedVar(field) << " in table entry";
}
```

**結論**: `controller_metadata` フィールドはパース時に無視される (parse 処理をスキップ)。それ以外の未知フィールドは `SWSS_RC_INVALID_PARAM` でエラーになる — **ホワイトリスト方式**。

---

## 要約テーブル

| フィールド / 挙動 | デフォルト / 実挙動 | 分類 |
|------------------|--------------------|----|
| `action` | `mark_for_p2p_tunnel_encap` 固定 (他はエラー) | 固定必須値 |
| `encap_src_ip` 省略 | parse 初期値 0.0.0.0 → isZero() バリデーションで `INVALID_PARAM` | 事実上必須 |
| `encap_dst_ip` 省略 | parse 初期値 0.0.0.0 → isZero() バリデーションで `INVALID_PARAM` | 事実上必須 |
| SAI トンネルタイプ | `SAI_TUNNEL_TYPE_IPINIP_GRE` 固定 (DB フィールドなし) | ハードコード |
| SAI ピアモード | `SAI_TUNNEL_PEER_MODE_P2P` 固定 (DB フィールドなし) | ハードコード |
| `overlay_if_oid` | `gUnderlayIfId` (グローバルループバック RIF) を代用 | ハードコード流用 |
| `neighbor_id` | `encap_dst_ip` と同値 (BRCM 要件) | BRCM SAI ハードコード |
| Update (SET on existing) | `SWSS_RC_UNIMPLEMENTED` エラー | 非対応 |
| `controller_metadata` | 無視 (DB 外フィールド) | ホワイトリスト外スキップ |
