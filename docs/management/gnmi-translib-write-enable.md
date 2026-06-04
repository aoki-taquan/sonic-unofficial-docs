---
title: gNMI SET / Translib 書き込み有効化
area: management
tags: [gnmi, translib, configuration, build]
description: gNMI SET リクエストが失敗する場合の原因と、Translib 書き込みを有効化してビルドする方法を説明する。
source_issues:
  - https://github.com/sonic-net/sonic-gnmi/issues/333
  - https://github.com/sonic-net/sonic-gnmi/issues/20
sources:
  - repo: sonic-net/sonic-gnmi
    path: gnmi_server/server.go
    ref: eb635b7679b260c3fd0786a6d0734fc8e82c9a22
  - repo: sonic-net/sonic-gnmi
    path: gnmi_server/constants_translib.go
    ref: eb635b7679b260c3fd0786a6d0734fc8e82c9a22
  - repo: sonic-net/sonic-gnmi
    path: gnmi_server/constants_translib_write.go
    ref: eb635b7679b260c3fd0786a6d0734fc8e82c9a22
  - repo: sonic-net/sonic-gnmi
    path: Makefile
    ref: eb635b7679b260c3fd0786a6d0734fc8e82c9a22
  - repo: sonic-net/sonic-buildimage
    path: rules/config
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-mgmt-common
    path: translib/db/db.go
    ref: f71cf829883c36963455cf4d90fe16dae35f0b80
related:
  _no_related_yang: true
  _no_related_config_db: true
  _no_related_cli: true
verification: code-verified
last_verified: 2026-06-04
---

# gNMI SET / Translib 書き込み有効化

## 概要

[gNMI](../reference/glossary.md#term-gnmi) SET リクエストを実行すると、次のような gRPC エラーが返される場合がある[^server-go]。

```
rpc error: code = Unimplemented desc = Translib write is disabled
```

このエラーは、[sonic-buildimage](../reference/glossary.md#term-sonic-buildimage) のビルド時に **Translib 書き込みが無効化された状態**でビルドされていることが原因である。

!!! note "別系統のエラーと混同しないこと"
    syslog や glog 出力に現れる `setEntry: DoCVL for UPDATE` は **本問題とは無関係** である。これは `sonic-mgmt-common` の `translib/db/db.go` が UPDATE 操作前に CVL (Config Validation Library) を呼び出す際の `glog.V(3)` デバッグログであり、Translib 書き込みが有効でも常に出力される[^docvl-log]。CVL バリデーション失敗は別途 `CVL Error` 系メッセージとして現れる。

## 原因

[SONiC](../reference/glossary.md#term-sonic) の gNMI サーバ（`sonic-gnmi`）は、デフォルトでは Translib の書き込み操作を無効にしてコンパイルされる。サーバは起動時に `EnableTranslibWrite` フラグを参照し、false の場合 SET ハンドラが `codes.Unimplemented` で即座に拒否する[^server-go]。これは意図的なセキュリティ上の選択であり、設定変更操作を明示的に許可する場合のみ有効化できる。

実装上は、ビルド時に `constants_translib.go`（デフォルト、`ENABLE_TRANSLIB_WRITE = false`）か `constants_translib_write.go`（`ENABLE_TRANSLIB_WRITE = true`）のいずれかを選択することで切り替わる[^constants]。

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

gNMI サーバが書き込み有効でビルドされているかを確認するには、SET リクエストを試みる。

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

[^server-go]: `sonic-gnmi/gnmi_server/server.go` L1149-1152 — `s.config.EnableTranslibWrite == false` のとき `grpc.Errorf(codes.Unimplemented, "Translib write is disabled")` を返す。
[^docvl-log]: `sonic-mgmt-common/translib/db/db.go` L1318-1320 — `if glog.V(3) { glog.Info("setEntry: DoCVL for UPDATE") }` は UPDATE 経路の CVL 呼び出し前デバッグログであり、エラーではない。
[^constants]: `sonic-gnmi/gnmi_server/constants_translib.go` L6（既定: `const ENABLE_TRANSLIB_WRITE = false`）と `sonic-gnmi/gnmi_server/constants_translib_write.go` L6（書き込み有効ビルド: `true`）、および `sonic-gnmi/Makefile` L38 の `ifeq ($(ENABLE_TRANSLIB_WRITE),y)` 分岐で選択される。

<!-- glossary-links-injected: 1260314c6f20 -->
