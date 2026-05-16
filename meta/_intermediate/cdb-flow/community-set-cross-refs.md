# COMMUNITY_SET 暗黙参照スキャン (Phase C)

`docs/reference/config-db/community-set.md` の Phase C (暗黙参照) ブロック裏付け資料。

ソースは `sonic-net/sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`。

## スキャン手順

```bash
# COMMUNITY_SET / comm_set_list への参照を全体スキャン
grep -n "community_set\|comm_set\|COMMUNITY_SET\|match_community\|set_community_ref\|com-ref" \
    .cache/sonic-sources/sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py

# bgpcfgd.py の存在確認
find .cache/sonic-sources/ -name "bgpcfgd.py" 2>/dev/null

# BGP_NEIGHBOR_AF の community 関連フィールド確認
grep -n "send_community\|BGP_NEIGHBOR_AF" \
    .cache/sonic-sources/sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py
```

## 検出結果

### bgpcfgd.py

`bgpcfgd.py` は `sonic-buildimage` リポジトリには存在しない。BGP 設定の実装は `frrcfgd.py` 内の `BGPConfigDaemon` クラスに統合されている。

### ROUTE_MAP からの被参照

#### match_community (frrcfgd.py:1938)

```python
# route_map_key_map の一部
('match_community', '[bgpd]{no:no-prefix}match community {}'),
```

`ROUTE_MAP` エントリの `match_community` フィールドが設定されると、その値（COMMUNITY_SET 名）をそのまま FRR bgpd の `match community <name>` コマンドに展開する。`COMMUNITY_SET` テーブルの存在チェックは `frrcfgd` 側では行わず、FRR bgpd が community-list 名として解釈する。

#### set_community_ref (frrcfgd.py:1953, L832-834)

```python
# route_map_key_map の一部
('set_community_ref', '[bgpd]{no:no-prefix}set community {:com-ref}'),
```

`{:com-ref}` フォーマット解決（`frrcfgd.py:832-834`）:

```python
elif format == 'com-ref':
    com_set = self.daemon.comm_set_list.get(self.value, None)
    if com_set is not None and com_set.is_configurable():
        return ' '.join(com_set.mbr_list)
```

`ROUTE_MAP.set_community_ref` の値を key として `daemon.comm_set_list`（= CONFIG_DB の `COMMUNITY_SET` テーブルをロードした dict）を lookup し、`community_member` リストを展開する。COMMUNITY_SET が未登録または `is_configurable()` = false の場合、format メソッドは `None` を返し、FRR コマンドは生成されない（サイレントスキップ）。

### BGP_NEIGHBOR_AF — COMMUNITY_SET 参照なし

```python
# nbr_af_key_map の一部 (frrcfgd.py:1910)
('send_community', '{no:no-prefix}neighbor {} send-community {}', hdl_send_com),
```

`BGP_NEIGHBOR_AF.send_community` は FRR の `neighbor <peer> send-community` コマンドを制御する（`standard` / `extended` / `both` 等の値）。`COMMUNITY_SET` テーブルを参照するロジックは存在しない。community の「送信ポリシー制御」であり、「コミュニティリスト参照」ではない。

### 参照元テーブルまとめ

| 参照元テーブル | フィールド | frrcfgd 解決方式 | COMMUNITY_SET 参照 | evidence |
|---|---|---|---|---|
| `ROUTE_MAP` | `match_community` | FRR へ名前をそのまま渡す | 間接（FRR bgpd 側で解決） | `frrcfgd.py:1938` |
| `ROUTE_MAP` | `set_community_ref` | `comm_set_list` を内部 lookup | 直接（frrcfgd 内で解決） | `frrcfgd.py:1953, L832-834` |
| `BGP_NEIGHBOR_AF` | `send_community` | FRR neighbor コマンドに展開 | なし | `frrcfgd.py:1910` |
