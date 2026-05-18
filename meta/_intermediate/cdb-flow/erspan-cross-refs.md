# erspan cross-refs 調査証跡

## 対象テーブル

`MIRROR_SESSION` (ERSPAN 種別) — `sonic-swss/orchagent/mirrororch.cpp`

## 調査方法

- `mirrororch.cpp`: MirrorOrch コンストラクタ、createEntry、activateSession を確認
- `mirrororch.h`: MirrorOrch クラス定義を確認
- orchdaemon.cpp: MirrorOrch 初期化時の依存orch 一覧を確認

## 検出された外部テーブル / コンポーネント依存

| 参照先 | 参照種別 | 条件 | evidence |
|--------|---------|------|----------|
| `PORT` (PortsOrch) | `allPortsReady()` 起動ガード | 常時。false の間は全 MIRROR_SESSION 処理がブロック | `mirrororch.cpp:1571` |
| RouteOrch (`m_routeOrch->attach(this, entry.dstIp)`) | 非同期 nexthop 解決 | ERSPAN 常時。dst_ip のルートが解決されるまで activateSession() 未実行 | `mirrororch.cpp:517, 557` |
| NeighOrch (`m_neighOrch->getNeighborEntry()`) | neighbor MAC/port 解決 | ERSPAN 常時。nexthop の ARP/ND が未解決なら activateSession() スキップ | `mirrororch.cpp:656-664` |
| `POLICER` (PolicerOrch `getPolicerOid()`) | policer OID 解決 | `policer` フィールド指定時のみ。未解決なら activateSession() return false → session inactive | `mirrororch.cpp:1052-1060` |
| `PORT`/`LAG` (PortsOrch `getPort()`) | src_port ポートオブジェクト解決 | `src_port` フィールド指定時。ポート未登録なら `task_invalid_entry` | `mirrororch.cpp:316, 892` |
| FdbOrch (observer) | FDB 変化通知受信 | 起動時 attach。FDB エントリ変化で `updateSession()` callback | `mirrororch.cpp:95` |
| `STATE_DB MIRROR_SESSION_TABLE` | 書き込み先（producer only） | activateSession() / deactivateSession() 後に書き込む | `mirrororch.cpp:579-637` |
| SAI Switch (`SAI_SWITCH_ATTR_QOS_MAX_NUMBER_OF_TRAFFIC_CLASSES`) | queue 値上限の SAI 問い合わせ | 初期化時 1 回。失敗時 m_maxNumTC=255 (fallback) | `mirrororch.cpp:100-109` |
| SAI Mirror Resource (`SAI_OBJECT_TYPE_MIRROR_SESSION` count) | HW リソース残量確認 | SET 時毎回。`isHwResourcesAvailable()` が false なら `task_failed` | `mirrororch.cpp:360-370` |

## YANG leafref 状況

- `MIRROR_SESSION.policer` は YANG で `sonic-policer.yang:POLICER_LIST` への leafref なし（実装レベルのみの参照整合性）
- `MIRROR_SESSION.src_port` は PORT / LAG への leafref なし

## 結論

ERSPAN セッションの活性化には RouteOrch + NeighOrch の非同期コールバックチェーンが必要。
policer フィールド指定時は POLICER テーブルが先行して登録されている必要がある。
