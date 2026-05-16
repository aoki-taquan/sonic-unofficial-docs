# CBF_NHG 順序依存関係 (Phase B 中間ファイル)

ソース: `sonic-swss/orchagent/cbf/cbfnhgorch.cpp`, `orchdaemon.cpp`

## 処理順序サマリ

CLASS_BASED_NEXT_HOP_GROUP_TABLE エントリが APPL_DB に書き込まれてから SAI へプログラムされるまでの順序依存関係。

### 1. ポートレディ前提 (doTask ゲート)

`CbfNhgOrch::doTask()` の冒頭で `gPortsOrch->allPortsReady()` を確認する。全ポートが ready になるまでタスクループ全体をスキップ (`cbfnhgorch.cpp:42-45`)。

### 2. NHG 上限ゲート

新規作成時、`gRouteOrch->getNhgCount() + NhgBase::getSyncedCount() >= gRouteOrch->getMaxNhgCount()` が真の場合、作成を保留して次タスクループへ (`cbfnhgorch.cpp:100-103`)。

### 3. メンバー NHG 先行要件

- 各メンバー文字列が `NhgOrch` の `m_syncdNhgs` に存在し、かつ synced でなければならない (`cbfnhgorch.cpp:644-662`)。
- 未 sync の場合 `syncMembers()` が `false` を返し、タスクが保留→再試行される。
- 一時 NHG (temp NHG) は許容されるが、促進されるまで `hasTemps()` が true のまま保留継続 (`cbfnhgorch.cpp:116-119`)。

### 4. selection_map 先行要件

`FC_TO_NHG_INDEX_MAP_TABLE` 上の selection_map が先に NhgMapOrch に登録されていなければならない。`gNhgMapOrch->getMapId()` が `SAI_NULL_OBJECT_ID` を返した場合、`sync()` は即 false を返す (`cbfnhgorch.cpp:321-325`)。

### 5. 全体の想定順序

```
FC_TO_NHG_INDEX_MAP_TABLE エントリ作成 (NhgMapOrch)
  ↓
NEXT_HOP_GROUP_TABLE エントリ作成 (NhgOrch) → sync 完了
  ↓
CLASS_BASED_NEXT_HOP_GROUP_TABLE エントリ作成 (CbfNhgOrch)
  ↓
SAI create_next_hop_group (TYPE=CLASS_BASED, SIZE=N, SELECTION_MAP=OID)
  ↓
SAI create_next_hop_group_member × N (NHG_ID, NEXT_HOP_ID, INDEX=0..N-1)
  ↓
CRM カウンタ加算 (CRM_NEXTHOP_GROUP)
```

### 6. member index は宣言順固定

`CbfNhg::CbfNhg()` コンストラクタでメンバーを `idx=0` から順に割り当てる。`SAI_NEXT_HOP_GROUP_MEMBER_ATTR_INDEX` は `CREATE_ONLY` 属性のため、順序変更時は全メンバーを remove → 新しい順序で再 sync する (`cbfnhgorch.cpp:508-553`)。

### 7. 更新時の順序

メンバーが同一で順序も変わらない場合は `hasSameMembers()` が true → NHG OID が変化したメンバーだけ `updateNhAttr()` で更新 (`cbfnhgorch.cpp:463-503`)。メンバー追加・削除・順序変更は必ず全 remove → 全 re-sync の流れ。

### 8. DEL + SET 順序保護

同一 key に対する DEL の後に SET が pending にある場合、DEL をスキップして SET を更新扱いにする (`cbfnhgorch.cpp:152-155`)。これにより DEL 完了後に SET が適用されるシナリオでオブジェクトが意図せず削除されるのを防ぐ。

### 9. warm-reboot 挙動

`orchdaemon.cpp` の `warmRestoreAndSyncUp()` は `m_orchList` 内の全 Orch（`CbfNhgOrch` を含む）を 3 回ループして `doTask()` を呼び出す。CBF NHG 固有の warm-reboot フック（bake/onWarmBootEnd のオーバーライド）は存在しない。依存 Orch（`NhgOrch`, `NhgMapOrch`）の方が `m_orchList` で先行するため、ループ 1 回目でメンバー NHG と selection_map が復元され、2 回目以降のループで CBF NHG が正常に sync される設計 (`orchdaemon.cpp:500`, `warmRestoreAndSyncUp():1140-1165`)。

### 10. orchList 内の順序

```
m_orchList = { ..., gNhgMapOrch, gNhgOrch, gCbfNhgOrch, gFgNhgOrch, gRouteOrch, ... }
```
(`orchdaemon.cpp:500`) — NhgMapOrch → NhgOrch → CbfNhgOrch の順で doTask が呼ばれるため、1 回のループ内で依存関係が自然に解消される。
