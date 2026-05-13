# BUFFER_PORT_INGRESS_PROFILE_LIST 値依存挙動分析

## enum フィールド
なし（フィールドは port: leafref と profile_list: leaf-list leafref のみ）

## 値依存挙動
- `packet_discard_action=trim` のプロファイルを `profile_list` に含めると、`BufferOrch` (bufferorch.cpp:1728) が
  `trimming eligible` エラーを返してタスクが失敗する。trim プロファイルは ingress 方向に適用不可。
- `profile_list` の順序は `ordered-by user` であり、SAI `SAI_PORT_ATTR_QOS_INGRESS_BUFFER_PROFILE_LIST` への bind 順となる。
- 動的バッファモード (`buffer_model=dynamic`) では buffermgrd が自動生成するため、ユーザ設定は通常不要。

## ソース
- `sonic-swss/orchagent/bufferorch.cpp:1725-1732`
