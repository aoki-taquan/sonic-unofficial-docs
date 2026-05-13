# VRF テーブル — 例外条件・特殊挙動

## スキーマ検証

- **名前パターン**: YANG `pattern "Vrf[a-zA-Z0-9_-]+"` — 違反は `"Invalid VRF name"` エラーで reject[^e2]。
- **`vni` 範囲**: `0..16777215`。0 は VNI マッピング解除を意味する[^e2]。

## ignore / skip

- **VNI 重複**: 同じ VNI が別の VRF にマップ済みの場合 `vrfmgr` は `SWSS_LOG_ERROR("vni %d is already mapped to vrf %s")` を記録して `false` を返す（エントリを破棄）[^e1]。
- **VRF の VNI 再マップ**: 既に VNI が設定されている VRF に別の VNI をセットしようとすると `SWSS_LOG_ERROR("vrf %s is already mapped to vni %d")` でエラー[^e1]。
- **削除遅延**: VRF 削除時に orchagent の VRF オブジェクトが残存していると `vrfmgr` は削除をリトライ待ち（`isVrfObjExist()` チェック）[^e1]。

## エラー時動作

- Linux VRF netdev 作成失敗: `SWSS_LOG_ERROR("Failed to create vrf netdev")` を記録、STATE_DB へは `state: ok` を書き込む前に失敗[^e1]。
- VNI マップ設定失敗: `SWSS_LOG_ERROR("VRF VNI Map Config Failed")` を記録してエントリを破棄[^e1]。

## デフォルト補完

- `fallback`: YANG `default false`[^e2]。
- `vni`: YANG `default 0`（VNI マッピングなし）[^e2]。

[^e1]: `sonic-swss/cfgmgr/vrfmgr.cpp` <https://github.com/sonic-net/sonic-swss/blob/master/cfgmgr/vrfmgr.cpp>
[^e2]: `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-vrf.yang` <https://github.com/sonic-net/sonic-buildimage/blob/master/src/sonic-yang-models/yang-models/sonic-vrf.yang>
