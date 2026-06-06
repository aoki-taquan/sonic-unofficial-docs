---
title: xcvrd クラッシュ（CMIS module_media_interface_id 未定義）
area: platform
tags: [xcvrd, cmis, transceiver, crash, platform-common]
description: CMIS アプリケーション広告に media interface ID が含まれない場合に xcvrd が KeyError でクラッシュする問題と回避策。
source_issues:
  - https://github.com/sonic-net/sonic-platform-common/issues/489
verification: issue-confirmed
last_verified: 2026-06-04
sources:
  - repo: sonic-net/sonic-platform-common
    path: sonic_platform_base/sonic_xcvr/api/public/cmis.py
    ref: 64beade8cddecdbc154531bc84bed2fa86581ea8
  - repo: sonic-net/sonic-platform-common
    path: sonic_platform_base/sonic_xcvr/fields/consts.py
    ref: 64beade8cddecdbc154531bc84bed2fa86581ea8
related:
  cli: []
  config_db: []
  yang: []
  _no_related_yang: true
  _no_related_config_db: true
---

# xcvrd クラッシュ（CMIS module_media_interface_id 未定義）

## 概要

CMIS（Common Management Interface Specification）対応光モジュールを搭載したシステムで、モジュールのアプリケーション広告リスト（Application Advertisement）に media interface ID エントリが正しく定義されていない場合、`xcvrd` がアプリケーション辞書アクセスで `KeyError` を投げてクラッシュする問題が報告されている。Issue [sonic-net/sonic-platform-common#489][1] では当該フィールドを CMIS 仕様用語で `MediaInterfaceIDApp` と呼称しているが、master のコード上のキー名は `module_media_interface_id` である[^1]。

## 影響範囲

- `sonic-platform-common` の `sonic_xcvr` ライブラリに依存するすべてのプラットフォーム
- CMIS 対応（QSFP-DD / OSFP / CMIS 準拠 SFP-DD 等）光モジュールを使用する環境

## 用語マッピング（Issue ↔ 実コード）

Issue / CMIS 仕様 と master 実装でのキー名対応は以下のとおり。

| Issue / CMIS 仕様での呼称 | master 実装での appl_dict キー | 定義箇所 |
|---|---|---|
| `MediaInterfaceIDApp` | `module_media_interface_id` | `cmis.py:637` `cmis.py:2308`[^1] |
| `HostInterfaceIDApp` | `host_electrical_interface_id` | `cmis.py:636` `cmis.py:2300`[^1] |

EEPROM 上のフィールド名としては `ModuleMediaInterface850nm` / `ModuleMediaInterfaceSM` / `ModuleMediaInterfacePassiveCopper` / `ModuleMediaInterfaceActiveCable` / `ModuleMediaInterfaceBaseT` がメディアタイプ別に定義されており（`consts.py:159-163`[^2]）、`get_application_advertisement()` がこれらを media type に応じて選択して `module_media_interface_id` キーへ格納する。

## 原因

Issue #489 で報告されたクラッシュは PR #457 適用前の実装に由来する。当時の `get_application_advertisement()` および呼び出し側（`is_lpo()` 等）は、アプリケーション広告辞書に対して `appl_dict['module_media_interface_id']` の形でキー直接参照を行っており、特定モジュールが CMIS アプリケーション広告に media interface ID 相当のエントリを欠いている場合に `KeyError: 'module_media_interface_id'` が発生していた[^3]。

現行 master (`64beade`) では PR #457 の方針が反映済みで、`get_application_advertisement()` は media interface ID 値が `None` / `'Unknown'` のエントリを走査時に `continue` でスキップし（`cmis.py:2305-2308`[^1]）、`is_lpo()` 等の利用箇所も `appl_dict.get('module_media_interface_id')` による安全アクセスに統一されている（`cmis.py:637`[^1]）。したがって本ページの記述は、(a) PR #457 適用以前の master を運用しているフォーク・古い branch、(b) 同等の直接参照パターンが残存している sonic-platform-common 派生コードに対する歴史的説明として参照されたい。

## 症状

```
xcvrd crashed with exception:
KeyError: 'module_media_interface_id'
```

またはそれに準ずる例外スタックトレースがシステムログに記録される。Issue 由来のクラッシュ報告では CMIS 仕様用語の `MediaInterfaceIDApp` がメッセージに現れるケースもある[^3]。

```bash
# ログ確認コマンド
sudo journalctl -u xcvrd -n 100
# または
sudo tail -100 /var/log/syslog | grep xcvrd
```

## 修正

PR [sonic-net/sonic-platform-common#457][2] の修正で、辞書アクセス箇所を `.get()` ベースの安全アクセスに変更し、media interface ID が未定義のエントリは走査時にスキップするようになった。本記事執筆時点 (commit `64beade`) の master にはこの修正方針が反映されており、`get_application_advertisement()` 側でも `appl_dict.get('module_media_interface_id')` を使う構造になっている[^1]。

## 暫定回避策

修正が適用されたバージョンへアップデートできない場合、問題のある光モジュールを一時的に取り外すか、別のポートに移動することで当該インターフェースでのクラッシュを回避できる。当該モジュールのアプリケーション広告内容は `sfputil show eeprom -dp <port>` で確認できる。

## 関連

- [SFF-8472 Rx パワーキャリブレーション問題](sfp-sff8472-rx-power-calibration.md)
- [SFP EEPROM 解析の欠損](sfp-eeprom-parsing-gaps.md)
- GitHub Issue: [sonic-net/sonic-platform-common#489][1]
- GitHub PR: [sonic-net/sonic-platform-common#457][2]

[1]: https://github.com/sonic-net/sonic-platform-common/issues/489
[2]: https://github.com/sonic-net/sonic-platform-common/pull/457

[^1]: `sonic-platform-common` `sonic_platform_base/sonic_xcvr/api/public/cmis.py` (commit `64beade`) — `is_lpo()` (L627-644) の `appl_dict.get('module_media_interface_id')` と、`get_application_advertisement()` 内の構築ループ (L2293-2308)。
[^2]: `sonic-platform-common` `sonic_platform_base/sonic_xcvr/fields/consts.py` (commit `64beade`) L158-163 で `HOST_ELECTRICAL_INTERFACE` / `MODULE_MEDIA_INTERFACE_{850NM,SM,PASSIVE_COPPER,ACTIVE_CABLE,BASE_T}` を定義。
[^3]: [sonic-net/sonic-platform-common#489](https://github.com/sonic-net/sonic-platform-common/issues/489) のクラッシュ報告内容（Issue 由来呼称 `MediaInterfaceIDApp`）。
