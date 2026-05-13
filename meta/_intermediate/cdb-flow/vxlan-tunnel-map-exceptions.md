# VXLAN_TUNNEL_MAP テーブル — 例外条件・特殊挙動

## スキーマ検証

- **`vlan` フィールド必須**: YANG `mandatory true`、かつ `pattern 'Vlan([0-9]{1,3}|...)'` — `Vlan` プレフィクスがない文字列は reject[^e2]。
- **`vni` フィールド必須**: YANG `mandatory true`[^e2]。
- **VLAN leafref コメントアウト**: libyang の back-link 問題のため VLAN の `leafref` は意図的にコメントアウトされ、パターン文字列のみで検証される（`sonic-vlan.yang` との整合性チェックなし）[^e2]。

## ignore / skip

- **VLAN 重複マッピング**: 同じ `vlan` が既にマップされている場合 `SWSS_LOG_ERROR("Vlan %s already mapped. Map Create failed")` を記録してエントリを破棄（`true` を返す）[^e1]。
- **VNI 重複マッピング**: 同じ `vni` が既にマップされている場合も同様に破棄[^e1]。
- **マップ重複（キー）**: キャッシュに同名マップが存在する場合 `SWSS_LOG_ERROR("Map already present")` で破棄[^e1]。
- **トンネル未 active**: 参照 `VXLAN_TUNNEL` が active でない場合リトライ待ち[^e1]。

[^e1]: `sonic-swss/cfgmgr/vxlanmgr.cpp` <https://github.com/sonic-net/sonic-swss/blob/master/cfgmgr/vxlanmgr.cpp>
[^e2]: `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-vxlan.yang` <https://github.com/sonic-net/sonic-buildimage/blob/master/src/sonic-yang-models/yang-models/sonic-vxlan.yang>
