# SRV6_MY_LOCATORS — Phase E 定数・上限値スキャンノート

対象テーブル: `SRV6_MY_LOCATORS|<locator_name>`
Consumer (bgpcfgd): `SRv6Mgr` (`sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_srv6.py`)
Consumer (orchagent): `Srv6Orch` (`sonic-swss/orchagent/srv6orch.cpp`)
スキャン範囲:
  - `srv6orch.cpp:19-27` (マクロ定数)
  - `srv6orch.cpp:331-350` (getLocatorCfgFromDb — ロケータ読取り)
  - `managers_srv6.py:6-12` (bgpcfgd 定数)
  - `managers_srv6.py:37-53` (locators_set_handler)
  - `managers_srv6.py:135-142` (Locator クラス)
Evidence: sonic-buildimage sha `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`, sonic-swss sha `4305596156d70e9797e8a881b3d19b46de0bce0d`

---

## 検出した定数・マジックナンバー・ハードコード値

### srv6orch.cpp — ロケータ長デフォルト (#define マクロ)

`getLocatorCfgFromDb()` (`srv6orch.cpp:331-350`) が CONFIG_DB のロケータエントリを読み取るとき、
各フィールドが存在しない場合に `get_value_or()` の第二引数として使われる固定文字列。

| 定数名 | 値 | 意味 | 参照箇所 |
|--------|-----|------|---------|
| `LOCATOR_DEFAULT_BLOCK_LEN` | `"32"` | ロケータ block_len フィールド省略時のフォールバック（ビット） | `srv6orch.cpp:21`, `srv6orch.cpp:347` |
| `LOCATOR_DEFAULT_NODE_LEN` | `"16"` | ロケータ node_len フィールド省略時のフォールバック（ビット） | `srv6orch.cpp:22`, `srv6orch.cpp:348` |
| `LOCATOR_DEFAULT_FUNC_LEN` | `"16"` | ロケータ func_len フィールド省略時のフォールバック（ビット） | `srv6orch.cpp:23`, `srv6orch.cpp:349` |
| `LOCATOR_DEFAULT_ARG_LEN` | `"0"` | ロケータ arg_len フィールド省略時のフォールバック（ビット） | `srv6orch.cpp:24`, `srv6orch.cpp:350` |

注: 上記 4 定数は YANG `default` 値（`block_len=32`, `node_len=16`, `func_len=16`, `arg_len=0`）と一致している。
Python `managers_srv6.py` の `Locator` クラスが使うフォールバック値も同値（`managers_srv6.py:138-141`）。

### managers_srv6.py — bgpcfgd 定数

| 定数名 | 値 | 意味 | 参照箇所 |
|--------|-----|------|---------|
| `DEFAULT_VRF` | `"default"` | `SID.decap_vrf` のデフォルト値。SID 処理で参照されるが、ロケータ設定コマンドには含まれない | `managers_srv6.py:11` |
| `SRV6_MY_SIDS_TABLE_NAME` | `"SRV6_MY_SIDS"` | ロケータと SID の関係を判断するテーブル名定数 | `managers_srv6.py:12` |

### FRR コマンド内ハードコード値

`locators_set_handler()` (`managers_srv6.py:37-53`) が生成する FRR vtysh コマンド:

```
segment-routing srv6 locators locator <name>
  prefix <prefix>/<block_len+node_len> block-len <block_len> node-len <node_len> func-bits <func_len>
  behavior usid
```

| ハードコード項目 | 固定値 | 意味 |
|----------------|--------|------|
| FRR `behavior` フラグ | `"usid"` | 全ロケータに無条件付与。micro-SID (uSID) 動作が強制される（`managers_srv6.py:47`）。CONFIG_DB フィールドでは変更不可 |
| プレフィックス長計算式 | `block_len + node_len` | FRR に渡すプレフィックス長は block+node の合計ビット数に固定（`managers_srv6.py:142`）。func_len・arg_len は含まれない |

### ビット長の有効範囲（YANG 制約）

`sonic-srv6.yang` で定義された整数範囲制約。コード側ではチェックなし（YANG バリデーション頼み）。

| フィールド | 型定義 | YANG 範囲 |
|-----------|--------|---------|
| `block_len` | `uint8` | 1–128 |
| `node_len` | `uint8` | 1–128 |
| `func_len` | `uint8` | 0–128 |
| `arg_len` | `uint8` | 0–128 |
| ビット長合計制約 | `must` | `block_len + node_len + func_len + arg_len <= 128` |

---

## 定数利用サマリ

1. **ロケータ長デフォルト (32/16/16/0)**: `Srv6Orch::getLocatorCfgFromDb()` と `Locator.__init__()` の両方が同一デフォルト値を使う。YANG default とも一致しており、三者が揃っている。
2. **`behavior usid` 固定付与**: FRR のロケータコマンドには常に `behavior usid` が付与される。これは uSID（micro-SID）モードを有効化する RFC 9252 準拠の設定だが、CONFIG_DB にはこの動作を制御するフィールドがない。
3. **プレフィックス長 = block + node のみ**: FRR に送るプレフィックス長は `block_len + node_len` の合計（デフォルト `/48`）であり、`func_len` / `arg_len` は含まれない。SID アドレスのキー計算（`getMySidCounterKey`）では `block + node + func` を使うため、ページ利用者がプレフィックス長を混同しないよう注意が必要。
