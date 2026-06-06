---
title: 動的ポート add/del 設定と運用（zero-port 起動・安全削除手順）
description: 動的ポート add/del の運用。zero-port 起動から redis-cli でのポート追加例、安全な port 削除の手順、トラブルシューティングを扱う。
area: acl-qos
verification: discrepancy-found
monitor: partially_implemented
last_verified: 2026-05-11
page_kind: split-child
sources:
- repo: sonic-net/SONiC
  path: doc/port-add-del-dynamically/dynamic_port_add_del_hld.md
  ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
  - PORT
  - DEBUG_COUNTER
  - BUFFER_PG
  - VLAN
  - ACL_TABLE
  - VLAN_MEMBER
  cli:
  - config interface
  - config vlan
  - show vlan
  - show acl
  - config acl
  yang:
  - sonic-port
  - sonic-vlan
---

# 動的ポート add/del 設定と運用

このページは [動的ポート add/del（概要ハブ）](enhancements-to-add-or-del-ports-dynamically.md) の派生で、**設定経路と安全な運用手順** に絞る。概念は [enhancements-to-add-or-del-ports-dynamically-concepts.md](enhancements-to-add-or-del-ports-dynamically-concepts.md)、内部実装は [enhancements-to-add-or-del-ports-dynamically-internals.md](enhancements-to-add-or-del-ports-dynamically-internals.md)、[HLD](../reference/glossary.md#term-hld) と実装の乖離は [enhancements-to-add-or-del-ports-dynamically-limitations.md](enhancements-to-add-or-del-ports-dynamically-limitations.md) を参照。

## 1. 関連する CONFIG_DB

| Table | 用途 |
|-------|------|
| `PORT` | 動的 add/del の対象。`admin_status`、`speed`、`mtu` 等 |
| `DEBUG_COUNTER` | port ingress/egress drop counter（動的に作成）|
| `BUFFER_PG` 系 | port 削除前に必ず先に削除 |

## 2. 関連する CLI

特定 CLI は HLD 内で追加されない。`config_db.json` 直接編集または `redis-cli` で `CONFIG_DB.PORT` を操作する想定[^1]。

## 3. 設定例（zero-port 起動からのポート追加）

```bash
# zero-port SKU で起動後、redis 経由でポート追加
redis-cli -n 4 HMSET 'PORT|Ethernet0' \
  speed 100000 admin_status down lanes 0,1,2,3 mtu 9100

# buffer 設定は別途投入（ref counter 経由）
# 最後に admin up
redis-cli -n 4 HSET 'PORT|Ethernet0' admin_status up
```

## 4. 安全な port 削除手順（運用 runbook）

!!! warning "HLD の ref counter は未取り込み"
    HLD は port 削除時の race を「ref counter による orchagent 側の自動拒否」で守ると述べているが、現行 master ではこの拒否ロジックが存在しない（詳細は [enhancements-to-add-or-del-ports-dynamically-limitations.md](enhancements-to-add-or-del-ports-dynamically-limitations.md)）。**運用側で全部やりきる**しかない。

port 削除の安全手順:

```bash
PORT=Ethernet64

# 1) 全依存を列挙
for db in 4 6; do
  sonic-db-cli $([ "$db" = "4" ] && echo CONFIG_DB || echo STATE_DB) keys "*$PORT*"
done

# 2) ACL バインド解除（ports はカンマ区切りリスト。部分一致で `Ethernet8` が
#    `Ethernet80` 等に誤マッチしないよう、要素単位で awk で除去する）
for tbl in $(sonic-db-cli CONFIG_DB keys 'ACL_TABLE|*'); do
  ports=$(sonic-db-cli CONFIG_DB hget "$tbl" ports)
  # 完全一致要素のみを除外し、空要素を残さない
  new=$(echo "$ports" | awk -v p="$PORT" 'BEGIN{FS=",";OFS=","} {
    n=0; for (i=1;i<=NF;i++) if ($i!=p && $i!="") a[++n]=$i;
    s=""; for (i=1;i<=n;i++) s=(i==1?a[i]:s OFS a[i]); print s
  }')
  if [ "$new" != "$ports" ]; then
    if [ -z "$new" ]; then
      # ports が空になる場合は ACL_TABLE エントリ自体を消す（空 ports は orchagent 非許容）
      sonic-db-cli CONFIG_DB del "$tbl"
    else
      sonic-db-cli CONFIG_DB hset "$tbl" ports "$new"
    fi
  fi
done

# 3) VLAN / PortChannel メンバ解除
for vm in $(sonic-db-cli CONFIG_DB keys "VLAN_MEMBER|*|$PORT"); do
  sonic-db-cli CONFIG_DB del "$vm"
done
for pcm in $(sonic-db-cli CONFIG_DB keys "PORTCHANNEL_MEMBER|*|$PORT"); do
  sonic-db-cli CONFIG_DB del "$pcm"
done

# 4) buffer PG / queue / qos-map をすべて消す
for k in $(sonic-db-cli CONFIG_DB keys "BUFFER_PG|$PORT|*" "BUFFER_QUEUE|$PORT|*" "QUEUE|$PORT|*" "PORT_QOS_MAP|$PORT"); do
  sonic-db-cli CONFIG_DB del "$k"
done

# 5) admin down → 削除
sudo config interface shutdown $PORT
sonic-db-cli CONFIG_DB del "PORT|$PORT"

# 6) orchagent ログで SAI_STATUS_OBJECT_IN_USE が出ていないか確認
sudo grep -i "SAI_STATUS_OBJECT_IN_USE\|$PORT" /var/log/syslog | tail -20
```

自動化する場合、削除前に `redis-cli -n 4 keys '*|<port>*'` で残依存を列挙して 0 件になることを確認する pre-check を入れる。

## 4.1 運用フェーズ別 実装境界

各運用フェーズで、master で実装済みの自動化と未実装で運用側がカバーする必要のある箇所を分けると次のとおり[^1]:

| Phase | 実装済 (master で動く) | 未実装 (HLD 提案のみ・運用側で代替) |
|-------|----------------------|----------------------------------|
| zero-port 起動 | ✅ port=0 で boot 完了 | — |
| redis-cli / config による port 追加 | ✅ [portsorch](../reference/glossary.md#term-portsorch) が SAI port を作成 | — |
| `admin_status` 切替 | ✅ 既存パスで動作 | — |
| port 削除前の依存検出 | — | ❌ ref counter 自動拒否は未取り込み（運用側で `keys '*|<port>*'` pre-check）|
| port 削除時の ACL バインド解除 | — | ❌ 自動解除なし（運用側で手順 2 を実行）|
| port 削除時の VLAN / [PortChannel](../reference/glossary.md#term-portchannel) メンバ解除 | — | ❌ 自動解除なし（運用側で手順 3 を実行）|
| port 削除時の buffer PG / queue / qos-map 削除 | — | ❌ 自動削除なし（運用側で手順 4 を実行）|
| port 削除本体 (`config_db` から `PORT` を消す) | ✅ portsorch / [portsyncd](../reference/glossary.md#term-portsyncd) が SAI port + host i/f を削除 | — |
| port restore | — | ❌ HLD 提案のみ未実装、削除後の再構築は手動で再投入 |

`✅` フェーズはユーザが触らずに動作するが、`❌` フェーズは現行 master では自動化されておらず、後述の `redis-cli` / `sonic-db-cli` 手順を運用側で踏む必要がある[^1]。

## 5. トラブルシューティング

- ポート追加に時間がかかる: `PortConfigDone` / `PortInitDone` フラグの状態を確認。[orchagent](../reference/glossary.md#term-orchagent) 連動が止まっている可能性。
- ポート削除で [SAI](../reference/glossary.md#term-sai) エラーが大量: 依存（buffer / [ACL](../reference/glossary.md#term-acl) / [VLAN](../reference/glossary.md#term-vlan)）が残っている。HLD の ref counter 機構が動作していない可能性[^1]。
- [LLDP](../reference/glossary.md#term-lldp) が古いポート情報を保持し続ける: `lldpmgrd` の `pending_cmds` を確認、改修取り込み状況を確認[^1]。
- zero-port 起動で boot loop: SAI profile / hwsku.json / platform.json が port エントリを完全に排除しているか確認。

### コマンド例: ポート動的追加/削除確認

下記コマンドを順に実行することで、関連する [CONFIG_DB](../reference/glossary.md#term-config_db) / APP_DB / [STATE_DB](../reference/glossary.md#term-state_db) のエントリと、
CLI 表示・syslog の整合を一通り突き合わせ確認できる。

```bash
# CONFIG_DB の PORT エントリ追加・削除と orchagent 反映状況
redis-cli -n 4 keys 'PORT|Ethernet*' | sort | head
show interfaces status | head
# 動的変更時の orchagent ログ
sudo grep -E 'portsorch|PortConfigDone|PortInitDone' /var/log/syslog | tail -50
```


## 実装との乖離

`monitor: partially_implemented` — 部分実装 — HLD の中核は実装済みだが、フィールド / API / 制約のいくつかが上流に未取り込み、または挙動が緩和されている。 本ページは split-child のため、差分の主要根拠 / 影響 / 回避策は親ページ [動的ポート add/del 設定と運用 親ページ](enhancements-to-add-or-del-ports-dynamically.md) の同セクション（`## 実装との乖離` または `!!! diff` ブロック）を参照のこと。

## 引用元

[^1]: `sonic-net/SONiC` `doc/port-add-del-dynamically/dynamic_port_add_del_hld.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- glossary-links-injected: 889740d66e5f -->
