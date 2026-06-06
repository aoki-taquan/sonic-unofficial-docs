---
title: sfputil read-eeprom / write-eeprom（ページ + オフセット指定で SFP/QSFP EEPROM 操作）
description: sfputil read-eeprom / write-eeprom（ページ + オフセット指定で SFP/QSFP EEPROM 操作）
  — 既存 platform API sfp.read_eeprom / sfp.write_eeprom は 「全体 offset」 しか取らず、ユーザは規格毎に
  page/of…
area: platform
verification: code-verified
last_verified: 2026-05-09
sources:
- repo: sonic-net/SONiC
  path: doc/sfputil/read_write_eeprom_by_page.md
  ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
  - PORT
  cli:
  - sfputil read-eeprom
  - sfputil write-eeprom
  - show platform
  - show interfaces
  yang:
  - sonic-port
---

<!-- topics-tip -->
!!! tip "Topics で読み物として読む"
    この HLD は実装詳細を含む。機能の概念・設定・運用を読み物として読みたい場合は [Topics 14 章: Platform / Port / Optics](../topics/14-platform-port-optics/index.md) を参照。
<!-- /topics-tip -->

!!! info "裏取りステータス: code-verified"
    `sonic-utilities/sfputil/main.py` で `read-eeprom` (L1812-) / `write-eeprom` (L1862-) サブコマンドを確認。`--page (-n)` / `--offset (-o)` / `--size` / `--no-format` / `--wire-addr`（sff8472 用）/ `--verify`（write 後リードバック比較）の各オプション、および `get_overall_offset_sff8472` ヘルパによる sff8472 wire-addr ハンドリング、`sfp.read_eeprom(flat_offset, size)` / `sfp.write_eeprom(overall_offset, len(bytes), bytes)` 経路をすべて確認。`sfp.read_eeprom() is currently not implemented for this platform` の ERROR_NOT_IMPLEMENTED 経路もエラー処理として実装されている。

# `sfputil read-eeprom` / `write-eeprom`（ページ + オフセット指定で SFP/QSFP EEPROM 操作）

## 概要

既存 platform API `sfp.read_eeprom` / `sfp.write_eeprom` は **「全体 offset」** しか取らず、ユーザは規格毎に page/offset の合算を自前計算する必要があった。本機能は **page と offset** を直接渡せる sfputil サブコマンド `read-eeprom` / `write-eeprom` を追加し、cable type 毎の妥当性検査を入れる[^1]。

## 動作仕様

### CLI

```text
sfputil read-eeprom -p <port> -n <page> -o <offset> -s <size> [--no-format] [--wire-addr a0h|a2h]
sfputil write-eeprom -p <port> -n <page> -o <offset> -d <hex> [--wire-addr a0h|a2h] [--verify]
```

- `--no-format`: 整形なし生 hex
- `--wire-addr`: sff8472 (SFP) のみ。`a0h` / `a2h`
- `--verify`: 書き込み後リードバックして比較

例[^1]:

```text
sfputil read-eeprom -p Ethernet0 -n 0 -o 100 -s 2
        00000064 4a 44                                            |..|

sfputil write-eeprom -p Ethernet0 -n 0 -o 100 -d 4a44 --verify
Error: Write data failed! Write: 4a44, read: 0000.
```

<!-- evidence: sonic-net/SONiC doc/sfputil/read_write_eeprom_by_page.md @49bab5b L48-L102 (CMIS / sff8436 / sff8636 / sff8472 各規格の passive/active 範囲定義) -->
### page / offset 範囲チェック[^1]

| 規格 | passive cable | active cable |
|------|---------------|---------------|
| **CMIS** | page 0 / offset 0-255 | page 0-255 / offset: page 0 は 0-255、page>0 は 128-255 |
| **sff8436 / sff8636** | 同上 | 同上 |
| **sff8472** | wire `A0h` / offset 0-128 | wire `A0h` (0-255) + `A2h` (0-255) |

- `offset + size` が page 範囲を超えるなら無効
- page>0 で offset<128 は **lower memory** で、CMIS / sff8636 active 系では無効
- active cable の page existence は **完全検証不可**。ユーザがケーブルマニュアル参照で担保[^1]

検証例:

```text
sfputil read-eeprom -p Ethernet0 -n 0 -o 255 -s 2  # invalid (255+2=257)
sfputil read-eeprom -p Ethernet0 -n 1 -o 0   -s 1  # invalid (page 1 では offset>=128)
```

### 実装方針

- `sonic-utilities/sfputil` に 2 サブコマンド追加[^1]
- 内部で page/offset → 全体 offset への変換を規格別に実装し、既存 `sfp.read_eeprom` / `sfp.write_eeprom` を呼ぶ
- vendor 未対応 (`NotImplementedError`) は明示的にハンドル
- それ以外のエラーは read/write 失敗として扱う
- RJ45 ポートは対象外[^1]

## 制限事項

- vendor の platform API 実装が前提。未実装 vendor では `NotImplementedError`[^1]
- active cable の page 存在チェックは完全には行わない
- RJ45 不可
- warm/fast-boot 影響なし、メモリ消費影響なし[^1]

## 干渉する機能

- **`sfputil` 既存サブコマンド**: 同じ CLI ツールに追加される
- **`sonic_platform_base.sfp_base.SfpBase.read_eeprom` / `write_eeprom`**: 下位 API
- **xcvrd / pmon**: EEPROM への書込はモジュール状態に影響するため運用注意

## 参考リンク

- [CONFIG_DB: PORT](../reference/config-db/port.md)
- [CLI: show platform](../reference/cli/show-platform.md)
- [CLI: show interfaces](../reference/cli/show-interfaces.md)
- [Topics: Platform / Port / Optics](../topics/14-platform-port-optics/index.md)
- [Glossary](../reference/glossary.md)
- [Reference 索引](../reference/index.md)

## 引用元

[^1]: [sonic-net/SONiC doc/sfputil/read_write_eeprom_by_page.md @ 49bab5b](https://github.com/sonic-net/SONiC/blob/49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06/doc/sfputil/read_write_eeprom_by_page.md)

<!-- glossary-links-injected: 8ba32e5aa69d -->
