# MGMT_PORT — Phase 6/7/8 derivation & handler-branching

対象ページ: `docs/reference/config-db/mgmt-port.md`
バッチ: cdb_batch_9

---

## Phase 6: 自動派生 (minigraph.py 代入)

<!-- derivation -->

### 1. `alias`・`admin_status`・`speed` の自動代入

**ソース**: `sonic-buildimage/src/sonic-config-engine/minigraph.py:2281-2296`

```python
results['MGMT_PORT'] = {}
...
results['MGMT_PORT'][name] = {'alias': alias, 'admin_status': 'up'}
if name in port_speeds_default:
    results['MGMT_PORT'][name]['speed'] = port_speeds_default[alias]
```

- `alias` は minigraph XML の `<ManagementInterface><InterfaceName>` から取得。
- `admin_status` は常時 `'up'` で固定代入される（XML に関わらず）。
- `speed` は `port_speeds_default` 辞書に alias が存在する場合のみ付与（デフォルトスピードテーブルは platform_config から取得）。

### 2. db_migrator.py — `migrate_mgmt_ports_on_s6100()`

**ソース**: `sonic-utilities/scripts/db_migrator.py:205,224`

```python
def migrate_mgmt_ports_on_s6100(self):
    ...
    self.configDB.set_entry('PORT', portName, entries[portName])
```

- S6100 プラットフォームに特有のマイグレーション。旧 CONFIG_DB の `MGMT_PORT` エントリを新フォーマットに変換して書き直す。
- `portName` は `eth0` 形式に正規化される。

<!-- /derivation -->

---

## Phase 7: 条件付き登録

<!-- derivation -->

該当なし。

`mgmt-intf` サービス（`mgmt_intf_monitor.py`）は `hostcfgd` とは独立した systemd サービスとして動作し、MGMT_PORT テーブルを購読する。Platform 条件による動的 manager 登録の仕組みは使用していない。

<!-- /derivation -->

---

## Phase 8: manager メソッド内 early return / dispatch

<!-- handler-branching -->

### mgmt-intf サービスの処理分岐

**ソース**: `sonic-buildimage/src/sonic-mgmt-framework/`（管理フレームワーク）

1. **op == "SET"**: `speed` フィールドが存在する場合 `ethtool -s eth0 speed <val> duplex full autoneg off` を実行。存在しない場合この呼び出しをスキップ（early return 相当）。
2. **`admin_status` == "down"**: `ip link set eth0 down` を発行。`"up"` の場合は `ip link set eth0 up` 後に IP 割り当て処理へ進む。
3. **名前解決失敗 early return**: インターフェース名が `/sys/class/net/` に存在しない場合は処理をスキップしてログ出力のみ。

<!-- /handler-branching -->
