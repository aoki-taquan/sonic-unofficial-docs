# DPU — Phase F: 副作用 (side-effects) 調査メモ

対象ドキュメント: `docs/reference/config-db/dpu.md`
調査日: 2026-05-17
根拠ソース:
- `sonic-swss/orchagent/dash/dashenifwdorch.cpp`
- `sonic-swss/orchagent/dash/dashenifwdinfo.cpp`
- `sonic-swss/orchagent/dash/dashenifwdorch.h`
- `sonic-host-services/scripts/caclmgrd`
- `sonic-gnmi/pkg/interceptors/dpuproxy/resolver.go`

---

## 目的

`DPU` テーブルのエントリが CONFIG_DB に SET / DEL されたとき、各コンシューマが
**他テーブル・OS・ハードウェアに対して行う副作用**を網羅する。
"副作用" = CONFIG_DB の変化に応じて、当該コンポーネントが別の DB テーブル / iptables /
SAI / カーネル状態 などへ書き込み・削除・実行する一連の処理。

---

## 1. orchagent (DashEniFwdOrch / DpuRegistry) の副作用

### 1-1. DpuRegistry への登録（SET 時・起動時）

`DpuRegistry::populate()` が `DPU` テーブルを一括読み込みし、
内部マップ `dpus_name_map_` に DPU 名 → `DpuData { type, pa_v4, npu_v4 }` を格納する。

```cpp
// dashenifwdorch.cpp:255-258
DpuData data;
data.type = dpu_type_t::LOCAL;
data.pa_v4 = dpu_request_.getAttrIP(DashEniFwd::PA_V4);
dpus_name_map_.insert({key, data});
```

- **副作用の範囲**: orchagent プロセスのヒープメモリのみ（DB 書き込みなし）。
- `state = "down"` のエントリは **DpuRegistry に挿入されない**（INFO ログのみ）。
- `populate()` は起動時の一括 `hgetall` で実行され、**runtime の DPU テーブル更新は反映されない**。
  orchagent 再起動なしに DPU を追加・修正しても DpuRegistry には届かない。

### 1-2. APPL_DB への ACL テーブル / ACL ルール書き込み（ENI 追加時）

`DPU` テーブル読み込み後、`ENI` テーブルが SET されると `DashEniFwdOrch::addOperation()` が起動し、
`EniFwdCtxBase::createAclRule()` / `addAclTable()` 経由で APPL_DB に以下を書き込む:

| APPL_DB テーブル | キー | 書き込みトリガ | 証跡 |
|-----------------|------|--------------|------|
| `ACL_TABLE_TYPE` | `ENI_REDIRECT` | 最初の ENI ACL ルール生成時（`acl_rule_count_ == 0`）に自動生成 | `dashenifwdorch.cpp:576-580, 603-625` |
| `ACL_TABLE` | `ENI` | ACL テーブルタイプ直後に生成 | `dashenifwdorch.cpp:635-643` |
| `ACL_RULE` | `ENI:<vnet_name>:<eni_mac>` または `ENI:<vnet_name>:<eni_mac>_TERM` | ENI エントリ追加/更新・ネクストホップ解決時 | `dashenifwdinfo.cpp:193-206` |

**DPU テーブルのどのフィールドが ACL 内容に影響するか**:

| DPU フィールド | APPL_DB への影響 |
|----------------|----------------|
| `pa_ipv4` | LOCAL DPU の場合: `ACL_RULE.redirect_action` の宛先 IP として使用 |
| `state = "down"` | DpuRegistry に未登録 → ENI の ACL ルールが生成されない（または既存ルールが残留） |

### 1-3. ACL テーブル削除（ENI 全削除時）

最後の ENI ACL ルール削除時（`acl_rule_count_ == 0`）に `deleteAclTable()` が
`ACL_TABLE` と `ACL_TABLE_TYPE` の両エントリを APPL_DB から DEL する。

```cpp
// dashenifwdorch.cpp:646-650
void EniFwdCtxBase::deleteAclTable()
{
    acl_table_->del(DashEniFwd::TABLE);
    acl_table_type_->del(DashEniFwd::TABLE_TYPE);
}
```

### 1-4. 近傍解決要求（Neighbor Resolution）の副作用

LOCAL DPU の場合、ENI のネクストホップ解決に `NeighOrch::resolveNeighbor()` を呼び出す:

```cpp
// dashenifwdinfo.cpp:30
ctx->resolveNeighbor(nh);  // NeighOrch に ARP 解決要求
```

これにより:
- `NeighOrch` が ARP リクエストを送出（カーネル / SAI への副作用）
- ARP が解決されると `update()` コールバック経由で ENI ACL ルールが APPL_DB に書かれる

この副作用は ENI テーブルのトリガが起点だが、**DPU の `pa_ipv4` が近傍解決の対象 IP** になる。

---

## 2. caclmgrd の副作用

### 2-1. iptables / ip6tables ルール追加（SET 時）

`DPU` テーブルへの SET イベントを `SubscriberStateTable` で受信し、`swbus_port` フィールドが
存在する場合に以下の iptables / ip6tables ルールを挿入する:

```python
# caclmgrd:1076-1079
iptables_cmds.append([..., 'iptables', '-I', 'INPUT', '2', '-p', 'tcp', '--dport', str(port), '-j', 'ACCEPT'])
iptables_cmds.append([..., 'ip6tables', '-I', 'INPUT', '2', '-p', 'tcp', '--dport', str(port), '-j', 'ACCEPT'])
```

- ルールは `INPUT` チェーンの **位置 2** に挿入（優先度 2）
- TCP のみ対象（UDP は含まない）
- swbus_port 単一ポートの許可ルール

### 2-2. iptables / ip6tables ルール削除（DEL 時または swbus_port 変更時）

```python
# caclmgrd:1063-1067
iptables_cmds.append([..., 'iptables', '-D', 'INPUT', '-p', 'tcp', '--dport', str(port), '-j', 'ACCEPT'])
iptables_cmds.append([..., 'ip6tables', '-D', 'INPUT', '-p', 'tcp', '--dport', str(port), '-j', 'ACCEPT'])
```

- `DPU` エントリ DEL → 対応する `swbus_port` ルールを削除
- `swbus_port` の値が変化した SET → 旧ルール削除 → 新ルール追加

### 2-3. 副作用のガード条件

| 条件 | 挙動 |
|------|------|
| `"dash-ha"` が FEATURE テーブルに不在 | `update_dash_ha_rules()` を呼ばない（iptables 副作用なし） |
| `swbus_port` フィールド欠如 | iptables 操作なし。INFO ログのみ出力 |
| `swbus_port` 値に変化なし | iptables 操作なし（早期 return） |

### 2-4. 内部 dashHaPortMap の更新

caclmgrd は `dashHaPortMap[dpu_name] = port` を更新してエントリを管理する。
これはプロセスのヒープメモリのみで、DB には書き込まれない。

---

## 3. sonic-gnmi DPU proxy の副作用

`sonic-gnmi` の DPU proxy (`dpuproxy/resolver.go`) は CONFIG_DB `DPU` テーブルを
**読み取るのみ**で、直接の副作用（他 DB テーブルへの書き込みや OS 変更）はない。

ただし、返却した接続先情報に基づいて上位の gNMI ハンドラが DPU に対して
gRPC 接続を確立するため、**間接的な DPU gNMI セッション確立**が副作用として発生する。

---

## 4. 副作用サマリ表

| # | トリガ操作 | コンポーネント | 副作用先 | 副作用内容 | 証跡 |
|---|------------|--------------|---------|-----------|------|
| 1 | DPU SET (起動時 populate) | orchagent `DpuRegistry` | ヒープ (`dpus_name_map_`) | DPU 名 → `{ type=LOCAL, pa_v4 }` を内部マップに登録 | `dashenifwdorch.cpp:255-258` |
| 2 | ENI SET（初回） | orchagent `EniFwdCtxBase` | APPL_DB `ACL_TABLE_TYPE\|ENI_REDIRECT` | ACL テーブルタイプを作成 | `dashenifwdorch.cpp:603-625` |
| 3 | ENI SET（初回） | orchagent `EniFwdCtxBase` | APPL_DB `ACL_TABLE\|ENI` | ACL テーブルを作成（バインドポート = 外部物理/LAG ポート） | `dashenifwdorch.cpp:635-643` |
| 4 | ENI SET（ネクストホップ解決後） | orchagent `EniAclRule` | APPL_DB `ACL_RULE\|ENI:<vnet>:<mac>` | ACL ルールを set（redirect 先 = DPU `pa_ipv4`） | `dashenifwdinfo.cpp:193-206` |
| 5 | ENI SET（LOCAL DPU 未解決時） | orchagent `LocalEniNH` | `NeighOrch` → ARP/SAI | ARP 解決要求を発行。ARP 解決時に ACL ルール書き込み | `dashenifwdinfo.cpp:30` |
| 6 | ENI DEL（最後のルール） | orchagent `EniFwdCtxBase` | APPL_DB `ACL_TABLE\|ENI`, `ACL_TABLE_TYPE\|ENI_REDIRECT` | ACL テーブル・テーブルタイプを削除 | `dashenifwdorch.cpp:646-650` |
| 7 | DPU SET (`swbus_port` あり, `dash-ha` feature 有効) | caclmgrd | Linux iptables / ip6tables | `INPUT` チェーン位置 2 に `tcp dport <swbus_port> ACCEPT` を挿入 | `caclmgrd:1073-1079` |
| 8 | DPU DEL（`swbus_port` 既登録） | caclmgrd | Linux iptables / ip6tables | 対応 `swbus_port` の ACCEPT ルールを削除 | `caclmgrd:1083-1090` |
| 9 | DPU SET（`swbus_port` 変更） | caclmgrd | Linux iptables / ip6tables | 旧ポートルール削除 → 新ポートルール挿入 | `caclmgrd:1104-1108` |

---

## 5. side-effects ブロック（最終形）

以下を `docs/reference/config-db/dpu.md` の `<!-- constants -->...<!-- /constants -->` ブロックの直後に挿入する。

```markdown
<!-- side-effects -->
## 副作用 (Phase F)

> 調査証跡: `meta/_intermediate/cdb-flow/dpu-side-effects.md`

`DPU` テーブルへの SET / DEL が発生したとき、各コンシューマが他テーブル・OS・ハードウェアに
対して行う副作用を示す。

| # | トリガ操作 | コンポーネント | 副作用先 | 副作用内容 | 証跡 |
|---|------------|--------------|---------|-----------|------|
| 1 | 起動時 `DPU` SET (populate) | orchagent `DpuRegistry` | ヒープ (`dpus_name_map_`) | DPU 名 → `{ type=LOCAL, pa_v4 }` を内部マップに登録。runtime 変更は反映されない（orchagent 再起動が必要） | `dashenifwdorch.cpp:255-258` |
| 2 | `ENI` SET（初回）→ DPU 情報解決 | orchagent `EniFwdCtxBase` | APPL_DB `ACL_TABLE_TYPE\|ENI_REDIRECT` | ACL テーブルタイプを作成（matches: `dst_ip`, `inner_dst_mac`, `tunnel_term`） | `dashenifwdorch.cpp:603-625` |
| 3 | `ENI` SET（初回）→ DPU 情報解決 | orchagent `EniFwdCtxBase` | APPL_DB `ACL_TABLE\|ENI` | 外部物理/LAG ポートをバインドポートとして ACL テーブルを作成 | `dashenifwdorch.cpp:635-643` |
| 4 | `ENI` SET（ネクストホップ解決後）| orchagent `EniAclRule` | APPL_DB `ACL_RULE\|ENI:<vnet>:<mac>` | `redirect_action = DPU.pa_ipv4` の ACL ルールを set | `dashenifwdinfo.cpp:193-206` |
| 5 | `ENI` SET（LOCAL DPU 未解決時） | orchagent `LocalEniNH` | `NeighOrch` → ARP / SAI | DPU `pa_ipv4` に対する ARP 解決要求を発行。ARP 解決後コールバックで ACL ルール書き込み | `dashenifwdinfo.cpp:18-31` |
| 6 | `ENI` DEL（最後のルール削除） | orchagent `EniFwdCtxBase` | APPL_DB `ACL_TABLE\|ENI`, `ACL_TABLE_TYPE\|ENI_REDIRECT` | ACL テーブル・テーブルタイプを APPL_DB から削除 | `dashenifwdorch.cpp:646-650` |
| 7 | `DPU` SET（`swbus_port` あり、`dash-ha` feature 有効） | caclmgrd | Linux iptables / ip6tables | `INPUT` チェーン位置 2 に `tcp dport <swbus_port> ACCEPT` を挿入（IPv4 + IPv6） | `caclmgrd:1073-1079` |
| 8 | `DPU` DEL（`swbus_port` 既登録） | caclmgrd | Linux iptables / ip6tables | 対応 `swbus_port` の ACCEPT ルールを削除 | `caclmgrd:1083-1090` |
| 9 | `DPU` SET（`swbus_port` 値変更） | caclmgrd | Linux iptables / ip6tables | 旧ポートルール削除 → 新ポートルール挿入（アトミックではない） | `caclmgrd:1104-1108` |

### ガード条件

- **副作用 #7-#9**: `FEATURE` テーブルに `"dash-ha"` キーが存在する場合のみ実行される (`caclmgrd:1265`)。
  `dash-ha` feature が無効のとき `DPU` テーブルへの変化は iptables に影響しない。
- **副作用 #7**: `swbus_port` フィールドが欠如した SET は iptables 操作なし（INFO ログのみ出力）。
- **副作用 #1-#6**: `DPU.state = "down"` のエントリは DpuRegistry に未登録となり、
  ENI フォワーディングの ACL ルール生成に使用されない。

### runtime 変更の非対称性

orchagent は `DPU` テーブルを起動時に一括読み込み（`DpuRegistry::populate()`）し、
**runtime の DPU SET/DEL イベントは orchagent には届かない**（副作用 #1）。
一方 caclmgrd は `SubscriberStateTable` で常時購読しており runtime 変更を即時反映する（副作用 #7-#9）。

DPU の設定変更（`state` / `pa_ipv4` 等）を orchagent に反映させるには
`swss` コンテナの再起動が必要。`swbus_port` 変更は orchagent 不要、caclmgrd が即時対応する。
<!-- /side-effects -->
```
