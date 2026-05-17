# vlan-state — Phase B 書込み順依存スキャンノート

対象テーブル: `STATE_DB VLAN_TABLE`
書き込み主体: `vlanmgrd` (`sonic-swss/cfgmgr/vlanmgr.cpp`)
スキャン範囲: vlanmgr.cpp 全行精読 + intfmgr.cpp / nbrmgr.cpp / stpmgr.cpp / natmgr.cpp / vxlanmgr.cpp 参照箇所確認
調査日: 2026-05-17

---

## 検出した順序依存・タイミング依存

### 1. gMacAddress 未確定ガード（STATE_DB 書込みの全ブロック）

`doVlanTask()` L318-322: `isVlanMacOk()` (= `!!gMacAddress`) が false の間、関数を即 `return` して全タスクをキューに留める。`gMacAddress` は syncd/SAI がスイッチ MAC を確定してからグローバル変数として有効化される。

```cpp
// vlanmgr.cpp:318-322
if (!isVlanMacOk())
{
    SWSS_LOG_DEBUG("VLAN mac not ready, delaying VLAN task");
    return;
}
```

**依存**: syncd 起動 → SAI スイッチ MAC 確定 → `gMacAddress` 有効 → `doVlanTask()` 処理開始 → STATE_DB 書込み。MAC 確定前は STATE_DB `VLAN_TABLE` への書き込みは発生しない（自動リトライ待機）。

evidence: `vlanmgr.cpp` L311-322

### 2. STATE_DB 書込み順序（Linux bridge → APP_DB → STATE_DB）

VLAN SET 処理内での書き込み順序は固定:

```cpp
// vlanmgr.cpp:383-443（概略）
addHostVlan(vlan_id);          // 1. Linux bridge 作成
m_appVlanTableProducer.set();  // 2. APP_DB VLAN_TABLE 書込み
m_stateVlanTable.set(key, fvVector);  // 3. STATE_DB VLAN_TABLE 書込み
```

**依存**: Linux bridge 作成と APP_DB 通知が完了した後に STATE_DB `VLAN_TABLE` のエントリが立つ。STATE_DB を参照する downstream consumers が ready を検出したとき、Linux bridge と APP_DB エントリの両方が存在することが保証される。

evidence: `vlanmgr.cpp` L383-443

### 3. STATE_DB エントリ存在が downstream consumers の前提条件

以下の consumers は自身の処理ループ内で `isVlanStateOk()` を呼び、STATE_DB `VLAN_TABLE` にエントリが存在しない場合はタスクをスキップして自動リトライ待機する:

| consumer | ファイル | 確認箇所 |
|---------|---------|---------|
| `vlanmgrd`（VLAN_MEMBER 処理） | `vlanmgr.cpp:642` | `doVlanMemberTask()` 内 |
| `intfmgrd` | `intfmgr.cpp:655` | VLAN インタフェース SET 前 |
| `nbrmgrd` | `nbrmgr.cpp` | ネイバーエントリ SET 前 |
| `stpmgrd` | `stpmgr.cpp:1282` | STP ポート/VLAN SET 前 |
| `natmgrd` | `natmgr.cpp:102` | NAT エントリ SET 前 |
| `vxlanmgrd` | `vxlanmgr.cpp:774` | VXLAN tunnel member SET 前 |

全ての読み取りは `m_stateVlanTable.get(alias, temp)` による存在チェック（bool）であり、`state` の値は参照されない。

**依存**: `VLAN_TABLE|VlanN` の SET 処理完了（STATE_DB 書込み）→ 上記 consumers の当該 VLAN に関連するタスク処理開始。VLAN が STATE_DB に未登録の間、downstream の全設定（VLAN_MEMBER / VLAN_INTERFACE / ネイバー / STP / NAT / VXLAN）は保留される。

evidence: `vlanmgr.cpp` L642, `intfmgr.cpp` L655, `stpmgr.cpp` L1282

### 4. DEL 時の STATE_DB エントリ削除と downstream への影響

```cpp
// vlanmgr.cpp:456-463
removeHostVlan(vlan_id);
m_vlans.erase(key);
m_appVlanTableProducer.del(key);
m_stateVlanTable.del(key);  // STATE_DB エントリを削除
```

CONFIG_DB `VLAN` DEL 操作受信と同時に STATE_DB からエントリを削除する。VLAN_MEMBER が残存している場合でも VLAN_MEMBER の DEL 完了を待たずに STATE_DB を削除する。

**副作用（逆順 DEL の危険）**: VLAN を先に DEL すると STATE_DB `VLAN_TABLE` から `Vlan<N>` が消えるため、残存する VLAN_MEMBER タスク（Consumer キュー内）の `isVlanStateOk()` チェックが永遠に false を返し、VLAN_MEMBER タスクが孤立・滞留する。

**推奨 DEL 順序**: VLAN_MEMBER を全て DEL → VLAN DEL の順。逆順（VLAN 先 DEL）は支障をきたす。

evidence: `vlanmgr.cpp` L456-471, L642

### 5. warm-restart: STATE_DB エントリを根拠とした重複スキップ

```cpp
// vlanmgr.cpp:371-378
if (isVlanStateOk(key) && m_vlans.find(key) == m_vlans.end())
{
    SWSS_LOG_DEBUG("%s already created", kfvKey(t).c_str());
    m_vlans.insert(key);
    m_vlanReplay.erase(kfvKey(t));
    it = consumer.m_toSync.erase(it);
    continue;
}
```

warm-restart 時: STATE_DB にエントリが存在し、かつ `m_vlans`（in-memory セット）に未登録の場合は Linux bridge 再作成をスキップして replay エントリを消化する。STATE_DB エントリの残存が冪等動作の根拠。

**依存**: コールドリブートでは STATE_DB がクリアされるため全 VLAN を再処理。warm-reboot では Linux bridge がカーネルに残るため、STATE_DB エントリ存在確認 → 再作成スキップの流れが機能する。

evidence: `vlanmgr.cpp` L371-378, L479-488

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | syncd/SAI MAC 確定 → STATE_DB 書込み開始 | 強制先行 | 自動リトライ（MAC 確定後に消化） |
| 2 | Linux bridge 作成 + APP_DB 書込み → STATE_DB 書込み | 同一処理内順序保証 | 常にこの順で実行 |
| 3 | STATE_DB `VLAN_TABLE` 書込み → downstream consumers 処理開始 | 強制先行 | downstream は自動リトライ待機 |
| 4 | VLAN_MEMBER DEL 完了 → VLAN DEL | 推奨（逆順 NG） | VLAN_MEMBER を先に DEL すること |
| 5 | warm-restart: STATE_DB エントリ存在 → Linux bridge 再作成スキップ | 条件スキップ | cold reboot では STATE_DB クリアで再処理 |
