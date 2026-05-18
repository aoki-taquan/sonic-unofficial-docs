---
title: STATE_DB LAG_TABLE (PortChannel 状態)
description: "STATE_DB LAG_TABLE — PortChannel (LAG) のランタイム状態を STATE_DB に保持するテーブル。teamsyncd が Linux netlink NEWLINK イベントを受信したときに書き込み、tlm_teamd が teamdctl JSON dump を解析して追記する。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-15
sources:
  - repo: sonic-net/sonic-swss
    path: teamsyncd/teamsync.cpp
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
  - repo: sonic-net/sonic-swss
    path: tlm_teamd/values_store.h
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
related:
  config_db:
    - PORTCHANNEL
    - PORTCHANNEL_MEMBER
  cli:
    - show interfaces portchannel
  _no_related_yang: true
---

# STATE_DB LAG_TABLE (PortChannel 状態)

## 概要

PortChannel ([LAG](../../reference/glossary.md#term-lag)) のランタイム状態を STATE_DB に保持するテーブル[^1]。`sonic-swss` の `teamsyncd` が Linux カーネルの netlink NEWLINK イベントを受信したときに主フィールドを書き込み、`tlm_teamd` が `teamdctl` の JSON dump を定期的に解析して補助フィールドを追記する。このテーブルは観測専用（書き込みは teamsyncd / tlm_teamd のみ）であり、`intfmgrd`・`vlanmgr`・`nbrmgrd`・`stpmgrd` が LAG の準備完了チェックに参照する。

CONFIG_DB の [`PORTCHANNEL`](portchannel.md) テーブルとは別テーブルであり、こちらは設定ではなく実行時状態を格納する。

## key 構造

```text
LAG_TABLE|<lag_name>
```

- `<lag_name>`: LAG インタフェース名。形式は `PortChannel<0-9999>`（例: `PortChannel0001`）
- テーブル名定数: `STATE_LAG_TABLE_NAME = "LAG_TABLE"` (`sonic-swss-common/common/schema.h:422`)

## フィールド

### teamsyncd 書き込みフィールド

`TeamSync::addLag()` (`teamsync.cpp:L146-176`) が Linux netlink から取得した実測値で書き込む。

| フィールド | 型 | 初期値 | 説明 |
|-----------|----|-------|------|
| `admin_status` | enum string | カーネル実測値 | 管理状態。`"up"` (IFF_UP) または `"down"` |
| `oper_status` | enum string | カーネル実測値 | 運用状態。`"up"` (IFF_LOWER_UP) または `"down"` |
| `mtu` | uint string | カーネル実測値 | MTU 値 (文字列)。カーネルの `rtnl_link_get_mtu()` から取得 |
| `state` | enum string | `"ok"` | LAG の初期化状態。常に `"ok"` を書き込む。エラー時はエントリ削除 |

### tlm_teamd 追記フィールド

`ValuesStore::m_lag_paths` (`values_store.h:L48-56`) が `teamdctl` の JSON dump を解析して追記する。

| フィールド (JSON パス) | 型 | 説明 |
|-----------------------|----|------|
| `setup.kernel_team_mode_name` | string | teamd が使用する runner モード名（例: `"lacp"`） |
| `setup.pid` | integer string | teamd プロセスの PID |
| `runner.active` | boolean string | LAG がアクティブ（ポート集約中）かどうか |
| `runner.fallback` | boolean string | LACP fallback が有効か (`PORTCHANNEL.fallback` を反映) |
| `runner.fast_rate` | boolean string | LACP fast rate が有効か (`PORTCHANNEL.fast_rate` を反映) |
| `team_device.ifinfo.dev_addr` | string | LAG の MAC アドレス |
| `team_device.ifinfo.ifindex` | integer string | LAG の ifindex |

!!! note "STATE_DB に書かれないフィールド"
    CONFIG_DB `PORTCHANNEL` の `min_links`・`lacp_key`・`mode`・`tpid`・`description` は STATE_DB LAG_TABLE には書き込まれない。これらは `teammgrd` が `teamd` の設定ファイル生成に使用するのみ。

## `state` フィールドの状態遷移

```mermaid
stateDiagram-v2
    [*] --> ok : RTM_NEWLINK (TeamSync::addLag)
    ok --> [*] : RTM_DELLINK (TeamSync::removeLag)
```

| `state` 値 | 意味 |
|-----------|------|
| `"ok"` | LAG が teamsyncd に認識されており、teamd 初期化成功 |
| (エントリなし) | LAG が削除または teamd 初期化に失敗した状態 |

エラー状態（`"error"` 等）は存在しない。失敗時は `SWSS_LOG_ERROR` を出力してエントリを書き込まない。

## 書き込みタイミング

1. **LAG 追加時** (`teamsync.cpp:L146-225`): `RTM_NEWLINK` イベントで LAG タイプ (`team`) を検出すると `addLag()` を呼び出し、`m_stateLagTable.set(lagName, fvVector)` で全フィールドを書き込む。`state = "ok"` を含む。
2. **LAG 更新時** (同上): `admin_state` / `oper_state` / `mtu` が変化したときも `addLag()` を呼び出してフィールドを更新する。
3. **LAG 削除時** (`teamsync.cpp:L228-259`): `RTM_DELLINK` イベントで `removeLag()` を呼び出し、`m_stateLagTable.del(lagName)` でエントリを削除する。
4. **Warm restart** (`teamsync.cpp:L84-98`): warm restart 時は直接書き込まず `m_stateLagTablePreserved` に一時保存し、タイムアウト後に `applyState()` で一括書き込む。
5. **tlm_teamd 定期更新** (`tlm_teamd/main.cpp`): `teamdctl` で LAG の JSON dump を取得し、`ValuesStore::update()` で tlm_teamd フィールドを STATE_DB に反映する。

## 購読者

- `intfmgrd` (`cfgmgr/intfmgr.cpp:L38,L51`): LAG インタフェース設定前に `isLagStateOk()` でエントリ存在確認
- `vlanmgrd` (`cfgmgr/vlanmgr.cpp:L497`): LAG を VLAN メンバに追加する前に LAG state を確認
- `nbrmgrd` (`cfgmgr/nbrmgr.cpp:L47`): 隣接エントリ処理前に LAG state を確認
- `stpmgrd` (`cfgmgr/stpmgr.cpp:L1296`): STP ポート処理前に LAG state を確認
- `tlm_teamd` (`tlm_teamd/main.cpp:L98`): `SubscriberStateTable` で変化を監視し teamdctl dump を同期

## 関連 CONFIG_DB / CLI

- 設定元: [`PORTCHANNEL`](portchannel.md) (CONFIG_DB)
- メンバ管理: [`PORTCHANNEL_MEMBER`](portchannel-member.md) (CONFIG_DB)
- 確認コマンド: `show interfaces portchannel`、`teamdctl <lag_name> state`

<!-- defaults -->
## フィールド暗黙デフォルト (Phase A — コード由来)

STATE_DB `LAG_TABLE` に対応する YANG schema は存在しない。すべてのフィールドとデフォルト値は `teamsync.cpp` および `values_store.h` のコードレベルで定義される。

<!-- evidence: meta/_intermediate/cdb-flow/portchannel-state-defaults.md -->

| フィールド | STATE_DB 初期値 | コード由来 | 備考 |
|-----------|---------------|----------|------|
| `admin_status` | カーネル IFF_UP フラグから実測 | `rtnl_link_get_flags(link) & IFF_UP` — `teamsync.cpp:L115,L151` | 固定デフォルトなし。カーネル実測値を `"up"` / `"down"` に変換 |
| `oper_status` | カーネル IFF_LOWER_UP フラグから実測 | `rtnl_link_get_flags(link) & IFF_LOWER_UP` — `teamsync.cpp:L116,L152` | 固定デフォルトなし。LAG メンバが集約されると `"up"` になる |
| `mtu` | カーネル実測 MTU 値の文字列 | `rtnl_link_get_mtu(link)` — `teamsync.cpp:L140,L153` | カーネル側初期値は `portmgr.h` の `DEFAULT_MTU_STR = "9100"` だが STATE_DB は実測値を反映 |
| `state` | `"ok"` | `FieldValueTuple s("state", "ok")` — `teamsync.cpp:L175` | 常に `"ok"` のみ。teamd 初期化失敗時はエントリ自体を書かない |
| `setup.kernel_team_mode_name` | `"lacp"` (LACP モード時) | `teamdctl` JSON `setup.kernel_team_mode_name` — `values_store.h:L49` | teamd が使用する runner モード。CONFIG_DB 設定次第 |
| `setup.pid` | teamd の実プロセス PID | `teamdctl` JSON `setup.pid` — `values_store.h:L50` | 固定値なし。teamd spawn ごとに変化 |
| `runner.active` | `"false"` → ポート集約後 `"true"` | `teamdctl` JSON `runner.active` — `values_store.h:L51` | LACP ネゴシエーション完了後に `"true"` へ遷移 |
| `runner.fallback` | `"false"` (未設定時) | `teamdctl` JSON `runner.fallback` — `values_store.h:L52` | CONFIG_DB `PORTCHANNEL.fallback = true` のときのみ `"true"` |
| `runner.fast_rate` | `"false"` (未設定時) | `teamdctl` JSON `runner.fast_rate` — `values_store.h:L53` | CONFIG_DB `PORTCHANNEL.fast_rate = true` のときのみ `"true"` |
| `team_device.ifinfo.dev_addr` | LAG 作成時の MAC アドレス | `teamdctl` JSON `team_device.ifinfo.dev_addr` — `values_store.h:L54` | 固定値なし。システム MAC またはユーザー指定値 |
| `team_device.ifinfo.ifindex` | LAG 作成時の ifindex | `teamdctl` JSON `team_device.ifinfo.ifindex` — `values_store.h:L55` | 固定値なし。カーネルが割り当てた整数値 |

### 補足

- `admin_status` / `oper_status` / `mtu` はカーネルの netlink 実測値であり、コードレベルの固定デフォルトは存在しない。システム起動直後の LAG の典型的な初期値は `admin_status = "down"`、`oper_status = "down"`、`mtu = "9100"`（`portmgr.h` の `DEFAULT_MTU_STR` がカーネル側に設定されるため）。
- `state = "ok"` は teamd 初期化成功を示す唯一の値であり、エラー状態は STATE_DB に書かれない。`teamdctl` 接続失敗時は `SWSS_LOG_ERROR` を記録し STATE_DB への書き込みをスキップする (`teamsync.cpp:L208-213`)。
- tlm_teamd フィールド（`setup.*`、`runner.*`、`team_device.*`）は `teamdctl` の JSON dump に完全に依存する。tlm_teamd が dump 取得に失敗しても LAG_TABLE エントリは `teamsync.cpp` 書き込み分が残留する（`values_store.cpp:L284-291` で LAG_TABLE のエントリは削除しない設計）。
- YANG schema が存在しないため、フィールドの型・範囲はすべてコードレベルで実施される。
<!-- /defaults -->

<!-- ordering -->
## 書込み順依存 (Phase B)

> 調査対象: `sonic-swss/teamsyncd/teamsync.cpp`, `sonic-swss/cfgmgr/teammgr.cpp`, `sonic-swss/cfgmgr/intfmgr.cpp`, `sonic-swss/cfgmgr/vlanmgr.cpp`, `sonic-swss/cfgmgr/stpmgr.cpp`
> 調査日: 2026-05-18
> 詳細調査ノート: `meta/_intermediate/cdb-flow/portchannel-state-ordering.md`

このテーブルは STATE_DB の **書き込み専用**（teamsyncd / tlm_teamd のみが書き込む）であり、ユーザーが直接操作するものではない。`state=ok` エントリの有無が複数デーモンの readiness ガードとして機能するため、書き込み・削除の順序が後続処理の可否を決定する。

### teamsyncd が LAG_TABLE に書き込むまでの事前条件

LAG_TABLE への書き込みは以下の連鎖が完了することで発生する:

| ステップ | 条件 | 担当 | コード根拠 |
|---------|------|------|-----------|
| 1 | CONFIG_DB `PORTCHANNEL` エントリが SET される | CLI / minigraph | — |
| 2 | `TeamMgr::doLagTask()` が PORTCHANNEL エントリを受信する | teammgrd | `teammgr.cpp:L157-` |
| 3 | `TeamMgr::addLag()` が teamd プロセスを起動する | teammgrd | `teammgr.cpp:L564-` |
| 4 | teamd が Linux に LAG netdev を作成し `RTM_NEWLINK` が発行される | Linux カーネル | — |
| 5 | `TeamSync::addLag()` が `m_stateLagTable.set(lagName, ...)` で `state=ok` を書き込む | teamsyncd | `teamsync.cpp:L175, L203, L223` |

ステップ 3 (`exec()` 失敗) は `task_need_retry` を返し STATE_DB への書き込みをせずリトライ (`teammgr.cpp:L640-644`)。ステップ 5 の `teamdctl` 接続失敗は `SWSS_LOG_ERROR` を記録し STATE_DB 書き込みをスキップして次の `RTM_NEWLINK` を待つ (`teamsync.cpp:L208-213`)。

### warm-restart 時の書き込み遅延

warm-restart 中 (`m_warmstart == true`) は `addLag()` が `m_stateLagTablePreserved` に一時保存し、`applyState()` がタイムアウト（デフォルト: `DEFAULT_WR_PENDING_TIMEOUT`）後に一括で `m_stateLagTable.set()` を呼ぶ (`teamsync.cpp:L84-98`)。この間、`state=ok` は STATE_DB に存在しないため後続デーモンは保留状態が長引く。

### LAG_TABLE を readiness ガードとして使用するデーモン

`state=ok` エントリが存在するまで以下の処理がブロックされる:

| デーモン | 関数 | 保留する処理 | コード根拠 |
|---------|------|-------------|-----------|
| `intfmgrd` | `IntfMgr::isIntfStateOk(alias)` | `PORTCHANNEL_INTERFACE` / サブ IF の SET 処理 | `intfmgr.cpp:L661-668, L833` |
| `teammgrd` | `TeamMgr::isLagStateOk(alias)` | `PORTCHANNEL_MEMBER` の teamd enslave 処理 | `teammgr.cpp:L89-103, L357` |
| `vlanmgrd` | `VlanMgr::isMemberStateOk(alias)` | LAG を VLAN_MEMBER として追加する処理 | `vlanmgr.cpp:L490-510` |
| `stpmgrd` | `StpMgr::isLagStateOk(alias)` | STP ポート処理 | `stpmgr.cpp:L1292-1304` |

各デーモンは `m_stateLagTable.get(alias, temp)` で LAG_TABLE エントリを確認し、存在しない場合はタスクをキューに残してリトライする（エントリが存在するまで自動リトライ）。

### DEL 時の連鎖的影響

teamsyncd が `RTM_DELLINK` を受信すると `m_stateLagTable.del(lagName)` でエントリを削除する (`teamsync.cpp:L255`)。この削除により、`isIntfStateOk()` / `isLagStateOk()` を呼ぶすべてのデーモンが対象 LAG に対する処理を停止する。

DEL 順序の推奨:

```
# 推奨削除順序
DEL PORTCHANNEL_MEMBER|PortChannelN|*   # 全メンバを先に削除
DEL PORTCHANNEL_INTERFACE|PortChannelN|* # IP プレフィクスを先に削除
DEL PORTCHANNEL_INTERFACE|PortChannelN   # L3 IF 属性ロウ削除
DEL PORTCHANNEL|PortChannelN             # PORTCHANNEL を削除
                                          # → teammgrd が teamd を停止
                                          # → カーネルが RTM_DELLINK を発行
                                          # → teamsyncd が LAG_TABLE エントリを削除
```

PORTCHANNEL を先に削除した場合、LAG_TABLE エントリが残存したまま teamd プロセスが停止し得る。teamsyncd は RTM_DELLINK を確認して LAG_TABLE を削除するが、タイミング次第で孤立エントリが残る可能性がある。

<!-- /ordering -->

<!-- cross-refs -->
## 暗黙参照 (Phase C)

> 調査対象: `sonic-swss/teamsyncd/teamsync.cpp`, `sonic-swss/tlm_teamd/main.cpp`, `sonic-swss/tlm_teamd/values_store.cpp`, `sonic-swss/cfgmgr/intfmgr.cpp`, `sonic-swss/cfgmgr/teammgr.cpp`, `sonic-swss/cfgmgr/vlanmgr.cpp`, `sonic-swss/cfgmgr/stpmgr.cpp`, `sonic-swss/cfgmgr/nbrmgr.cpp`, `sonic-swss/cfgmgr/natmgr.cpp`
> 調査日: 2026-05-18
> 詳細調査ノート: `meta/_intermediate/cdb-flow/portchannel-state-cross-refs.md`

YANG leafref を超えた他テーブル・他 DB・プロセスへの実装上の依存関係。STATE_DB テーブルであるため「何が書き込むか」と「何が読むか」の両方向を示す。

| 参照先 | DB / 場所 | 方向 | 契機 | 根拠コード |
|--------|-----------|------|------|-----------|
| Linux netlink (`RTM_NEWLINK` / `RTM_DELLINK`) | カーネル | READ | LAG netdev の追加・削除イベントを受信し `addLag()` / `removeLag()` を呼び出す。netlink イベントがなければ LAG_TABLE は書かれない | `teamsync.cpp:101-143` |
| `teamdctl` JSON dump（UNIX socket） | プロセス間 | READ | `TeamPortSync::readData()` が `teamdctl_connect()` で teamd プロセスソケットに接続し JSON dump を取得。`ValuesStore::update()` が `setup.*` / `runner.*` / `team_device.*` フィールドを LAG_TABLE に書き込む | `teamsync.cpp:317-348`, `values_store.cpp:352-380` |
| `STATE_DB::LAG_TABLE`（自己購読） | STATE_DB | READ | `tlm_teamd` が `SubscriberStateTable` で `LAG_TABLE` を購読し、`state=ok` 書き込みをトリガーに teamdctl 接続を開始する（循環構造） | `tlm_teamd/main.cpp:98-106` |
| `intfmgrd` — `isIntfStateOk()` | STATE_DB | READ by consumer | `PORTCHANNEL_INTERFACE` SET 処理前に `m_stateLagTable.get(alias)` でエントリ存在を確認。エントリなしは処理保留・retry | `intfmgr.cpp:38,663-668,833` |
| `teammgrd` — `isLagStateOk()` | STATE_DB | READ by consumer | `PORTCHANNEL_MEMBER` enslave 前に `m_stateLagTable.get(alias)` で確認。エントリなしは保留 | `teammgr.cpp:38,89-103,357` |
| `vlanmgrd` — `isMemberStateOk()` | STATE_DB | READ by consumer | `VLAN_MEMBER` への LAG 追加前に `m_stateLagTable.get(alias)` で確認。エントリなしは保留 | `vlanmgr.cpp:30,497` |
| `stpmgrd` — `isLagStateOk()` | STATE_DB | READ by consumer | STP ポート処理前に `m_stateLagTable.get(alias)` で確認。エントリなしは保留 | `stpmgr.cpp:32,1296` |
| `nbrmgrd` | STATE_DB | READ by consumer | 隣接エントリ処理前に LAG 状態を確認する | `nbrmgr.cpp:47` |
| `natmgrd` — NAT ポートマッピング | STATE_DB | READ by consumer | NAT インタフェースとして LAG を使用する場合に `m_stateLagTable.get(port)` で確認 | `natmgr.cpp:38,111` |

!!! note "補足"
    - **書き込みは teamsyncd と tlm_teamd のみ**。orchagent / portsorch は APP_DB の `APP_LAG_TABLE` を購読して SAI に反映するため、STATE_DB の LAG_TABLE を直接読まない。
    - **tlm_teamd の自己購読**は teamsyncd が先に `state=ok` を書くことを前提とした依存関係であり、teamsyncd が書かないと tlm_teamd は teamdctl 接続を開始しない。
    - **values_store.cpp の LAG_TABLE 削除回避**（L284-291）: tlm_teamd は LAG_TABLE のエントリ本体を削除しない。LAG 削除は teamsyncd の `RTM_DELLINK` 処理のみが担う。

<!-- /cross-refs -->

## 引用元

[^1]: `sonic-swss/teamsyncd/teamsync.cpp` (L26-30 コンストラクタ, L101-143 onMsg, L146-226 addLag, L228-259 removeLag). <https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/teamsyncd/teamsync.cpp>
      `sonic-swss/tlm_teamd/values_store.h` (L48-56 m_lag_paths). <https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/tlm_teamd/values_store.h>

## 確認コマンド

```bash
sonic-db-cli STATE_DB keys 'LAG_TABLE|*'
sonic-db-cli STATE_DB hgetall 'LAG_TABLE|PortChannel0001'
show interfaces portchannel
teamdctl PortChannel0001 state
```
