# PORT.macsec — Phase F 副次 DB 書込スキャンノート

対象ページ: `docs/reference/config-db/macsec-port.md`
対象テーブル: `CONFIG_DB`
  - `PORT` (macsec フィールド)
Producer: `macsecmgrd` (`sonic-swss/cfgmgr/macsecmgr.cpp`) + `MACsecOrch` (`sonic-swss/orchagent/macsecorch.cpp`)
スキャン範囲: `MACsecOrch` コンストラクタ / `createMACsecPort()` / `deleteMACsecPort()` / `createMACsecSC()` / `deleteMACsecSC()` / `createMACsecSA()` / `deleteMACsecSA()` / `installCounter()` / `uninstallCounter()` の全行精読

---

## 検出した副次 DB 書込み

`PORT.macsec` に値が設定されると、`macsecmgrd` が `wpa_supplicant` を起動し MKA ネゴシエーションが始まる。MKA 完了後 `wpa_supplicant` が APPL_DB (`APP_MACSEC_PORT_TABLE` 等) に書き込み、`MACsecOrch` がそれを処理して以下の副次 DB 書込みを行う。

### 1. STATE_DB — STATE_MACSEC_PORT_TABLE

`MACsecOrch::createMACsecPort()` (`macsecorch.cpp:1532-1535`) は SAI MACsec Port 作成成功後に STATE_DB の `STATE_MACSEC_PORT_TABLE_NAME` へ `max_sa_per_sc` と `state=ok` を書き込む。削除時 (`deleteMACsecPort()`, `macsecorch.cpp:1792`) は同テーブルエントリを削除する。

### 2. STATE_DB — STATE_MACSEC_EGRESS_SC_TABLE / STATE_MACSEC_INGRESS_SC_TABLE

`createMACsecSC()` (`macsecorch.cpp:2039-2043`) は SC (Security Channel) 作成成功後に STATE_DB の `STATE_MACSEC_EGRESS_SC_TABLE_NAME` または `STATE_MACSEC_INGRESS_SC_TABLE_NAME` へ SC 情報を書き込む。削除時 (`macsecorch.cpp:2161-2165`) は対応エントリを削除。

### 3. STATE_DB — STATE_MACSEC_EGRESS_SA_TABLE / STATE_MACSEC_INGRESS_SA_TABLE

`createMACsecSA()` (`macsecorch.cpp:2371-2376`) は SA (Security Association) 作成成功後に STATE_DB の `STATE_MACSEC_EGRESS_SA_TABLE_NAME` または `STATE_MACSEC_INGRESS_SA_TABLE_NAME` へ SA 情報を書き込む。削除時 (`macsecorch.cpp:2433-2437`) は対応エントリを削除。

### 4. COUNTERS_DB — COUNTERS_MACSEC_NAME_MAP (SA/Flow オブジェクト名マップ)

`MACsecOrch::installCounter()` (`macsecorch.cpp:2589`) は SAI MACsec SA / Flow オブジェクト作成後に `COUNTERS_DB` の `COUNTERS_MACSEC_NAME_MAP` テーブルへ `<obj_name>` → `<sai_object_id>` のマッピングを `hset` で書き込む。アンインストール時 (`macsecorch.cpp:2618`) は `hdel` で削除。Gearbox 存在時は `GB_COUNTERS_DB` の同テーブルにも同様に書き込む。

### 5. FLEX_COUNTER_DB — SA attr / SA stat / Flow stat グループ

`installCounter()` は `FlexCounterManager` 経由で FLEX_COUNTER_DB に次の 3 グループのカウンタ設定を書き込む:

| FlexCounterManager | グループ名 | ポーリング間隔 |
|---|---|---|
| `m_macsec_sa_attr_manager` | `COUNTERS_MACSEC_SA_ATTR_GROUP` | 1000 ms (XPN カウンタ) |
| `m_macsec_sa_stat_manager` | `COUNTERS_MACSEC_SA_GROUP` | 10000 ms |
| `m_macsec_flow_stat_manager` | `COUNTERS_MACSEC_FLOW_GROUP` | 10000 ms |

`setCounterIdList()` (`macsecorch.cpp:2584-2593`) で SA/Flow の SAI OID と統計属性リストを FLEX_COUNTER_DB に登録。アンインストール時 (`clearCounterIdList()`, `macsecorch.cpp:2613-2622`) で削除。Gearbox 存在時は `m_gb_macsec_*` 系 FlexCounterManager でも同様に登録。

---

## 副次 DB 書込みサマリ

| 副次 DB | テーブル / キー | 書込タイミング | 根拠 |
|---|---|---|---|
| STATE_DB | `STATE_MACSEC_PORT_TABLE\|<port>` | SAI MACsec Port 作成成功時 (set) / 削除時 (del) | `macsecorch.cpp:1535, 1792` |
| STATE_DB | `STATE_MACSEC_EGRESS_SC_TABLE\|<port>\|<sci>` | Egress SC 作成成功時 (set) / 削除時 (del) | `macsecorch.cpp:2039, 2161` |
| STATE_DB | `STATE_MACSEC_INGRESS_SC_TABLE\|<port>\|<sci>` | Ingress SC 作成成功時 (set) / 削除時 (del) | `macsecorch.cpp:2043, 2165` |
| STATE_DB | `STATE_MACSEC_EGRESS_SA_TABLE\|<port>\|<sci>\|<an>` | Egress SA 作成成功時 (set) / 削除時 (del) | `macsecorch.cpp:2371, 2433` |
| STATE_DB | `STATE_MACSEC_INGRESS_SA_TABLE\|<port>\|<sci>\|<an>` | Ingress SA 作成成功時 (set) / 削除時 (del) | `macsecorch.cpp:2376, 2437` |
| COUNTERS_DB | `COUNTERS_MACSEC_NAME_MAP` | SA/Flow SAI OID 登録時 (hset) / 削除時 (hdel) | `macsecorch.cpp:2589, 2618` |
| GB_COUNTERS_DB | `COUNTERS_MACSEC_NAME_MAP` | Gearbox 存在時のみ、同上 | `macsecorch.cpp:2560-2568` |
| FLEX_COUNTER_DB | `COUNTERS_MACSEC_SA_ATTR_GROUP` / `COUNTERS_MACSEC_SA_GROUP` / `COUNTERS_MACSEC_FLOW_GROUP` | SA/Flow 作成時 (setCounterIdList) / 削除時 (clearCounterIdList) | `macsecorch.cpp:2584-2622` |

---

## ページ反映方針

- `<!-- side-effects -->` ブロックを `<!-- constants -->` ブロックの直後 (`<!-- /constants -->` の後) に挿入する。
- 副次 DB サマリ表 + 主要書込み経路の散文を含める。
- 既存の全ブロックは触らない。
