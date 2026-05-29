---
title: STATE_DB LAG_TABLE (PortChannel 状態)
description: "STATE_DB LAG_TABLE — PortChannel (LAG) のランタイム状態を STATE_DB に保持するテーブル。teamsyncd が Linux netlink NEWLINK イベントを受信したときに書き込み、tlm_teamd が teamdctl JSON dump を解析して追記する。"
area: reference
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

[PortChannel](../../reference/glossary.md#term-portchannel) ([LAG](../../reference/glossary.md#term-lag)) のランタイム状態を [STATE_DB](../../reference/glossary.md#term-state_db) に保持するテーブル[^1]。`sonic-swss` の `teamsyncd` が Linux カーネルの netlink NEWLINK イベントを受信したときに主フィールドを書き込み、`tlm_teamd` が `teamdctl` の JSON dump を定期的に解析して補助フィールドを追記する。このテーブルは観測専用（書き込みは teamsyncd / tlm_teamd のみ）であり、`intfmgrd`・`vlanmgr`・`nbrmgrd`・`stpmgrd` が [LAG](../../reference/glossary.md#term-lag) の準備完了チェックに参照する。

[CONFIG_DB](../../reference/glossary.md#term-config_db) の [`PORTCHANNEL`](portchannel.md) テーブルとは別テーブルであり、こちらは設定ではなく実行時状態を格納する。

## key 構造

```text
LAG_TABLE|<lag_name>
```

- `<lag_name>`: [LAG](../../reference/glossary.md#term-lag) インタフェース名。形式は `PortChannel<0-9999>`（例: `PortChannel0001`）
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
| `setup.kernel_team_mode_name` | string | [teamd](../../reference/glossary.md#term-teamd-teamsyncd-teammgrd) が使用する runner モード名（例: `"lacp"`） |
| `setup.pid` | integer string | [teamd](../../reference/glossary.md#term-teamd-teamsyncd-teammgrd) プロセスの PID |
| `runner.active` | boolean string | LAG がアクティブ（ポート集約中）かどうか |
| `runner.fallback` | boolean string | [LACP](../../reference/glossary.md#term-lacp) fallback が有効か (`PORTCHANNEL.fallback` を反映) |
| `runner.fast_rate` | boolean string | [LACP](../../reference/glossary.md#term-lacp) fast rate が有効か (`PORTCHANNEL.fast_rate` を反映) |
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
| `"ok"` | LAG が teamsyncd に認識されており、[teamd](../../reference/glossary.md#term-teamd-teamsyncd-teammgrd) 初期化成功 |
| (エントリなし) | LAG が削除または teamd 初期化に失敗した状態 |

エラー状態（`"error"` 等）は存在しない。失敗時は `SWSS_LOG_ERROR` を出力してエントリを書き込まない。

## 書き込みタイミング

1. **LAG 追加時** (`teamsync.cpp:L146-225`): `RTM_NEWLINK` イベントで LAG タイプ (`team`) を検出すると `addLag()` を呼び出し、`m_stateLagTable.set(lagName, fvVector)` で全フィールドを書き込む。`state = "ok"` を含む。
2. **LAG 更新時** (同上): `admin_state` / `oper_state` / `mtu` が変化したときも `addLag()` を呼び出してフィールドを更新する。
3. **LAG 削除時** (`teamsync.cpp:L228-259`): `RTM_DELLINK` イベントで `removeLag()` を呼び出し、`m_stateLagTable.del(lagName)` でエントリを削除する。
4. **Warm restart** (`teamsync.cpp:L84-98`): warm restart 時は直接書き込まず `m_stateLagTablePreserved` に一時保存し、タイムアウト後に `applyState()` で一括書き込む。
5. **tlm_teamd 定期更新** (`tlm_teamd/main.cpp`): `teamdctl` で LAG の JSON dump を取得し、`ValuesStore::update()` で tlm_teamd フィールドを [STATE_DB](../../reference/glossary.md#term-state_db) に反映する。

## 購読者

- `intfmgrd` (`cfgmgr/intfmgr.cpp:L38,L51`): LAG インタフェース設定前に `isLagStateOk()` でエントリ存在確認
- `vlanmgrd` (`cfgmgr/vlanmgr.cpp:L497`): LAG を [VLAN](../../reference/glossary.md#term-vlan) メンバに追加する前に LAG state を確認
- `nbrmgrd` (`cfgmgr/nbrmgr.cpp:L47`): 隣接エントリ処理前に LAG state を確認
- `stpmgrd` (`cfgmgr/stpmgr.cpp:L1296`): STP ポート処理前に LAG state を確認
- `tlm_teamd` (`tlm_teamd/main.cpp:L98`): `SubscriberStateTable` で変化を監視し teamdctl dump を同期

## 関連 CONFIG_DB / CLI

- 設定元: [`PORTCHANNEL`](portchannel.md) ([CONFIG_DB](../../reference/glossary.md#term-config_db))
- メンバ管理: [`PORTCHANNEL_MEMBER`](portchannel-member.md) ([CONFIG_DB](../../reference/glossary.md#term-config_db))
- 確認コマンド: `show interfaces portchannel`、`teamdctl <lag_name> state`

<!-- defaults -->
## フィールド暗黙デフォルト (コード由来)

[STATE_DB](../../reference/glossary.md#term-state_db) `LAG_TABLE` に対応する [YANG](../../reference/glossary.md#term-yang) schema は存在しない。すべてのフィールドとデフォルト値は `teamsync.cpp` および `values_store.h` のコードレベルで定義される。

| フィールド | STATE_DB 初期値 | コード由来 | 備考 |
|-----------|---------------|----------|------|
| `admin_status` | カーネル IFF_UP フラグから実測 | `rtnl_link_get_flags(link) & IFF_UP` — `teamsync.cpp:L115,L151` | 固定デフォルトなし。カーネル実測値を `"up"` / `"down"` に変換 |
| `oper_status` | カーネル IFF_LOWER_UP フラグから実測 | `rtnl_link_get_flags(link) & IFF_LOWER_UP` — `teamsync.cpp:L116,L152` | 固定デフォルトなし。LAG メンバが集約されると `"up"` になる |
| `mtu` | カーネル実測 MTU 値の文字列 | `rtnl_link_get_mtu(link)` — `teamsync.cpp:L140,L153` | カーネル側初期値は `portmgr.h` の `DEFAULT_MTU_STR = "9100"` だが STATE_DB は実測値を反映 |
| `state` | `"ok"` | `FieldValueTuple s("state", "ok")` — `teamsync.cpp:L175` | 常に `"ok"` のみ。teamd 初期化失敗時はエントリ自体を書かない |
| `setup.kernel_team_mode_name` | `"lacp"` ([LACP](../../reference/glossary.md#term-lacp) モード時) | `teamdctl` JSON `setup.kernel_team_mode_name` — `values_store.h:L49` | teamd が使用する runner モード。CONFIG_DB 設定次第 |
| `setup.pid` | teamd の実プロセス PID | `teamdctl` JSON `setup.pid` — `values_store.h:L50` | 固定値なし。teamd spawn ごとに変化 |
| `runner.active` | `"false"` → ポート集約後 `"true"` | `teamdctl` JSON `runner.active` — `values_store.h:L51` | LACP ネゴシエーション完了後に `"true"` へ遷移 |
| `runner.fallback` | `"false"` (未設定時) | `teamdctl` JSON `runner.fallback` — `values_store.h:L52` | CONFIG_DB `PORTCHANNEL.fallback = true` のときのみ `"true"` |
| `runner.fast_rate` | `"false"` (未設定時) | `teamdctl` JSON `runner.fast_rate` — `values_store.h:L53` | CONFIG_DB `PORTCHANNEL.fast_rate = true` のときのみ `"true"` |
| `team_device.ifinfo.dev_addr` | LAG 作成時の MAC アドレス | `teamdctl` JSON `team_device.ifinfo.dev_addr` — `values_store.h:L54` | 固定値なし。システム MAC またはユーザ指定値 |
| `team_device.ifinfo.ifindex` | LAG 作成時の ifindex | `teamdctl` JSON `team_device.ifinfo.ifindex` — `values_store.h:L55` | 固定値なし。カーネルが割り当てた整数値 |

### 補足

- `admin_status` / `oper_status` / `mtu` はカーネルの netlink 実測値であり、コードレベルの固定デフォルトは存在しない。システム起動直後の LAG の典型的な初期値は `admin_status = "down"`、`oper_status = "down"`、`mtu = "9100"`（`portmgr.h` の `DEFAULT_MTU_STR` がカーネル側に設定されるため）。
- `state = "ok"` は teamd 初期化成功を示す唯一の値であり、エラー状態は STATE_DB に書かれない。`teamdctl` 接続失敗時は `SWSS_LOG_ERROR` を記録し STATE_DB への書き込みをスキップする (`teamsync.cpp:L208-213`)。
- tlm_teamd フィールド（`setup.*`、`runner.*`、`team_device.*`）は `teamdctl` の JSON dump に完全に依存する。tlm_teamd が dump 取得に失敗しても LAG_TABLE エントリは `teamsync.cpp` 書き込み分が残留する（`values_store.cpp:L284-291` で LAG_TABLE のエントリは削除しない設計）。
- [YANG](../../reference/glossary.md#term-yang) schema が存在しないため、フィールドの型・範囲はすべてコードレベルで実施される。
<!-- /defaults -->

<!-- ordering -->
## 書込み順依存

> 調査対象: `sonic-swss/teamsyncd/teamsync.cpp`, `sonic-swss/cfgmgr/teammgr.cpp`, `sonic-swss/cfgmgr/intfmgr.cpp`, `sonic-swss/cfgmgr/vlanmgr.cpp`, `sonic-swss/cfgmgr/stpmgr.cpp`

このテーブルは STATE_DB の **書き込み専用**（teamsyncd / tlm_teamd のみが書き込む）であり、ユーザが直接操作するものではない。`state=ok` エントリの有無が複数デーモンの readiness ガードとして機能するため、書き込み・削除の順序が後続処理の可否を決定する。

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
## 暗黙参照

> 調査対象: `sonic-swss/teamsyncd/teamsync.cpp`, `sonic-swss/tlm_teamd/main.cpp`, `sonic-swss/tlm_teamd/values_store.cpp`, `sonic-swss/cfgmgr/intfmgr.cpp`, `sonic-swss/cfgmgr/teammgr.cpp`, `sonic-swss/cfgmgr/vlanmgr.cpp`, `sonic-swss/cfgmgr/stpmgr.cpp`, `sonic-swss/cfgmgr/nbrmgr.cpp`, `sonic-swss/cfgmgr/natmgr.cpp`

[YANG](../../reference/glossary.md#term-yang) leafref を超えた他テーブル・他 DB・プロセスへの実装上の依存関係。STATE_DB テーブルであるため「何が書き込むか」と「何が読むか」の両方向を示す。

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
| `natmgrd` — [NAT](../../reference/glossary.md#term-nat) ポートマッピング | STATE_DB | READ by consumer | [NAT](../../reference/glossary.md#term-nat) インタフェースとして LAG を使用する場合に `m_stateLagTable.get(port)` で確認 | `natmgr.cpp:38,111` |

!!! note "補足"
    - **書き込みは teamsyncd と tlm_teamd のみ**。orchagent / portsorch は APP_DB の `APP_LAG_TABLE` を購読して SAI に反映するため、STATE_DB の LAG_TABLE を直接読まない。
    - **tlm_teamd の自己購読**は teamsyncd が先に `state=ok` を書くことを前提とした依存関係であり、teamsyncd が書かないと tlm_teamd は teamdctl 接続を開始しない。
    - **values_store.cpp の LAG_TABLE 削除回避**（L284-291）: tlm_teamd は LAG_TABLE のエントリ本体を削除しない。LAG 削除は teamsyncd の `RTM_DELLINK` 処理のみが担う。

<!-- /cross-refs -->

<!-- failure -->
## 失敗挙動

> 調査対象: `sonic-swss/teamsyncd/teamsync.cpp`, `sonic-swss/cfgmgr/teammgr.cpp`, `sonic-swss/cfgmgr/intfmgr.cpp`

STATE_DB `LAG_TABLE` への書き込みは teamsyncd と teammgrd の正常完了に依存するため、各ステップで失敗が発生すると `state=ok` エントリが書かれず後続デーモンが保留状態になる。

### teamsyncd — TeamPortSync 初期化失敗 (`teamsync.cpp:L208-213, L280-365`)

`TeamSync::addLag()` は `TeamPortSync` コンストラクタを `try-catch` で保護している。コンストラクタ内では最大 3 回リトライ (`max_retries = 3`) を `sleep(1)` 間隔で実施し、すべて失敗すると `system_error` をリスローする。

| 失敗原因 | errno | 挙動 |
|---------|-------|------|
| `team_alloc()` 失敗 | `EADDRNOTAVAIL` | `system_error` スロー → リトライ |
| `team_init()` 失敗 | `EADDRNOTAVAIL` | `system_error` スロー → リトライ。コンテナ再起動直後に多発（旧 ifindex が無効になるため） |
| `teamdctl_alloc()` 失敗 | `EADDRNOTAVAIL` | `system_error` スロー → リトライ |
| `teamdctl_connect()` 失敗 | `ECONNREFUSED` | `system_error` スロー → リトライ（teamd がまだ起動中の場合） |
| `teamdctl_config_get_raw_direct()` 失敗 | `EIO` | `system_error` スロー → リトライ |
| 3 回リトライ後も失敗 | 上記いずれか | `SWSS_LOG_ERROR` → STATE_DB 書き込みスキップ → 次の `RTM_NEWLINK` を待つ |

3 回失敗後は `addLag()` の外側 catch が `SWSS_LOG_ERROR("addLag: Failed to initialize team handler for LAG %s ...")` を記録し、STATE_DB への書き込みをせずに return する。次の `RTM_NEWLINK` イベント（teamd が LAG netdev を再作成した際に発行）で再試行される。

### teammgrd — teamd 起動失敗 (`teammgr.cpp:L640-644`)

`TeamMgr::addLag()` が `exec("teamd -r ...")` の戻り値が非ゼロのとき `task_need_retry` を返す。Consumer ループがタスクをキューに残し自動リトライする。teamd が起動しなければ Linux に LAG netdev が作成されず `RTM_NEWLINK` が発行されないため、STATE_DB には `state=ok` が書かれない。

```
exec(teamd_cmd) != 0
  → SWSS_LOG_INFO("Failed to start port channel %s with teamd, retry...")
  → return task_need_retry
  → Consumer がキューにタスクを保持・自動リトライ
```

### warm-restart 時の遅延書き込み (`teamsync.cpp:L84-98, L197-203`)

warm-restart 中 (`m_warmstart == true`) は `addLag()` が STATE_DB に直接書かず `m_stateLagTablePreserved` に保存する。`applyState()` がタイムアウト（`WarmStart::getWarmStartTimer()` または `DEFAULT_WR_PENDING_TIMEOUT`）後に一括書き込みを実施する。タイムアウトまでの間、後続デーモンは保留状態になる。

### 後続デーモンへの影響

`state=ok` エントリが LAG_TABLE に書かれるまで以下の処理がすべて保留される:

| デーモン | 保留される処理 |
|---------|-------------|
| `intfmgrd` | `PORTCHANNEL_INTERFACE` の IP アドレス付与・IPv6 有効化 |
| `teammgrd` | `PORTCHANNEL_MEMBER` の teamd enslave |
| `vlanmgrd` | VLAN_MEMBER への LAG 追加 |
| `stpmgrd` | STP ポート処理 |

いずれも `m_stateLagTable.get(alias)` 失敗時にタスクをキューに残してリトライするため、LAG_TABLE に `state=ok` が書かれた瞬間に自動的に解消される。

<!-- /failure -->

<!-- constants -->
## ハードコード定数

> 調査対象: `sonic-swss/teamsyncd/teamsync.h`, `sonic-swss/teamsyncd/teamsync.cpp`, `sonic-swss/cfgmgr/teammgr.cpp`, `sonic-swss/cfgmgr/portmgr.h`, `sonic-swss/cfgmgr/shellcmd.h`, `sonic-swss-common/common/schema.h`

以下の定数は STATE_DB `LAG_TABLE` の書き込み動作・タイミングに直接影響するマジックナンバーおよびハードコード値。

| 定数 / マクロ名 | 値 | 定義ファイル | 意味・影響 |
|-----------------|-----|--------------|-----------|
| `DEFAULT_WR_PENDING_TIMEOUT` | `70` 秒 | `teamsync.h:16` | warm restart 時に `m_stateLagTablePreserved` の内容を STATE_DB へ一括書き込みするまでのタイムアウト。`WarmStart::getWarmStartTimer()` が設定されていない場合のフォールバック値 |
| `TEAMSYNCD_APP_NAME` | `"teamsyncd"` | `teamsync.h:14` | WarmStart フレームワークへの登録名。warm restart 検出・状態遷移管理に使用。warm restart タイマーキー名にも反映される |
| `TEAM_DRV_NAME` | `"team"` | `teamsync.cpp:24` | netlink `RTM_NEWLINK` イベントで LAG を識別するドライバ名文字列。`rtnl_link_get_type()` の戻り値と `strcmp()` で比較し、一致しない netdev は無視される |
| `max_retries` | `3` | `teamsync.cpp:286` | `TeamPortSync` コンストラクタ内で `team_init()` / `teamdctl_connect()` 失敗時の最大リトライ回数。3 回失敗すると `system_error` をリスローし STATE_DB への書き込みがスキップされる |
| リトライ間隔 | `1` 秒 | `teamsync.cpp:363` | `team_init()` / `teamdctl_connect()` リトライ間の `sleep()` 値。固定値。最大 3 回 × 1 秒 = 最大 3 秒の待機が発生しうる |
| `DEFAULT_ADMIN_STATUS_STR` | `"down"` | `portmgr.h:14` | CONFIG_DB `PORTCHANNEL` に `admin_status` が未指定の場合に `teammgrd` が使用するデフォルト値 |
| `DEFAULT_MTU_STR` | `"9100"` | `portmgr.h:15` | CONFIG_DB `PORTCHANNEL` に `mtu` が未指定の場合に `teammgrd` が使用するデフォルト値 (文字列)。カーネルに設定された後 `teamsyncd` が実測値として STATE_DB `LAG_TABLE.mtu` に書き込む |
| `TEAMD_CMD` | `"/usr/bin/teamd"` | `shellcmd.h:13` | `TeamMgr::addLag()` が LAG 作成時に `exec()` する teamd バイナリの絶対パス |
| `STATE_LAG_TABLE_NAME` | `"LAG_TABLE"` | `schema.h:422` | STATE_DB 内テーブル名定数 |
| `APP_LAG_TABLE_NAME` | `"LAG_TABLE"` | `schema.h:43` | APP_DB 内テーブル名定数。STATE_DB と APP_DB で同一テーブル名 `"LAG_TABLE"` を使用する |
| warmboot ダンプパス | `"/var/warmboot/teamd/"` | `teammgr.cpp:573` | warm restart 時に teamd 設定ダンプを読み書きするファイルシステムパス。partner MAC アドレスの復元に使用 |
| `partner_system_id_offset` | `40` バイト | `teammgr.cpp:581` | warmboot ダンプファイル内で LACP partner system MAC が格納されるバイトオフセット |

!!! note "TeamMgr 起動時の LAG_TABLE クリア"
    `TeamMgr()` コンストラクタ (`teammgr.cpp:L43-50`) は起動直後に `m_stateLagTable.getKeys()` → `m_stateLagTable.del()` で STATE_DB `LAG_TABLE` の既存エントリをすべて削除する。これにより `teammgrd` 再起動時に古い `state=ok` エントリが残留しない設計となっている。ただしこの削除は一時的に後続デーモン（`intfmgrd`, `vlanmgrd` 等）の readiness チェックを失敗させる点に注意。

!!! note "APP_DB と STATE_DB で同名テーブル"
    `APP_LAG_TABLE_NAME = "LAG_TABLE"` と `STATE_LAG_TABLE_NAME = "LAG_TABLE"` は同一文字列だが、接続先 DB (`APPL_DB` と `STATE_DB`) が異なるため衝突しない。コードでは `m_lagTable`（APP_DB 用）と `m_stateLagTable`（STATE_DB 用）で別変数に格納される（`teamsync.cpp:L28-30`）。

<!-- /constants -->

<!-- side-effects -->
## 副次 DB 書込

> 調査対象: `sonic-swss/tlm_teamd/values_store.h`, `sonic-swss/tlm_teamd/values_store.cpp`, `sonic-swss/cfgmgr/intfmgr.cpp`

STATE_DB `LAG_TABLE` への書き込みをトリガーとして、他テーブル・他 DB へのカスケード書き込みが発生する。

### 1. STATE_DB `LAG_MEMBER_TABLE` への追記 (tlm_teamd)

`tlm_teamd` は `SubscriberStateTable` で `LAG_TABLE` の変化を受信すると (`main.cpp:L98-107`)、`teamdctl` の JSON dump (`teamdctl_mgr.get_dumps()`) を取得し `ValuesStore::update()` → `extract_values()` を呼び出す。このとき JSON dump に含まれる各メンバポートに対して **`STATE_DB::LAG_MEMBER_TABLE|<lag_name>|<port>`** エントリを生成・更新する (`values_store.cpp:L170-184`)。

書き込まれるフィールドは `m_member_paths` (`values_store.h:L60-75`) で定義されている:

| フィールド (JSON パス) | 型 | 説明 |
|-----------------------|----|------|
| `ifinfo.dev_addr` | string | メンバポートの MAC アドレス |
| `ifinfo.ifindex` | integer string | メンバポートの ifindex |
| `link.up` | boolean string | リンクが物理的に UP かどうか |
| `link_watches.list.link_watch_0.up` | boolean string | link watch の状態 |
| `runner.actor_lacpdu_info.port` | integer string | LACP actor ポート番号 |
| `runner.actor_lacpdu_info.state` | integer string | LACP actor 状態フラグ |
| `runner.actor_lacpdu_info.system` | string | LACP actor システム MAC |
| `runner.partner_lacpdu_info.port` | integer string | LACP partner ポート番号 |
| `runner.partner_lacpdu_info.state` | integer string | LACP partner 状態フラグ |
| `runner.partner_lacpdu_info.system` | string | LACP partner システム MAC |
| `runner.aggregator.id` | integer string | aggregator ID |
| `runner.aggregator.selected` | boolean string | aggregator が選択されているか |
| `runner.selected` | boolean string | ポートが集約に選択されているか |
| `runner.state` | string | LACP runner 状態 (`"defaulted"`, `"expired"` 等) |

!!! note "LAG_TABLE エントリは削除しない"
    `ValuesStore::remove_keys_db()` (`values_store.cpp:L284-293`) は teamdctl dump 取得失敗時に古いキーを削除する際、`table_name == "LAG_TABLE"` のエントリをスキップする。`LAG_TABLE` の削除は teamsyncd の `RTM_DELLINK` 処理のみが担う設計。

### 2. APP_DB `INTF_TABLE` への連鎖書き込み (intfmgrd — サブインタフェース)

`intfmgrd` は `doPortTableTask()` (`intfmgr.cpp:L1244-1270`) で `LAG_TABLE` の変化を受信し、対象 LAG にサブインタフェース（`PortChannelN.VID` 形式）が存在する場合、以下の副次書き込みを行う:

| フィールド変化 | 副次処理 | 書き込み先 |
|-------------|---------|-----------|
| `admin_status` 変化 | `updateSubIntfAdminStatus()` → `m_appIntfTableProducer.set(subIntf, ...)` | APP_DB `INTF_TABLE|PortChannelN.VID` |
| `mtu` 変化 | `updateSubIntfMtu()` → `m_appIntfTableProducer.set(subIntf, ...)` | APP_DB `INTF_TABLE|PortChannelN.VID` |

これにより親 LAG の `admin_status` / `mtu` 変化がサブインタフェースに自動継承される (`intfmgr.cpp:L464-489, L407-461`)。

### 3. STATE_DB `LAG_TABLE` へのサブインタフェース用書き込み (intfmgrd)

サブインタフェース (`PortChannelN.VID`) が正常に設定されると、`IntfMgr::setSubIntfStateOk()` (`intfmgr.cpp:L543-549`) が `m_stateLagTable.set(subIntfAlias, {{"state", "ok"}})` を呼ぶ。これにより **`LAG_TABLE|PortChannelN.VID`** エントリが STATE_DB に書かれ、さらに下流処理（nbrmgrd 等）の readiness ガードとして機能する。

<!-- /side-effects -->

<!-- pubsub -->
## Redis 通知メカニズム

> 調査対象: `sonic-swss/tlm_teamd/main.cpp`, `sonic-swss/cfgmgr/intfmgr.cpp`, `sonic-swss-common/common/subscriberstatetable.cpp`

### SubscriberStateTable の仕組み（共通基盤）

`SubscriberStateTable` はコンストラクタ内で [Redis](../../reference/glossary.md#term-redis) keyspace notification を PSUBSCRIBE し、テーブル変化を push 通知として受け取る (`subscriberstatetable.cpp:L20-24`)。`LAG_TABLE` に対するパターン:

```
__keyspace@6__:LAG_TABLE|*
```

(STATE_DB の db_id = 6 — `database_config.json`)

起動時には既存キーをすべて `m_buffer` に積んで初期同期を行う (`subscriberstatetable.cpp:L26-42`)。

### tlm_teamd — 主要購読者

`tlm_teamd` (`main.cpp:L98-99`) は STATE_DB の `LAG_TABLE` を `SubscriberStateTable` で購読する唯一のプロセス:

```cpp
swss::SubscriberStateTable sst_lag(&db, STATE_LAG_TABLE_NAME);
s.addSelectable(&sst_lag);
```

| `s.select()` 戻り値 | 処理 | select タイムアウト |
|--------------------|------|-------------------|
| `OBJECT` | `update_interfaces()` → `values_store.update(get_dumps(false))` | — (即時) |
| `TIMEOUT` | `process_add_queue()` + `values_store.update(get_dumps(true))` | **1000 ms** (`main.cpp:L68`) |

- `SET` イベント受信 → `mgr.add_lag(lag_name)` → 次の select で teamdctl dump を取得し `setup.*` / `runner.*` / `team_device.*` フィールドを STATE_DB に追記
- `DEL` イベント受信 → `mgr.remove_lag(lag_name)` → teamdctl 接続を即時解除
- サブインタフェース (`VLAN_SUB_INTERFACE_SEPARATOR` を含むキー) は `update_interfaces()` 内でスキップ (`main.cpp:L34-37`)

### intfmgrd — 副次購読者（サブインタフェース管理）

`intfmgrd` (`intfmgr.cpp:L50-53`) も `STATE_LAG_TABLE_NAME` を `SubscriberStateTable` で購読する（priority=200）:

```cpp
auto subscriberStateLagTable = new swss::SubscriberStateTable(stateDb,
        STATE_LAG_TABLE_NAME, DEFAULT_POP_BATCH_SIZE, 200);
```

`STATE_LAG_TABLE_NAME` の SET/DEL イベントを受信すると `doPortTableTask()` を呼び出し、親 LAG の `admin_status` / `mtu` 変化をサブインタフェース (`PortChannelN.VID`) の APP_DB `INTF_TABLE` にカスケード更新する (`intfmgr.cpp:L1183-1186`)。

### vlanmgrd / stpmgrd / nbrmgrd — ポーリング方式（非購読）

`vlanmgrd` / `stpmgrd` / `nbrmgrd` は `SubscriberStateTable` による push 通知ではなく、各自タスクループ内で `m_stateLagTable.get(alias, temp)` を呼び出すポーリング方式。LAG_TABLE の変化通知は受け取らず、それぞれのトリガーイベント（VLAN_MEMBER SET・STP ポート追加等）発生時に現在値を参照する。

### 通知フロー

```
teamsyncd: m_stateLagTable.set(lagName, fvVector)  [teamsync.cpp:L203]
  │
  └─ Redis keyspace notification: __keyspace@6__:LAG_TABLE|<lag>
       │
       ├─→ [tlm_teamd] select OBJECT → update_interfaces() → values_store.update()
       │     → STATE_DB LAG_TABLE に setup.*/runner.*/team_device.* 追記 (最大 1 秒遅延)
       │     → STATE_DB LAG_MEMBER_TABLE に各メンバフィールド書込み
       │
       └─→ [intfmgrd] stateLagConsumer → doPortTableTask()
             → APP_DB INTF_TABLE|PortChannelN.VID にカスケード更新

teamsyncd: m_stateLagTable.del(lagName)  [teamsync.cpp:L255]
  └─ Redis keyspace notification: DEL event
       ├─→ [tlm_teamd] mgr.remove_lag() → teamdctl 接続解除
       └─→ [intfmgrd] DEL イベント → サブインタフェース状態クリーンアップ
```

<!-- /pubsub -->

<!-- platform -->
## プラットフォーム差

STATE_DB `LAG_TABLE` への書き込みは Linux netlink (`RTM_NEWLINK` / `RTM_DELLINK`) と `teamdctl` UNIX ソケット経由の JSON dump に依存する。いずれも [SAI](../../reference/glossary.md#term-sai) を経由しないカーネル・ユーザ空間の仕組みであるため、プラットフォーム（[ASIC](../../reference/glossary.md#term-asic) ベンダー）差異は生じない。

| 観点 | 結果 | 根拠 |
|------|------|------|
| [ASIC](../../reference/glossary.md#term-asic) 種別 (Broadcom / Mellanox / Marvell / Innovium 等) | 影響なし | `teamsyncd` は `libteam` + netlink のみを使用し [SAI](../../reference/glossary.md#term-sai) API を呼ばない。`teamsyncd.cpp` に [SAI](../../reference/glossary.md#term-sai) インクルードなし。フィールド値・書き込みタイミング・テーブル構造はすべての [ASIC](../../reference/glossary.md#term-asic) で同一 |
| multi-asic (namespace 分離構成) | 各 namespace で独立動作・差異なし | `teamsyncd` / `tlm_teamd` / `teammgrd` はいずれも `DBConnector("STATE_DB", 0)` を無引数で開く (`teamsyncd.cpp:L31-32`, `teammgrd.cpp:L48-50`, `tlm_teamd/main.cpp:L91`)。multi-asic 環境では各 namespace に独立インスタンスが起動し、同一ロジックで自 namespace の `LAG_TABLE` に書き込む |
| [VOQ](../../reference/glossary.md#term-voq) chassis (Virtual Output Queue) | 影響なし | [VOQ](../../reference/glossary.md#term-voq) chassis 固有の `SYSTEM_LAG_TABLE` / `SYSTEM_LAG_ID_TABLE` (`orchagent/lagids.lua`) は [APPL_DB](../../reference/glossary.md#term-appl_db) / CHASSIS_APP_DB 上のテーブルであり `STATE_DB::LAG_TABLE` とは別物。`teamsyncd` は [VOQ](../../reference/glossary.md#term-voq) 特有コードパスを持たず Linux netlink イベントに純粋に従う |
| warm restart タイマー | プラットフォーム非依存 | `WarmStart::getWarmStartTimer(TEAMSYNCD_APP_NAME, "teamd")` でタイマー取得し、未設定時は `DEFAULT_WR_PENDING_TIMEOUT = 70` 秒を使用 (`teamsync.h:L16`)。タイマー値はプラットフォームではなく mgmt 設定に依存 |

<!-- /platform -->

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

<!-- glossary-links-injected: 47111cc4fb33 -->
