# STATE_DB LAG_TABLE 暗黙参照調査 (Phase C)

生成日: 2026-05-18  
対象ページ: `docs/reference/config-db/portchannel-state.md`

## 調査概要

STATE_DB `LAG_TABLE` がソースコードレベルで依存する（または参照される）周辺テーブル・DB・プロセスを列挙した。
このテーブルは teamsyncd / tlm_teamd が書き込み、複数のデーモンが readiness ガードとして読む構造を持つ。

---

## A. LAG_TABLE が依存する入力（書き込みの前提）

### A-1. Linux カーネル netlink（RTM_NEWLINK / RTM_DELLINK）

- **経路**: `TeamSync::onMsg()` が `nl_object` から `RTM_NEWLINK` / `RTM_DELLINK` を受信し、
  `addLag()` / `removeLag()` を呼び出して LAG_TABLE を更新する。
- **証跡**: `teamsync.cpp:101-143`
- **影響**: netlink イベントが発生しない限り LAG_TABLE は書かれない。
  LAG netdev が存在しない（teamd が起動していない）場合はエントリが作成されない。

### A-2. teamdctl（tlm_teamd が内部で使用するソケット）

- **経路**: `TeamPortSync::readData()` が `teamdctl_connect()` + `teamdctl_config_get_raw_direct()` で
  teamd のプロセスソケットに接続し、JSON dump を取得する。
  `ValuesStore::update()` がその dump を解析して STATE_DB `LAG_TABLE` の追加フィールドを書き込む。
- **証跡**: `teamsync.cpp:317-348`, `values_store.cpp:352-380`
- **影響**: teamd プロセスが存在しない / teamdctl 接続失敗時は `setup.*` / `runner.*` / `team_device.*` フィールドが LAG_TABLE に書かれない。
  ただし `teamsync.cpp` が書いた `state`, `admin_status`, `oper_status`, `mtu` は残留する（`values_store.cpp:284-291`）。

### A-3. STATE_DB LAG_TABLE（tlm_teamd が自身を購読）

- **経路**: `tlm_teamd/main.cpp:98` — `SubscriberStateTable sst_lag(&db, STATE_LAG_TABLE_NAME)` で
  STATE_DB の `LAG_TABLE` を購読する。
  teamsyncd が `state=ok` を書いた時点でイベントを受信し `mgr.add_lag(lag_name)` を呼んで teamdctl 接続を開始する。
- **証跡**: `tlm_teamd/main.cpp:98-106`
- **影響**: teamsyncd による `state=ok` 書き込みが tlm_teamd の起動トリガーになっている（循環構造）。

---

## B. LAG_TABLE を読む外部参照（X → LAG_TABLE）

### B-1. intfmgrd（sonic-swss/cfgmgr/intfmgr.cpp）

- **用途**: `IntfMgr::isIntfStateOk(alias)` — LAG がL3 interface 設定の前提条件を満たすかチェック。
  `m_stateLagTable.get(alias, temp)` でエントリ存在確認。
- **証跡**: `intfmgr.cpp:38,663-668,833`
- **影響**: LAG_TABLE にエントリがない状態で `PORTCHANNEL_INTERFACE` を SET すると処理が保留される。

### B-2. teammgrd（sonic-swss/cfgmgr/teammgr.cpp）

- **用途**: `TeamMgr::isLagStateOk(alias)` — LAG が初期化済みか確認してからメンバーを enslave する。
  `m_stateLagTable.get(alias, temp)` でエントリ存在確認。
- **証跡**: `teammgr.cpp:38,89-103,357`
- **影響**: LAG_TABLE エントリがない段階で `PORTCHANNEL_MEMBER` を SET すると teamd への enslave が保留される。

### B-3. vlanmgrd（sonic-swss/cfgmgr/vlanmgr.cpp）

- **用途**: `VlanMgr::isMemberStateOk(alias)` — LAG を VLAN メンバに追加する前に LAG 状態を確認。
  `m_stateLagTable.get(alias, temp)` でエントリ確認。
- **証跡**: `vlanmgr.cpp:30,497`
- **影響**: LAG_TABLE エントリなしで `VLAN_MEMBER` に LAG を追加しようとすると処理が保留される。

### B-4. stpmgrd（sonic-swss/cfgmgr/stpmgr.cpp）

- **用途**: `StpMgr::isLagStateOk(alias)` — STP ポート処理前に LAG 状態を確認。
  `m_stateLagTable.get(alias, temp)` でエントリ確認。
- **証跡**: `stpmgr.cpp:32,1296`
- **影響**: LAG が STP ポートとして登録される前に LAG_TABLE エントリが必要。

### B-5. nbrmgrd（sonic-swss/cfgmgr/nbrmgr.cpp）

- **用途**: 隣接エントリ処理前に LAG 状態を確認する。
- **証跡**: `nbrmgr.cpp:47` `m_stateLagTable(stateDb, STATE_LAG_TABLE_NAME)`
- **影響**: LAG 経由の static neighbor 設定が遅延する可能性がある。

### B-6. natmgrd（sonic-swss/cfgmgr/natmgr.cpp）

- **用途**: NAT ポートマッピング設定前に LAG 状態を確認する。
  `m_stateLagTable.get(port, temp)` でエントリ確認 (`natmgr.cpp:111`)。
- **証跡**: `natmgr.cpp:38,111`
- **影響**: LAG を NAT インタフェースとして使用する場合、LAG_TABLE エントリが必要。

---

## C. 制約なし確認（明示的に除外したもの）

| テーブル | 判定 | 根拠 |
|---------|------|------|
| APP_DB APP_LAG_TABLE | 直接読まない | teamsyncd が同時に書くが LAG_TABLE とは独立 |
| orchagent portsorch | STATE_LAG_TABLE を直接読まない | APP_LAG_TABLE を購読して SAI に反映する |
| CHASSIS_APP_DB SYSTEM_LAG_TABLE | 直接参照なし | VoQ 専用; teamsyncd は STATE_LAG のみ書く |

---

## D. 暗黙参照まとめ（cross-refs ブロック用）

```
netlink(RTM_NEWLINK/DELLINK) → LAG_TABLE      (書き込みトリガー; teamsyncd)
teamdctl JSON dump            → LAG_TABLE      (追加フィールド書き込み; tlm_teamd)
LAG_TABLE                     → LAG_TABLE      (tlm_teamd 自身が SubscriberStateTable で自己購読)
LAG_TABLE ← intfmgrd          (PORTCHANNEL_INTERFACE readiness ガード)
LAG_TABLE ← teammgrd          (PORTCHANNEL_MEMBER enslave readiness ガード)
LAG_TABLE ← vlanmgrd          (VLAN_MEMBER LAG追加 readiness ガード)
LAG_TABLE ← stpmgrd           (STP ポート readiness ガード)
LAG_TABLE ← nbrmgrd           (静的隣接エントリ readiness ガード)
LAG_TABLE ← natmgrd           (NAT ポートマッピング readiness ガード)
```

---

## E. 証跡ソース一覧

| ファイル | 行番号 | 内容 |
|---------|--------|------|
| `sonic-swss/teamsyncd/teamsync.cpp` | 26-30 | `m_stateLagTable(stateDb, STATE_LAG_TABLE_NAME)` 初期化 |
| `sonic-swss/teamsyncd/teamsync.cpp` | 101-143 | `onMsg()` — RTM_NEWLINK/DELLINK 受信 |
| `sonic-swss/teamsyncd/teamsync.cpp` | 203,223,255 | `m_stateLagTable.set()` / `del()` |
| `sonic-swss/teamsyncd/teamsync.cpp` | 317-348 | teamdctl 接続・JSON 取得 |
| `sonic-swss/tlm_teamd/main.cpp` | 98-106 | `SubscriberStateTable sst_lag` で LAG_TABLE 購読 |
| `sonic-swss/tlm_teamd/values_store.cpp` | 284-291 | LAG_TABLE エントリを削除しない設計 |
| `sonic-swss/tlm_teamd/values_store.cpp` | 352-380 | `update_db()` で LAG_TABLE に追記 |
| `sonic-swss/cfgmgr/intfmgr.cpp` | 38,663-668,833 | `m_stateLagTable` 参照 |
| `sonic-swss/cfgmgr/teammgr.cpp` | 38,89-103,357 | `m_stateLagTable` 参照 |
| `sonic-swss/cfgmgr/vlanmgr.cpp` | 30,497 | `m_stateLagTable` 参照 |
| `sonic-swss/cfgmgr/stpmgr.cpp` | 32,1296 | `m_stateLagTable` 参照 |
| `sonic-swss/cfgmgr/nbrmgr.cpp` | 47 | `m_stateLagTable` 初期化 |
| `sonic-swss/cfgmgr/natmgr.cpp` | 38,111 | `m_stateLagTable` 参照 |
