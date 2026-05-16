# PREFIX_LIST — Phase D 失敗挙動 中間ファイル

生成日: 2026-05-16

ソース: `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_prefix_list.py`

<!-- failure -->
## Phase D: 失敗挙動・エラーパス スキャン結果

### 1. 不正 prefix 文字列 → netaddr 例外

`set_handler` / `del_handler` 両方で `netaddr.IPNetwork(str(prefix_str))` 呼び出し。
以下の例外を捕捉して `log_warn` + `return True`（FRR 設定生成スキップ）:

- `netaddr.NotRegisteredError`
- `netaddr.AddrFormatError`
- `netaddr.AddrConversionError`

```python
# L106-109 (set_handler)
try:
    prefix = netaddr.IPNetwork(str(prefix_str))
except (netaddr.NotRegisteredError, netaddr.AddrFormatError, netaddr.AddrConversionError):
    log_warn("PrefixListMgr:: Prefix '%s' format is wrong for prefix list '%s'" % (prefix_str, prefix_type))
    return True
```

代表的な不正例:
- `999.999.999.999/32` — 値が範囲外
- `192.168.1.0/33` — prefix 長が範囲外
- `not-an-ip` — 非 IP 文字列

### 2. FRR vtysh エラー

`cfg_mgr.push(cmd)` は fire-and-forget。vtysh 構文エラー時は bgpcfgd コマンドマネージャがログ記録するが PrefixListMgr は再送しない。
FRR 側エラー例: `% Invalid prefix range for af_ipv4, make sure len < ge, le >= ge`

確認コマンド:
```
vtysh -c 'show ip prefix-list'
```

### 3. 重複 seq — 非該当

`PREFIX_LIST` テーブルは seq を key に持たない。YANG list key 制約により同キー重複は CONFIG_DB レベルで上書きされるため、seq 重複問題は本テーブルで発生しない。

### 4. prefix_type 未サポート → log_warn + return False

`ANCHOR_PREFIX` / `SUPPRESS_PREFIX` 以外の type: `generate_prefix_list_config()` が `log_warn("PrefixListMgr:: Prefix type '%s' is not supported")` + `return False`。FRR 設定なし、DB エントリは残存。

### 5. DEVICE_METADATA 未準備 → return False

`DEVICE_METADATA|localhost` 未存在: `log_info` + `return False`（リトライ待ち）。
`type` / `bgp_asn` キー欠如: `KeyError` キャッチ → `log_warn` + `return False`。

<!-- /failure -->
