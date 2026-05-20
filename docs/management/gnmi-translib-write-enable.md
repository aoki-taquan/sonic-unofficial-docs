---
title: gNMI SET / Translib 書き込み有効化
area: management
tags: [gnmi, translib, configuration, build]
description: gNMI SET リクエストが失敗する場合の原因と、Translib 書き込みを有効化してビルドする方法を説明する。
source_issues:
  - https://github.com/sonic-net/sonic-gnmi/issues/333
  - https://github.com/sonic-net/sonic-gnmi/issues/20
verification: issue-confirmed
last_verified: 2026-05-20
---

# gNMI SET / Translib 書き込み有効化

## 概要

[gNMI](../reference/glossary.md#term-gnmi) SET リクエストを実行すると、次のようなエラーが返される場合がある。

```
Translib write is disabled
```

または

```
setEntry: DoCVL for UPDATE
```

これらのエラーは、[sonic-buildimage](../reference/glossary.md#term-sonic-buildimage) のビルド時に **Translib 書き込みが無効化された状態**でビルドされていることが原因である。

## 原因

[SONiC](../reference/glossary.md#term-sonic) の gNMI サーバー（`sonic-gnmi`）は、デフォルトでは Translib の書き込み操作を無効にしてコンパイルされる。これは意図的なセキュリティ上の選択であり、設定変更操作を明示的に許可する場合のみ有効化できる。

## 解決方法

### ビルド時に Translib 書き込みを有効化する

`sonic-buildimage` をビルドする際、以下のオプションを指定する。

```bash
make ENABLE_TRANSLIB_WRITE=y <target>
```

または `rules/config` ファイルに以下を追加する。

```
ENABLE_TRANSLIB_WRITE = y
```

### 確認方法

gNMI サーバーが書き込み有効でビルドされているかを確認するには、SET リクエストを試みる。

```bash
gnmi_set \
  -xpath /openconfig-interfaces:interfaces/interface[name=Ethernet0]/config/description \
  -string_val "test" \
  -target_addr <sonic-ip>:8080 \
  -username admin \
  -password <password>
```

`Translib write is disabled` エラーが返る場合は、書き込みが無効なビルドを使用している。

## 注意事項

- `ENABLE_TRANSLIB_WRITE=y` はビルド時のオプションであり、ランタイムで切り替えることはできない
- 書き込みを有効にすると、gNMI 経由で設定変更が可能になるため、認証・認可の設定を適切に行うこと
- TLS を使用していない環境では、`-notls` オプションを追加することで接続できるが、本番環境では TLS を使用することを強く推奨する

## 関連

- [gNMI 利用ガイド](gnmi-usage.md)
- [gNMI ストリーミングテレメトリの落とし穴](gnmi-streaming-telemetry-pitfalls.md)
- GitHub Issue: [sonic-net/sonic-gnmi#333](https://github.com/sonic-net/sonic-gnmi/issues/333)
- GitHub Issue: [sonic-net/sonic-gnmi#20](https://github.com/sonic-net/sonic-gnmi/issues/20)

<!-- glossary-links-injected: 8ba32e5aa69d -->
