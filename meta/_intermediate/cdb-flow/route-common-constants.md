# route-common (ROUTE_REDISTRIBUTE) — Phase E: ハードコード定数スキャン

調査日: 2026-05-18  
対象ソース: `frrcfgd/frrcfgd.py` (ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd)  
スキャン範囲: L97（デーモンリスト）, L1979-1980（key_map）, L3149-3168（ROUTE_REDISTRIBUTE イベント処理）

---

## 検出したハードコード定数

### 1. ip_type = 'unicast'（固定文字列）

`frrcfgd.py:3153`:

```python
ip_type = 'unicast'
```

`address-family <af> unicast` の `unicast` 部分は CONFIG_DB フィールドから取得せず、常に文字列リテラル `'unicast'` を使用する。`multicast` や `vpn` への拡張は現在サポートされていない。

### 2. ospf3 → ospf6 プロトコル名変換（ハードコードマッピング）

`frrcfgd.py:3151-3152`:

```python
if af == 'ipv6' and src_proto == 'ospf3':
    src_proto = 'ospf6'
```

CONFIG_DB の `src_protocol` フィールドに `ospf3` を格納した場合、`addr_family=ipv6` のときのみ `ospf6` へ内部変換される。FRR bgpd は `redistribute ospf3` コマンドを認識しないため、`frrcfgd` が変換して `redistribute ospf6` を発行する。同様の変換は `CommandArgument.format` の `src-proto` フォーマット（L926-927）でも行われる。

### 3. dst_protocol 許容値 = 'bgp' のみ（ハードコード検証）

`frrcfgd.py:3156-3158`:

```python
if dst_proto != 'bgp':
    syslog.syslog(syslog.LOG_ERR, 'only bgp could be used as dst protocol, but {} was given'.format(dst_proto))
    continue
```

YANG モジュール（`sonic-route-common.yang`）では `dst_protocol` を `type string` として定義しており enum 制約はない。実行時に `frrcfgd` が `'bgp'` のみを許容するハードコード検証を行う。

### 4. ROUTE_REDISTRIBUTE のターゲットデーモン = ['bgpd']（ハードコードリスト）

`frrcfgd.py:97`:

```python
'ROUTE_REDISTRIBUTE': ['bgpd'],
```

`BGPConfigDaemon.tbl_to_daemon` に定義されており、ROUTE_REDISTRIBUTE イベントは `bgpd` デーモンのみに vtysh コマンドを送信する。`zebra` や `staticd` は含まれない。

### 5. route_map の max-elements = 1（YANG 定数）

`sonic-route-common.yang`:

```yang
leaf-list route_map {
    max-elements 1;
    ...
}
```

`route_map` フィールドは leaf-list 型だが要素数が最大 1 に制限されている。複数の route-map を指定することはできない。

---

## 定数一覧

| 定数 / リテラル | 値 | 定義箇所 | 用途 |
|---|---|---|---|
| `ip_type` | `'unicast'` | `frrcfgd.py:3153` | `address-family <af> unicast` の ip_type 固定値 |
| ospf3→ospf6 変換条件 | `af == 'ipv6' and src_proto == 'ospf3'` | `frrcfgd.py:3151-3152` | FRR コマンドで `ospf6` を使用するための変換 |
| 許容 dst_protocol | `'bgp'` | `frrcfgd.py:3156` | 実行時検証（YANG enum 制約なし） |
| ROUTE_REDISTRIBUTE デーモン | `['bgpd']` | `frrcfgd.py:97` | vtysh コマンドの送信先デーモン |
| route_map 最大要素数 | `1` | `sonic-route-common.yang max-elements` | leaf-list の要素数上限 |
