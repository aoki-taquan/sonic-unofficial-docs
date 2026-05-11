---
title: L2 Forwarding 強化（FDB flush / aging / static MAC / VLAN range）
area: switching
verification: discrepancy-found
monitor: partially_implemented
last_verified: 2026-05-09
sources:
  - repo: sonic-net/SONiC
    path: doc/layer2-forwarding-enhancements/SONiC Layer 2 Forwarding Enhancements HLD.md
    ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
    - FDB
    - SWITCH
  cli:
    - sonic-clear fdb
    - config mac
    - config vlan range
    - config vlan member range
    - show mac
  yang: []
---

!!! warning "裏取りステータス: discrepancy-found"
    orchagent 側（`fdborch.cpp` / `switchorch.cpp`）は HLD のとおり実装済み。一方で **`config mac` / `config vlan range` CLI は sonic-utilities 現行 master に存在しない**。詳細は本文末尾の「実装との乖離」を参照（verified at: 2026-05-09）。

# L2 Forwarding 強化

## なぜ拡張するのか

SONiC 初期の L2 機能に欠けていた 6 項目を一括導入する HLD[^1]:

1. **per-port / per-VLAN / per-(port,VLAN) FDB flush** （port down / VLAN 抜去 / STP topo change 時）
2. **MAC move event** の SAI / orchagent 対応
3. **FDB aging time の CLI 設定**（既定 600 秒、0〜1,000,000 秒）
4. **Static FDB の CLI 設定**
5. **`sonic-clear fdb` 拡張**（port / VLAN 指定）
6. **VLAN range CLI**（4094 VLAN を一括操作）

warm boot 既存挙動は維持[^1]。

## FDB Flush 仕様

```mermaid
flowchart TD
    EV{event} -->|port oper down| F1[per-port flush<br/>dynamic のみ]
    EV -->|port を VLAN 抜去| F2[per-(port,VLAN)<br/>static + dynamic<br/>※CONFIG_DB の static は残す]
    EV -->|STP topo change| F3[per-port or<br/>per-(port,VLAN)<br/>dynamic のみ]
    EV -->|portchannel down| F4[per-portchannel<br/>dynamic のみ]
    F1 & F2 & F3 & F4 --> SDB[STATE_DB / ASIC_DB / HW / m_entries]
```

port が VLAN メンバでない / VLAN から外れた static は orchagent の **「saved FDB」** に保持され、port が VLAN に再追加された時に再 program される。`FdbOrch` のデータ構造は `set<(MAC, bv_id)>` → `map<(MAC, bv_id), fdb_type>` に変更され、type 情報をキャッシュ化。

## CONFIG_DB / CLI（HLD 提案）

```text
FDB|<vlan>|<mac>    port=<port>
SWITCH_TABLE        fdb_aging_time=<sec>
```

| CLI | 用途 |
|-----|------|
| `config mac aging_time <0-1000000>` | aging 秒（0=無効、既定 600） |
| `config mac add <mac> <vlan> <port>` / `del <mac> <vlan>` | static FDB |
| `sonic-clear fdb [all\|port <p>\|vlan <v>\|port <p> vlan <v>]` | dynamic FDB クリア |
| `config vlan range add\|del <first> <last> [-w]` | VLAN bulk |
| `config vlan member range add\|del <first> <last> <port> [-w]` | VLAN member bulk |

VLAN range は **2 値のみ**（リスト形式不可）、redis pipeline で一括 SET / DEL。`-w` はバリデーション警告。

### 設定例（HLD どおりの記法）

```bash
config mac aging_time 60
config mac add 00:11:22:33:44:55 100 Ethernet0
config vlan range add 100 199 -w
config vlan member range add 100 199 Ethernet0 -w
sonic-clear fdb port Ethernet0
```

## 制限事項

- HLD は **2019 年改訂** で命名揺れあり（特に `SWITCH_TABLE` / `FDB` のキー区切り）
- VLAN range は 2 値のみ、複数レンジ合成不可
- `sonic-clear fdb` は dynamic のみ。static は CLI で個別削除
- MAC move event は **SAI 側サポート必須**
- VLAN range bulk 中の途中失敗 rollback は HLD 上明示なし

## 干渉する機能

`FdbOrch`（主体）/ `SwitchOrch`（aging）/ `VlanMgr` / `VlanOrch` / STP / teamd・Portchannel（down 時 flush）/ warm boot / sonic-utilities

## 実装との乖離

実コード裏取りで判明（verified at: 2026-05-09）:

### 1. `config mac` / `config vlan range` CLI 未取り込み

- **HLD**: `config mac aging_time` / `config mac add|del` / `config vlan range` / `config vlan member range` を `sonic-utilities` に追加
- **実態**: `sonic-utilities/config/main.py` には該当 click group が存在しない。`show mac aging-time` (`show/main.py`) のみ実装済み
- **影響**: HLD の CLI 例をそのまま打つと "no such command" で失敗
- **回避策**:
    - aging: `sonic-db-cli CONFIG_DB HSET 'SWITCH|switch' fdb_aging_time 300`（`switchorch.cpp:1674-1686` で `SAI_SWITCH_ATTR_FDB_AGING_TIME` に反映）
    - static MAC: `sonic-db-cli CONFIG_DB HSET 'FDB|Vlan100|00-11-22-33-44-55' port Ethernet0`
    - VLAN bulk: `for i in $(seq 100 199); do config vlan add $i; done` または `config_db.json` 直編集
    - FDB クリア: `sonic-clear fdb [all|port X]` は実装済み

### 2. orch 側は HLD 一致

- **MAC move**: `fdborch.cpp:91-138`、`SAI_FDB_ENTRY_ATTR_ALLOW_MAC_MOVE` を `:507,583` で設定
- **saved FDB**: `fdborch.cpp:459` で `saved_fdb_entries[port].push_back(...)`、`:1254-1271` で VLAN member 追加時に再投入
- **flush API**: `fdborch.cpp:1079-1090` `FdbOrch::flushFDBEntries(bridge_port_oid, vlan_oid)` がコア。`:985`/`:1006`/`:1038,1248` で per-port / per-VLAN / per-(port,VLAN) として呼び出し
- **aging_time**: `switchorch.cpp:49,664,1674-1686` で `SAI_SWITCH_ATTR_FDB_AGING_TIME`

### 3. キー区切り揺れ

HLD 図中の `FDB_TABLE:<vlan>:<mac>` と現行 schema の `FDB_TABLE:<vlan>|<mac>` が混在。redis-cli の pattern を実キーで確認すること（バージョンによって揺らぐ）。

## トラブルシューティング

```bash
redis-cli -n 4 HGETALL 'SWITCH|switch'                 # aging_time 確認
redis-cli -n 0 KEYS 'FDB_TABLE:*' | head
redis-cli -n 6 KEYS 'FDB_TABLE|*' | head               # STATE_DB
saidump | grep -A2 SAI_FDB
```

port が VLAN メンバでない間に投入した static は orchagent ログで saved に積まれているか確認。

## 関連 Topics

- [06-l2-vlan-lag/operations](../topics/06-l2-vlan-lag/operations.md): FDB / VLAN 運用
- [06-l2-vlan-lag/internals](../topics/06-l2-vlan-lag/internals.md): FdbOrch 内部
- [11-reboot/operations](../topics/11-reboot/operations.md): warm boot と FDB

## 引用元

[^1]: `sonic-net/SONiC` `doc/layer2-forwarding-enhancements/SONiC Layer 2 Forwarding Enhancements HLD.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`
