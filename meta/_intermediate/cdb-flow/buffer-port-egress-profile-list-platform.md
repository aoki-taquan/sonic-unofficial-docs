# BUFFER_PORT_EGRESS_PROFILE_LIST — Phase H: プラットフォーム差分

**対象ページ**: `docs/reference/config-db/buffer-port-egress-profile-list.md`
**ソース調査ファイル**:
- `sonic-swss/cfgmgr/buffermgrdyn.cpp` (dynamic buffer model manager)
- `sonic-swss/cfgmgr/buffermgr.cpp` (static buffer model manager)
- `sonic-swss/orchagent/bufferorch.cpp` (BufferOrch)

---

## 1. Dynamic vs Static モデル差分

| 観点 | Static model (`buffermgr.cpp`) | Dynamic model (`buffermgrdyn.cpp`) |
|------|-------------------------------|-------------------------------------|
| 有効条件 | `DEVICE_METADATA.buffer_model != "dynamic"` | `DEVICE_METADATA.buffer_model == "dynamic"` |
| 処理スキップ | `dynamic_buffer_model == true` の場合は `SWSS_LOG_DEBUG("Dynamic buffer model enabled. Skipping further processing")` で即 return | — |
| CONFIG_DB → APPL_DB 変換 | `doBufferTableTask()`: フィールド検証なし、そのままコピー | `handleSingleBufferPortProfileListEntry()` + `checkBufferProfileDirection()` で direction 検証あり |
| direction 検証 | なし (orchagent 段で初めて制約が現れる) | あり: ingress profile を egress list に設定 → `task_failed` |
| profile 存在検証 | なし (orchagent 段で `task_need_retry`) | あり: `m_bufferProfileLookup` に未登録 → `task_need_retry` |
| admin-down port 置換 | なし (CONFIG_DB 値をそのまま APPL_DB へ) | あり: ゼロプロファイルリストへ差し替え (`buffermgrdyn.cpp:3418-3438`) |
| buffer pool guard | なし | あり: `m_bufferPoolReady == false` → pending (`buffermgrdyn.cpp:3408-3415`) |
| DEL 操作 | APPL_DB から削除 | `// Not supported on Mellanox platform for now.` 注記付きで削除処理 (L3443) |

evidence:
- `buffermgr.cpp:476-480` — dynamic_buffer_model 検出してスキップ
- `buffermgrdyn.cpp:3390-3453` — `handleSingleBufferPortProfileListEntry()` SET/DEL 完全実装

---

## 2. ASIC vendor 差分 (buffermgrdyn.cpp)

### Mellanox 固有

`buffermgrdyn.cpp` は `ASIC_VENDOR` 環境変数でプラットフォームを判別する (`buffermgrdyn.cpp:68-80`)。

| 挙動 | 対象 | evidence |
|------|------|---------|
| Lua プラグイン名 `buffer_headroom_<vendor>.lua` をロード | 全ベンダー共通 (vendor 文字列を組み込む) | `buffermgrdyn.cpp:76-78` |
| Mellanox SN シリーズモデル番号 (`m_model_number`) を取得 | Mellanox のみ | `buffermgrdyn.cpp:84-102` |
| 8 レーンポートで xon 値を倍増 (profile 名に `_8lane` を付与) | Mellanox 4xxx (400G 以外) および 5xxx (800G 以外) | `buffermgrdyn.cpp:504-522` |
| DEL パスに `// Not supported on Mellanox platform for now.` のコメント | Mellanox 固有の留意事項として明記 | `buffermgrdyn.cpp:3443` |

#### 注記: BUFFER_PORT_EGRESS_PROFILE_LIST への直接影響

`8_lane` / モデル番号ロジックは **PG バッファプロファイル名生成** に関わるもので、BUFFER_PORT_EGRESS_PROFILE_LIST キー・フィールドそのものには影響しない。ただし、このテーブルが参照する `BUFFER_PROFILE` の名前がプラットフォームによって異なる名称になることに注意。

DEL 動作の Mellanox 注記は **egress / ingress 両 profile list** の DEL パスに存在する (同一関数 `handleSingleBufferPortProfileListEntry`)。削除処理自体は実行されるが、Mellanox での正式サポートはコメント上「現時点では未サポート」。

### Broadcom / その他 ベンダー

`ASIC_VENDOR` が `mellanox` 以外のベンダー (`broadcom`, `cavium`, `barefoot` 等) の場合、モデル番号取得や 8 レーン xon 倍増は行われない。Lua ヘッドルームプラグインはベンダー別ファイルが呼ばれる (`buffer_headroom_broadcom.lua` 等)。
BUFFER_PORT_EGRESS_PROFILE_LIST テーブル自体の SET/DEL 処理コードは vendor 条件分岐なしで動作する (非 Mellanox 向け DEL パスにも上記コメントが残っている点に留意)。

---

## 3. VOQ Chassis 差分 (bufferorch.cpp)

### 調査結果

`bufferorch.cpp` を `voq` キーワードで全行検索した結果、`processEgressBufferProfileList` / `processEgressBufferProfileListBulk` / `processEgressBufferProfileListPost` の各関数内に **`gMySwitchType == "voq"` 分岐は存在しない**。

VOQ chassis での `gMySwitchType == "voq"` 分岐が存在するのは以下のコンテキストのみ:
- `initVoqBufferReadyList()` の呼び出し — BUFFER_QUEUE の初期化 (ingress PG / VOQ 用)
- BUFFER_QUEUE ハンドラ内のシステムポートキー解析 (`tokens.size() != 4`)
- BUFFER_QUEUE の FlexCounter 登録スキップ (`gMySwitchType != "voq"`)
- BUFFER_QUEUE の ref count 管理スキップ (`gMySwitchType != "voq"`)
- `doTask(Consumer &consumer)` の `isInitDone()` / `isConfigDone()` 選択

### BUFFER_PORT_EGRESS_PROFILE_LIST への影響

| 項目 | 標準スイッチ | VOQ Chassis |
|------|------------|------------|
| `processEgressBufferProfileList` 実行 | 通常通り | **同一コードパスが実行される**（分岐なし） |
| 処理開始条件 | `isConfigDone()` | `isInitDone()` (より早い段階) |
| SAI 属性 | `SAI_PORT_ATTR_QOS_EGRESS_BUFFER_PROFILE_LIST` | 同じ属性（VOQ 固有の代替なし） |
| BufferMgrDynamic (`buffermgrdyn.cpp`) | voq 分岐なし | voq 分岐なし（同一コードパス） |

**結論**: VOQ Chassis において BUFFER_PORT_EGRESS_PROFILE_LIST の挙動は標準スイッチと同一。voq 固有のキー拡張（`tokens.size() == 4` 形式）は BUFFER_QUEUE にのみ適用される。egress profile list では `isInitDone()` による開始タイミングの早期化のみが間接的に影響する。

evidence:
- `bufferorch.cpp:2079-2094` — `doTask(Consumer)` 内の voq / 非 voq 分岐 (`isInitDone` vs `isConfigDone`)
- `bufferorch.cpp:1853-1964` — `processEgressBufferProfileList`: voq 条件分岐なし
- `bufferorch.cpp:1986-2075` — `processEgressBufferProfileListBulk`: voq 条件分岐なし
- `bufferorch.cpp:116-140` — `initVoqBufferReadyList` 呼び出し: BUFFER_QUEUE のみ対象

---

## 4. まとめ

| 差分カテゴリ | 差分有無 | 備考 |
|------------|---------|------|
| dynamic vs static model | **あり** | direction 検証・admin-down 置換・pool guard は dynamic のみ |
| Mellanox DEL 未サポートコメント | **あり** | DEL 処理は動作するが正式未サポート注記 |
| Mellanox 8 レーン xon 倍増 | 間接的 | 参照 BUFFER_PROFILE 名に影響、このテーブル直接処理には影響なし |
| VOQ Chassis | **差分なし** | 処理開始タイミング以外は同一コードパス |
| その他 ASIC vendor | **差分なし** | Lua プラグイン名のみ異なる（テーブル処理コードに分岐なし） |
