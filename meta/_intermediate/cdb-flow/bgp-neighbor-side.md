# BGP_NEIGHBOR — Phase F: SET/DEL 副次 DB 書込

調査日: 2026-05-15  
対象ページ: `docs/reference/config-db/bgp-neighbor.md`

## 調査対象ソース

- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py` (全体精読)
- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py` (DB 書込箇所確認)
- `sonic-swss-common/common/schema.h` (テーブル名定数確認)

---

## 副次 DB 書込まとめ

### 1. STATE_DB — `BGP_PEER_CONFIGURED_TABLE`

**テーブル名定数**: `STATE_BGP_PEER_CONFIGURED_TABLE_NAME = "BGP_PEER_CONFIGURED_TABLE"`  
(定義: `sonic-swss-common/common/schema.h:511`)

**書込主体**: `BGPPeerMgrBase.update_state_db()` (`managers_bgp.py:271`)

| 操作 | 呼び出し元 | key 形式 | 内容 |
|------|-----------|---------|------|
| SET | `add_peer()` (L239) | `<nbr>` (default VRF) または `<vrf>\|<nbr>` | CONFIG_DB の data フィールドをそのまま SET |
| SET | `change_ip_range()` (L443) — dynamic peer | 同上 | ip_range 更新後の data |
| SET | `apply_admin_status()` (L353) — admin_status 変更成功時 | 同上 | 変更後の data |
| DEL | `del_handler()` 成功時 (L487) | 同上 | エントリ削除 (`state_peer_table.delete(key)`) |

**key 構成ロジック** (`managers_bgp.py:280-283`):
```python
if (vrf == "default"):
    key = nbr
else:
    key = vrf + "|" + nbr
```

**値**: `list(sorted(data.items()))` — CONFIG_DB から受け取った全フィールドをソートして格納。

**DEL 時の条件**: 既存エントリが存在しない場合は `log_warn` のみ（削除試行なし）。

---

### 2. FRR vtysh — `bgp suppress-fib-pending` 暗黙注入

SET/DEL いずれの操作でも `apply_op()` 経由で FRR に vtysh コマンドが送られる際、BGP インスタンス設定として `bgp suppress-fib-pending` が**自動的にプレフィックス注入**される (`managers_bgp.py:502-506`)。  
この設定は CONFIG_DB / STATE_DB / APPL_DB のいずれにも書込まれないが、FRR running-config（= APPL 相当）に副次的影響を与える。

---

### 3. frrcfgd 経路での STATE_DB / APPL_DB 書込

`frrcfgd.py` (sonic-frr-mgmt-framework) は `ConfigDBConnector` のみ使用し、STATE_DB / APPL_DB への直接書込は**なし**。FRR 設定は vtysh / config 経由で完結。

---

## side-effects ブロック（ページ挿入用）

```markdown
<!-- side-effects -->
## SET/DEL の副次 DB 書込

### STATE_DB — `BGP_PEER_CONFIGURED_TABLE`

`bgpcfgd`（`BGPPeerMgrBase.update_state_db()`）が SET/DEL の都度 STATE_DB へ書き込む。

| 操作 | トリガー | key | 内容 |
|------|---------|-----|------|
| SET | `add_peer()` 成功後 | `<nbr>` (default VRF) / `<vrf>\|<nbr>` | CONFIG_DB の全フィールドを `sorted(data.items())` で格納 |
| SET | `apply_admin_status()` FRR 適用成功後 | 同上 | admin_status 変更後の data |
| SET | `change_ip_range()` 成功後（dynamic peer） | 同上 | ip_range 更新後の data |
| DEL | `del_handler()` FRR 削除成功後 | 同上 | エントリ削除 |

> **注意**: DEL 時に対象エントリが STATE_DB に存在しない場合は `log_warn` のみ（例外なし）。

key 構成: VRF が `"default"` なら `<nbr>` のみ、それ以外は `<vrf>|<nbr>`。

### APPL_DB — 書込なし

`bgpcfgd` / `frrcfgd` いずれも APPL_DB への直接書込は行わない。BGP neighbor の反映は FRR vtysh 経由で完結。

### FRR running-config への暗黙注入

`apply_op()` 呼び出しごとに `bgp suppress-fib-pending` が BGP インスタンス設定として自動プレフィックスされる（`managers_bgp.py:502-506`）。CONFIG_DB フィールドには現れない副次効果。

> **ソース**: `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py:271-300, 239, 353, 443, 487`; `sonic-swss-common/common/schema.h:511`
<!-- /side-effects -->
```
