# VXLAN_EVPN_NVO — Phase A: フィールドのコード由来デフォルト調査

## 調査対象

`docs/reference/config-db/vxlan-evpn-nvo.md`

## フィールド一覧とデフォルト調査結果

### `name` (key)

- **型**: string
- **YANG**: `mandatory` 相当（key leaf）
- **デフォルト**: なし。オペレータが `config vxlan evpn_nvo add <nvo_name> <vxlan_name>` で明示指定する。
- **証拠**: `sonic-utilities/config/vxlan.py:129` — `config_db.set_entry('VXLAN_EVPN_NVO', nvo_name, fvs)`

### `source_vtep`

- **型**: leafref → `VXLAN_TUNNEL.name`
- **YANG**: `mandatory true`（`sonic-vxlan.yang`）
- **デフォルト**: なし。CLI が `fvs = {'source_vtep': vxlan_name}` として書き込む（ユーザー引数の `<vxlan_name>`）。
- **証拠**: `sonic-utilities/config/vxlan.py:127-129`
- **ランタイム挙動**: `vxlanmgr.cpp:doVxlanEvpnNvoCreateTask()` がこのフィールドを読み取り、`isTunnelActive(value)` で参照先 VXLAN_TUNNEL のアクティブ状態を確認する。未 active の場合はリトライ待ち。

## 結論

`VXLAN_EVPN_NVO` テーブルのフィールドはすべて mandatory であり、コード側にハードコードされたデフォルト値は存在しない。エントリ自体もビルド時・minigraph・db_migrator いずれからも自動生成されない。オペレータの明示的な CLI 操作によってのみ書き込まれる。

## 参照ソース

- `sonic-utilities/config/vxlan.py` (lines 102–131)
- `sonic-swss/cfgmgr/vxlanmgr.cpp` (lines 672–705: `doVxlanEvpnNvoCreateTask`)
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-vxlan.yang` (VXLAN_EVPN_NVO_LIST)
