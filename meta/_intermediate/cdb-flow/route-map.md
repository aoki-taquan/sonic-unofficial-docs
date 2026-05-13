# ROUTE_MAP 例外条件抽出 (cdb-batch-7)

## ソース
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_rm.py`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_allow_list.py`

## 抽出した例外条件

1. **BGPRouteMapMgr は固定 2 キーのみ処理**: `ROUTE_MAP` テーブルのうち `FROM_SDN_SLB_ROUTES` / `FROM_SDN_APPLIANCE_ROUTES` の 2 キーのみを処理対象とする。それ以外のキーは `log_err("BGPRouteMapMgr:: Invalid key for route-map %s")` で拒否し、FRR への設定生成をスキップ。
   - 証拠: `ROUTE_MAPS = ["FROM_SDN_SLB_ROUTES", "FROM_SDN_APPLIANCE_ROUTES"]` (l.5)、`__set_handler_validate` / `__del_handler_validate` (l.44 / l.63)

2. **community_id 形式不正**: `community_id` フィールドが `<0-65535>:<0-65535>` 形式でない場合 `log_err` してスキップ。ValueError の場合も同様。
   - 証拠: `log_err("BGPRouteMapMgr:: data %s doesn't include valid community id")` (l.54)

3. **BGP ASN 未設定 (constants)**: `deployment_id_asn_map` が constants に存在しない、または `deployment_id=2` のエントリがない場合は `log_err` して route-map の更新をスキップ（既存 route-map は残る）。
   - 証拠: `__read_asn` の `log_err` 2 箇所 (l.74-80)

4. **AllowList との共存**: `managers_allow_list.py` が同一 route-map 名に対してシーケンス番号管理を行う。シーケンス番号が枯渇した場合 (`RuntimeError("No free sequence numbers for '%s'")`) は route-map 追加が失敗する。

5. **data が None / 空**: `data is None` チェックで `log_err("BGPRouteMapMgr:: data is None")` を出しスキップ。
