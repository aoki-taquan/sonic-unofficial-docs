# cluster: Phase D — 失敗挙動調査

## 調査対象

`cluster` フィールド (DEVICE_METADATA|localhost / DEVICE_NEIGHBOR_METADATA|<device>) の失敗挙動。
書き込み経路は `minigraph.py` (sonic-cfggen) のみ。ランタイム消費デーモンなし。

## grep entry

```
grep -n "IndexError\|cluster\|ClusterName" \
  sonic-buildimage/src/sonic-config-engine/minigraph.py
```

ヒット箇所（失敗関連）:
- L493: `cluster = None` — parse_device() 初期値
- L514-515: `elif node.tag == str(QName(ns, "ClusterName")): cluster = node.text`
- L667-668: `if cluster != None: device_data['cluster'] = cluster`
- L2170: `cluster = [devices[key] for key in devices if key.lower() == hostname.lower()][0].get('cluster', "")` — IndexError リスク

## 失敗パス分析

### 1. hostname がどのデバイスにも一致しない → IndexError

`minigraph.py:2170` のリスト内包式:

```python
cluster = [devices[key] for key in devices if key.lower() == hostname.lower()][0].get('cluster', "")
```

`devices` dict に `hostname` と大文字小文字を無視して一致するキーが 0 件の場合、`[...][0]` が `IndexError` を送出し `parse_xml()` がクラッシュする。`sonic-cfggen` は例外を補足せず終了コード非ゼロで終了 → CONFIG_DB 書き込みなし。

**実運用での発生条件**: minigraph XML の `<Hostname>` が装置実際のホスト名と不一致の場合。ただし同パスで `devices` は PngDec/MetadataDeclaration から構築されており、通常は自ノードが含まれる。

### 2. `<ClusterName>` タグの text が None → 書き込みスキップ (silent)

XML の `<ClusterName></ClusterName>` (空タグ) の場合 `node.text` は `None`。
- `parse_device()` では `cluster = None` に残る。
- DEVICE_NEIGHBOR_METADATA 書き込み条件 `if cluster != None:` が False → スキップ。
- DEVICE_METADATA 書き込み条件 `if cluster:` も False → スキップ。
- エラーログなし、警告なし。

### 3. YANG 型検証: cluster フィールドに型制約なし → 任意文字列を許容

YANG:
```yang
leaf cluster {
    type string;
    description "The switch is a member of this cluster.";
}
```
型は `string` のみ、range/pattern 制約なし。任意の文字列が書き込まれても YANG バリデーションは通過する。

### 4. DEVICE_NEIGHBOR_METADATA: 空文字列の非対称書き込み

DEVICE_NEIGHBOR_METADATA では `if cluster != None:` のため、空文字列 `""` は書き込まれる（None のみ除外）。  
DEVICE_METADATA では `if cluster:` のため、空文字列は書き込まれない。  
この非対称性は設計上の不整合だが、`cluster` フィールドがランタイム消費されないため実害はない。

## ランタイム失敗なし

`cluster` フィールドはランタイムで読み出すデーモンが存在しない write-only フィールドのため、DB への書き込み後の失敗パスは存在しない。orchagent・bgpcfgd・linkmgrd 等は `cluster` を参照しない（Phase C 調査で確認済み）。

## 結論

| # | 失敗トリガー | 影響 | ログ |
|---|------------|------|------|
| 1 | hostname 不一致 (devices に自ノードなし) | sonic-cfggen IndexError クラッシュ → CONFIG_DB 書き込み全失敗 | なし (例外) |
| 2 | `<ClusterName>` が空タグ (None) | cluster フィールド書き込みスキップ (silent) | なし |
| 3 | 不正文字列 | YANG が許容 → 書き込まれる | なし |
| 4 | 空文字列 `""` | DEVICE_METADATA には書かれず、DEVICE_NEIGHBOR_METADATA には書かれる (非対称) | なし |
