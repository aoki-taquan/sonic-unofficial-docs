# BUFFER_PORT_EGRESS_PROFILE_LIST 値依存挙動分析

## enum フィールド
なし（フィールドは port: leafref と profile_list: leaf-list leafref のみ）

## 値依存挙動
- `packet_discard_action=trim` のプロファイルを `profile_list` に含めようとすると、`BufferOrch` (bufferorch.cpp:1918) が
  `trimming eligible` エラーを返してタスクが失敗する（ingress/egress 両方で禁止）。
- `profile_list` の順序は `ordered-by user` であり SAI `SAI_PORT_ATTR_QOS_EGRESS_BUFFER_PROFILE_LIST` への bind 順となる。
- 依存: static-buffer モードで主に使用。dynamic-buffer モードでは `buffermgrd` が自動生成する。

## ソース
- `sonic-swss/orchagent/bufferorch.cpp:1915-1924`
