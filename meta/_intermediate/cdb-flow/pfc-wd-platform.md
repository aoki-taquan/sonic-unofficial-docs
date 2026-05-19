# PFC_WD — プラットフォーム差調査

Task F Phase H: `PFC_WD` テーブル処理時のプラットフォーム差を `pfcwdorch.cpp` と `orchdaemon.cpp` (sonic-swss) から精読した結果。

## 結論

**プラットフォーム差あり（重大）**。PFC Watchdog の `action` ハンドラクラス・SAI カウンタ種別・Lua 検出スクリプトはすべて ASIC ベンダーごとに異なる。プラットフォーム識別できない場合は `PfcWdSwOrch` が登録されず PFC-WD 機能が無効になる。

## 根拠

### 1. orchdaemon.cpp — ASIC 別 Handler 登録分岐

`orchdaemon.cpp:635-843` に `getenv("platform")` を用いた大規模 if-else チェーンが存在し、PFC-WD Handler クラスと SAI カウンタ種別を切り替える。

| platform 文字列 | 登録 Handler | SAI ポートカウンタ種別 | ソース |
|---|---|---|---|
| `mellanox` / `vs` | `PfcWdSwOrch<PfcWdZeroBufferHandler, PfcWdLossyHandler>` | `SAI_PORT_STAT_PFC_*_PAUSE_DURATION_US` (μs 単位) | `orchdaemon.cpp:635-672` |
| `marvell-teralynx` / `marvell-prestera` / `clounix` / `nephos` | `PfcWdSwOrch<PfcWdZeroBufferHandler, PfcWdLossyHandler>` | `SAI_PORT_STAT_PFC_*_PAUSE_DURATION` (ms 単位) | `orchdaemon.cpp:709-720` |
| `barefoot` | `PfcWdSwOrch<PfcWdAclHandler, PfcWdLossyHandler>` | `SAI_PORT_STAT_PFC_*_PAUSE_DURATION` (ms 単位) | `orchdaemon.cpp:722-731` |
| `broadcom` (DLR init 有効) | `PfcWdSwOrch<PfcWdDlrHandler, PfcWdDlrHandler>` | `SAI_PORT_STAT_PFC_*_RX_PKTS` + `SAI_PORT_STAT_PFC_*_ON2OFF_RX_PKTS` + `SAI_QUEUE_ATTR_PAUSE_STATUS` | `orchdaemon.cpp:786-792` |
| `broadcom` (DLR init 無効) | `PfcWdSwOrch<PfcWdAclHandler, PfcWdLossyHandler>` | 同上 | `orchdaemon.cpp:796-803` |
| `cisco-8000` | `PfcWdSwOrch<PfcWdSaiDlrInitHandler, PfcWdActionHandler>` | `SAI_PORT_STAT_PFC_*_RX_PKTS` + `SAI_PORT_STAT_PFC_*_TX_PKTS` + `SAI_QUEUE_ATTR_PAUSE_STATUS` | `orchdaemon.cpp:836` |
| それ以外（未知 platform） | **登録なし（PFC-WD 無効）** | — | `orchdaemon.cpp:635-843` の else 分岐なし |

### 2. platform 別 Lua 検出スクリプト

`pfcwdorch.cpp:693` で `"pfc_detect_" + m_platform + ".lua"` というファイル名を動的に構成してロードする。存在する検出スクリプト:

- `pfc_detect_mellanox.lua`
- `pfc_detect_broadcom.lua`
- `pfc_detect_barefoot.lua`
- `pfc_detect_cisco-8000.lua`
- `pfc_detect_clounix.lua`
- `pfc_detect_marvell-prestera.lua`
- `pfc_detect_marvell-teralynx.lua`
- `pfc_detect_nephos.lua`
- `pfc_detect_vs.lua`

復旧スクリプトは Cisco-8000 のみ `pfc_restore_cisco-8000.lua` を使用し（`pfcwdorch.cpp:698`）、他の全プラットフォームは共通の `pfc_restore.lua` を使用する（`pfcwdorch.cpp:700`）。

### 3. Cisco-8000 固有制約: `action = forward` 非サポート

`pfcwdorch.cpp:233-236`: `m_platform == CISCO_8000_PLATFORM_SUBSTRING` かつ `action == PFC_WD_ACTION_FORWARD` の場合、`task_invalid_entry` を返し設定を拒否する。エラーログ: `"Unsupported action %s for platform %s"`。他のプラットフォームでは `forward` は許容される。

### 4. Broadcom 固有制約: 全ポート同一 action 強制

`pfcwdorch.cpp:237-263`: Broadcom プラットフォームで DLR 有効時 (`checkPfcDlrInitEnable()`)、`SAI_SWITCH_ATTR_PFC_DLR_PACKET_ACTION` をスイッチ全体に適用する。既存エントリと異なる `action` を持つ新エントリは `task_invalid_entry` で拒否される（DLR の制約: 全ポート同一 action）。

### 5. Broadcom DLR 初期化制御

`orchdaemon.cpp:766-782`: Broadcom プラットフォームの場合、`gSwitchOrch->checkPfcDlrInitEnable()` の返値で Handler クラスが切り替わる。環境変数 `PFC_DLR_INIT_ENABLE=1/0` で強制上書き可能（テスト用途）。

### 6. multi-asic / VoQ / DASH — PFC_WD への影響なし

`pfcwdorch.cpp` に `gMySwitchType`・`gFabricPortsOrch`・`IS_MULTI_NPU`・`namespace` 参照はゼロヒット。PFC-WD の物理ポート per-port 設定ロジックはシングル ASIC・multi-asic・VoQ chassis いずれの構成でも同一コードパスを通る。ただし multi-asic 構成では各 ASIC namespace の orchagent が独立して起動し、それぞれが自 namespace の `PFC_WD` テーブルを購読する。

## まとめ

PFC_WD の platform 差は community SONiC の中でも特に重大なカテゴリに属する。ASIC ベンダーが識別できない場合は機能自体が無効化され、ベンダーが識別できても SAI カウンタ種別・Lua 検出アルゴリズム・復旧 Handler クラスがすべて異なる。Cisco-8000 の `forward` 禁止・Broadcom の全ポート action 統一制約など、**CONFIG_DB 書き込み時のバリデーション挙動もプラットフォーム依存**である点に注意が必要。
