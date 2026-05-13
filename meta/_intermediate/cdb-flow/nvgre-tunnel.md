# nvgre-tunnel 例外条件エビデンス

## 調査ソース

- `sonic-swss/orchagent/nvgreorch.cpp`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-nvgre-tunnel.yang`

## 例外条件まとめ

### スキーマ検証 (YANG)
- `src_ip` は `inet:ip-address` 型、必須 (mandatory)。未設定またはフォーマット不正は YANG validate で reject。
- `vlan_id` は uint16 (1..4094)、`vsid` は uint32 (0..16777214)。範囲外は YANG 段階で拒否。
- `NVGRE_TUNNEL_MAP` の `tunnel_name` は `leafref` → `NVGRE_TUNNEL`。親トンネルが存在しない場合は YANG validate で reject。

### consumer (orchagent) 例外動作
- 重複 SET: `NVGRE tunnel '%s' already exists` → WARN ログ、処理スキップ (nvgreorch.cpp:359)
- 存在しない親トンネルへの MAP 追加: `NVGRE tunnel '%s' doesn't exist` → WARN (nvgreorch.cpp:473)
- 重複 MAP エントリ: `NVGRE tunnel map '%s' already exist` → WARN (nvgreorch.cpp:482)
- `vlan_id` が未登録: `VLAN ID doesn't exist: %d` → WARN (nvgreorch.cpp:491)
- `vsid` 範囲外: `VSID is invalid: %d` → WARN (nvgreorch.cpp:498)
- SAI オブジェクト生成失敗: `std::runtime_error` throw → orchagent クラッシュ扱い (nvgreorch.cpp:106,190,253,438)
- DEL で存在しない tunnel/map: `does not exist` → WARN、処理スキップ (nvgreorch.cpp:565,571)
- 削除中の SAI エラー: `SWSS_LOG_ERROR` + `return false` でタスク再試行 (nvgreorch.cpp:327,543)
