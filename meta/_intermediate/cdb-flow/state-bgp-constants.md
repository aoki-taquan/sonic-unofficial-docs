# STATE_DB BGP テーブル群 — Phase E ハードコード定数スキャンノート

対象テーブル: `BGP_STATE_TABLE` / `BGP_PEER_CONFIGURED_TABLE` (STATE_DB), `BGP_NEIGHBOR_TABLE` / `BGP_RIB_IN_TABLE` / `BGP_RIB_OUT_TABLE` (BMP_STATE_DB)
スキャン対象:
- `sonic-swss/fpmsyncd/fpmsyncd.cpp`
- `sonic-swss/fpmsyncd/bgp_eoiu_marker.py`
- `sonic-net/sonic-swss-common/common/schema.h`

---

## 検出した定数

### fpmsyncd.cpp — Warm Restart タイマー定数

| 定数 | 型 | 値 | 用途 | ソース |
|------|----|----|------|--------|
| `DEFAULT_ROUTING_RESTART_INTERVAL` | `uint32_t` | `120` 秒 | Warm Restart 全体タイムアウト。BGP EOIU が検出されなかった場合に reconciliation を開始するフォールバックタイマー | fpmsyncd.cpp L46 |
| `DEFAULT_EOIU_HOLD_INTERVAL` | `uint32_t` | `3` 秒 | IPv4・IPv6 の両 EOIU フラグが `"reached"` になった後に reconciliation を開始するまでの待機時間 | fpmsyncd.cpp L51 |
| `FLUSH_TIMEOUT` | `#define int` | `500` ms | ルートエントリのバッチフラッシュ間隔。小トラフィック検出時に APPL_DB へのフラッシュをトリガーする | fpmsyncd.cpp L25–26 |
| `SMALL_TRAFFIC` | `#define int` | `500` | フラッシュ判定の残キュー閾値。キュー残エントリ数がこれ未満なら idle 時間に基づいてフラッシュする | fpmsyncd.cpp L28 |
| `INFINITE` | `#define int` | `-1` | select タイムアウトを無限に設定するためのセンチネル値 | fpmsyncd.cpp L24 |

### bgp_eoiu_marker.py — EOR 待機タイマー定数

| 定数 | 型 | 値 | 用途 | ソース |
|------|----|----|------|--------|
| `BgpStateCheck.DEF_TIME_OUT` | class attribute | `120` 秒 | `wait_for_bgp_eoiu()` のループタイムアウト。全ネイバーの EOR 受信完了を待つ上限時間。`fpmsyncd` の `DEFAULT_ROUTING_RESTART_INTERVAL` と同値で意図的に一致させてある | bgp_eoiu_marker.py L33 |
| `BgpStateCheck.CHECK_INTERVAL` | class attribute | `1` 秒 | `wait_for_bgp_eoiu()` がネイバー EOR 状態をポーリングする間隔 | bgp_eoiu_marker.py L36 |

### schema.h — DB 番号・テーブル名定数

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `BMP_STATE_DB` | DB ID `20` | BMP テーブル群が格納される Redis DB 番号 | schema.h L33 |
| `STATE_BGP_TABLE_NAME` | `"BGP_STATE_TABLE"` | EOIU マーカーテーブル名 | schema.h L437 |
| `STATE_BGP_PEER_CONFIGURED_TABLE_NAME` | `"BGP_PEER_CONFIGURED_TABLE"` | bgpcfgd がピア設定完了後に書き込むテーブル名 | schema.h L511 |
| `BMP_STATE_BGP_NEIGHBOR_TABLE` | `"BGP_NEIGHBOR_TABLE"` | BMP ネイバー属性テーブル名 | schema.h L557 |
| `BMP_STATE_BGP_RIB_IN_TABLE` | `"BGP_RIB_IN_TABLE"` | BMP RIB-In テーブル名 | schema.h L558 |
| `BMP_STATE_BGP_RIB_OUT_TABLE` | `"BGP_RIB_OUT_TABLE"` | BMP RIB-Out テーブル名 | schema.h L559 |

## 備考

- `DEFAULT_ROUTING_RESTART_INTERVAL` と `BgpStateCheck.DEF_TIME_OUT` は共に `120` 秒で設計上意図的に一致させてある（bgp_eoiu_marker.py L30–31 コメント参照）。どちらが先に満了しても reconciliation/復旧がトリガーされる。
- `DEFAULT_EOIU_HOLD_INTERVAL` は `WarmStart::getWarmStartTimer("eoiu_hold", "bgp")` で設定されたユーザー値があればそちらが優先される（fpmsyncd.cpp L226–230）。ユーザー設定なし（0）の場合のみ `3` 秒のデフォルトが使われる。
- YANG モデル上でこれらの定数を管理するスキーマは存在しない（CONFIG_DB 不在）。
