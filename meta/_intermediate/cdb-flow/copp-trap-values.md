# COPP_TRAP 値依存挙動分析

## enum フィールド
1. `always_enabled`: boolean (`true` / `false`)

## 値依存挙動

### always_enabled
- `true`: `coppmgr` (coppmgr.cpp:90) が feature state と無関係に trap を APPL_DB に書き込む。
  ユーザが `config feature state <feature> disabled` を実行しても当該 trap はアクティブのまま。
  BGP / LLDP など必須プロトコルの trap がこれに該当。
- `false` / 未設定: `coppmgr` が feature の有効/無効を確認し、feature が enabled のときのみ trap をインストール。
  feature が disabled になると trap が削除される。

### trap_ids (string enum 相当)
- `trap_ids` の値は SAI hostif trap type (`bgp`, `bgpv6`, `lldp`, `arp_req`, `arp_resp`, `lacp`, `dhcp`, `ip2me` 等)。
- 存在しない / スペルミスの trap_id は `CoppOrch` が `trap_id_map.at()` で例外を投げ、当該エントリ全体が無視される（silent failure）。
- プラットフォーム SAI が対応しない trap_id は `STATE_DB.COPP_TRAP_CAPABILITY_TABLE` の supported=false として記録される。

## ソース
- `sonic-swss/cfgmgr/coppmgr.cpp:85-90, 164, 182, 365, 620`
- `sonic-swss/orchagent/copporch.cpp:55-103`
