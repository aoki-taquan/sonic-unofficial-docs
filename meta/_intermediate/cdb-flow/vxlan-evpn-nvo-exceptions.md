# VXLAN_EVPN_NVO テーブル — 例外条件・特殊挙動

## スキーマ検証

- **最大 1 エントリ**: YANG `max-elements 1` — 2 エントリ目は YANG で reject される[^e2]。
- **`vxlanmgr` でも重複チェック**: キャッシュに既存の NVO エントリがある場合 `SWSS_LOG_ERROR("Only Single NVO object allowed")` を記録して破棄（YANG 検証をバイパスした場合の二重防護）[^e1]。

## ignore / skip

- **VTEP 未 active**: `source_vtep` が参照する `VXLAN_TUNNEL` が active でない場合 `SWSS_LOG_ERROR("NVO %s creation failed. VTEP not present")` を記録してリトライ待ち（`false` を返す）[^e1]。

## エラー時動作

- NVO エントリが見つからない状態での削除: `SWSS_LOG_ERROR("NVO deletion NVO: %s not found exception: %s")` を記録[^e1]。
- NVO 作成成功時: `disableLearningForAllVxlanNetdevices()` を呼び出してすべての VXLAN netdev の MAC learning を無効化する（EVPN 前提の動作）[^e1]。

[^e1]: `sonic-swss/cfgmgr/vxlanmgr.cpp` <https://github.com/sonic-net/sonic-swss/blob/master/cfgmgr/vxlanmgr.cpp>
[^e2]: `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-vxlan.yang` <https://github.com/sonic-net/sonic-buildimage/blob/master/src/sonic-yang-models/yang-models/sonic-vxlan.yang>
