# errordb cross-refs 調査証跡

## 調査日: 2026-05-18

## 対象ファイル
- `docs/reference/config-db/errordb.md`

## 参照根拠

### ASIC_DB 通知チャネル
- HLD Section 3.3.1: "syncd sends a notification to OrchAgent via ASIC_DB notification channel"
- OrchAgent は ASIC_DB の通知チャネルを listen し、SAI 操作失敗を受信してから ERROR_DB に書き込む
- producer 経路として必須の依存関係

### INTF_TABLE / VLAN_INTF_TABLE / LAG_INTF_TABLE
- HLD Section 3.4.3.3: ERROR_NEIGH_TABLE key の `<intf>` は `INTF_TABLE.name` / `VLAN_INTF_TABLE.name` / `LAG_INTF_TABLE.name` のいずれか
- YANG leafref は存在しないが、OrchAgent が隣接エントリを書き込む際に対応インタフェーステーブルが前提
- インタフェース削除後のエントリ残留は warm reboot まで継続する可能性あり

### BGP_GLOBALS.bgp_error_handling
- BGP HLD Section 3.7.1: fpmsyncd は `BGP_GLOBALS|default.bgp_error_handling` を参照
- false または未設定の場合、ErrorListener 未登録で ERROR_ROUTE_TABLE の購読なし
- community SONiC では bgp_error_handling 機能自体が未マージ (2026-05 時点)

### BGP_NEIGHBOR
- BGP HLD: fpmsyncd が ERROR_ROUTE_TABLE の購読者として BGP ルートインストール失敗を受け取る
- 具体的な BGP_NEIGHBOR フィールド参照ではなく、fpmsyncd が BGP ルートの prefix key を解釈する際に使用

## YANG leafref の有無
- ERROR_DB 全体として YANG 定義なし (community SONiC)
- 全参照は実装上の暗黙依存であり、CVL バリデーションなし
