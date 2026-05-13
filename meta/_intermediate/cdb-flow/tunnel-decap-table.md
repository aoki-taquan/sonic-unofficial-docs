# TUNNEL_DECAP_TABLE 例外条件調査メモ

ソース: `sonic-swss/orchagent/tunneldecaporch.cpp` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)

## 抽出した例外条件 (tunneldecaporch.cpp)

1. **不正な tunnel_type** — `tunnel_type` が `IPINIP` でも他の既知タイプでもない場合、
   `"Invalid tunnel type <type>"` を LOG_ERROR してスキップ。

2. **`src_ip` の変更不可** — 既存トンネルの `src_ip` を変更しようとすると
   `"cannot modify src ip for existing tunnel"` を LOG_ERROR して拒否する。
   src_ip は作成時のみ設定可能で、変更するにはトンネルを削除して再作成する必要がある。

3. **不正な dscp_mode / ecn_mode / ttl_mode** — 有効値以外のモード文字列が来ると
   `"Invalid dscp mode <mode>"` / `"Invalid ecn mode <mode>"` / `"Invalid ttl mode <mode>"` を
   LOG_ERROR してスキップ。

4. **`encap_ecn_mode` の制約** — `ecn_mode` が `standard` 以外の場合、
   `"Only standard encap ecn mode is supported currently"` を LOG_ERROR して拒否する。

5. **不明フィールド** — 未知フィールドが来ると `"unknown decap tunnel table attribute '<field>'"` を
   LOG_ERROR してスキップ。

6. **ASIC_DB への追加失敗** — `sai_tunnel_api->create_tunnel()` が失敗すると
   `"Failed to add tunnel <key> to ASIC_DB."` を LOG_ERROR する。

7. **存在しないトンネルの削除** — 未作成のトンネルを DEL しようとすると
   `"Tunnel <key> cannot be removed since it doesn't exist."` を LOG_ERROR する。

8. **decap term キーの不正** — IP prefix として解釈できないキーは
   `"invalid destination IP prefix <reason>"` を LOG_ERROR してスキップ。

9. **subnet decap 制約** — subnet decap の decap term に source IP がない場合や
   subnet decap が無効のまま decap term を追加しようとすると対応エラーを LOG_ERROR する。

10. **MP2MP 制約** — subnet decap term は `MP2MP` タイプのトンネルにのみ許可される。
    違反時は `"only MP2MP tunnel decap term is allowed for subnet decap tunnel."` を LOG_ERROR。
