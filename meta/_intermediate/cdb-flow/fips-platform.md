# FIPS — プラットフォーム差調査

Task F Phase H: `FIPS` テーブル適用時のプラットフォーム/構成差を `hostcfgd` (`sonic-host-services`) と `sonic-buildimage` の FIPS 関連アセットから精読した結果。

## 結論

**プラットフォーム差なし**。FIPS は host 単位で適用され、ASIC 種別・multi-asic / VOQ chassis 構成・ベンダーに依らない。

## 根拠

### 1. hostcfgd は host CONFIG_DB のみを購読する

`scripts/hostcfgd` の `FipsCfg.__init__` (L1753–1769) は:

- `ConfigDBConnector()` 引数なし相当の `state_db_conn` を受け取るだけで、`asicN` namespace には接続しない
- `register_callbacks` (hostcfgd:2456–2509) が `config_db.subscribe("FIPS", ...)` を呼ぶ際も host namespace の CONFIG_DB のみを対象とする
- `is_multi_npu()` 値は `FipsCfg` クラスに渡されず、FIPS 処理経路に現れない

### 2. FipsCfg が操作するリソースはすべて host filesystem

`FipsCfg.update()` のコールチェーンが書き換えるのはすべて host root filesystem のグローバルリソース:

- `/etc/fips/fips_enable` — OpenSSL FIPS provider フラグ（`update_noneenforce_config` hostcfgd:1806–1809）
- `/proc/cmdline` 読み取り — host kernel コマンドライン（hostcfgd:1771–1773）
- bootloader grub エントリ — `sonic_installer.bootloader.get_bootloader()` 経由（hostcfgd:1838–1846）
- `systemctl restart ssh telemetry.service restapi` — host systemd（hostcfgd:1832–1835）

これらはコンテナごと・ASIC ごとではなく **host 1 か所**。ASIC データパスには一切関与しない。

### 3. YANG `sonic-fips` に platform 条件分岐なし

`src/sonic-yang-models/yang-models/sonic-fips.yang` を `platform|asic|chassis|namespace|vendor` で grep しても 0 ヒット。`container FIPS_LIST` の `leaf enable` / `leaf enforce` に条件制約はなく、ASIC 種別によるフィールド制限も存在しない。

### 4. buildimage に FIPS プラットフォーム別上書きなし

`sonic-buildimage/files/image_config/` および `files/build_templates/` に `fips` 関連のプラットフォーム別 override ディレクトリは存在しない。`/etc/sonic/fips.json` はランタイムに配置するオプション設定ファイルであり、ビルド時のプラットフォーム差異を持たない。

### 5. multi-asic / VOQ chassis 構成での扱い

`is_multi_npu()` が true でも FIPS テーブルは host CONFIG_DB のみに置かれ、`asicN` namespace の CONFIG_DB には `FIPS` テーブルが存在しない。VOQ chassis の supervisor / line card 双方で各 host が独立に FIPS 設定を保持し、`hostcfgd` が各 host で `/etc/fips/fips_enable` を書き換える。chassis 全体での一括強制機構はない。

### 6. SAI 非経由

FIPS は OpenSSL / kernel bootloader の操作のみであり、SAI API を一切呼ばない。Broadcom / Mellanox / Marvell / Innovium 等の ASIC SDK との依存関係がないため、ASIC ベンダーによる動作差異は発生しない。

## まとめ

FIPS 経路は SAI を経由せず、ASIC SDK にも依存しない host-only な「OpenSSL FIPS provider 有効化 + bootloader grub 書換え + systemd サービス再起動」処理。よって `T0 / T1 / VOQ chassis / multi-asic` 等の物理構成や ASIC ベンダーに関わらず動作・適用範囲は同一。
