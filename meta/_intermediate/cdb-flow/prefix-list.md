# PREFIX_LIST 例外条件抽出 (cdb-batch-7)

## ソース
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_prefix_list.py`

## 抽出した例外条件

1. **prefix_type が未サポート**: `PREFIX_TYPE_CONFIG` に存在しないキー (`ANCHOR_PREFIX` / `SUPPRESS_PREFIX` 以外) は `log_warn` を出してスキップ (`return False`)。FRR への設定生成は行われない。
   - 証拠: `if type_cfg is None: log_warn("PrefixListMgr:: Prefix type '%s' is not supported" % prefix_type); return False`

2. **DEVICE_METADATA 未準備**: `CONFIG_DB/DEVICE_METADATA_TABLE|localhost` が存在しない場合は `log_info` を出してリトライ (`return False`)。
   - 証拠: `if not self.directory.path_exist(...): log_info("PrefixListMgr:: Device metadata is not ready yet"); return False`

3. **必須メタデータキー不足**: `type` / `bgp_asn` が DEVICE_METADATA に無い場合は `KeyError` をキャッチして `log_warn` しスキップ。
   - 証拠: `except KeyError as e: log_warn("PrefixListMgr:: Missing metadata key: %s" % e); return False`

4. **デバイスタイプ制限 (ANCHOR_PREFIX)**: `allowed_devices` チェックで `SpineRouter/UpstreamLC` / `UpperSpineRouter` 以外のデバイスには設定生成をスキップ (`log_warn` → `return False`)。`SUPPRESS_PREFIX` は `allowed_devices=None` で全デバイス許可。

5. **プレフィクス形式不正**: `netaddr.IPNetwork()` が失敗した場合 (`NotRegisteredError` / `AddrFormatError` / `AddrConversionError`) は `log_warn` してエントリをスキップ (`return True` でエラー扱いしない)。
   - 証拠: `except (...): log_warn("PrefixListMgr:: Prefix '%s' format is wrong"); return True`

6. **constants オーバーライド**: `bgp.prefix_list.<type>.ipv4_name` / `ipv6_name` が constants に定義されていればデフォルトの prefix_list 名を上書きする。
