# Phase A — DSCP_TO_TC_MAP コード由来暗黙デフォルト調査メモ

対象ページ: `docs/reference/config-db/dscp-to-tc-map.md`

## フィールド列挙

| フィールド | 種別 | YANG 型 |
|-----------|------|---------|
| `name` | key (list key) | string 1..32, pattern `[a-zA-Z0-9]{1}([-a-zA-Z0-9_]{0,31})` |
| `dscp` | key (inner list key) | string, pattern `6[0-3]\|[1-5][0-9]?\|[0-9]?` (0..63) |
| `tc` | value field | stypes:tc_type (uint8 0..15 in YANG template) |

## entry-grep 結果 (1回のみ)

主要な consumer ファイル:
- `sonic-swss/orchagent/qosorch.cpp` — primary consumer (DscpToTcMapHandler)
- `sonic-swss/orchagent/tunneldecaporch.cpp` — secondary consumer (tunnel decap QoS)
- `sonic-buildimage/files/build_templates/qos_config.j2` — ビルド時デフォルト生成
- `sonic-utilities/scripts/db_migrator.py` — migration: global DSCP_TO_TC_MAP

## 検出された暗黙デフォルト・挙動詳細

### 1. YANG-実装 discrepancy: `tc` フィールドの有効範囲

**種類**: YANG-実装 discrepancy

- **YANG** (`sonic-types.yang.j2:338`): `tc_type` は `uint8 range "0..15"` として定義
- **実装** (qosorch.cpp:246): `(uint8_t)stoi(fvValue(*i))` で SAI へそのまま渡す
- **SAI/ASIC 実態**: 大多数の ASIC は TC 0..7 のみサポート。TC 8 以上を設定すると SAI エラーで `task_failed` になる
- **結論**: YANG では 0..15 を許可しているが、実運用上 8..15 は ASIC により reject される。**silent failure ではなく task_failed**

### 2. `dscp` フィールドの文字列キャスト: 黙示変換

**種類**: 書き込み時 vs 実行時 乖離 (string→uint8 暗黙変換)

- CONFIG_DB に格納されるキーは **string 型** (`"0"`..`"63"`)
- qosorch.cpp:245: `(uint8_t)stoi(fvField(*i))` で `uint8_t` に変換して SAI へ
- **no validation**: `stoi` に例外処理なし。数値以外の文字列を書いても `std::invalid_argument` が propagate → `task_failed`
- Dot1pToTcMapHandler に比べ exception handling が存在しない (Dot1p 側は try/catch あり)

### 3. スパース定義: 未定義 DSCP のデフォルト TC

**種類**: 暗黙デフォルト / silent drop+fallback

- DSCP_TO_TC_MAP は 0..63 全エントリを定義する義務なし（スパース定義可）
- 未定義 DSCP のデフォルト TC は **ASIC/SAI 実装依存**。多くの場合 TC=0 だが保証なし
- SONiC 標準 AZURE マップ (`qos_config.j2:265-332`) は全 64 エントリを明示定義

### 4. ビルド時デフォルトマップ: AZURE ハードコード値

**種類**: ハードコード固定値 / プラットフォーム依存

`qos_config.j2` のフォールバック AZURE マップ（プラットフォーム固有 `generate_dscp_to_tc_map` 未定義時）:

```
DSCP 0..7   → TC: 1,1,1,3,4,2,1,1
DSCP 8      → TC: 0   (CS1: best-effort)
DSCP 46     → TC: 5   (EF: expedited forwarding)
DSCP 48     → TC: 6   (CS6: network control)
その他全て  → TC: 1
```

- LeafRouter で `tunnel_qos_remap_enable` かつ `generate_dscp_to_tc_map` 定義時は **AZURE_UPLINK** マップ参照（uplink port）
- DualToR subtype の uplink port も AZURE_UPLINK を使用

### 5. `PORT_QOS_MAP|global` — スイッチレベル適用の条件分岐

**種類**: プラットフォーム依存 / 経路依存乖離

- `PORT_QOS_MAP|global` エントリが存在する場合、`QosOrch::applyDscpToTcMapToSwitch()` がスイッチ全体に適用
- `gSwitchOrch->querySwitchCapability(SAI_OBJECT_TYPE_SWITCH, SAI_SWITCH_ATTR_QOS_DSCP_TO_TC_MAP)` が false の場合はスキップ（return true でエラーとしない）
- db_migrator `migrate_port_qos_map_global()`: **Broadcom ASIC のみ** `PORT_QOS_MAP|global` を自動生成 (`asics_require_global_dscp_to_tc_map = ["broadcom"]`)

### 6. DEL 時の参照カウント + pending_remove

**種類**: 暗黙 reset+restore / partial failure

- マップが PORT_QOS_MAP 等から参照中の状態で DEL 操作 → `m_pendingRemove = true` を立て `task_need_retry`
- pending_remove 中に SET 操作が来ると `task_need_retry` を返す（SET も実行しない）
- 参照解除後の次の SELECT イテレーションで実際に削除される

### 7. Tunnel Decap 経路での別エントリポイント

**種類**: 経路依存乖離 / dead consumer 候補ではない別経路

- `tunneldecaporch.cpp` は `TUNNEL_DECAP_TABLE` の `decap_dscp_to_tc_map` フィールドで DSCP_TO_TC_MAP を参照
- SAI 属性は `SAI_TUNNEL_ATTR_DECAP_QOS_DSCP_TO_TC_MAP` (port 属性ではなく tunnel 属性)
- 参照されない場合 (`dscp_to_tc_map_id == SAI_NULL_OBJECT_ID`) はトンネル作成時に設定しない (silent skip)

### 8. db_migrator による自動注入 (Broadcom のみ)

**種類**: ランタイム注入 / プラットフォーム依存

- `migrate_port_qos_map_global()` が Broadcom ASIC で、既存 DSCP_TO_TC_MAP が存在し `PORT_QOS_MAP|global` がない場合に **自動で** `PORT_QOS_MAP|global = {"dscp_to_tc_map": <first_map_name>}` を書き込む
- 複数の DSCP_TO_TC_MAP が存在する場合は **最初の1件を使用**（get_keys() の返却順）

## 要出力事項まとめ

```
<!-- defaults -->
フィールド: tc
  YANG range: 0..15 (stypes:tc_type in sonic-types.yang.j2:338)
  ASIC実態:  0..7 が実質上限。8以上はSAIエラー→task_failed (YANG-実装 discrepancy)

フィールド: dscp (key)
  変換: string → uint8_t via stoi() 。例外処理なし (invalid_argument → task_failed)
  未定義DSCP: ASIC依存でデフォルトTC=0が多いが未定義動作

ハードコードデフォルト (qos_config.j2):
  AZURE fallback: DSCP8→TC0, DSCP46→TC5, DSCP48→TC6, 他→TC1

スイッチレベル適用:
  PORT_QOS_MAP|global 経由。Broadcomのみdb_migratorが自動生成。
  SAI_SWITCH_ATTR_QOS_DSCP_TO_TC_MAP capability false → skip (not error)
<!-- /defaults -->
```
