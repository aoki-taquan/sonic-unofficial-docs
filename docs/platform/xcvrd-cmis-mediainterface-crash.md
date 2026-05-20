---
title: xcvrd クラッシュ（MediaInterfaceIDApp 未定義）
area: platform
tags: [xcvrd, cmis, transceiver, crash, platform-common]
description: CMIS アプリケーション広告リストに MediaInterfaceIDApp が定義されていない場合に xcvrd がクラッシュする問題と回避策。
source_issues:
  - https://github.com/sonic-net/sonic-platform-common/issues/489
verification: issue-confirmed
last_verified: 2026-05-20
---

# xcvrd クラッシュ（MediaInterfaceIDApp 未定義）

## 概要

CMIS（Common Management Interface Specification）対応光モジュールを搭載したシステムで、モジュールのアプリケーション広告リストに `MediaInterfaceIDApp` が定義されていない場合、`xcvrd` がクラッシュする問題が報告されている。

## 影響範囲

- `sonic-platform-common` に依存するすべてのプラットフォーム
- CMIS 対応（QSFP-DD / OSFP / CMIS 準拠 SFP 等）光モジュールを使用する環境

## 原因

`sonic-platform-common` PR #457 において、アプリケーション広告リスト（Application Advertisement List）データへのアクセス方法が変更された。この変更により、`MediaInterfaceIDApp` が `Undefined` または未定義の場合に、`xcvrd` がその値を処理しようとして例外を発生させクラッシュする。

具体的には、アプリケーション広告エントリの `MediaInterfaceIDApp` フィールドが存在しないモジュールでは、辞書アクセスが `KeyError` を引き起こす。

## 症状

```
xcvrd crashed with exception:
KeyError: 'MediaInterfaceIDApp'
```

またはそれに準ずる例外スタックトレースがシステムログに記録される。

```bash
# ログ確認コマンド
sudo journalctl -u xcvrd -n 100
# または
sudo tail -100 /var/log/syslog | grep xcvrd
```

## 修正

PR [sonic-net/sonic-platform-common#457](https://github.com/sonic-net/sonic-platform-common/pull/457) の修正を適用することで解消される。

修正の要点：
- `MediaInterfaceIDApp` が存在しない場合に `Undefined` として扱う安全なアクセスを実装
- アプリケーション広告リストの走査時に `None` / 未定義チェックを追加

## 暫定回避策

修正が適用されたバージョンにアップデートできない場合、問題のある光モジュールを一時的に取り外すか、別のポートに移動することで当該インターフェースでのクラッシュを回避できる。

## 関連

- [SFF-8472 Rx パワーキャリブレーション問題](sfp-sff8472-rx-power-calibration.md)
- [SFP EEPROM 解析の欠損](sfp-eeprom-parsing-gaps.md)
- GitHub Issue: [sonic-net/sonic-platform-common#489](https://github.com/sonic-net/sonic-platform-common/issues/489)
- GitHub PR: [sonic-net/sonic-platform-common#457](https://github.com/sonic-net/sonic-platform-common/pull/457)
