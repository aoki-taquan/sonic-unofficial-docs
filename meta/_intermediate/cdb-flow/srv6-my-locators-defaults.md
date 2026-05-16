# SRV6_MY_LOCATORS — Phase A コード由来の暗黙デフォルト (grep 証跡)

## 探索対象 field 一覧

SRV6_MY_LOCATORS のフィールド: prefix (mandatory), block_len, node_len, func_len, arg_len, vrf

---

## 探索コマンド

```
grep -n "block_len\|node_len\|func_len\|arg_len\|vrf" \
  sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_srv6.py
grep -n "block_len\|node_len\|func_len\|arg_len\|default.*vrf\|vrf.*default" \
  sonic-buildimage/src/sonic-yang-models/yang-models/sonic-srv6.yang
```

---

## field: prefix

**探索結果**:
- `sonic-srv6.yang:35-38`: `mandatory true`
- `managers_srv6.py:142`: `self.prefix = data['prefix'].lower() + "/{}".format(self.block_len + self.node_len)` — 存在前提でアクセス (KeyError で例外)

**code fallback**: なし — `mandatory true` のため省略不可。KeyError で crash。

---

## field: block_len

**探索結果**:
- `managers_srv6.py:138`:
  ```python
  self.block_len = int(data['block_len'] if 'block_len' in data else 32)
  ```
- `sonic-srv6.yang:47`: `default 32;`

**code fallback**: **省略時 `32`** (Python 側 `in data` ガード + YANG `default 32` の二重定義)。YANG とコードで一致。

---

## field: node_len

**探索結果**:
- `managers_srv6.py:139`:
  ```python
  self.node_len = int(data['node_len'] if 'node_len' in data else 16)
  ```
- `sonic-srv6.yang:56`: `default 16;`

**code fallback**: **省略時 `16`** (Python + YANG 両方で一致)。

---

## field: func_len

**探索結果**:
- `managers_srv6.py:140`:
  ```python
  self.func_len = int(data['func_len'] if 'func_len' in data else 16)
  ```
- `sonic-srv6.yang:65`: `default 16;`

**code fallback**: **省略時 `16`** (Python + YANG 両方で一致)。

---

## field: arg_len

**探索結果**:
- `managers_srv6.py:141`:
  ```python
  self.arg_len = int(data['arg_len'] if 'arg_len' in data else 0)
  ```
- `sonic-srv6.yang:74`: `default 0;`

**code fallback**: **省略時 `0`** (Python + YANG 両方で一致)。

---

## field: vrf

**探索結果**:
- `sonic-srv6.yang:90`: `default "default";`
- `managers_srv6.py` の `Locator` クラス: `vrf` フィールドは参照せず (FRR 向け locator コマンドに vrf は含まれない)
- `frrcfgd.py:121`: `'SRV6_MY_LOCATORS': ['zebra']` — zebra が購読するが vrf フィールドは frrcfgd では未使用

**code fallback**: YANG では `default "default"` だが、`bgpcfgd` の `Locator` クラスは `vrf` を読み取らない。YANG default のみ有効。

---

## prefix 拡張の計算式

`managers_srv6.py:142`:
```python
self.prefix = data['prefix'].lower() + "/{}".format(self.block_len + self.node_len)
```

省略時のデフォルト値を使った場合: `/{}`.format(32 + 16) = `/48`

つまり `prefix: "fc00::/48"` と同等の効果 (block_len=32, node_len=16 のデフォルト使用時)。

---

## YANG 制約

`sonic-srv6.yang:77`:
```yang
must 'block_len + node_len + func_len + arg_len <= 128';
```

デフォルト値合計: 32 + 16 + 16 + 0 = 64 ≤ 128。制約を満たす。

---

## YANG-コード 乖離サマリ

| フィールド | YANG default | コード fallback | 乖離 |
|-----------|-------------|----------------|------|
| `prefix` | mandatory true | なし (KeyError) | なし |
| `block_len` | `32` | `32` | なし (一致) |
| `node_len` | `16` | `16` | なし (一致) |
| `func_len` | `16` | `16` | なし (一致) |
| `arg_len` | `0` | `0` | なし (一致) |
| `vrf` | `"default"` | 読取なし (`Locator` クラスが `vrf` を無視) | あり — YANG は default を定義するが bgpcfgd は vrf を FRR コマンドに反映しない |

---

## 証跡ファイル

- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_srv6.py` L135-142 (Locator クラス)
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-srv6.yang` L24-93 (SRV6_MY_LOCATORS コンテナ)
- commit: `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd` (sonic-buildimage)
