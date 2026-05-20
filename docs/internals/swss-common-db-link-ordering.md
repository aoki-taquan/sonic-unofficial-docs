---
title: swss-common DB リンク順序制約（linkToDbNative / linkToDb）
area: internals
tags: [swss-common, database, api, producer-state-table, internal]
description: linkToDbNative を linkToDb より先に呼ばなければならない順序制約の理由とクラッシュパターン。
source_issues:
  - https://github.com/sonic-net/sonic-swss-common/issues/507
verification: issue-confirmed
last_verified: 2026-05-20
---

# swss-common DB リンク順序制約（linkToDbNative / linkToDb）

## 概要

`sonic-swss-common` の一部クラスでは、`linkToDbNative()` を呼んだ後に `linkToDb()` を呼ぶ順序が必須となっている。順序を逆にするか、`linkToDbNative()` を 2 回呼ぶと、クラッシュやデータ競合が発生する。

## 対象クラス

この順序制約が問題になる主なクラス：

- `ProducerStateTable`
- `SubscriberStateTable`
- `ConsumerStateTable`

## 制約の内容

```cpp
// 正しい順序
obj.linkToDbNative(db_native);  // 1. ネイティブ DB へのリンク
obj.linkToDb(db);               // 2. DB へのリンク

// 間違い: 順序が逆
obj.linkToDb(db);               // エラー: linkToDbNative が先に必要
obj.linkToDbNative(db_native);

// 間違い: 二重呼び出し
obj.linkToDbNative(db_native);
obj.linkToDbNative(db_native);  // クラッシュ: 前のスレッドが動いているまま dtor が呼ばれる
```

## クラッシュのメカニズム

### `linkToDbNative()` 二重呼び出し時

`linkToDbNative()` は内部でバックグラウンドスレッドを起動する。2 回目の呼び出し時に前のスレッドが実行中のまま destructor が呼ばれ、以下のようなクラッシュが発生する。

```
#0  0x00007f...raise () from /lib64/libc.so.6
#1  0x00007f...abort () from /lib64/libc.so.6
...
```

### 順序が逆の場合

`linkToDb()` は `linkToDbNative()` によって初期化されたデータ構造を前提としているため、順序が逆の場合は初期化されていないポインタや構造体へのアクセスが発生する。

## API 改善の議論

この問題の議論で、以下の改善案が提起された。

1. **順序を API 内部で強制する**: `linkToDbNative()` が呼ばれていない状態で `linkToDb()` が呼ばれた場合に例外を投げる
2. **二重呼び出しを安全にする**: 前回のスレッドを適切に停止してから新しいスレッドを起動する

ただし、公開 API の変更はすべての呼び出し元への影響があるため、慎重な検討が必要とされている。

## 利用者への注意

`swss-common` を使用する swss / [orchagent](../reference/glossary.md#term-orchagent) や、カスタムエージェントを実装する際：

- `linkToDbNative()` と `linkToDb()` を使用する場合は必ず `linkToDbNative()` を先に呼ぶ
- `linkToDbNative()` を複数回呼ばない
- オブジェクトのライフサイクル管理を適切に行い、スレッドが動作中に destructor が呼ばれないようにする

## 関連

- [swss-common データベース設定](swss-common-database-config.md)
- GitHub Issue: [sonic-net/sonic-swss-common#507](https://github.com/sonic-net/sonic-swss-common/issues/507)

<!-- glossary-links-injected: e2892b76fd9a -->
