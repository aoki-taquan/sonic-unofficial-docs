# STATE_DB VRF 関連テーブル — コード由来デフォルト調査メモ (Phase A)

調査日: 2026-05-14
対象: STATE_DB `VRF_TABLE` / `VRF_OBJECT_TABLE`

## 調査対象ファイル

- `sonic-swss/cfgmgr/vrfmgr.cpp` — `m_stateVrfTable` への書き込み主体
- `sonic-swss/orchagent/vrforch.cpp` — `m_stateVrfObjectTable` への書き込み主体
- `sonic-swss/orchagent/vrforch.h` — request_description, VRFOrch クラス定義
- `sonic-swss/cfgmgr/intfmgr.cpp` — `m_stateVrfTable` の consumer (VRF ready check)
- `sonic-swss/cfgmgr/vxlanmgr.cpp` — `m_stateVrfTable` の consumer (isVrfStateOk)
- `sonic-swss-common/common/schema.h` — テーブル名定数

---

## テーブル構造

### STATE_DB `VRF_TABLE|<vrfName>`

**書き込み主体**: `vrfmgrd` (VrfMgr::doTask)

**書き込みコード** (vrfmgr.cpp:288-289):
```cpp
vector<FieldValueTuple> fvVector;
fvVector.emplace_back("state", "ok");
m_stateVrfTable.set(vrfName, fvVector);
```

**タイミング**: CONFIG_DB `VRF` テーブルへの SET 操作後、Linux VRF デバイス (`ip link add <name> type vrf table <id>`) を作成したあとに書き込む。

**フィールド**:

| フィールド | 型 | 値 | 意味 |
|-----------|----|----|------|
| `state` | string | `"ok"` (固定) | VRF デバイスが Linux に存在し APP_DB へも書き込まれた |

**暗黙デフォルト / コード由来挙動**:
- `"ok"` の文字列がハードコードされており、他の値は取り得ない (vrfmgr.cpp:288)
- `setLink()` が失敗 (`SWSS_LOG_ERROR("Failed to create vrf netdev")`) した場合でも `m_stateVrfTable.set()` は呼ばれる — Linux VRF デバイス作成失敗でも state=ok が書き込まれる点に注意 (vrfmgr.cpp:281-289)
- DEL 時: vrfmgrd は `isVrfObjExist()` (= VRF_OBJECT_TABLE への問い合わせ) が true になるまで待機し、false になったら `m_stateVrfTable.del(vrfName)` を実行 (vrfmgr.cpp:328-339)

**consumer**:
- `intfmgrd` (intfmgr.cpp:671, 680): `m_stateVrfTable.get(alias, temp)` で VRF の存在確認 — 存在しない場合はインタフェースへの VRF バインドを遅延
- `vxlanmgr` (vxlanmgr.cpp:744): `isVrfStateOk()` で VRF_TABLE の存在確認 — VXLAN マッピング設定の前提条件

---

### STATE_DB `VRF_OBJECT_TABLE|<vrfName>`

**書き込み主体**: `orchagent` (VRFOrch::addOperation / delOperation)

**書き込みコード** (vrforch.cpp:120, 150):
```cpp
m_stateVrfObjectTable.hset(vrf_name, "state", "ok");
```

**削除コード** (vrforch.cpp:193):
```cpp
m_stateVrfObjectTable.del(vrf_name);
```

**フィールド**:

| フィールド | 型 | 値 | 意味 |
|-----------|----|----|------|
| `state` | string | `"ok"` (固定) | SAI VR (Virtual Router) オブジェクトが正常に作成済み |

**暗黙デフォルト / コード由来挙動**:
- `"ok"` 固定。SAI `create_virtual_router()` が `SAI_STATUS_SUCCESS` 以外を返した場合、hset は呼ばれない (vrforch.cpp:96-119)
- 新規作成 (addOperation) と更新 (既存 VRF への属性変更) の両方で `hset(vrf_name, "state", "ok")` を書く — upsert 相当
- `delOperation` の後に `del(vrf_name)` を呼ぶことで vrfmgrd の削除待ちループを unblock する

**consumer**:
- `vrfmgrd` (vrfmgr.cpp:208, 331): `isVrfObjExist()` で VRF_OBJECT_TABLE の存在確認 — VRF 削除時に orchagent が SAI VR を削除し終わるまで Linux VRF デバイスの削除を遅延 (DEL 順序保証)

---

## 挙動乖離・注意点

1. **VRF_TABLE state=ok は "Linux VRF デバイスが作れた" を保証しない**
   - `setLink()` 失敗後も `m_stateVrfTable.set()` が呼ばれる (vrfmgr.cpp:281-289)
   - `"ok"` は「SET 操作を受理した」を意味し、`"Linux VRF netdev 作成成功"` を厳密には意味しない

2. **VRF_OBJECT_TABLE の存在 = SAI VR オブジェクト存在の evidence**
   - `SAI_STATUS_SUCCESS` のときのみ hset される (vrforch.cpp:97-120)
   - 失敗ハンドリング後に `parseHandleSaiStatusFailure` で false を返す場合は書き込まない
   - orchagent が落ちた場合、STATE_DB の VRF_OBJECT_TABLE エントリが残留して vrfmgrd が削除を永久に待つ可能性あり (warm start 未考慮シナリオ)

3. **両テーブルとも YANG 未定義**
   - `sonic-vrf.yang` は CONFIG_DB の VRF テーブルのみ定義する
   - STATE_DB の `VRF_TABLE` / `VRF_OBJECT_TABLE` に YANG スキーマはなく、フィールド `state` の値は完全にコードハードコード

4. **mgmt VRF は VRF_TABLE に書かれるが VRF_OBJECT_TABLE には書かれない**
   - `CFG_MGMT_VRF_CONFIG_TABLE_NAME` からの SET も vrfmgrd の doTask で処理され `m_stateVrfTable.set()` を呼ぶ (vrfmgr.cpp:286-289)
   - mgmt VRF の vrfName は `"mgmt"` で、orchagent の VRFOrch は APP_VRF_TABLE を購読するが、mgmt VRF の場合は orchagent 側で SAI VR を作成しない (orchdaemon 起動時にデフォルト VR を使用するため)
   - 結果: `VRF_TABLE|mgmt` は存在しうるが `VRF_OBJECT_TABLE|mgmt` は存在しない

---

## 経路依存挙動まとめ

| 条件 | `VRF_TABLE` | `VRF_OBJECT_TABLE` |
|------|------------|-------------------|
| CONFIG_DB VRF SET → vrfmgrd 正常 | `state=ok` 書き込み | — |
| orchagent SAI VR 作成成功 | — | `state=ok` 書き込み |
| orchagent SAI VR 作成失敗 | — | 書き込みなし |
| CONFIG_DB VRF DEL → orchagent SAI VR 削除成功 | vrfmgrd が del (VRF_OBJECT_TABLE が消えてから) | del |
| mgmt VRF (hostcfgd 管轄) | `state=ok` 書き込み (vrfmgrd) | 書き込みなし |
| setLink() 失敗 (Linux VRF 作成失敗) | `state=ok` 書き込み (バグ相当) | — |
