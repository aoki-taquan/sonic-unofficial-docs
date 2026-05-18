# errordb — Phase D 失敗挙動 調査証跡

## 調査対象

- `SONiC/doc/error-handling/error_handling_design_spec.md` Rev 0.1 (2019-05-06)
- `SONiC/doc/bgp_error_handling/BGP_Route_Error_Handling_Arlo.md`
- `sonic-swss-common/common/status_code_util.h` (SWSS_RC enum — 実装済み)

## 実装状況

ERROR_DB / ErrorReporter / ErrorListener は 2026-05 時点で sonic-swss master 未マージ。
`status_code_util.h` の SWSS_RC_* enum のみ実装済み。
以下の分析は HLD 設計に基づく。

## 失敗パターン

### HLD Section 3.3.1 の状態遷移テーブル

| Previous Notification | Current Notification | Framework Action |
|-----------------------|----------------------|-----------------|
| Create failure        | Update failure       | Update entry + notify |
| Create failure        | Delete failure       | Remove entry + notify |
| Create failure        | Update success       | Remove entry + notify |
| Create success        | Delete failure       | Add entry + notify |
| Delete failure        | Create success       | Remove entry + notify |

### last-known error policy (HLD 1.1.7)

- 同一オブジェクトが複数回失敗 → DB エントリは1件のみ (最新で上書き)
- ErrorListener へは各失敗ごとに個別通知

### sonic-clear error-database (HLD 3.3.3)

- OrchAgent が通知チャネル経由でクリア要求を受信
- `DEL` で DB エントリを直接削除
- registered application への `publish` は行わない

### warm reboot (HLD Section 6)

- ERROR_DB は非永続設計
- warm reboot 後に全エントリ消滅
- warm reboot 跨ぎの failover は非サポート

## Phase D ブロック挿入箇所

`docs/reference/config-db/errordb.md` の `<!-- /cross-refs -->` 直後、`<!-- cdb-exceptions -->` の前に挿入。
