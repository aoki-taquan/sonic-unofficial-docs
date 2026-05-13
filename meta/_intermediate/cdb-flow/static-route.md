# STATIC_ROUTE 例外条件抽出 (cdb-batch-7)

## ソース
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_static_rt.py`

## 抽出した例外条件

1. **IP ネクストホップ解析例外**: `IpNextHopSet` 構築時に例外が発生した場合 `log_crit("Got an exception %s: Traceback: %s")` を出し `return False` でスキップ。その静的経路は FRR に設定されない。
   - 証拠: `except Exception as exc: log_crit(...); return False` (l.61-63)

2. **key フォーマット不正 (APPL_DB)**: APPL_DB の key が VRF を含む場合 `<vrf>:<prefix>` 形式を期待する。コロン区切りで 2 要素に分割できない場合は `log_debug("invalid input in APPL_DB {}".format(key))` → `raise ValueError` で処理中断。
   - 証拠: l.174-179

3. **BFD 有効時の APPL_DB 削除スキップ**: `bfd=true` が設定された静的経路で APPL_DB から削除イベントが来ても、CONFIG_DB に経路が残っている場合は FRR からの削除をスキップする (`skip_appl_del` が True を返す)。これは staticroutebfd との race condition 防止。
   - 証拠: `skip_appl_del` 関数 (l.82-120)

4. **BGP ASN 未設定時の redistribute 保留**: 静的経路の最初のエントリ設定時に `bgp_asn` が DEVICE_METADATA に存在しない場合、redistribute static コマンドは発行されず `vrf_pending_redistribution` に VRF 名が追加される。後で bgp_asn が設定されたときに retroactively に redistribute が有効化される。
   - 証拠: l.63-71

5. **BFD セッション全断時の自動削除**: BFD が有効な nexthop のすべての BFD セッションが down になると staticroutebfd が APPL_DB から経路エントリを削除する。この場合は `skip_appl_del` が False を返し FRR から経路が削除される。
   - 証拠: コメント `"bfd field is true but all the sessions are down, need to allow this deletion"` (l.86-100)

6. **VRF 単位の redistribution**: VRF ごとに `redistribute static route-map STATIC_ROUTE_FILTER` が個別に設定される。VRF を削除する前に全静的経路を削除しないと VRF-in-FRR で孤立した redistribute 設定が残ることがある。
