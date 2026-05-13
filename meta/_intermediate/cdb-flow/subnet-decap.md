# SUBNET_DECAP 例外条件抽出 (cdb-batch-7)

## ソース
- `sonic-swss/orchagent/tunneldecaporch.cpp`

## 抽出した例外条件

1. **src_ip と src_ip_v6 の両方が未設定**: `src_ip` と `src_ip_v6` のどちらも設定されていない場合 `SWSS_LOG_ERROR("Both src_ip and src_ip_v6 of subnet decap are not set.")` → valid=false でエントリ破棄。
   - 証拠: tunneldecaporch.cpp l.638-640

2. **src_ip に IPv4 以外を指定**: `src_ip` フィールドに IPv6 アドレスを指定した場合 `SWSS_LOG_ERROR("Invalid source IP prefix %s.")` (isV4() チェック失敗) → 処理中断。
   - 証拠: l.595-601

3. **src_ip_v6 に IPv4 アドレスを指定**: `src_ip_v6` に IPv4 を指定すると `isV4()` が true になり `SWSS_LOG_ERROR("Invalid source IPv6 prefix %s.")` → 処理中断。
   - 証拠: l.613-619

4. **IP プレフィクス形式不正**: `swss::IpPrefix()` のコンストラクタが `std::invalid_argument` を投げた場合 `SWSS_LOG_ERROR("Invalid source IP prefix %s.")` → 処理中断。
   - 証拠: l.591-594 / l.609-612

5. **未知のフィールド**: `src_ip` / `src_ip_v6` / `status` 以外のフィールドは `SWSS_LOG_ERROR("unknown subnet decap table attribute '%s'.")` → valid=false でエントリ破棄。
   - 証拠: l.624-628

6. **src_ip 変更時の既存デカップル用トンネル更新**: `src_ip` が変更された場合、`enable=true` のときは既存の IPv4 デカップルトンネルターム全体の src_ip が `setIpAttribute()` + `updateUnhandledDecapTunnelTerms()` で更新される。enable=false 時は更新せず変数のみ変更。

7. **MP2MP 以外のトンネル term は SUBNET_DECAP トンネルに紐付け不可**: `TUNNEL_DECAP_TERM` エントリで `tunnel_type` が `MP2MP` でない term を subnet decap トンネルに紐付けようとすると `SWSS_LOG_ERROR("only MP2MP tunnel decap term is allowed for subnet decap tunnel.")` → 拒否。
   - 証拠: l.446-448

8. **SUBNET_DECAP は key 1 エントリのみ有効**: コードは `subnetDecapConfig` をシングルトン構造体として保持する。テーブルに複数エントリを書いても最後の SET_COMMAND で上書きされる。
