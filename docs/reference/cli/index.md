---
title: CLI リファレンス
area: reference
verification: meta
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-utilities
    path: setup.py
    ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
related:
  config_db: []
  cli: []
  yang: []
---

# CLI リファレンス

SONiC の運用 CLI は `sonic-utilities` リポジトリの click ベースのコマンドツリーで定義される。本リファレンスは、master の固定 commit (`39732bc`) を一次情報として、コマンド単位ではなく **「最初のサブグループ単位」** でページを区切って整理する。

## トップレベルツリー

`sonic-utilities` は複数の click エントリポイントを `setup.py` で同時にインストールする[^1]。本ページではそのうち主要な 3 系統 + パッケージ管理系を扱う。

```
config           # /usr/local/bin/config (= config/main.py:config)
show             # /usr/local/bin/show   (= show/main.py:cli)
clear            # /usr/local/bin/sonic-clear (= clear/main.py:cli)
sonic-installer  # SONiC イメージ install / sonic_installer/main.py
sonic-package-manager
                 # コンテナ化機能の追加 / sonic_package_manager/main.py
```

このうち `config` `show` `clear` の 3 つは数百のサブコマンドを束ねており、それぞれ `<group>/main.py` から動的に register される構造を取っている。**一部のサブグループは別ファイルに切り出されたあと `<group>.add_command(<subgroup>)` の形で登録される**ため、cli.json の機械抽出だけでは全コマンドを補足できない。本リファレンスは個別ページで該当ファイルを直接参照する。

## ページ粒度ルール

| 単位 | 例 | 1 ページに収める範囲 |
|------|----|---------------------|
| **`config <subgroup>`** | `config bgp`, `config interface`, `config vlan` | そのサブグループ配下のコマンド・引数・オプション全て |
| **`show <subgroup>`** | `show interfaces`, `show ip` | 同上 |
| **`clear <subgroup>` または `clear` 全体** | `clear counters`, `clear arp` | 規模が小さいので `clear` は 1 ページに集約 |

各ページが含む内容:

- サブグループの **概要**（何を制御するか / どのデーモンを操作するか）
- **コマンド一覧表**（コマンド + 用途）
- 各コマンドの **用法 / 引数 / オプション / 動作**
- 関連する **CONFIG_DB テーブル**（コマンド実装中の DB 書き込みから抽出）
- 一次情報の脚注

## 主要サブグループ index（順次追加予定）

サブグループ単位の個別ページは `docs/reference/cli/<group>-<subgroup>.md` の slug で並ぶ。awesome-pages プラグインがファイル名順で自動的に nav に組み込むため、新規ページを追加してもこの index を都度更新する必要はない。

### config 系

- `config bgp` ... BGP shutdown / startup / remove / autonomous-system
- `config interface` ... 物理ポート・SubInterface のステート / 速度 / FEC / IP / VRF
- `config vlan` ... VLAN 作成、メンバ追加、DHCP relay
- `config portchannel` ... LAG (LACP) 作成・メンバ追加
- `config acl` ... ACL テーブル更新・ルール削除
- `config vxlan` ... VTEP / EVPN / VLAN-VNI マッピング

### show 系

- `show interfaces` ... インターフェイス状態・カウンタ・transceiver 等
- `show ip` ... IPv4 ルーティング情報（BGP / route / interfaces）
- `show vlan` ... VLAN ブリッジ表示
- `show platform` ... プラットフォーム情報・PSU・FAN・温度
- `show acl` ... ACL テーブル・ルール表示

### clear 系

- `clear` ... ARP / NDP / counters / FDB / BGP セッション等

## 全体的な仕様メモ

### click の構造

`config/main.py` 末尾には次の様な動的 add_command が並ぶ。これにより、本体 `main.py` には書かれていないサブグループが実行時に挿入される。

```python
# 例: config/main.py 末尾
from . import vlan, vxlan, mclag, ...
config.add_command(vlan.vlan)
config.add_command(vxlan.vxlan)
```

このため、cli.json (`meta/index/cli.json`) には `config bgp` がトップ要素しか出てこないが、実装は `config/bgp_cli.py` 等に存在する。本リファレンスではこの分割ファイル側も `sources` に記録する。

### `--namespace` / `-n` オプション (multi-ASIC)

`config` / `show` の多くのコマンドは multi-ASIC SONiC で動作する場合 `--namespace asic0` 等を受け取る。各ページの「オプション」節で個別に明示しないコマンドでも、SONiC が multi-ASIC で動いているときは `-n` が常に有効である[^2]。

### CONFIG_DB との対応

`config` 系コマンドは ConfigDBConnector もしくは `validated_config_db_connector` 経由で `CONFIG_DB` の特定テーブルを操作する。各コマンド説明に「`<TABLE>` テーブルの `<field>` を書き換える」を明示する。

## 引用元

- `setup.py` の `entry_points` 定義（`config = config.main:config` 等）

[^1]: `sonic-utilities` の `setup.py` に `entry_points` が定義されており、`config` / `show` / `sonic-clear` / `sonic-installer` / `sonic-package-manager` が同時インストールされる。<https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/setup.py>

[^2]: `config/main.py` の `multi_asic.is_multi_asic()` 分岐を参照。<https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/config/main.py>

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: リファレンス横断索引](../../topics/22-reference-index/index.md)
