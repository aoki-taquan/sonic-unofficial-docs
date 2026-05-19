# errordb — Phase F 副次 DB 書込 調査証跡

調査日: 2026-05-19  
担当: batch824 (Phase F)

## 調査ソース

1. `SONiC/doc/error-handling/error_handling_design_spec.md` Rev 0.1
   - Section 3.1: ERROR_DB の設計方針（pub/sub による通知）
   - Section 3.3.1: OrchAgent のイベント処理（HSET → publish の順序）
   - Section 3.3.2: ErrorListener 登録インタフェース
   - Section 3.3.3: Clearing ERROR_DB（publish なし）
   - Section 5: Serviceability and Debug（swssloglevel）

2. `SONiC/doc/bgp_error_handling/BGP_Route_Error_Handling_Arlo.md` Rev 0.1
   - Section 3.1: fpmsyncd による ERROR_ROUTE_TABLE 購読
   - Section 3.3.1: Zebra の route withdraw 処理
   - Section 3.3.2: BGP の "pending FIB install" フラグ
   - Section 3.4.1: fpmsyncd の Zebra FPM ソケット経由メッセージ
   - Section 3.7.1: BGP_ERROR_CFG_TABLE による enable/disable

3. `sonic-swss-common/common/status_code_util.h`
   - SAI status → SWSS_RC_* 変換（プラットフォーム非依存）

## 調査結論

### 副次書込の有無

| DB | 書込 | 根拠 |
|----|------|------|
| ERROR_DB | 書込あり（HSET / DEL + publish）| OrchAgent が唯一の producer — HLD Section 3.1 |
| STATE_DB | なし | HLD に記述なし、実装もマージ未 |
| APPL_DB | なし | HLD Section 3.4.2: "None" |
| COUNTERS_DB | なし | HLD Section 3.2.5（BGP HLD）に言及なし |
| CONFIG_DB | なし | HLD Section 3.4.1: "None" |
| kernel FIB | あり（間接） | fpmsyncd → Zebra → netlink — BGP HLD Section 3.3.1 |

### pub/sub チェーン

ERROR_DB への書込が起点となる連鎖:

```
OrchAgent HSET ERROR_ROUTE_TABLE
  └→ publish ERROR_DB
       └→ fpmsyncd ErrorListener コールバック（bgp_error_handling=true 時のみ）
            └→ FPM ソケット → Zebra
                 └→ kernel route DEL（netlink）
                      └→ BGP "FIB-install pending" フラグ
                           └→ RIB-OUT 除外（ピア広告停止）
```

### ログ

HLD Section 5 に swssloglevel 対応が明記:
- 購読登録 / 解除
- Syncd からの通知受信
- ERROR_DB エントリ追加 / 削除
- アプリへの通知発行
- clear コマンド受信

### プラットフォーム依存

なし。status_code_util.h の変換テーブルは HW 非依存。

## 実装状況注記

ERROR_DB フレームワーク（ErrorReporter / ErrorListener クラス）は 2026-05 時点で master 未マージ。
ただし SWSS_RC_* enum (`status_code_util.h`) は実装済み。
上記の副次処理は HLD 設計に基づく記述であり、現行 master では動作しない。
