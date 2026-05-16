# POLICER Phase A — コード由来の暗黙デフォルト調査

調査日: 2026-05-14  
対象ファイル: `sonic-swss/orchagent/policerorch.cpp` (全行精読済み)  
evidence lines: policerorch.cpp:116-589

---

## フィールド別デフォルト一覧

### POLICER テーブル経路 (doTask SET)

| フィールド | 省略時の挙動 | コード根拠 |
|-----------|------------|-----------|
| `METER_TYPE` | `meter_type = false` のまま。`!meter_type` 判定で ERROR ログを出すが **return しない**。SAI `create_policer()` が不完全な attrs で呼ばれ SAI エラーになる (silent-proceed バグ) | policerorch.cpp:414, 491-495, 498 |
| `MODE` | `mode = false` のまま。同上 — ERROR ログ後に SAI create が呼ばれる | policerorch.cpp:414, 491-495, 498 |
| `COLOR_SOURCE` | SAI へ渡されない → SAI プラットフォームデフォルト (通常 `SAI_POLICER_COLOR_SOURCE_BLIND`) が適用 | policerorch.cpp:438-441 (存在時のみ push) |
| `CIR` | SAI へ渡されない → SAI デフォルト 0 (unlimited or platform-defined) | policerorch.cpp:448-451 (存在時のみ push) |
| `CBS` | SAI へ渡されない → SAI デフォルト 0 | policerorch.cpp:443-446 |
| `PIR` | SAI へ渡されない → SAI デフォルト 0 | policerorch.cpp:456-459 |
| `PBS` | SAI へ渡されない → SAI デフォルト 0 | policerorch.cpp:453-456 |
| `GREEN_PACKET_ACTION` | SAI へ渡されない → SAI プラットフォームデフォルト (通常 `FORWARD`) | policerorch.cpp:468-471 (存在時のみ push) |
| `YELLOW_PACKET_ACTION` | SAI へ渡されない → SAI プラットフォームデフォルト (通常 `FORWARD`) | policerorch.cpp:473-476 |
| `RED_PACKET_ACTION` | SAI へ渡されない → SAI プラットフォームデフォルト (通常 `DROP`) | policerorch.cpp:462-466 |

### PORT_STORM_CONTROL 経路 (handlePortStormControlTable)

storm-control 経由では以下がハードコードされ、CONFIG_DB フィールドは無視される:

| 属性 | ハードコード値 | コード根拠 |
|-----|--------------|-----------|
| `METER_TYPE` | `BYTES` (kbps → bps 換算) | policerorch.cpp:157-159 |
| `MODE` | `STORM_CONTROL` | policerorch.cpp:162-164 |
| `RED_PACKET_ACTION` | `DROP` | policerorch.cpp:167-169 |
| `KBPS` フィールド変換 | `stoul(value)*1000/8` → CIR (bytes/sec) | policerorch.cpp:181-184 |

### UPDATE 経路 (既存 policer への SET)

`update=true` 時、以下のみ SAI に渡される (他は silently ignored):

| SET 可能 | SAI 属性 | コード根拠 |
|---------|---------|-----------|
| `CIR` | `SAI_POLICER_ATTR_CIR` | policerorch.cpp:527-533 |
| `CBS` | `SAI_POLICER_ATTR_CBS` | 同上 |
| `PIR` | `SAI_POLICER_ATTR_PIR` | 同上 |
| `PBS` | `SAI_POLICER_ATTR_PBS` | 同上 |

`METER_TYPE`, `MODE`, `COLOR_SOURCE`, `*_PACKET_ACTION` は **create-only**。
SET で指定しても policerorch がフィルタして SAI に渡さない。

---

## 検出された特記事項

### 1. 必須フィールド欠落の silent-proceed バグ

`policerorch.cpp:491-495`:
```cpp
if (!meter_type || !mode)
{
    SWSS_LOG_ERROR("Failed to create policer %s, missing mandatory fields", key.c_str());
}
// ← ここに return/continue が無い
sai_object_id_t policer_id;
sai_status_t status = sai_policer_api->create_policer(...);
```
`METER_TYPE` または `MODE` が無い場合、ERROR ログは出るが処理が続行し SAI create が呼ばれる。
SAI は不正な attr セットでエラーを返し、policer は作成されないが、そのエントリは `m_toSync` から削除されるため **二度とリトライされない**。

### 2. COLOR_SOURCE 省略時のプラットフォーム依存

`COLOR_SOURCE` を省略した場合、SAI の platform-specific デフォルトが適用される。
SAI 仕様では `SAI_POLICER_COLOR_SOURCE_BLIND` がデフォルト (`sai.h`)。
ただし ASIC/SDK によって異なる可能性がある。

### 3. パケットアクション省略時の挙動

`*_PACKET_ACTION` を省略した場合は SAI デフォルトが適用:
- `GREEN_PACKET_ACTION`: SAI デフォルト `FORWARD`
- `YELLOW_PACKET_ACTION`: SAI デフォルト `FORWARD`
- `RED_PACKET_ACTION`: SAI デフォルト `DROP`

これらは policerorch から明示的に設定されないため、実際の挙動は SAI/ASIC 依存。

### 4. packet_action_map に `COPY`/`COPY_CANCEL`/`TRAP`/`LOG`/`DENY`/`TRANSIT` が存在

ドキュメント上は `FORWARD`/`DROP` のみ記載されているが、実装では `COPY`, `COPY_CANCEL`, `TRAP`, `LOG`, `DENY`, `TRANSIT` も受け付ける (policerorch.cpp:50-59)。

### 5. storm-control 更新時は CIR のみ SAI に渡す

`handlePortStormControlTable` の update パスでは `attr.id == SAI_POLICER_ATTR_CIR` のみフィルタして SAI set を呼ぶ (policerorch.cpp:252-253)。
`CBS` は storm-control update では更新されない — CBS を変えたい場合は policer を再作成する必要がある。

---

## 結論: defaults ブロック草案

```markdown
<!-- defaults -->
## コード由来の暗黙デフォルト (Phase A)

| フィールド | 省略時の実挙動 | 分類 |
|-----------|--------------|------|
| `METER_TYPE` | ERROR ログ後に SAI create が続行 → SAI エラー + リトライなし | 必須フィールド欠落バグ |
| `MODE` | 同上 | 必須フィールド欠落バグ |
| `COLOR_SOURCE` | SAI プラットフォームデフォルト (通常 `BLIND`) | platform-dependent |
| `CIR` / `CBS` / `PIR` / `PBS` | SAI デフォルト 0 (unlimited or platform-defined) | platform-dependent |
| `GREEN_PACKET_ACTION` | SAI デフォルト `FORWARD` | platform-dependent |
| `YELLOW_PACKET_ACTION` | SAI デフォルト `FORWARD` | platform-dependent |
| `RED_PACKET_ACTION` | SAI デフォルト `DROP` | platform-dependent |

**storm-control 経由のハードコード** (PORT_STORM_CONTROL テーブル):
- `METER_TYPE` → `BYTES` (固定)
- `MODE` → `STORM_CONTROL` (固定)
- `RED_PACKET_ACTION` → `DROP` (固定)
- `KBPS` → `kbps * 1000 / 8` で CIR (bytes/sec) に変換

**create-only フィールド** (UPDATE で silently ignored):
- `METER_TYPE`, `MODE`, `COLOR_SOURCE`, `*_PACKET_ACTION`

**packet_action_map の実際の受理値** (ドキュメント未記載):
- `COPY`, `COPY_CANCEL`, `TRAP`, `LOG`, `DENY`, `TRANSIT` も有効

<!-- /defaults -->
```
