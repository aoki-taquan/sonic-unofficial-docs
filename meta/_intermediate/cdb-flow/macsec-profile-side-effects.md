# macsec-profile — Phase F 副次 DB 書込 中間ファイル

**対象ページ**: `docs/reference/config-db/macsec-profile.md`
**フェーズ**: Phase F（副次 DB 書込）
**ソース調査ファイル**:
- `sonic-swss/orchagent/macsecorch.cpp`
- `sonic-swss/cfgmgr/macsecmgr.cpp`

## 抽出内容サマリー

### STATE_DB 書込

`MACsecOrch` が以下の STATE_DB テーブルに書き込む:

1. `STATE_MACSEC_PORT_TABLE` (`STATE_MACSEC_PORT_TABLE_NAME`) — `createMACsecPort()` で `max_sa_per_sc`, `state=ok` を set
2. `STATE_MACSEC_EGRESS_SC_TABLE` — `createMACsecSC()` で egress 方向の `state=ok` を set（key: `port_name|SCI`）
3. `STATE_MACSEC_INGRESS_SC_TABLE` — `createMACsecSC()` で ingress 方向の `state=ok` を set（key: `port_name|SCI`）
4. `STATE_MACSEC_EGRESS_SA_TABLE` — `createMACsecSA()` で egress SA の `state=ok` を set（key: `port_name|sci|an`）
5. `STATE_MACSEC_INGRESS_SA_TABLE` — `createMACsecSA()` で ingress SA の `state=ok` を set（key: `port_name|sci|an`）

削除 API: 対応する `del()` 呼び出しで各エントリを削除する。

コードエビデンス:
```cpp
// macsecorch.cpp L1535
m_state_macsec_port.set(port_name, fvVector);
// L2039
m_state_macsec_egress_sc.set(swss::join('|', port_name, MACsecSCI(sci)), fvVector);
// L2371
m_state_macsec_egress_sa.set(swss::join('|', port_name, sci, an), fvVector);
```

### ASIC_DB 書込（SAI 経由）

`sai_macsec_api` 呼び出し:
- `create_macsec()` — グローバル MACsec オブジェクト作成 (L1253, L1285)
- `create_macsec_port()` — ポートごとの MACsec 有効化 (L1558)
- `create_macsec_sc()` — SC オブジェクト作成 (L2084)
- `create_macsec_sa()` — SA オブジェクト作成。属性: AN, SAK, SALT, AUTH_KEY, XPN (L2504)
- `remove_macsec_sa()` — SA 削除 (L2524)
- `set_macsec_sa_attribute()` — XPN 更新 (L2203)

### wpa_supplicant 書込

`macsecmgr.cpp` L750-830: `wpa_cli set_network` 経由でプロセス内状態に書き込む。
書き込まれるフィールド: `macsec_policy`, `macsec_integ_only`, `mka_cak`, `mka_ckn`,
`mka_priority`, `mka_rekey_period` (rekey_period > 0 のみ), `macsec_ciphersuite`,
`macsec_include_sci`, `macsec_replay_protect`, `macsec_replay_window` (enable_replay_protect=true のみ)。

## ステータス

- [x] STATE_DB 書込テーブル特定
- [x] ASIC_DB / SAI API 特定
- [x] wpa_supplicant 書込フィールド特定
- [x] `<!-- side-effects -->` ブロック追加完了
