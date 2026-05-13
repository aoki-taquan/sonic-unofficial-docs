# BGP_GLOBALS_AF_AGGREGATE_ADDR テーブル — consumer 例外条件分析

## Consumer: frrcfgd (sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py)

### 処理関数
- `bgp_table_handler_common` → BGP_GLOBALS_AF_AGGREGATE_ADDR 分岐 (L3169)

### 例外条件・特殊挙動

#### 1. key フォーマット検証 → 不正 IP prefix は syslog ERR & continue
key は `<AF_TYPE>|<ip_prefix>` 形式。`MatchPrefix.normalize_ip_prefix()` が None を返した場合、syslog ERR を出して continue。FRR には反映されない。

```python
# frrcfgd/frrcfgd.py:3177
norm_ip_prefix = MatchPrefix.normalize_ip_prefix((socket.AF_INET if af == 'ipv4' else socket.AF_INET6), ip_prefix)
if norm_ip_prefix is None:
    syslog.syslog(syslog.LOG_ERR, 'invalid IP prefix format %s for af %s' % (ip_prefix, af))
    continue
```

#### 2. AF_TYPE パース → `<af>_<ip_type>` 必須
key の最初のセグメントを `af_type.lower().split('_')` で 2 分割。フォーマット不正な場合は ValueError が上位に伝播する。

#### 3. as_set / summary_only の内部キャッシュ管理
DEL 以外の操作で `as_set`/`summary_only` が `"true"` の場合、`af_aggr_list[vrf][norm_ip_prefix]` に `AggregateAddr` オブジェクトをキャッシュ。
DEL 時は `af_aggr_list[vrf].pop(norm_ip_prefix, None)` で除去 (KeyError なし)。

#### 4. FRR コマンド実行失敗 → syslog ERR & continue
`key_map.run_command(...)` が失敗した場合、syslog ERR を出して次のエントリへ continue。
内部キャッシュは更新されない。

```python
if not ret_val:
    syslog.syslog(syslog.LOG_ERR, 'failed running BGP IP prefix AF config command')
    continue
```

#### 5. bgp_asn / vrf 依存
`local_asn` と `vrf` は上位ハンドラから取得。BGP_GLOBALS が設定されていないと `local_asn` が不在で例外。
BGP_GLOBALS の処理依存あり (waitingリスト方式)。

#### 6. 更新は必ず全置換
FRR の `address-family` コンテキストで aggregate-address コマンドを再投入するため、既存エントリの削除と新規追加を組み合わせた全置換となる。
