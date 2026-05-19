# FABRIC_MONITOR テーブル — Phase H: プラットフォーム差 中間ファイル

生成日: 2026-05-19 (q67-f-batch903)

対象ページ: `docs/reference/config-db/fabric-monitor.md`
対象テーブル: `CONFIG_DB.FABRIC_MONITOR`
Producer: `fabricmgrd` (`sonic-swss/cfgmgr/fabricmgr.cpp`, `cfgmgr/fabricmgrd.cpp`)
Consumer: `FabricPortsOrch` (`sonic-swss/orchagent/fabricportsorch.cpp`)
Orchestration: `sonic-swss/orchagent/orchdaemon.cpp`, `main.cpp`

スキャン範囲:
- `orchdaemon.cpp` L601-611 (OrchDaemon::init — voq 向け FabricPortsOrch 登録)
- `orchdaemon.cpp` L1292-1303 (FabricOrchDaemon::init — fabric 向け FabricPortsOrch 登録)
- `main.cpp` L997-1010 (gMySwitchType による orchdaemon 種別分岐)
- `fabricportsorch.cpp` L104-110 (コンストラクタ内 gMySwitchType 条件分岐)
- `fabricportsorch.cpp` L1577-1580 (doTask timer 内 gMySwitchType 条件)
- `fabricportsorch.cpp` L1201-1219 (updateFabricCapacity — voq 専用ログ)

---

## gMySwitchType 別の FabricPortsOrch 起動差異

### voq スイッチタイプ (VOQ Chassis の line card / supervisor)

- `main.cpp:997-1005`: `gMySwitchType != "fabric"` かつ `gMySwitchType == "voq"` のとき `OrchDaemon` を生成し、
  `orchDaemon->setFabricEnabled(true)` を呼ぶ。
- `orchDaemon->setFabricPortStatEnabled(true)`, `setFabricQueueStatEnabled(false)` も設定。
- `OrchDaemon::init` L601-610: `if (m_fabricEnabled)` 条件下で `FabricPortsOrch` を `m_fabricPortStatEnabled=true`,
  `m_fabricQueueStatEnabled=false` で生成。
- Switch drop counter タイマー: `SWITCH_DEBUG_COUNTER_POLLING_INTERVAL_MS = 500` ms (fabricportsorch.cpp:33,106)
- `updateFabricCapacity()` 内の容量警告ログ (`SWSS_LOG_NOTICE("Total links...")`) は `gMySwitchType == "voq"` のときのみ出力 (fabricportsorch.cpp:1201,1214)

### fabric スイッチタイプ (Fabric Card — forwarding plane なし)

- `main.cpp:1007-1009`: `gMySwitchType == "fabric"` のとき `FabricOrchDaemon` を生成。
- `FabricOrchDaemon::init` L1297-1303: `FabricPortsOrch` をデフォルト引数 (stat フラグなし) で生成 —
  `m_fabricPortStatEnabled=false`, `m_fabricQueueStatEnabled=false`。
- Switch drop counter タイマー: `FABRIC_SWITCH_DEBUG_COUNTER_POLLING_INTERVAL_MS = 60000` ms (fabricportsorch.cpp:34,106)
- 容量警告ログ: `gMySwitchType == "voq"` 条件を満たさないため出力されない。

### switch / chassis-packet / dpu スイッチタイプ (通常 ToR 等)

- `m_fabricEnabled` は `false` のまま。`OrchDaemon::init` の `if (m_fabricEnabled)` ブロックに入らないため
  `FabricPortsOrch` は生成されない。
- `fabricmgrd` は起動するが、orchagent 側に consumer が存在しないため APPL_DB 書込みは参照されない。
- FABRIC_MONITOR テーブルを CONFIG_DB に設定しても、監視処理は実行されない。

---

## FlexCounter / 統計収集差異

| 項目 | voq | fabric |
|------|-----|--------|
| `m_fabricPortStatEnabled` | `true` | `false` |
| `m_fabricQueueStatEnabled` | `false` | `false` |
| Switch drop counter タイマー | 500 ms | 60,000 ms |
| 容量警告ログ (`SWSS_LOG_NOTICE`) | 出力 | 出力なし |

fabricmgrd 側 (`fabricmgrd.cpp`) に switchtype 分岐なし。`fabricmgrd` は switchtype によらず同一ロジックで動作する。

---

## fabricmgrd のプラットフォーム非依存性

`fabricmgrd.cpp` は `gMySwitchType` を参照しない。`CONFIG_DB.FABRIC_MONITOR` の変化を常に購読し、無条件に APPL_DB へ転写する。プラットフォーム差はすべて orchagent 側（`FabricPortsOrch` の生成有無と `gMySwitchType` 分岐）で吸収される。

---

## ページ反映方針

- `<!-- platform -->` ブロックを `<!-- /constants -->` の直後に挿入する。
- voq / fabric / それ以外の 3 区分でテーブル化する。
- fabricmgrd がプラットフォーム非依存である点を明示する。
