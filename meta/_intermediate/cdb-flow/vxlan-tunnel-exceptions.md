# VXLAN_TUNNEL テーブル — 例外条件・特殊挙動

## スキーマ検証

- **最大 2 エントリ**: YANG `max-elements 2` — 3 エントリ目は YANG で reject される[^e2]。
- **`ttl_mode`**: `pattern "uniform|pipe"` — それ以外の値は YANG で reject[^e2]。
- **`src_ip` / `dst_ip`**: `inet:ip-address` 型 — 不正 IP は YANG で reject[^e2]。

## ignore / skip

- **削除時の NVO 残留**: tunnel 削除時に NVO エントリが残っている場合 `SWSS_LOG_WARN("Tunnel %s deletion failed. Need to delete NVO")` を記録してリトライ待ち[^e1]。
- **削除時のマップ残留**: tunnel map エントリが残っている場合も `SWSS_LOG_WARN("Need to delete mapping entries")` でリトライ待ち[^e1]。

## エラー時動作

- tunnel 削除失敗: `SWSS_LOG_WARN` を記録。state VXLAN tunnel テーブルが未クリアの場合 `SWSS_LOG_WARN("State VXLAN tunnel table not yet empty.")` を記録してリトライ[^e1]。
- Vxlan Net Dev 作成失敗: `SWSS_LOG_WARN("Vxlan Net Dev creation failure for %s VNI(%s) VLAN(%s)")` を記録[^e1]。

[^e1]: `sonic-swss/cfgmgr/vxlanmgr.cpp` <https://github.com/sonic-net/sonic-swss/blob/master/cfgmgr/vxlanmgr.cpp>
[^e2]: `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-vxlan.yang` <https://github.com/sonic-net/sonic-buildimage/blob/master/src/sonic-yang-models/yang-models/sonic-vxlan.yang>
