# VNET テーブル — 例外条件・特殊挙動

## スキーマ検証

- **`vrf_name` パターン**: YANG で `pattern "default"` のみ許可（VRF 名は `default` 固定）。それ以外は YANG バリデーションで `"Invalid VRF name"` エラー[^e2]。
- **`vxlan_tunnel` + `vni` 必須**: `vxlanmgr` はこれら両方が揃うまで `"information is incomplete, just ignore this message"` としてメッセージを破棄してリトライ待ち[^e1]。

## ignore / skip

- **VxLAN トンネル未作成**: 参照する `VXLAN_TUNNEL` エントリがキャッシュに存在しない場合、`vxlanmgr` はメッセージを suspend してリトライ[^e1]。
- **VRF 未 ready**: `isVrfStateOk()` が false の場合もリトライ待ち[^e1]。
- **MAC アドレス未設定**: ルータ MAC が取得できない場合もリトライ[^e1]。

## エラー時動作

- VxLAN デバイス作成失敗: `SWSS_LOG_ERROR("Cannot create vxlan %s")` を記録して false を返す[^e1]。
- VNET が存在しない状態での操作: `SWSS_LOG_WARN("Vxlan(Vnet %s) hasn't been created")` を記録[^e1]。
- orchagent での VR オブジェクト作成失敗: `std::runtime_error` を throw し呼び出し元でキャッチ、`SWSS_LOG_ERROR` を記録[^e3]。

[^e1]: `sonic-swss/cfgmgr/vxlanmgr.cpp` <https://github.com/sonic-net/sonic-swss/blob/master/cfgmgr/vxlanmgr.cpp>
[^e2]: `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-vnet.yang` <https://github.com/sonic-net/sonic-buildimage/blob/master/src/sonic-yang-models/yang-models/sonic-vnet.yang>
[^e3]: `sonic-swss/orchagent/vnetorch.cpp` <https://github.com/sonic-net/sonic-swss/blob/master/orchagent/vnetorch.cpp>
