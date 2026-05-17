# state-vrf: Phase B — 書込み順依存 (ordering)

調査日: 2026-05-17  
ソース:
- sonic-net/sonic-swss cfgmgr/vrfmgr.cpp (master)
- sonic-net/sonic-swss cfgmgr/intfmgr.cpp (master)
- sonic-net/sonic-swss cfgmgr/vxlanmgr.cpp (master)

## 結論

STATE_DB の VRF_TABLE / VRF_OBJECT_TABLE は書込み順序の sentinel として設計されており、
前段テーブルの書込み完了を後続プロセスが polling して待機する構造になっている。

## SET 方向の順序制約

```
CONFIG_DB VRF|<name> SET
  ↓
vrfmgrd: setLink() → Linux VRF デバイス作成
  ↓
vrfmgrd: STATE_DB VRF_TABLE|<name> SET {state=ok}   ← (1) vrfmgrd が先に書く
  ↓
vrfmgrd: APP_DB APP_VRF_TABLE|<name> SET             ← (2) その後 APP_DB に通知
  ↓
VRFOrch: SAI create_virtual_router()
  ↓
VRFOrch: STATE_DB VRF_OBJECT_TABLE|<name> SET {state=ok}  ← (3) orchagent が最後
```

- intfmgrd は VRF バインド設定時に STATE_DB VRF_TABLE の存在を確認してから処理する
  (intfmgr.cpp:678-681: `m_stateVrfTable.get(alias, temp)` が true でないと処理スキップ)
- vxlanmgr は VXLAN VRF マッピング設定前に `isVrfStateOk()` で VRF_TABLE を確認する
  (vxlanmgr.cpp:744)

## DEL 方向の順序制約 (vrfmgr.cpp:323-351)

```
CONFIG_DB VRF|<name> DEL
  ↓
vrfmgrd: isVrfObjExist() = STATE_DB VRF_OBJECT_TABLE|<name> の存在確認
  → false の場合: it++ continue (要求をキューに残して再試行)    ← wait loop
  → true の場合: 下記へ進む
  ↓
vrfmgrd: APP_DB APP_VRF_TABLE|<name> DEL → VRFOrch へ削除通知
vrfmgrd: STATE_DB VRF_TABLE|<name> DEL
  ↓
VRFOrch: SAI remove_virtual_router()
VRFOrch: STATE_DB VRF_OBJECT_TABLE|<name> DEL
  ↓
vrfmgrd: isVrfObjExist() が false になる → Linux VRF 削除 (delLink)
```

重要: DEL 方向では vrfmgrd が VRF_OBJECT_TABLE の存在を polling し、
orchagent による SAI 削除完了を待ってから Linux デバイスを削除する。
これにより fpmsyncd が VRF ifname を参照できる期間を保証する (vrfmgr.cpp:316コメント)。

## intfmgrd の依存関係 (intfmgr.cpp:668-684)

```cpp
// isIntfStateOk() の VRF 判定ロジック
else if ((!alias.compare(0, strlen(VRF_PREFIX), VRF_PREFIX)) ||
        (alias == VRF_MGMT))
{
    if (m_stateVrfTable.get(alias, temp))
    {
        SWSS_LOG_DEBUG("Vrf %s is ready", alias.c_str());
        return true;
    }
}
```

インタフェースに VRF バインドを設定する際、VRF_TABLE の存在が前提条件となる。
VRF_TABLE がない状態でインタフェース設定が到着した場合、
m_toSync キューに残留して次の doTask() で再処理される。

## VNET の非対称性

VNET は CONFIG_DB の VNET テーブルから SET を受けると:
- VRF_TABLE に書き込む (vrfmgr.cpp:308: m_appVnetTableProducer.set + m_stateVrfTable.set)
- VRF_OBJECT_TABLE には書き込まない (VNETOrch が担当するが現状未実装)
→ VNET VRF の DEL 処理では isVrfObjExist() チェックをスキップする別コードパスを通る
  (vrfmgr.cpp:353-356: m_appVnetTableProducer.del + m_stateVrfTable.del を直接実行)
