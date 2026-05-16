# BGP_NEIGHBOR — Phase F: 副次 DB 書込 (Side Effects)

調査日: 2026-05-16  
対象ソース: `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py`  
調査対象クラス: `BGPPeerMgrBase`

---

## 副次書込先: STATE_DB / BGP_PEER_CONFIGURED_TABLE

`BGPPeerMgrBase` は CONFIG_DB `BGP_NEIGHBOR` テーブルの変化を受け FRR にコマンドを発行した後、
`update_state_db()` メソッドを介して STATE_DB の `BGP_PEER_CONFIGURED_TABLE` にも書き込む。
これは "副次 DB 書込" であり、APPL_DB / ASIC_DB / COUNTER_DB への書込はない。

---

## 呼び出し経路

| 呼び出し元メソッド | 条件 | STATE_DB 操作 | evidence |
|-----------------|------|--------------|----------|
| `add_peer()` | Jinja2 テンプレートレンダリング成功 かつ `apply_op()` 後 | `SET key data` | `managers_bgp.py:239` |
| `apply_admin_status()` | `apply_op()` が `True` を返した場合のみ | `SET key data` (admin_status 含む全フィールド) | `managers_bgp.py:353` |
| `apply_range_changes()` | ip_range 更新成功後 | `SET key data` | `managers_bgp.py:443` |
| `del_handler()` | `apply_op()` が `True` を返した場合のみ | `DEL key` | `managers_bgp.py:487` |

---

## key 構造 (STATE_DB)

```
BGP_PEER_CONFIGURED_TABLE|<neighbor>             # vrf == "default"
BGP_PEER_CONFIGURED_TABLE|<vrf>|<neighbor>       # 名前付き VRF
```

`update_state_db()` 内 L280–283 で構築:
```python
if (vrf == "default"):
    key = nbr
else:
    key = vrf + "|" + nbr
```

---

## SET 時の書込内容

`state_peer_table.set(key, list(sorted(data.items())))` — CONFIG_DB から受け取った `data` ディクショナリ全体を sorted fvs として格納する。  
`admin_status` 変更時は `change_admin_status()` → `apply_admin_status()` が `data` をそのまま渡すため、最新の全フィールドが上書きされる。

---

## DEL 時の動作

1. `state_peer_table.get(key)` で事前存在確認
2. 存在する (`status == True`) → `state_peer_table.delete(key)`
3. 存在しない → `LOG_WARN "Peer not found in BGP_PEER_CONFIGURED_TABLE"`（削除処理自体は続行）

---

## 失敗時の動作

`update_state_db()` 全体が `try/except` で囲まれている。  
Exception 発生時: `LOG_ERR "Update of state db failed for peer ..."` → `return False`  
ただし FRR への `apply_op()` は既に完了しているため、**FRR と STATE_DB の乖離が生じうる**。  
`ERROR_TABLE` / `APPL_DB` への伝播はなし。

---

## apply_admin_status の条件分岐

```python
# managers_bgp.py:352-356
ret_code = self.apply_op(self.templates[template_name].render(neighbor_addr=nbr), vrf)
if ret_code:
    self.update_state_db(vrf, nbr, data, "SET")  # FRR 成功時のみ
else:
    log_err(...)  # FRR 失敗時は STATE_DB 書込なし
```

`admin_status=up` / `down` のどちらの場合も同一パスを通る。`admin_status` が up/down 以外の場合は `change_admin_status()` で早期 `log_err` → `apply_admin_status()` は呼ばれない → STATE_DB 書込なし。

---

## 他 DB への書込なし（確認済み）

- APPL_DB: 書込なし（bgpcfgd は FRR 直接操作、APPL_DB 経由なし）
- ASIC_DB: 書込なし
- COUNTER_DB: 書込なし
- ERROR_TABLE: 書込なし
- CHASSIS_APP_DB: `BGPPeerMgrBase` スコープでは書込なし（`ChassisAppDbMgr` は別クラス）

---

## サマリ表

| トリガー操作 | 副次書込先 | key | value | 条件 |
|------------|-----------|-----|-------|------|
| CONFIG_DB BGP_NEIGHBOR SET (新規) | STATE_DB `BGP_PEER_CONFIGURED_TABLE` | `<nbr>` or `<vrf>\|<nbr>` | 全フィールド (sorted fvs) | テンプレートレンダリング成功 |
| CONFIG_DB BGP_NEIGHBOR SET (admin_status 更新) | STATE_DB `BGP_PEER_CONFIGURED_TABLE` | 同上 | 同上 | `apply_op()` True |
| CONFIG_DB BGP_NEIGHBOR SET (ip_range 更新) | STATE_DB `BGP_PEER_CONFIGURED_TABLE` | 同上 | 同上 | `apply_op()` True |
| CONFIG_DB BGP_NEIGHBOR DEL | STATE_DB `BGP_PEER_CONFIGURED_TABLE` | 同上 | (削除) | `apply_op()` True |
