# VLAN_SUB_INTERFACE テーブル — 例外条件・特殊挙動

## スキーマ検証

- **名前長**: 15 文字超の場合 YANG `must` 制約で `"Must condition not satisfied, please follow vlan sub interface naming convention"` エラー[^e2]。
- **親インタフェース**: 名前のドット前部分が `PORT_LIST` または `PORTCHANNEL_LIST` に存在しない場合も YANG が reject[^e2]。
- **VLAN ID 範囲**: ドット後 ID は 1〜4094[^e2]。short-name 形式では `vlan` フィールドが必須（なければ YANG `must` 違反）。
- **`isValid()` チェック**: `intfmgr` が `subIntf::isValid()` で invalid と判定した場合 `SWSS_LOG_ERROR("Invalid subnitf")` を記録して skip[^e1]。

## ignore / skip

- **VLAN ID 未設定**: short-name 形式で `vlan` フィールドが `"0"` または空の場合 `SWSS_LOG_INFO("Vlan ID not configured")` を記録してリトライ待ち[^e1]。
- **ip link コマンド失敗**: netdev 作成 / MTU 設定 / admin_status 設定で `runtime_error` 発生時は `SWSS_LOG_NOTICE` を記録してリトライ待ち[^e1]。

## デフォルト補完

- `mtu` 省略時: `MTU_INHERITANCE`（親インタフェースの MTU を継承）が補完される[^e1]。
- `admin_status` 省略時: `"up"` が補完される。ただし親インタフェースの admin status が適用されて実効値が決定される[^e1]。

[^e1]: `sonic-swss/cfgmgr/intfmgr.cpp` <https://github.com/sonic-net/sonic-swss/blob/master/cfgmgr/intfmgr.cpp>
[^e2]: `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-vlan-sub-interface.yang` <https://github.com/sonic-net/sonic-buildimage/blob/master/src/sonic-yang-models/yang-models/sonic-vlan-sub-interface.yang>
