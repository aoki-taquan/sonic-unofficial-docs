# state-vrf — 暗黙参照 (cross-table refs) 調査メモ

## 調査対象

`docs/reference/config-db/state-vrf.md` Phase C 追加分。
本ページの主題は **STATE_DB の 2 テーブル**（`VRF_TABLE` / `VRF_OBJECT_TABLE`）。
`VRF_TABLE` は `vrfmgrd` が**書き手 (producer)**、`intfmgrd` / `vxlanmgr` が**読み手 (consumer)**。
`VRF_OBJECT_TABLE` は `VRFOrch` が**書き手**、`vrfmgrd` が**読み手**（削除同期 sentinel）。

調査日: 2026-05-18  
ソースファイル:
- `sonic-swss/cfgmgr/vrfmgr.cpp`
- `sonic-swss/cfgmgr/intfmgr.cpp`
- `sonic-swss/cfgmgr/vxlanmgr.cpp`
- `sonic-swss/orchagent/vrforch.cpp`
- `sonic-swss/orchagent/intfsorch.cpp`

---

## 暗黙参照 (実装レベル)

### 1. `intfmgrd` — VRF_TABLE READ（VRF バインド前提チェック）

- **参照先テーブル**: `STATE_DB VRF_TABLE`
- **参照方向**: 読み取り（`m_stateVrfTable.get(alias, temp)`）
- **条件**: `*_INTERFACE` テーブルで `vrf_name` が指定されているとき、常時
- **意味**: `intfmgrd` は VRF バインドを行う前に `m_stateVrfTable.get(alias, temp)` でエントリ存在を確認する。取得失敗（VRF_TABLE にエントリなし）の場合は処理を `m_toSync` に残して次の `doTask()` まで保留。VRF が Linux デバイスとして準備できていない間は INTERFACE の VRF バインドが待機状態になる。
- **evidence**: `intfmgr.cpp:40` (`m_stateVrfTable` 初期化), `intfmgr.cpp:671` (`m_stateVrfTable.get`), `intfmgr.cpp:680` (同)

### 2. `vxlanmgr` — VRF_TABLE READ（VXLAN VRF マッピング前提チェック）

- **参照先テーブル**: `STATE_DB VRF_TABLE`
- **参照方向**: 読み取り（`isVrfStateOk()` → `m_stateVrfTable.get(vrfName, temp)`）
- **条件**: `VNET` テーブルで VRF が指定されているとき
- **意味**: `vxlanmgr` は `isVrfStateOk(info.m_vnet)` で VRF が STATE_DB に登録済みか確認する（`vxlanmgr.cpp:328`）。VRF_TABLE にエントリがなければ VXLAN VRF マッピング設定を保留。VRF 作成完了通知で再トリガされる。
- **evidence**: `vxlanmgr.cpp:192` (`m_stateVrfTable` 初期化), `vxlanmgr.cpp:328` (`isVrfStateOk` 呼び出し), `vxlanmgr.cpp:738–744` (`isVrfStateOk` 実装)

### 3. `vrfmgrd` — VRF_OBJECT_TABLE READ（削除同期 sentinel）

- **参照先テーブル**: `STATE_DB VRF_OBJECT_TABLE`
- **参照方向**: 読み取り（`isVrfObjExist()` → `m_stateVrfObjectTable.get(vrfName, temp)`）
- **条件**: CONFIG_DB `VRF` への DEL 操作受信時
- **意味**: VRF 削除シーケンスで `vrfmgrd` は `isVrfObjExist(vrfName)` を繰り返し確認し、`VRF_OBJECT_TABLE` エントリが消えるまで（`VRFOrch` が SAI VR を削除するまで）APP_DB への DEL と Linux VRF 削除を保留する。これが VRF 削除の 2 フェーズ同期機構の核心。
- **evidence**: `vrfmgr.cpp:204–208` (`isVrfObjExist` 実装), `vrfmgr.cpp:331` (DEL 待機ループ), `vrfmgr.cpp:342` (再確認)

### 4. `VRFOrch` — VRF_OBJECT_TABLE WRITE（SAI 完了通知）

- **参照先テーブル**: `STATE_DB VRF_OBJECT_TABLE`
- **参照方向**: 書き込み（`m_stateVrfObjectTable.hset` / `del`）
- **条件**: SAI `create_virtual_router()` 成功時（SET）、`remove_virtual_router()` 成功時（DEL）
- **意味**: `VRFOrch` が SAI VR を作成した後に `VRF_OBJECT_TABLE|<name>` を SET し、削除後に DEL することで、`vrfmgrd` の削除待機ループへ完了通知を行う。STATE_DB の書き手として `VRFOrch` 以外は存在しない（VNET の VNETOrch は `VRF_OBJECT_TABLE` を書かない）。
- **evidence**: `vrforch.cpp:120` (`hset` — SAI create 1 回目成功), `vrforch.cpp:150` (`hset` — SAI create 2 回目成功パス), `vrforch.cpp:193` (`del` — SAI remove 成功)

### 5. `vrfmgrd` — VRF_TABLE WRITE（VRF 存在通知）

- **参照先テーブル**: `STATE_DB VRF_TABLE`
- **参照方向**: 書き込み（`m_stateVrfTable.set` / `del`）
- **条件**: CONFIG_DB `VRF` / `VNET` への SET/DEL 操作受信時
- **意味**: `vrfmgrd` が Linux VRF デバイス作成後に `VRF_TABLE|<name>` を SET（`vrfmgr.cpp:289`）。削除時は `isVrfObjExist()` が false になった後に DEL（`vrfmgr.cpp:339, 351`）。`intfmgrd` / `vxlanmgr` のコンシューマはこのエントリを readiness sentinel として使用する。
- **evidence**: `vrfmgr.cpp:25` (`m_stateVrfTable` 初期化), `vrfmgr.cpp:289` (SET), `vrfmgr.cpp:339` (DEL), `vrfmgr.cpp:351` (VNET 経路の DEL)

---

## 参照関係サマリ

```
STATE_DB VRF_TABLE
  書き手: vrfmgrd (Linux VRF 作成後 SET、削除確認後 DEL)
  読み手: intfmgrd  → VRF バインド前の readiness チェック (intfmgr.cpp:671, 680)
          vxlanmgr  → VXLAN VRF マッピング前の readiness チェック (vxlanmgr.cpp:744)

STATE_DB VRF_OBJECT_TABLE
  書き手: VRFOrch (SAI create 成功後 hset、SAI remove 成功後 del)
  読み手: vrfmgrd  → VRF 削除の 2 フェーズ同期（削除待機ループ）(vrfmgr.cpp:331)
```

## evidence

- `vrfmgr.cpp`: L25 (`m_stateVrfTable`/`m_stateVrfObjectTable` 初期化), L204–208 (`isVrfObjExist`), L289 (`VRF_TABLE.set`), L331 (DEL 待機), L339 (`VRF_TABLE.del`), L342 (再確認), L351 (VNET DEL パス)
- `intfmgr.cpp`: L40 (`m_stateVrfTable` 初期化), L671 (`VRF_TABLE.get` — SET パス), L680 (`VRF_TABLE.get` — DEL パス)
- `vxlanmgr.cpp`: L192 (`m_stateVrfTable` 初期化), L328 (`isVrfStateOk` 呼び出し), L738–744 (`isVrfStateOk` 実装)
- `vrforch.cpp`: L120 (`VRF_OBJECT_TABLE.hset` — SAI create), L150 (同), L193 (`VRF_OBJECT_TABLE.del` — SAI remove)
