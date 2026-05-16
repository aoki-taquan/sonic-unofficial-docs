# VRF — Phase D: 失敗挙動 (retry / recovery / task_need_retry)

調査日: 2026-05-15
ソース:
- `sonic-swss/cfgmgr/vrfmgr.cpp`
- `sonic-swss/orchagent/vrforch.cpp`
- `sonic-swss/orchagent/saihelper.cpp`
- `sonic-swss/orchagent/orch.h`

---

## 1. vrfmgrd 側の失敗挙動

vrfmgrd (`cfgmgr/vrfmgr.cpp`) はシンプルなループ (`doTask`) を持ち、失敗時のリトライをキューレベルで制御する。

### 1-1. SET 操作の失敗

| 失敗箇所 | コード参照 | 挙動 |
|---------|-----------|------|
| `setLink()` 失敗 (テーブル枯渇 / `ip link add` 失敗) | `vrfmgr.cpp:281-284` | `SWSS_LOG_ERROR("Failed to create vrf netdev %s")` を記録するが、**エントリを破棄して次に進む** (`it` を erase して continue)。リトライなし。ただし `STATE_DB.VRF_TABLE` への `state=ok` は書かれるため、`*_INTERFACE` 側の wait は永続化する |
| VNI マップ設定失敗 (`doVrfVxlanTableCreateTask` が `false` を返す) | `vrfmgr.cpp:295-301` | `SWSS_LOG_ERROR("VRF VNI Map Config Failed")` → `erase(it)` で即破棄。**リトライなし** |
| VNI 重複 | `vrfmgr.cpp:441-443` | `SWSS_LOG_ERROR("vni %d is already mapped to vrf %s")` → `return false` → 呼び出し元で即破棄 |
| 既存 VRF への VNI 上書き | `vrfmgr.cpp:461-463` | `SWSS_LOG_ERROR("vrf %s is already mapped to vni %d")` → `return false` → 即破棄 |

### 1-2. DEL 操作のリトライ (passive retry)

DEL 操作では、orchagent が SAI VR を削除するまで vrfmgrd はループをスキップしてキュー内で待機し続ける。これが唯一のリトライ機構。

```
// vrfmgr.cpp:331-334: VRFOrch が STATE_VRF_OBJECT_TABLE にエントリを残している間はスキップ
if (!isVrfObjExist(vrfName))
{
    it++;   // ← erase せず、次回ループで再試行
    continue;
}
```

```
// vrfmgr.cpp:342-346: VRFOrch がまだオブジェクトを削除していない場合もスキップ
if (isVrfObjExist(vrfName))
{
    it++;   // ← erase せず、次回ループで再試行
    continue;
}
```

- `isVrfObjExist()` は `STATE_DB.VRF_OBJECT_TABLE|<vrfName>` を参照 (`vrfmgr.cpp:204-215`)
- orchagent `VRFOrch::delOperation` が `m_stateVrfObjectTable.del(vrfName)` を呼ぶまで待機し続ける
- timeout / deadline なし。永続的な受動リトライ

### 1-3. テーブル枯渇 (最大 VRF 数超過)

`setLink()` 内の `getFreeTable()` が利用可能なルーティングテーブル ID を返せない場合 `0` を返す。

```cpp
// vrfmgr.cpp:185-188
uint32_t table = getFreeTable();
if (table == 0)
{
    return false;
}
```

- `VRF_TABLE_START=1001` 〜 `VRF_TABLE_END=5097` で最大 4096 VRF
- 超過時は `setLink()` が `false` を返し、上位の `doTask()` で `SWSS_LOG_ERROR("Failed to create vrf netdev %s")` → エントリ破棄
- **回復方法**: 既存 VRF を削除して空きテーブルを確保してから再投入

---

## 2. orchagent (VRFOrch) 側の失敗挙動

### 2-1. SAI create 失敗 → task_need_retry

`VRFOrch::addOperation` は `sai_virtual_router_api->create_virtual_router()` 失敗時に `handleSaiCreateStatus` を呼ぶ。

```cpp
// vrforch.cpp:97-104
if (status != SAI_STATUS_SUCCESS)
{
    task_process_status handle_status = handleSaiCreateStatus(SAI_API_VIRTUAL_ROUTER, status);
    if (handle_status != task_success)
    {
        return parseHandleSaiStatusFailure(handle_status);
    }
}
```

`handleSaiCreateStatus` (saihelper.cpp:581) の戻り値マッピング:

| SAI ステータス | task_process_status | parseHandleSaiStatusFailure の戻り値 | 実効挙動 |
|--------------|--------------------|------------------------------------|---------|
| `SAI_STATUS_INSUFFICIENT_RESOURCES` | `task_need_retry` | `false` (リトライ要求) | Consumer キューに残留、次回ループで再試行 |
| `SAI_STATUS_TABLE_FULL` | `task_need_retry` | `false` (リトライ要求) | 同上 |
| `SAI_STATUS_NO_MEMORY` | `task_need_retry` | `false` (リトライ要求) | 同上 |
| `SAI_STATUS_NV_STORAGE_FULL` | `task_need_retry` | `false` (リトライ要求) | 同上 |
| その他エラー | `task_failed` | `true` (リトライ不要) | エントリ破棄 + `handleSaiFailure` 呼び出し |

### 2-2. SAI set 失敗 (属性更新)

`VRFOrch::addOperation` の属性更新パスでも同様に `handleSaiSetStatus` → `parseHandleSaiStatusFailure`。
リソース不足系は `task_need_retry`、それ以外は `task_failed`。

### 2-3. SAI remove 失敗 → OBJECT_IN_USE 時のみリトライ

`VRFOrch::delOperation` は `sai_virtual_router_api->remove_virtual_router()` 失敗時に `handleSaiRemoveStatus` を呼ぶ。

```cpp
// vrforch.cpp:176-181
task_process_status handle_status = handleSaiRemoveStatus(SAI_API_VIRTUAL_ROUTER, status);
if (handle_status != task_success)
{
    return parseHandleSaiStatusFailure(handle_status);
}
```

`handleSaiRemoveStatus` (saihelper.cpp:670) のリトライ条件:

| SAI ステータス | task_process_status | 実効挙動 |
|--------------|--------------------|---------| 
| `SAI_STATUS_OBJECT_IN_USE` | `task_need_retry` | `false` を返す → Consumer キューに残留、次回再試行 |
| `SAI_STATUS_ITEM_NOT_FOUND` / `SAI_STATUS_ADDR_NOT_FOUND` | `task_success` | 成功扱い（冪等） |
| その他 | `task_failed` | エントリ破棄 |

### 2-4. 不明属性フィールドのサイレントスキップ (vrforch.cpp:80-83)

`VRFOrch::addOperation` のフィールドループで認識されないフィールド名が来た場合:

```cpp
// vrforch.cpp:80-83
SWSS_LOG_ERROR("Logic error: Unknown attribute: %s", name.c_str());
continue;   // attrs に push せず次フィールドへ
```

- エントリ全体は破棄されず、不明フィールドをスキップして処理継続
- `fallback` フィールドがこのパスに落ちる（Phase A defaults 調査で確認済み）
- `mgmtVrfEnabled` / `in_band_mgmt_enabled` は `SWSS_LOG_INFO` でスキップ（エラーではない）

### 2-5. DEL で存在しない VRF (vrforch.cpp:163-167)

```cpp
// vrforch.cpp:163-167
if (vrf_table_.find(vrf_name) == std::end(vrf_table_))
{
    SWSS_LOG_ERROR("VRF '%s' doesn't exist", vrf_name.c_str());
    return true;  // ← 成功扱い (no-op)
}
```

- エラーログを出力するが **`true` (成功) を返す**
- リトライなし、エントリ破棄なし（そもそもエントリが存在しないため冪等）
- 重複 DEL や順序逆転時も安全に処理される

### 2-6. ref_count ガード (DEL のブロック)

orchagent の DEL 操作で最も重要な失敗防止機構。

```cpp
// vrforch.cpp:169-170
if (vrf_table_[vrf_name].ref_count)
    return false;
```

- `ref_count > 0` の間は `delOperation` が `false` を返し続ける
- `false` は Consumer に「まだ処理中」として扱われ、キューに残留
- `decreaseVrfRefCount` を呼ぶ側: `intfsorch.cpp:640` (インタフェース削除時)、`routeorch.cpp:2773` (ルート削除時)
- タイムアウトなし、永続的な passive retry

---

## 3. 失敗挙動まとめ

| 失敗シナリオ | 発生場所 | リトライ有無 | 回復操作 |
|------------|---------|------------|---------|
| Linux netdev 作成失敗 (ip link add エラー) | vrfmgrd | なし (即破棄) | CONFIG_DB エントリ再投入 |
| テーブル枯渇 (4096 VRF 超過) | vrfmgrd | なし (即破棄) | 既存 VRF 削除後に再投入 |
| VNI 重複 | vrfmgrd | なし (即破棄) | 重複 VNI を解除してから再設定 |
| VNI 上書き禁止 | vrfmgrd | なし (即破棄) | `vni=0` にリセット後に新 VNI を設定 |
| VRF 削除待ち (orchagent SAI 削除完了前) | vrfmgrd | passive retry (無制限) | orchagent の ref_count がゼロになるのを待つ |
| 不明属性フィールド | orchagent | なし (フィールドスキップ、エントリ継続) | 有効フィールドのみで SAI create が進む |
| DEL 対象 VRF 不在 | orchagent | なし (no-op、success 扱い) | 冪等操作のため何もしなくてよい |
| SAI create リソース不足 | orchagent | task_need_retry (自動再試行) | リソース解放後に自動回復 |
| SAI remove OBJECT_IN_USE | orchagent | task_need_retry (自動再試行) | 参照オブジェクト削除後に自動回復 |
| ref_count > 0 で VRF DEL | orchagent | passive retry (無制限) | インタフェース・ルートを先に削除 |

---

## 4. STATE_DB 連携

- **VRF 作成成功**: vrfmgrd が `STATE_DB.VRF_TABLE|<name>` に `state=ok` を書く (vrfmgr.cpp:289)
- **VRF SAI 作成成功**: VRFOrch が `STATE_DB.VRF_OBJECT_TABLE|<name>` に `state=ok` を書く (vrforch.cpp:120)
- **VRF SAI 削除成功**: VRFOrch が `STATE_DB.VRF_OBJECT_TABLE|<name>` を消去 (vrforch.cpp:193)
- vrfmgrd は DEL 時に `STATE_DB.VRF_OBJECT_TABLE` の消去を `isVrfObjExist()` で監視し、消去されたら Linux netdev を削除

この STATE_DB 連携が vrfmgrd ↔ VRFOrch 間の唯一の協調機構であり、リトライ条件の根拠となる。
