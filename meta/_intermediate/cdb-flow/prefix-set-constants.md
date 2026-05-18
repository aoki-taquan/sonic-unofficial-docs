# prefix-set-constants — Phase E: ハードコード定数スキャン結果

## スキャン対象

- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`

## 検出されたハードコード定数

### 1. TABLE_DAEMON ディスパッチ定数 (frrcfgd.py:83)

```python
TABLE_DAEMON = {
    'PREFIX_SET': ['bgpd'],
    'PREFIX':     ['zebra', 'bgpd', 'ospfd', 'pimd'],
    ...
}
```

`PREFIX_SET` テーブルのイベントは **bgpd のみ** に FRR コマンドを発行する。
`PREFIX` テーブルは zebra / bgpd / ospfd / pimd の 4 プロセスに同時発行する。
この非対称性は、`PREFIX` を経由した prefix-list が BGP だけでなく OSPF / PIM のポリシーマッチにも使われることに対応したもの。

### 2. MatchPrefix.IPV4_MAXLEN / IPV6_MAXLEN (frrcfgd.py:1606-1607)

```python
class MatchPrefix:
    IPV4_MAXLEN = 32
    IPV6_MAXLEN = 128
```

`masklength_range` の `lo..hi` パースで `hi == 32` (IPv4) または `hi == 128` (IPv6) のときに FRR の `le` 修飾子を省略する（FRR デフォルト最大長と一致するため冗長修飾が不要）。Config 上の `masklength_range "0..32"` は FRR コマンド上では `le` が消え `ge 0` のみになる。

### 3. af_mode 文字列定数 (frrcfgd.py:1665)

```python
self.af = socket.AF_INET if af_mode == 'ipv4' else socket.AF_INET6
```

`PREFIX_SET.mode` の `'IPv4'` / `'IPv6'` は frrcfgd の `bgp_table_handler_common` が `.lower()` で小文字化してから評価する（frrcfgd.py:2904）。
`mode` フィールドの大文字小文字は YANG enum 制約 (大文字) に従うが、frrcfgd 内部では小文字文字列 `'ipv4'`/`'ipv6'` として扱われる。YANG 経路以外からの直接書き込みで `mode=IPV4`（大文字）を渡しても frrcfgd が `.lower()` 変換するため問題なし。

### 4. FRR コマンドテンプレート (frrcfgd.py:2945, 2960, 2977, 2991)

```python
'no {} prefix-list {} {}'.format(('ip' if af == socket.AF_INET else 'ipv6'), pfx_set_name, str(del_pfx))
'{} prefix-list {} {}'.format(('ip' if af == socket.AF_INET else 'ipv6'), pfx_set_name, str(add_pfx))
```

FRR へ発行するコマンド文字列は frrcfgd にハードコードされている。`ip prefix-list` (IPv4) または `ipv6 prefix-list` (IPv6) の二択。YANG / CONFIG_DB 上のフィールド名とは独立した内部定数。

## 影響

- `masklength_range` に `0..32` (IPv4) を指定した場合、FRR prefix-list の `le 32` が省略されるため `show ip prefix-list` の出力と CONFIG_DB 値が微妙に異なって見える。
- `TABLE_DAEMON` の非対称性（PREFIX: 4 プロセス、PREFIX_SET: 1 プロセス）により、PREFIX エントリの DEL はルーティングデーモン全体への影響が広い。

## 証跡

- `frrcfgd.py` L83 (TABLE_DAEMON), L1606-1607 (IPV4_MAXLEN/IPV6_MAXLEN), L1665 (af_mode), L2904 (`.lower()`), L2945/2960/2977/2991 (FRR コマンドテンプレート)
