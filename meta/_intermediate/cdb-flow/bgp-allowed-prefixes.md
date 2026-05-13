# BGP_ALLOWED_PREFIXES テーブル — consumer 例外条件分析

## Consumer: bgpcfgd / BGPAllowListMgr (sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_allow_list.py)

### 処理関数
- `BGPAllowListMgr.set_handler(key, data)` (L~52)
- `BGPAllowListMgr.__set_handler_validate(key, data)` (L~75)

### 例外条件・特殊挙動

#### 1. 機能無効時 → warn & return True (消化)
`self.enabled` が False (constants で無効化されている) 場合、SET/DEL いずれも処理せずに return True。

```python
if not self.enabled:
    log_warn("BGPAllowListMgr::Received 'SET' command, but this feature is disabled in constants")
    return True
```

#### 2. key パターン検証 → 不一致は log_err & return True
key は `re.compile(r"^DEPLOYMENT_ID\|\d+\|\S+$|...")` に一致しなければエラー log して return True (消化)。
再試行なし。

```python
if not self.key_re.match(key):
    log_err("BGPAllowListMgr::Received BGP ALLOWED 'SET' message with invalid key: '%s'" % key)
    return False
```

#### 3. data が None → log_err & return False
data が None の場合は検証で False を返し、消化されない (再試行の可能性)。

#### 4. prefixes_v4/prefixes_v6 の IP アドレス検証
`prefixes_v4` の各要素が IPv4 でない、または `prefixes_v6` の要素が IPv6 でない場合 → log_err & return False。
`ge`/`le` サフィックスを含む場合は split して prefix 部分のみ検証。

```python
if not all(TemplateFabric.is_ipv4(re.split('ge|le', prefix)[0]) for prefix in prefixes_v4):
    log_err(...)
    return False
```

#### 5. prefixes 両方空 → log_err & return False
`prefixes_v4` も `prefixes_v6` も空の場合は reject。少なくとも一方が必要。

#### 6. default_action の値検証
`default_action` が `"permit"` または `"deny"` 以外の場合 → log_err & return False。

#### 7. NEIGHBOR_TYPE キーの特殊パース
key に `|NEIGHBOR_TYPE|` が含まれる場合、neighbor_type と community_value を特殊パースする。
パースに失敗した場合（`split` エラー等）は例外が上位に伝播する。

#### 8. DEL の key 検証 → 不一致は log_err & return (消化)
DEL の key もパターン検証があるが、`return False` ではなく単純な `return` (値なし) なので消化扱い。
