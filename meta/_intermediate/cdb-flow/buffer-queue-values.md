# BUFFER_QUEUE 値依存挙動分析

## enum フィールド
なし（profile: leafref のみ。key の switch_type は DEVICE_METADATA で決定）

## 値依存挙動

### switch_type による list 切り替え
- YANG `when` 条件: `DEVICE_METADATA.localhost.switch_type != 'voq'` → `BUFFER_QUEUE_LIST` が有効
- `switch_type = 'voq'` → `VOQ_BUFFER_QUEUE_LIST` が有効（key に hostname/asic_name が追加）
- 誤った list に設定してもバリデーションエラーになり適用されない。

### profile の trimming 制約
- 参照する `BUFFER_PROFILE.packet_discard_action=trim` のプロファイルは `BufferOrch` の egress queue 設定では
  制約チェックなし（egress queue に trim プロファイルを割り当てること自体は許可）。
  ただし ingress PG / ingress profile list への trim 適用は禁止。

## ソース
- `sonic-swss/orchagent/bufferorch.cpp` (BufferOrch doTask)
- YANG: `sonic-buffer-queue.yang` (when condition)
