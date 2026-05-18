# state-vrf: Phase F 副次 DB 書込調査

調査日: 2026-05-18
対象: STATE_DB VRF_TABLE / VRF_OBJECT_TABLE
書込プロセス: vrfmgrd (VRF_TABLE), VRFOrch (VRF_OBJECT_TABLE)

## 調査方針

VRF_TABLE / VRF_OBJECT_TABLE への書込が、他の DB テーブルへの書込をトリガーするかを調査する。
これらは STATE_DB の読み取り専用観測テーブルであり、他プロセスが subscribe/poll して処理を起動する「gate」として機能する。

## VRF_TABLE 書込の副次 DB 書込

### intfmgrd → APP_DB INTF_TABLE

`sonic-swss/cfgmgr/intfmgr.cpp:671, 680`

intfmgrd は `isInterfaceCreateDone()` ヘルパー内で `m_stateVrfTable.get(alias, temp)` をポーリングし、
VRF_TABLE エントリが存在すれば VRF バインドを進める。

VRF_TABLE|<name> が SET されると、intfmgrd が CONFIG_DB INTERFACE テーブルの未処理エントリを処理し、
APP_DB `INTF_TABLE|<intf>:<prefix>` へ書き込む。

証拠: `intfmgr.cpp:677-684` — VRF_PREFIX または VRF_MGMT を持つインタフェースについて、
`m_stateVrfTable.get()` が true を返した場合に isInterfaceCreateDone() が true を返し、
doTask() が APPL_DB への set を実行する。

### vxlanmgr → APP_DB VXLAN_VRF_TABLE

`sonic-swss/cfgmgr/vxlanmgr.cpp:744`

VxlanMgr::isVrfStateOk() が VRF_TABLE のエントリ存在を確認し、VXLAN VRF マッピング設定の前提条件とする。
VRF_TABLE が存在する場合に APP_DB `VXLAN_VRF_TABLE` への書込が実行される。

## VRF_OBJECT_TABLE 書込の副次 DB 書込

### vrfmgrd → 削除ブロック解除 → APP_DB VRF_TABLE del

`sonic-swss/cfgmgr/vrfmgr.cpp:204-214, 331-346`

vrfmgrd は VRF 削除処理の待機ループで `isVrfObjExist()` を呼び出す。
VRF_OBJECT_TABLE|<name> が DEL されると、vrfmgrd のブロックが解除され、
APP_DB `APP_VRF_TABLE_NAME` の del および STATE_DB `VRF_TABLE` の del が実行される。

これは VRF_OBJECT_TABLE への書込（正確には DEL）が APP_DB への書込を連鎖的に起動するパターン。

## 直接の副次書込なし（書込方向）

VRF_TABLE / VRF_OBJECT_TABLE への SET は他プロセスに直接 NOTIFY するわけではなく、
ポーリング（get() の成否）により検出される。このため、SET の瞬間に同期的な副次 DB 書込は発生しない。
副次書込は他プロセスの次の doTask() イテレーション内で起動される。

## 結論

| トリガー操作 | 副次書込先 | 書込プロセス | 書込条件 |
|---|---|---|---|
| VRF_TABLE SET | APP_DB INTF_TABLE | intfmgrd | VRF バインドされた INTERFACE エントリが CONFIG_DB に存在する場合 |
| VRF_TABLE SET | APP_DB VXLAN_VRF_TABLE | vxlanmgr | VXLAN VRF マッピング設定が CONFIG_DB に存在する場合 |
| VRF_OBJECT_TABLE DEL | APP_DB APP_VRF_TABLE (del) + STATE_DB VRF_TABLE (del) | vrfmgrd | VRF 削除処理の待機ループが解除されたとき |
| VRF_TABLE SET | 他 STATE_DB / ASIC_DB | なし | VRF_TABLE は sentinel 読み取りのみ。ASIC_DB への書込は VRFOrch が APP_DB 経由で行う |
