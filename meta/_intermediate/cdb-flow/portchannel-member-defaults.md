# PORTCHANNEL_MEMBER — Phase A: コード由来デフォルト調査

**対象テーブル**: `PORTCHANNEL_MEMBER`
**調査日**: 2026-05-14
**担当フェーズ**: Phase A (field defaults from code)

---

## 結論サマリ

`PORTCHANNEL_MEMBER` は **key-only テーブル** であり、追加フィールドを一切持たない。
したがって「フィールドのデフォルト値」という概念は本テーブルには存在しない。
エントリの値は常に空ハッシュ `{}` であり、存在自体がメンバー関係を表す。

---

## ソース調査

### YANG モデル

ファイル: `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-portchannel.yang` L130-156

```yang
container PORTCHANNEL_MEMBER {
    list PORTCHANNEL_MEMBER_LIST {
        key "name port";

        leaf name {
            type leafref { ... PORTCHANNEL_LIST/name }
        }
        leaf port {
            /* key elements are mandatory by default */
            type leafref { ... PORT_LIST/name }
        }
    }
}
```

- `default` 文なし
- key leaf (`name`, `port`) は YANG spec 上 mandatory (key は必須)
- 付加 leaf なし → デフォルト設定値ゼロ

### minigraph.py

ファイル: `sonic-buildimage/src/sonic-config-engine/minigraph.py`

```python
# L967: pc_members へのエントリ追加
pc_members[(pcintfname, pcmbr_list[i])] = {}
# L2547: CONFIG_DB への書き込み
results['PORTCHANNEL_MEMBER'] = pc_members
```

値は `{}` (空辞書)。minigraph 経由では値フィールドなし。

### CLI (sonic-utilities/config/main.py)

`config portchannel member add` が `set_entry('PORTCHANNEL_MEMBER', (pc_name, port), {})` を呼ぶ。
値は同様に `{}` — フィールドなし。

---

## フィールドデフォルト表

| フィールド | 型 | デフォルト | ソース | 備考 |
|-----------|---|-----------|-------|------|
| `name` (key) | leafref | なし (必須) | YANG key | PORTCHANNEL.name への参照 |
| `port` (key) | leafref | なし (必須) | YANG key | PORT.name への参照 |

*付加フィールドなし。デフォルト値なし。*

---

## `<!-- defaults -->` ブロック (docs ページ挿入テキスト)

```markdown
<!-- defaults -->
## フィールドデフォルト (コード由来)

`PORTCHANNEL_MEMBER` は key-only テーブルであり付加フィールドを持たない。
エントリの値は常に空ハッシュ `{}` で、デフォルト設定値は存在しない。

| フィールド | デフォルト | 由来 |
|-----------|-----------|------|
| `name` (key) | なし (必須) | YANG leafref キー |
| `port` (key) | なし (必須) | YANG leafref キー |

> **ソース**: `sonic-portchannel.yang` L134-154、`minigraph.py` L967
<!-- /defaults -->
```
