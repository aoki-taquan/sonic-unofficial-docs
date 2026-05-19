# DEFAULT_LOSSLESS_BUFFER_PARAMETER — Phase E: ハードコード定数調査

## 対象ファイル

- `sonic-swss/cfgmgr/buffermgrdyn.h` (マクロ定数定義)
- `sonic-swss/cfgmgr/buffermgrdyn.cpp` (コンストラクタ・タイマー・プロファイル命名ロジック)

---

## 1. バッファプール名 / MTU マクロ (buffermgrdyn.h L14-17)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `INGRESS_LOSSLESS_PG_POOL_NAME` | `"ingress_lossless_pool"` | lossless PG に対応する ingress バッファプールの固定キー名。`handleDefaultLossLessBufferParam()` 内で `m_bufferPoolLookup.find()` の引数として使用 | buffermgrdyn.h L14 |
| `DEFAULT_MTU_STR` | `"9100"` | MTU 未設定時のデフォルト MTU 文字列。`getDynamicProfileName()` で MTU がこの値と一致する場合、プロファイル名に `_mtu<value>` サフィックスを付加しない（プロファイル名を短縮する） | buffermgrdyn.h L15 |
| `BUFFERMGR_TIMER_PERIOD` | `10` (秒) | `SelectableTimer` の周期。ポート初期化完了ポーリング (`PORT_INIT_DONE_POLL_TIMER`) の間隔として使用 | buffermgrdyn.h L17 |

---

## 2. 追加ゼロプロファイル適用遅延 (buffermgrdyn.cpp L156-171)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `m_waitApplyAdditionalZeroProfiles` (cold/fast reboot 初期値) | `3` (カウント) | cold/fast reboot 時に追加ゼロプロファイル適用を遅らせるためのカウントダウン初期値。タイマー周期 (`BUFFERMGR_TIMER_PERIOD = 10` 秒) × `3` = **30 秒** の遅延に相当 | buffermgrdyn.cpp L169 |
| `m_waitApplyAdditionalZeroProfiles` (warm reboot 初期値) | `0` (カウント) | warm reboot 時はゼロプロファイルを即時適用するためカウントを 0 に設定 | buffermgrdyn.cpp L164 |

> `3 * BUFFERMGR_TIMER_PERIOD(10) = 30 秒` の遅延は fast reboot の収束時間を短縮するために意図的に設けられている (buffermgrdyn.cpp L3737-3739 コメント)。

---

## 3. 動的プロファイル命名規則のハードコード (buffermgrdyn.cpp L481-501)

`getDynamicProfileName()` で生成されるプロファイル名のプレフィックス・サフィックスは文字列リテラルとしてハードコードされている。

| 要素 | リテラル | 挙動 | ソース |
|------|----------|------|--------|
| プロファイル名プレフィックス | `"pg_lossless_"` | すべての動的 lossless プロファイル名の先頭固定文字列 | buffermgrdyn.cpp L487, L491 |
| 非デフォルト threshold サフィックス | `"_th"` | threshold が `m_defaultThreshold` と一致しない場合のみ `_th<value>` を付加 | buffermgrdyn.cpp L496 |
| 非デフォルト MTU サフィックス | `"_mtu"` | MTU が `DEFAULT_MTU_STR("9100")` と一致しない場合のみ `_mtu<value>` を付加 | buffermgrdyn.cpp L491 |

プロファイル名の最終形：
- 標準: `pg_lossless_<speed>_<cable>`
- MTU 非標準: `pg_lossless_<speed>_<cable>_mtu<mtu>`
- threshold 非デフォルト: `pg_lossless_<speed>_<cable>_th<threshold>`
- gearbox あり: `pg_lossless_<speed>_<cable>_<gearbox_model>`

---

## 4. ゼロプール xoff ハードコード (buffermgrdyn.cpp L773, L1701)

| 箇所 | リテラル | 用途 | ソース |
|------|----------|------|--------|
| SHP 無効化時の xoff リセット | `"0"` | SHP が無効化された場合 (`refreshSharedHeadroomPool()` 経由)、ingress_lossless_pool の `xoff` を `"0"` に設定して APPL_DB を更新 | buffermgrdyn.cpp L1701 |
| ゼロプール xoff 初期値 | `"0"` | ゼロバッファプール生成時の xoff 値 | buffermgrdyn.cpp L773 |

---

## 5. 起動時 `m_defaultThreshold` 初期化 (buffermgrdyn.cpp L148-154)

コンストラクタは CONFIG_DB から `DEFAULT_LOSSLESS_BUFFER_PARAMETER` の先頭キーの `default_dynamic_th` を読み込んで `m_defaultThreshold` を設定する。CONFIG_DB にエントリがない場合、`m_defaultThreshold` は `""` (空文字列) のまま残る。空文字列のままでは lossless PG のバッファ計算が全保留される (`refreshPgsForPort()` の `m_defaultThreshold.empty()` チェック L1460)。

---

## スキャン証跡

- `buffermgrdyn.h` L14-17 全行読了 (マクロ定義)
- `buffermgrdyn.cpp` L126-131 (タイマー初期化)
- `buffermgrdyn.cpp` L148-172 (コンストラクタ末尾)
- `buffermgrdyn.cpp` L481-501 (`getDynamicProfileName()`)
- `buffermgrdyn.cpp` L765-780, L1695-1705 (xoff ハードコード)
- `buffermgrdyn.cpp` L3735-3748 (追加ゼロプロファイル遅延ロジック)
