# BGP_PEER_RANGE — Phase F 副次 DB 書込調査

**調査日**: 2026-05-16  
**対象ソース**:
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py`
- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`

---

## 検出された副次 DB 書込

### STATE_DB — BGP_PEER_CONFIGURED_TABLE

`managers_bgp.py` の `update_state_db()` メソッド (L271–304) が `STATE_DB` へ副次書込を行う。

**テーブル名**: `swsscommon.STATE_BGP_PEER_CONFIGURED_TABLE_NAME`  
（テストコードより: `"BGP_PEER_CONFIGURED_TABLE"`）

**書込タイミング**:

| 呼び出し元 | 行 | op | 条件 |
|---|---|---|---|
| `add_peer()` | L239 | SET | FRR へのコマンド適用成功時 (`apply_op()` が None 以外の cmd を生成) |
| `apply_admin_status()` | L353 | SET | FRR への admin_status テンプレート適用成功時 |
| `change_ip_range()` 内 apply 成功後 | L443 | SET | ip_range 更新コマンド適用成功時 |
| `del_handler()` | L487 | DEL | FRR でのピア削除成功時 (`apply_op()` が True を返す) |

**key 形式**:
- `default` VRF: `<peer_range_name>` (e.g., `PEER_GROUP_DYN1`)
- 非 default VRF: `<vrf_name>|<peer_range_name>` (e.g., `Vrf1|PEER_GROUP_DYN1`)

**書込内容** (SET 時): CONFIG_DB の `BGP_PEER_RANGE` フィールド (`ip_range`, `peer_asn`, `src_address`, `name` など) をそのまま `fvs` として格納。

**書込内容** (DEL 時): キーのみ削除（空 data `{}`）。

---

## COUNTERS_DB 書込

**なし**。`managers_bgp.py` および `frrcfgd.py` 双方において `COUNTERS_DB` への参照・書込は存在しない。

---

## APPL_DB 書込

**なし**。`bgpcfgd` は FRR へ `vtysh` 経由で直接コマンドを送出するアーキテクチャであり、`APPL_DB` は介在しない。`frrcfgd.py` も同様に `APPL_DB` への書込は行わない。

---

## frrcfgd.py 経路の副次書込

`frrcfgd.py` は `BGP_GLOBALS_LISTEN_PREFIX` テーブルを購読する別経路だが、`STATE_DB` / `COUNTERS_DB` / `APPL_DB` への書込は一切存在しない（grep で確認）。FRR vtysh へのコマンド送出のみ。

---

## まとめ

| DB | テーブル | 書込種別 | 発生条件 |
|---|---|---|---|
| STATE_DB | BGP_PEER_CONFIGURED_TABLE | SET (add/update) / DEL | FRR コマンド適用成功時 |
| COUNTERS_DB | — | なし | — |
| APPL_DB | — | なし | — |

BGP_PEER_RANGE に対する副次 DB 書込は **STATE_DB への BGP_PEER_CONFIGURED_TABLE 更新のみ**。FRR vtysh への送出は副次書込ではなく主経路であり、別途 `<!-- runtime-trace -->` に記載済み。
