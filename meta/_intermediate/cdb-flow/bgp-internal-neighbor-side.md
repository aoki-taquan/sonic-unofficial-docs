# BGP_INTERNAL_NEIGHBOR — 副次 DB 書込スキャン (Task F Phase F)

> 対象ページ: `docs/reference/config-db/bgp-internal-neighbor.md`
> 対象ソース: `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py`,
> `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`
> 調査日: 2026-05-16

## 結論サマリ

`BGP_INTERNAL_NEIGHBOR` テーブルの set/del を契機に `bgpcfgd`
(`BGPPeerMgrBase`, `peer_type="internal"`) が行う副次 DB 書込は
**STATE_DB `BGP_PEER_CONFIGURED_TABLE|<key>` への書込のみ**。
COUNTERS_DB / APPL_STATE_DB / ASIC_DB への直接書込は無い。
FRR bgpd への反映は `cfg_mgr.push()` 経由の vtysh push に閉じる。

`frrcfgd.py`（frr-mgmt-framework パス）は `BGP_INTERNAL_NEIGHBOR` を
購読しないため、副次書込の対象外。

## 副次 DB 走査結果

| 副次 DB | テーブル名 | 書込有無 | 根拠 |
|---|---|---|---|
| STATE_DB | `BGP_PEER_CONFIGURED_TABLE` | **あり** | `update_state_db()` が `swsscommon.STATE_BGP_PEER_CONFIGURED_TABLE_NAME`（= `"BGP_PEER_CONFIGURED_TABLE"`）へ書込 / 削除。`add_peer()` L239, `apply_admin_status()` L353, `apply_range_changes()` L443, `del_handler()` L487 から各成功・失敗パスで呼ばれる |
| COUNTERS_DB | — | なし | `managers_bgp.py` に `COUNTERS_DB` / `FlexCounter` 参照なし |
| APPL_STATE_DB | — | なし | `managers_bgp.py` に `APPL_STATE_DB` / `APP_STATE_DB` 参照なし |
| ASIC_DB | — | なし (間接のみ) | bgpcfgd は SAI を直接触らない。FRR `bgpd` → APPL_DB `ROUTE_TABLE` → `RouteOrch` → `sairedis` 経路で ASIC_DB に達するが、これは RouteOrch 配下の副作用であり BGP_INTERNAL_NEIGHBOR handler 由来ではない |
| ERROR_TABLE | — | なし | 実装なし |

## STATE_DB 書込の発火点

`update_state_db(vrf, nbr, data, op)` は `STATE_DB` コネクタを毎回開き、
テーブル `BGP_PEER_CONFIGURED_TABLE` を操作する (`managers_bgp.py:271-304`)。

key 形式:

- vrf == `"default"` のとき: `<neighbor-ip>`
- vrf != `"default"` のとき: `<vrf>|<neighbor-ip>`

| 発火点 | op | 書込値 | コード根拠 |
|---|---|---|---|
| `add_peer()` 成功後（FRR push 完了時） | `SET` | `data`（CONFIG_DB から取得したフィールド全件） | `managers_bgp.py:239` |
| `apply_admin_status()` 成功後（admin_status 変更時） | `SET` | `data` | `managers_bgp.py:353` |
| `apply_range_changes()` 成功後（ip_range 変更時） | `SET` | `data` | `managers_bgp.py:443` |
| `del_handler()` 成功後（FRR から peer 削除時） | `DEL` | `{}` | `managers_bgp.py:487` |

> **注**: `BGP_INTERNAL_NEIGHBOR` は `peer_type="internal"` のため
> `peer_type == 'dynamic'` / `'sentinels'` 限定の ip_range 処理
> (`apply_range_changes`) は通常呼ばれない（`managers_bgp.py:461`）。
> 実際に発火するのは `add_peer` SET と `del_handler` DEL、および
> `apply_admin_status` SET の 3 パスが主体。

## FRR vtysh push の経路

`apply_op()` (`managers_bgp.py:494-508`) は jinja2 テンプレートで
生成した vtysh コマンドを `self.cfg_mgr.push()` でバッファし、FRR に
渡す。APPL_DB / STATE_DB への直接書込はここでは行われない。

## frrcfgd.py スキャン結果

`sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py` に
`BGP_INTERNAL_NEIGHBOR` / `internal_neighbor` の参照は一切存在しない。
`DEVICE_METADATA.frr_mgmt_framework_config=true` の環境でも内部 iBGP は
`bgpcfgd` が担当し、`frrcfgd` は不介入。

## 検証手段

```bash
# STATE_DB 書込確認
sonic-db-cli STATE_DB keys 'BGP_PEER_CONFIGURED_TABLE|*'
sonic-db-cli STATE_DB hgetall 'BGP_PEER_CONFIGURED_TABLE|10.1.0.1'

# COUNTERS_DB に該当キーが無いこと
sonic-db-cli COUNTERS_DB keys '*BGP*INTERNAL*'
```
