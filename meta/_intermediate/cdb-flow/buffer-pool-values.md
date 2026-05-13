# BUFFER_POOL 値依存挙動分析

## enum フィールド

### type (`ingress`/`egress`/`both`)
- bufferorch.cpp:443-453:
  - `ingress` → `SAI_BUFFER_POOL_TYPE_INGRESS`
  - `egress`  → `SAI_BUFFER_POOL_TYPE_EGRESS`
  - `both`    → `SAI_BUFFER_POOL_TYPE_BOTH`

### mode (`static`/`dynamic`)
- bufferorch.cpp:474-480:
  - `dynamic` → `SAI_BUFFER_POOL_THRESHOLD_MODE_DYNAMIC`
  - `static`  → `SAI_BUFFER_POOL_THRESHOLD_MODE_STATIC`

## 組み合わせ条件
- `percentage` フィールドは `DEVICE_METADATA.buffer_model = 'dynamic'` かつ `mode = 'dynamic'` のときのみ有効
- `size` と `percentage` は排他 (YANG must 制約)
- `xoff` は lossless ingress pool (`type=ingress`, `mode=static`) で意味を持つ

## 典型名と挙動
| pool 名 | type | mode | xoff |
|---------|------|------|------|
| `ingress_lossless_pool` | ingress | static | 設定有り |
| `ingress_lossy_pool`    | ingress | dynamic | なし |
| `egress_lossless_pool`  | egress | static | なし |
| `egress_lossy_pool`     | egress | dynamic | なし |

## まとめ
- enum 有り: type (3値), mode (2値)
- type × mode の組み合わせで SAI API への引数が決まる
