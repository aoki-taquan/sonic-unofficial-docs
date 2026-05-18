# DOT1X / PAC テーブル — プラットフォーム差調査 (Phase H)

Task F Phase H: `PAC_PORT_CONFIG_TABLE` / `HOSTAPD_GLOBAL_CONFIG_TABLE` 適用時のプラットフォーム・構成差を `pacmgrd` / `hostapdmgrd` のソース (`sonic-buildimage/src/sonic-pac/`) から精読した結果。

## 結論

**プラットフォーム差なし**。PAC / DOT1X は SAI 非経由のホスト内認証フレームワークであり、ASIC 種別・multi-asic / VOQ chassis 構成・ベンダー固有実装に依存しない。

## 根拠

### 1. pacmgrd は SAI を呼ばない

`pacmgr.cpp` を `sai_` / `SAI_` でgrepしても 0 ヒット。`pacmgrd` は CONFIG_DB を直接購読し、`authmgr*()` ライブラリ関数 (内部プロセス) を呼び出すのみ。ASIC 操作は発生しない。

### 2. hostapdmgrd も SAI 非経由

`hostapdmgr.cpp` (1293 行) を `platform|asic|chassis|sai_|namespace|multi_asic|voq` でgrepすると 0 ヒット。hostapdmgr は `wpa_ctrl` ソケット経由でホスト上の `hostapd` プロセスを制御し、RADIUS サーバ設定ファイルを書き換えるのみ。

### 3. RADIUS 依存はプラットフォーム非依存

`hostapdmgr.cpp:42-46` で `RADIUS_SERVER` / `RADIUS` テーブルを CONFIG_DB から購読するが、RADIUS サーバは外部エンティティ (RFC 2865)。プラットフォーム差を持たない。

### 4. ビルド・デバイス設定にプラットフォーム分岐なし

- `sonic-buildimage/device/` 配下を `dot1x|PAC_PORT|hostapd` でgrepしても 0 ヒット（platform 固有の PAC 設定ファイル挿入なし）
- `rules/` 配下を `pac\b|PAC\b|dot1x` でgrepしても 0 ヒット（platform 向け mk フラグなし）
- `files/build_templates/` および `files/image_config/` にも PAC 固有 j2 テンプレートは存在しない

### 5. YANG モデルにプラットフォーム条件なし

`sonic-buildimage/src/sonic-yang-models` を `pac_port|HOSTAPD|dot1x` でgrepしても 0 ヒット（sonic-pac は独立の YANG 定義を持つが shallow clone 未収録）。ビルド時のプラットフォーム分岐は確認されない。

### 6. multi-asic / VOQ chassis 構成

`pacmgrd` / `hostapdmgrd` は host Docker で動作し、`asicN` namespace の APP_DB / STATE_DB を参照しない (`pacmgr.cpp:62-68` の DB 接続は `configDb` / `stateDb` / `appDb` の 3 本のみ; namespace 引数なし)。VOQ chassis 構成では各 line card ホストが独立に PAC を処理する。

## まとめ

| 観点 | 結果 | 根拠 |
|------|------|------|
| ASIC 種別 (Broadcom / Mellanox / Marvell 等) | 影響なし | pacmgrd / hostapdmgrd は SAI 非経由 |
| multi-asic | 影響なし | DB 接続に namespace 引数なし。host scope のみ |
| VOQ chassis | 各 host で独立動作 | line card ごとに `pacmgrd` が処理 |
| ベンダー固有 PAC モジュール | なし | community master に hook ポイント存在せず |
| デバイス固有設定ファイル | なし | `device/` 配下に PAC 関連ファイルなし |
