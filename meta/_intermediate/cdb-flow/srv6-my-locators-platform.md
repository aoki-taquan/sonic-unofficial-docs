# SRV6_MY_LOCATORS — Phase H プラットフォーム制約 (grep 証跡)

## 探索対象

`SRV6_MY_LOCATORS` テーブルのプラットフォーム依存挙動:
- SAI ケイパビリティ照会の有無
- ハードコード動作 (`behavior usid`)
- bgpcfgd / frrcfgd の FRR コマンド差異
- IPv6 専用制約
- `arg_len` の扱い

---

## 探索 1: SAI ケイパビリティ照会の有無

**探索コマンド**:
```
grep -n "sai_query_attribute_capability\|SRV6_MY_LOCATOR\|locator.*SAI\|SAI.*locator" srv6orch.cpp
```

**結果**:
`srv6orch.cpp:107`: `m_locatorCfgTable(cfgDb, CFG_SRV6_MY_LOCATOR_TABLE_NAME)` — `Table` 型（GET 専用）。
`srv6orch.cpp:122`: `m_mysid_counters_supported = queryMySidCountersCapability()` — ロケータではなく MY_SID エントリのカウンタ向け照会。

ロケータ向けの SAI ケイパビリティ照会: **0 ヒット**。ロケータは SAI オブジェクトとして作成されない。

---

## 探索 2: `behavior usid` ハードコード

**探索コマンド**:
```
grep -n "behavior usid\|usid" managers_srv6.py
```

**結果** (`managers_srv6.py:47`):
```python
cmd_list += ['locators',
             'locator {}'.format(locator_name),
             'prefix {} block-len {} node-len {} func-bits {}'.format(
             locator.prefix,
             locator.block_len, locator.node_len, locator.func_len),
             "behavior usid"   # ← ハードコード文字列
]
```

`behavior usid` は CONFIG_DB フィールドではなく Python ソースに直接埋め込まれた定数。変更手段なし。

---

## 探索 3: frrcfgd パスの FRR コマンド

**探索コマンド**:
```
grep -n "SRV6_MY_LOCATORS\|locator.*prefix\|behavior" frrcfgd.py
```

**結果** (`frrcfgd.py:2732-2744`):
```python
elif table == 'SRV6_MY_LOCATORS':
    if not del_table:
        locator_name = prefix
        prefix = data['prefix']
        cmd = ['vtysh', '-c', 'configure terminal',
               '-c', 'segment-routing', '-c', 'srv6', '-c', 'locators',
               '-c', 'locator {}'.format(locator_name),
               '-c', 'prefix {} block-len {} node-len {} func-bits {}'.format(
                    prefix.data, data['block_len'].data, data['node_len'].data, data['func_len'].data)]
```

`behavior usid` **なし**。bgpcfgd との差異を確認。

---

## 探索 4: IPv6 専用制約 (YANG)

**探索コマンド**:
```
grep -n "ipv6-prefix\|ipv4\|inet:ip" sonic-srv6.yang
```

**結果**: `sonic-srv6.yang:63`: `type inet:ipv6-prefix` — IPv4 は受け付けない。

---

## 探索 5: `arg_len` の FRR コマンドへの反映

**探索コマンド**:
```
grep -n "arg_len\|arg-len\|args-bits\|func_len" managers_srv6.py frrcfgd.py
```

**結果**:
- `managers_srv6.py:46`: `'func-bits {}'.format(locator.func_len)` — `arg_len` はコマンドに含まれない
- `frrcfgd.py:2744`: `func-bits {}'.format(data['func_len'].data)` — 同様に `arg_len` なし
- `srv6orch.cpp:339-349`: Srv6Orch では `arg_len` を SAI エントリに詰める

`arg_len` フィールドはロケータの SAI エントリ（MY_SID 処理）にのみ使われ、FRR コマンドには送られない: **0 ヒット（FRR コマンド側）**。

---

## 参照ファイル

- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_srv6.py`
  (SHA: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd)
- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`
  (SHA: 参照 repos.json)
- `sonic-swss/orchagent/srv6orch.cpp`
  (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-srv6.yang`
  (SHA: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd)
