# nat-static — Phase F 副次 DB 書込スキャン結果

## スキャン対象

- `sonic-swss/cfgmgr/natmgr.cpp` — `addStaticSingleNatEntry()` L1992-2069, `removeStaticSingleNatEntry()` L2650-2719, `addStaticTwiceNatEntry()` L2072-2250, `removeStaticTwiceNatEntry()` L2736-2875, `addDnatPoolEntry()` L1502-1524, `removeDnatPoolEntry()` L1525-1548, `addConntrackStaticSingleNatEntry()` L457-489
- `sonic-swss/orchagent/natorch.cpp` — `addHwNatEntry()` L789-796, `removeHwNatEntry()` L951, `updateNatCounters()` L4049-4061, `updateStaticNatCounters()` L4481-4490

## 副次 DB 書込み一覧

| 副次先 | テーブル / キー | 書込フィールド | 発火条件 | evidence |
|--------|----------------|--------------|----------|---------|
| APPL_DB | `NAT_TABLE\|<global_ip>` (DNAT) + `NAT_TABLE\|<local_ip>` (SNAT) | `translated_ip`, `nat_type`, `entry_type=static` | `addStaticSingleNatEntry()` 成功時 (NAT enabled + L3 interface up) | `natmgr.cpp:2052-2053` |
| APPL_DB | `NAT_DNAT_POOL_TABLE\|<dnat_ip>` | なし (NULL:NULL フラグ) | DNAT エントリ追加時に `addDnatPoolEntry()` を呼ぶ。参照カウンタ管理で最終参照削除時のみ DEL | `natmgr.cpp:2031-2033, 1502-1524` |
| kernel conntrack | 仮 conntrack エントリ (UDP, timeout=432000) | — | `addConntrackStaticSingleNatEntry()` / `addConntrackStaticTwiceNatEntry()` が `/usr/sbin/conntrack -I` を実行 | `natmgr.cpp:2058, 457-489, 492-514` |
| kernel iptables | `nat` テーブル PREROUTING/POSTROUTING ルール | — | `setStaticNatIptablesRules(INSERT, ...)` — iptables コマンドを直接実行 | `natmgr.cpp:2060-2068, 956-1000` |
| COUNTERS_DB | `COUNTERS_NAT\|<global_ip>` | `NAT_TRANSLATIONS_PKTS`, `NAT_TRANSLATIONS_BYTES` (0 初期化) | NatOrch が `addHwNatEntry()` / `removeHwNatEntry()` 完了直後に `updateNatCounters(ip, 0, 0)` を呼ぶ | `natorch.cpp:789, 951, 4049-4061` |
| COUNTERS_DB | `COUNTERS_GLOBAL_NAT\|Values` | `STATIC_NAT_ENTRIES` (int) | NatOrch が static NAT エントリ追加/削除後に `updateStaticNatCounters(count)` を呼ぶ | `natorch.cpp:796, 951, 4481-4490` |

## 検出されなかった副次書込み

- STATE_DB: 書込みなし
- FLEX_COUNTER_DB: 書込みなし
- LOGLEVEL_DB: 書込みなし
- CONFIG_DB への書き戻し: なし

## 備考

- APPL_DB への NAT_TABLE 書込みは「副次」兼「主作用」の二重性がある。CONFIG_DB STATIC_NAT の主な目的が APPL_DB NAT_TABLE を経由して SAI に降ろすことであるため、NAT_DNAT_POOL_TABLE と kernel conntrack / iptables が「隠れた副次作用」として重要。
- `addDnatPoolEntry()` は参照カウンタ (`m_natDnatPoolInfo`) を管理し、複数の STATIC_NAT / STATIC_NAPT / NAT_BINDINGS から同一 DNAT IP を参照している場合は refcount が 0 になるまで DEL しない。
- iptables / conntrack 書込みは `swss::exec()` による OS コマンド直接実行であり、Redis DB 経由ではない。
