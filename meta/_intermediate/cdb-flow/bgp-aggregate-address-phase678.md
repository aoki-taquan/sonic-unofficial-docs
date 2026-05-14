# BGP_AGGREGATE_ADDRESS — Phase 6/7/8 中間ファイル

生成日: 2026-05-14 (batch cdb_batch_0)

<!-- derivation -->
## Phase 6: 自動派生代入スキャン

### 全ソース — 該当なし

minigraph.py / config_samples / db_migrator.py / init_cfg.json.j2 に BGP_AGGREGATE_ADDRESS への代入なし。CLI または REST/gNMI で明示設定。

**結論**: Phase 6 派生なし。

<!-- /derivation -->

<!-- derivation -->
## Phase 7: 条件付き manager/orch 登録

### bgpcfgd — AggregateAddressMgr

```python
# sonic-bgpcfgd/bgpcfgd/main.py:106
AggregateAddressMgr(common_objs, "CONFIG_DB", BGP_AGGREGATE_ADDRESS_TABLE_NAME),
```

`AggregateAddressMgr` は **常時** 登録される。条件付き登録なし。

### BBR 依存サブスクリプション

```python
# managers_aggregate_address.py:41
self.directory.subscribe(
    [(CONFIG_DB_NAME, BGP_BBR_TABLE_NAME, BGP_BBR_STATUS_KEY)],
    self.on_bbr_change
)
```

`BGP_BBR` テーブルの状態変化に対するコールバックも登録される（常時）。

<!-- /derivation -->

<!-- handler-branching -->
## Phase 8: manager メソッド内 early return / dispatch

### AggregateAddressMgr.set_handler() — BBR 依存 early return

```python
# managers_aggregate_address.py:set_handler()
bbr_required = data.get('bbr-required', 'false') == 'true'
if bbr_status not in (BGP_BBR_STATUS_ENABLED, BGP_BBR_STATUS_DISABLED) and bbr_required:
    # BBR 状態不明かつ bbr-required=true → スキップ（inactive）
    self.set_address_state(key, data, ADDRESS_INACTIVE_STATE)
elif bbr_status == BGP_BBR_STATUS_DISABLED and bbr_required:
    # BBR 無効かつ bbr-required=true → スキップ（inactive）
    self.set_address_state(key, data, ADDRESS_INACTIVE_STATE)
else:
    # 通常処理
    if self.address_set_handler(key, data):
        self.set_address_state(key, data, ADDRESS_ACTIVE_STATE)
```

| 条件 | 処理 |
|------|------|
| `bbr-required=false`（デフォルト） | 常時 FRR に `aggregate-address` コマンドを push |
| `bbr-required=true` かつ BBR enabled | FRR に push、STATE_DB を `active` に更新 |
| `bbr-required=true` かつ BBR disabled | early return、STATE_DB を `inactive` に更新 |
| `bbr-required=true` かつ BBR 状態不明 | early return、STATE_DB を `inactive` に更新 |

### address_set_handler() — prefix 検証 early return

```python
# managers_aggregate_address.py:address_set_handler()
net, reason = validate_prefix(prefix)
if net is None:
    log_err("invalid aggregate prefix %s: %s" % (prefix, reason))
    return False  # early return: 無効プレフィックス
```

無効プレフィックス（CIDR 形式不正）の場合は FRR push をスキップ。

### summary-only / as-set フィールド分岐

boolean フィールド (`summary-only`, `as-set`) の値により FRR `aggregate-address` コマンドに追加オプションが付与される:

| フィールド値 | FRR コマンド |
|------------|------------|
| `summary-only=true` | `aggregate-address <prefix> summary-only` |
| `as-set=true` | `aggregate-address <prefix> as-set` |
| 両方 true | `aggregate-address <prefix> summary-only as-set` |

<!-- /handler-branching -->
