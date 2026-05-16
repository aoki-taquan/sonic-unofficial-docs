# FABRIC_PORT — Phase A コード由来の暗黙デフォルト調査

調査日: 2026-05-14  
対象ページ: `docs/reference/config-db/fabric-port.md`

## 1. field 列挙

YANG (`sonic-fabric-port.yang`) で定義されるフィールド:

| field | YANG type | YANG default |
|-------|-----------|-------------|
| `isolateStatus` | `boolean_type` | `"False"` |
| `alias` | string (1..128) | なし（optional） |
| `lanes` | string (1..128) | なし（mandatory） |
| `forceUnisolateStatus` | uint32 | `0` |

## 2. entry grep 結果 (1回)

```
grep -rln "FABRIC_PORT" .cache/sonic-sources/
```

主要 consumer:
- `sonic-swss/cfgmgr/fabricmgr.cpp` — CONFIG_DB → APPL_DB 翻訳
- `sonic-swss/orchagent/fabricportsorch.cpp` — APPL_DB consumer、SAI 操作
- `sonic-buildimage/src/sonic-config-engine/portconfig.py` — fabric_port_config.ini から CONFIG_DB 初期投入
- `sonic-utilities/config/fabric.py` — CLI `config fabric port isolate/unisolate`

## 3. コード由来の暗黙デフォルト・挙動

### 3.1 `isolateStatus`

**YANG default**: `"False"`

**コード由来の追加挙動**:

1. **書き込み時 vs 実行時乖離**: CLI `config fabric port isolate` は `{'isolateStatus': True}` を CONFIG_DB に書く（fabric.py:65）。FabricMgr はこれをそのまま APPL_DB に転送（fabricmgr.cpp:86-89）。FabricPortsOrch は APPL_DB の `isolateStatus` を読んで `cfgIsolated` フラグ（0/1）にマップ（fabricportsorch.cpp:601-613）。実際の SAI 操作は `cfgIsolated` と `autoIsolated` の OR で決まるため、CONFIG_DB の `isolateStatus=False` でも `autoIsolated=1` なら SAI 上は isolate 状態が継続する（自動 isolate が優先）。

2. **silent fallback**: `doFabricPortTask` で `isolateStatus == ""` の場合、APPL_DB から `hget` で再取得を試みる（fabricportsorch.cpp:1465-1478）。取得失敗 + alias/lanes も欠如なら処理を silent skip（fabricportsorch.cpp:1480-1484）。

3. **forceUnisolate によるリセット**: `isolateStatus=False` かつ `forceUnisolateStatus` が STATE_DB の `FORCE_UN_ISOLATE` と異なる場合、STATE_DB の isolate 関連フラグが全リセットされ SAI で unisolate される（fabricportsorch.cpp:1517-1542）。つまり `forceUnisolateStatus` のインクリメントが実質的な強制 unisolate トリガ。

4. **link flap 後の自動 unisolate**: link down event 検出時（PORT_DOWN_COUNT 変化）、`origIsolated=1` かつ `cfgIsolated=0` の場合のみ clearFabricCnt(lane, true) で auto isolate がクリアされる。cfgIsolated=1（手動 isolate）の場合は link flap 後もクリアされない（fabricportsorch.cpp:743-750）。

5. **永続 isolate（PRM_ISOLATED）**: 一定期間内に複数回の auto isolate が発生すると `addErrorTime()` で `permIsolate=1` が設定される。以降は `cfgIsolated=0` + `autoIsolated=0` になっても `isolated=1` が維持される（fabricportsorch.cpp:917-922）。

### 3.2 `alias`

**YANG default**: なし（optional）

**コード由来の追加挙動**:

1. **暗黙 fallback**: `portconfig.py` の `get_fabric_port_config()` が `fabric_port_config.ini` をパースする際、`alias` 列が存在しない場合 `data.setdefault('alias', name)` でポート名（例: `Fabric0`）を alias のデフォルトとして設定する（portconfig.py:167）。つまり alias 未設定時は name と同じ値が実質的に入る。

2. **doFabricPortTask での partial update 処理**: `alias==""` の場合 APPL_DB から `hget` で読み直す（fabricportsorch.cpp:1436-1448）。取得失敗時は処理 skip（silent drop）。

### 3.3 `lanes`

**YANG**: mandatory（欠如時 YANG バリデーション reject）

**コード由来の追加挙動**:

1. **プラットフォーム依存**: `lanes` の値は `fabric_port_config.ini` のプラットフォーム固有値（例: `Fabric0` → `lanes=0`）。SAI の `SAI_PORT_ATTR_HW_LANE_LIST` で同じ lane 番号のポートを特定する（fabricportsorch.cpp:202-216）。

2. **lanes が SAI lane ID として使用**: `doFabricPortTask` 内で `isolateFabricLink(to_uint<uint8_t>(lanes), setVal)` のように lanes 文字列を直接 lane ID に変換して SAI 呼び出しに使う（fabricportsorch.cpp:1541）。lanes の値が SAI lane ID と一致しない場合、SAI 操作は対象不明で失敗する可能性がある。

### 3.4 `forceUnisolateStatus`

**YANG default**: `0`

**コード由来の追加挙動**:

1. **インクリメント挙動**: CLI `config fabric port unisolate -f` は現在の CONFIG_DB 値を読んで +1 してから書き直す（fabric.py:108-111, 134-137）。つまり CONFIG_DB の値はカウンタとして機能する。

2. **STATE_DB との比較**: FabricPortsOrch は `FORCE_UN_ISOLATE`（STATE_DB）と CONFIG_DB 由来の `forceUnisolateStatus` を比較し、値が異なる場合のみ強制 unisolate を実行（fabricportsorch.cpp:1517-1542）。同じ値が 2 回連続で書かれても効果なし（冪等ではなくエッジトリガ）。

3. **`all` 指定時の一括処理**: `unisolate all` の場合、STATE_DB のポート一覧を走査して各ポートを処理する。但し `portConfigData['forceUnisolateStatus']` が存在しない場合 KeyError で例外となるリスクがある（fabric.py:108）。

## 4. ハードコード固定値（orchagent 内）

fabricportsorch.cpp の `#define` / クラスメンバ:

| 定数 | 値 | 意味 |
|-----|-----|------|
| `FABRIC_POLLING_INTERVAL_DEFAULT` | 30 (sec) | updateFabricPortState ポーリング間隔 |
| `FABRIC_DEBUG_POLLING_INTERVAL_DEFAULT` | 12 (sec) | updateFabricDebugCounters ポーリング間隔（レート計算の loadInterval にも使用） |
| `FABRIC_PORT_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS` | 10000 ms | ポートカウンタ収集間隔 |
| `FABRIC_QUEUE_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS` | 100000 ms | キューカウンタ収集間隔 |
| `MAX_SKIP_CRCERR_ON_LNKUP_POLLS` | 20 | リンクアップ直後の CRC エラースキップポーリング数 |
| `MAX_SKIP_FECERR_ON_LNKUP_POLLS` | 20 | リンクアップ直後の FEC エラースキップポーリング数 |
| `ERROR_RATE_CRC_CELLS_CFG` | 1 | monErrThreshCrcCells のハードコードデフォルト |
| `ERROR_RATE_RX_CELLS_CFG` | 61035156 | monErrThreshRxCells のハードコードデフォルト |
| `FABRIC_LINK_RATE` | 44316 | ファブリックリンクレート（capacity 計算用） |
| `m_defaultPollWithErrors` | 0 | force unisolate 後の POLL_WITH_ERRORS リセット値 |
| `m_defaultPollWithNoErrors` | 8 | force unisolate 後の POLL_WITH_NO_ERRORS リセット値 |
| `m_defaultPollWithFecErrors` | 0 | force unisolate 後の POLL_WITH_FEC_ERRORS リセット値 |
| `m_defaultPollWithNoFecErrors` | 8 | force unisolate 後の POLL_WITH_NOFEC_ERRORS リセット値 |
| `m_defaultConfigIsolated` | 0 | force unisolate 後の CONFIG_ISOLATED リセット値 |
| `m_defaultIsolated` | 0 | force unisolate 後の ISOLATED / PRM_ISOLATED リセット値 |
| `m_defaultAutoIsolated` | 0 | force unisolate 後の AUTO_ISOLATED リセット値 |

## 5. dead field / dead consumer 調査

- `alias` は APPL_DB に転送されるが、FabricPortsOrch で実際の SAI 操作には使用されない（ログ出力のみ）。dead field に近いが完全な dead ではない（将来拡張の可能性）。
- `forceUnisolateStatus` は CONFIG_DB からの直接 SAI 操作はなく、STATE_DB の `FORCE_UN_ISOLATE` との差分をトリガとする間接的な制御のみ。

## 6. YANG-実装 discrepancy

- YANG では `isolateStatus` の type は `stypes:boolean_type`（"True"/"False" 文字列）。CLI は Python `bool` の `True`/`False` を渡す（fabric.py:65: `{'isolateStatus': True}`）。Redis 書き込み時に文字列化されるが、大文字小文字が Python `True` → `"True"` として保存される。FabricPortsOrch は `applResult == "True"` で比較（fabricportsorch.cpp:602）するため整合性あり。但し `"true"` や `"TRUE"` は認識されない（ケース制約）。

## 7. 経路依存乖離

- `monState=disable` の場合、`checkFabricPortMonState()` が false を返し `doFabricPortTask` は early return（fabricportsorch.cpp:1396-1400）。この状態では `isolateStatus` 変更が CONFIG_DB に書かれても FabricPortsOrch 側で処理されない。monState を後から enable に変更しても pending な isolate 指示は再処理されない（APPL_DB の既存値が使われる）。

## 8. 参照ソース

- `sonic-swss/orchagent/fabricportsorch.cpp`: 全行精読（getFabricPortList, updateFabricDebugCounters, doFabricPortTask, isolateFabricLink, clearFabricCnt）
- `sonic-swss/orchagent/fabricportsorch.h`: m_default* メンバ変数（L62-68）
- `sonic-swss/cfgmgr/fabricmgr.cpp`: CONFIG_DB → APPL_DB 翻訳（全行精読）
- `sonic-buildimage/src/sonic-config-engine/portconfig.py`: get_fabric_port_config（L125-169）
- `sonic-utilities/config/fabric.py`: CLI isolate/unisolate（全行精読）
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-fabric-port.yang`: YANG 定義（全行精読）
