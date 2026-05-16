# PREFIX_SET — Task F Phase A: コード由来デフォルト

このメモは `docs/reference/config-db/prefix-set.md` の `<!-- defaults -->` ブロック生成に用いた一次調査。
ソース: `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`
(レイアウト上 `dockers/docker-fpm-frr/` 経由でビルドされる frrcfgd 本体)

## 1. `mode` — デフォルトなし（実装は必須扱い）

```python
# frrcfgd.py L2901-2905 (PREFIX_SET add 経路)
if 'mode' not in data:
    syslog.syslog(syslog.LOG_ERR, 'no mode given for prefix-set %s' % pfx_set_name)
    continue
set_mode = data['mode'].data.lower()
self.prefix_set_list[pfx_set_name] = MatchPrefixList(set_mode)
```

- `mode` フィールドが CONFIG_DB に**存在しないと frrcfgd はエラーログを出して当該エントリを完全スキップ**する。
- YANG 側に `default "IPv4"` 宣言があるため YANG バリデーション経由（sonic-yang-mgmt / GNMI / sonic-cfggen YANG モード）で投入すると `mode = IPv4` で埋まる。直接 `redis-cli` / `sonic-db-cli hset` で書くと欠落しエラー。
- 大文字小文字: 実装は `.lower()` で正規化。`IPv4` / `ipv4` / `IPV4` いずれも受理し `ipv4` として処理。
- `ipv4` 以外の値はすべて IPv6 扱い: `MatchPrefixList.__init__` L1664-1665 が `af_mode == 'ipv4'` 一致以外を `AF_INET6` にフォールバック（typo に弱い）。

## 2. `MatchPrefixList()` の引数なし生成 — `af = None`（NEIGHBOR_SET/NEXTHOP_SET 経路のみ）

```python
# frrcfgd.py L1660-1665
def __init__(self, af_mode = None):
    super(MatchPrefixList, self).__init__()
    if af_mode is None:
        self.af = None
    else:
        self.af = socket.AF_INET if af_mode == 'ipv4' else socket.AF_INET6
```

- `PREFIX_SET` ハンドラからは常に `mode` 引数付きで呼ばれるため `af = None` にはならない。
- `NEIGHBOR_SET` / `NEXTHOP_SET` 経路 (L2983) では引数なしで生成 → `add_prefix` が `__get_ip_af` で最初に追加された prefix の family を採用して埋める。
- このため NEIGHBOR_SET/NEXTHOP_SET の family は「最初に挿入された address の family」がデフォルト相当。`PREFIX_SET` には適用されない。

## 3. `action` — `'permit'` 既定（PREFIX 側だが PREFIX_SET と表裏一体）

```python
# frrcfgd.py L1622, L1682
def __init__(self, af, ip_prefix, len_range = None, action = 'permit', sequence_number = None):
def add_prefix(self, ip_pfx, len_range = None, action = 'permit', sequence_number = None):
```

- ただし `PREFIX_SET` テーブル自体に `action` フィールドは無く、メンバ `PREFIX_LIST` 側で持つ。YANG default も `permit`。

## 4. family 推定（`mode` 欠落時のフォールバックなし）

- `mode` 欠落エントリは frrcfgd で握りつぶされるため family 推定の余地なし。Phase 8 で書いた「`ip_prefix` の `:` で IPv4/IPv6 を判定」する処理は **PREFIX メンバ追加時の sanity 用** で、`PREFIX_SET` 自体の `mode` を埋める処理ではない。
- 結果として「PREFIX_SET の `mode` 暗黙デフォルト IPv4」は **YANG 側だけが提供する**。frrcfgd 単独では暗黙デフォルトを持たない。

## ページへの反映方針

`<!-- defaults -->` ブロックを `<!-- /handler-branching -->` の直後・`<!-- runtime-trace -->` の直前に挿入する。
内容:

1. `mode` の YANG-実装乖離: YANG `default IPv4` vs 実装は必須扱い (`continue` でスキップ)
2. `mode` の大小文字: `.lower()` で正規化、`ipv4` 以外は IPv6 扱い
3. family 既定: `PREFIX_SET` 経路では mode から決定。NEIGHBOR_SET/NEXTHOP_SET だけ「最初の prefix の family」が暗黙既定
4. `action` 既定 `'permit'`（PREFIX メンバ側、参考）
