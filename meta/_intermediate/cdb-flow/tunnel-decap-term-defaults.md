# TUNNEL_DECAP_TERM_TABLE — Phase A 暗黙デフォルト調査

調査日: 2026-05-14
対象ファイル:
- `sonic-swss/orchagent/tunneldecaporch.cpp` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/cfgmgr/tunnelmgr.cpp` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss-common/common/schema.h` (SHA: 158de8d3463ff4b841653f6d57190bb142b80d9c)
- `sonic-buildimage/dockers/docker-orchagent/ipinip.json.j2` (SHA: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd)
- `SONiC/doc/decap/subnet_decap_HLD.md`

---

## テーブル所在

`TUNNEL_DECAP_TERM_TABLE` は **APPL_DB** および **STATE_DB** のテーブルであり、CONFIG_DB テーブルではない。

- `APP_TUNNEL_DECAP_TERM_TABLE_NAME` = `"TUNNEL_DECAP_TERM_TABLE"` (schema.h L50)
- `STATE_TUNNEL_DECAP_TERM_TABLE_NAME` = `"TUNNEL_DECAP_TERM_TABLE"` (schema.h L489)
- YANG モジュール: 対応なし（APPL_DB のみ）

キー構造: `TUNNEL_DECAP_TERM_TABLE:<tunnel_name>:<dst_ip_prefix>`

---

## フィールド別デフォルト・暗黙挙動

### term_type

- **YANG default**: なし（YANG 未定義テーブル）
- **コード初期化**: `TunnelTermType term_type = TUNNEL_TERM_TYPE_P2MP;`
  (tunneldecaporch.cpp L361) — フィールド省略時は `P2MP` が暗黙デフォルト
- **tunnelmgr 側の書き込み**: `tunnelmgr.cpp` (L281-288) にて
  - `src_ip` フィールドが存在する → `term_type = "P2P"` を書き込む
  - `src_ip` フィールドが存在しない → `term_type = "P2MP"` を書き込む
- **ipinip.json.j2 の実例**:
  - 通常 IP-in-IP tunnel term: `"term_type":"P2MP"` (src_ip なし)
  - subnet decap term: `"term_type":"MP2MP"` (src_ip + dst_ip マスク付き)
- **有効値**: `"P2P"`, `"P2MP"`, `"MP2MP"`
  - `"P2P"` → `SAI_TUNNEL_TERM_TABLE_ENTRY_TYPE_P2P`
  - `"P2MP"` → `SAI_TUNNEL_TERM_TABLE_ENTRY_TYPE_P2MP`
  - `"MP2MP"` → `SAI_TUNNEL_TERM_TABLE_ENTRY_TYPE_MP2MP`
- **制約**:
  - `P2P` の場合は `src_ip` が必須 (L456)
  - `MP2MP` かつ non-subnet-decap の場合も `src_ip` が必須 (L461)
  - subnet decap term は `MP2MP` のみ許可 (L446)
  - `subnet_type` が存在する場合も `MP2MP` のみ許可 (L451)
- **結論**: 省略時の暗黙値 = `P2MP`。`tunnelmgr` は常に明示的に書き込む

### src_ip

- **YANG default**: なし（任意フィールド）
- **コード**: `src_ip_str` が空文字列で初期化 (tunneldecaporch.cpp L358)
- **P2MP では省略可**: `P2MP` タイプでは `src_ip` は SAI に設定されない
  (tunneldecaporch.cpp L948-959: P2P または MP2MP の場合のみ `SAI_TUNNEL_TERM_TABLE_ENTRY_ATTR_SRC_IP` を設定)
- **P2P では必須**: `src_ip` なしで `P2P` を指定すると
  `"no source IP is provided."` を LOG_ERROR してスキップ (L456-459)
- **MP2MP かつ subnet decap**: `subnetDecapConfig.src_ip` から自動注入 (L478-500)
- **STATE_DB への書き込み**: `src_ip_str` が空でない場合のみ `setDecapTunnelTermStatus()` で書き込む (L1551-1553)
- **結論**: P2MP では省略 = `src_ip` なし (SAI 属性未設定)。P2P では必須

### dst_ip (キー要素)

- **YANG default**: なし (キー要素)
- **役割**: `TUNNEL_DECAP_TERM_TABLE:<tunnel_name>:<dst_ip>` のキーの2番目の要素
- **型**: IP prefix (`IpPrefix` クラスで解析)。IPv4/IPv6 両対応
- **MP2MP 時の mask**: `MP2MP` では dst_ip の mask も SAI に設定される
  `SAI_TUNNEL_TERM_TABLE_ENTRY_ATTR_DST_IP_MASK` (tunneldecaporch.cpp L970-974)
- **IP バージョン**: dst_ip が IPv4 か IPv6 かは `is_v4_term = dst_ip.isV4()` で判定 (L395)。
  subnet decap の src_ip はバージョンに合わせて `src_ip` / `src_ip_v6` が選ばれる
- **結論**: 必須キー要素。デフォルトなし

### subnet_type

- **YANG default**: なし（任意フィールド）
- **コード初期化**: `subnet_type` は空文字列で初期化 (L362)
- **有効値**: `"vlan"`, `"vip"` (tunneldecaporch.cpp L428-432)
- **省略時**: フィールドなし = subnet decap term ではない通常 IP-in-IP term
- **STATE_DB への書き込み**: `subnet_type` が空でない場合のみ書き込む (L1555-1557)
- **SAI 設定への影響**: `subnet_type` 自体は SAI 属性に直接マップされない。
  ただし `subnet_type` が存在する場合は `MP2MP` タイプが必須 (L451)
- **ipinip.json.j2 の実例**: `"subnet_type": "vlan"` (ipinip.json.j2 L119, L185)
- **結論**: 省略可能。省略 = 通常 P2MP/P2P term

---

## 書き込み元 (Writer)

### tunnelmgr (主要書き込み元)

`tunnelmgr.cpp` L278-289:
```cpp
// src_ip があれば P2P、なければ P2MP として APPL_DB へ書き込む
if (!src_ip.empty()) {
    fvs.emplace_back("src_ip", src_ip);
    fvs.emplace_back("term_type", "P2P");
} else {
    fvs.emplace_back("term_type", "P2MP");
}
m_appIpInIpTunnelDecapTermTable.set(tunnelName + DEFAULT_KEY_SEPARATOR + tunInfo.dst_ip, fvs);
```
- CONFIG_DB `TUNNEL` テーブルの `src_ip` の有無から `term_type` を自動決定
- `tunnel_type == IPINIP` の場合のみ書き込む (L250)

### swssconfig / ipinip.json.j2 (ビルド時テンプレート)

- `TUNNEL_DECAP_TERM_TABLE:IPINIP_TUNNEL:<ip>`: `term_type=P2MP` (src_ip なし)
- `TUNNEL_DECAP_TERM_TABLE:IPINIP_SUBNET:<prefix>`: `term_type=MP2MP`, `subnet_type=vlan` (src_ip は後で subnetDecapConfig から注入)

### db_migrator.py

`db_migrator.py` にて TUNNEL_DECAP_TABLE から TUNNEL_DECAP_TERM_TABLE へのマイグレーションロジックあり:
`decap_term_table_key = app_db_separator.join(["TUNNEL_DECAP_TERM_TABLE", key, dip])`

---

## SAI マッピング

| フィールド/条件 | SAI 属性 |
|---|---|
| `term_type=P2P` | `SAI_TUNNEL_TERM_TABLE_ENTRY_TYPE_P2P` |
| `term_type=P2MP` | `SAI_TUNNEL_TERM_TABLE_ENTRY_TYPE_P2MP` |
| `term_type=MP2MP` | `SAI_TUNNEL_TERM_TABLE_ENTRY_TYPE_MP2MP` |
| `src_ip` (P2P/MP2MP) | `SAI_TUNNEL_TERM_TABLE_ENTRY_ATTR_SRC_IP` |
| `src_ip mask` (MP2MP) | `SAI_TUNNEL_TERM_TABLE_ENTRY_ATTR_SRC_IP_MASK` |
| dst_ip (全タイプ) | `SAI_TUNNEL_TERM_TABLE_ENTRY_ATTR_DST_IP` |
| dst_ip mask (MP2MP) | `SAI_TUNNEL_TERM_TABLE_ENTRY_ATTR_DST_IP_MASK` |
| VR_ID (常に) | `SAI_TUNNEL_TERM_TABLE_ENTRY_ATTR_VR_ID = gVirtualRouterId` |
| TUNNEL_TYPE (常に) | `SAI_TUNNEL_TERM_TABLE_ENTRY_ATTR_TUNNEL_TYPE = SAI_TUNNEL_TYPE_IPINIP` |
| ACTION_TUNNEL_ID (常に) | `SAI_TUNNEL_TERM_TABLE_ENTRY_ATTR_ACTION_TUNNEL_ID = tunnel.tunnel_id` |

---

## 既存ドキュメント (tunnel-decap-table.md) との乖離

| 項目 | tunnel-decap-table.md 記載 | 実装コード | 判定 |
|---|---|---|---|
| TUNNEL_DECAP_TERM_TABLE の位置付け | APPL_DB sub テーブルとして言及のみ | 詳細フィールド未記載 | 未記載（本ページが補完） |
| term_type の暗黙 P2MP デフォルト | 記載なし | `= TUNNEL_TERM_TYPE_P2MP` 初期化 | 未記載 |
| MP2MP の src_ip 必須制約 | 記載なし | L461: non-subnet MP2MP も必須 | 未記載 |
| subnet_type の SAI 非マップ | 記載なし | SAI attrs に含まれない | 未記載 |

---

## ソース参照

- `sonic-swss/orchagent/tunneldecaporch.cpp` L338-551 (doDecapTunnelTermTask)
- `sonic-swss/orchagent/tunneldecaporch.cpp` L892-1003 (addDecapTunnelTermEntry)
- `sonic-swss/orchagent/tunneldecaporch.cpp` L1539-1561 (setDecapTunnelTermStatus)
- `sonic-swss/cfgmgr/tunnelmgr.cpp` L221-319 (doTunnelTask)
- `sonic-buildimage/dockers/docker-orchagent/ipinip.json.j2` L114-155, L181-222
- `SONiC/doc/decap/subnet_decap_HLD.md` §6.2.2
