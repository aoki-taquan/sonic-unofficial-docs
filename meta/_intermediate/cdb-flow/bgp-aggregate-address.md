# BGP_AGGREGATE_ADDRESS テーブル — consumer 例外条件分析

## Consumer: bgpcfgd / AggregateAddressMgr (sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_aggregate_address.py)

### 処理関数
- `AggregateAddressMgr.set_handler(key, data)` (L~74)
- `AggregateAddressMgr.address_set_handler(key, data)` (L~97)

### 例外条件・特殊挙動

#### 1. prefix の IP アドレス検証 → INACTIVE 状態でスキップ
`validate_prefix(prefix)` が None を返した場合、FRR コマンドは実行されず、STATE_DB に `state=inactive` が書かれて skip。
エントリはキューから消去されるが再試行されない (return True)。

```python
# managers_aggregate_address.py:set_handler
net, reason = validate_prefix(prefix)
if net is None:
    log_err("AggregateAddressMgr::invalid aggregate prefix %s: %s" % (prefix, reason))
    self.set_address_state(key, data, ADDRESS_INACTIVE_STATE)
    return True
```

#### 2. BBR 状態が不明かつ bbr-required=true → INACTIVE スキップ
BBR 状態 (enabled/disabled) が CONFIG_DB に存在しない状態で `bbr-required=true` のアドレスが来た場合 → INACTIVE。

```python
if bbr_status not in (BGP_BBR_STATUS_ENABLED, BGP_BBR_STATUS_DISABLED) and bbr_required:
    log_info("...BBR state is unknown and bbr-required is true. Skip the address %s" % prefix)
    self.set_address_state(key, data, ADDRESS_INACTIVE_STATE)
```

#### 3. BBR が disabled かつ bbr-required=true → INACTIVE スキップ
BBR が明示的に disabled のとき、bbr-required アドレスは FRR に投入されない。

#### 4. BBR 状態変更によるアドレスの再有効化/無効化
`on_bbr_change()` で BBR が enabled に変わると、STATE_DB の bbr_required アドレスを全て再投入。
BBR が disabled になると全て削除 (STATE_DB は inactive に更新)。

#### 5. DEL 操作 — inactive アドレスの FRR 削除スキップ
STATE_DB の `state=inactive` のアドレスを DEL する際、FRR への削除コマンドはスキップ。

```python
# del_handler
if address_state.get(ADDRESS_STATE_KEY) == ADDRESS_INACTIVE_STATE:
    log_info("...address %s is inactive, skip FRR removal" % key2prefix(key))
```

#### 6. 依存フィールド: bgp_asn 未設定 → KeyError
`directory.get_slot(...)["localhost"]["bgp_asn"]` が失敗すると KeyError が上位に伝播し、manager が例外を出す。
`bgp_asn` (DEVICE_METADATA.localhost) は前提条件として必須。

#### 7. FRR push 失敗 → INACTIVE
`address_set_handler` が False を返した場合、STATE_DB に inactive を書いて終了。再試行はなし。
