# ports-status Phase C 中間調査ノート

## 対象

STATE_DB `PORT_TABLE|<port>` の Phase C（暗黙参照テーブル）調査。

## 書込みトリガ側の依存

### portsyncd/linksync (linksync.cpp)

- `linksync.cpp:147-160`: `LinkSync` コンストラクタで `m_ifindexOidMap` を初期化。portsyncd が APP_PORT_TABLE 全件を読んで ifindex → ポート名マップを構築する。
- `linksync.cpp:193-208`: `onMsg()` で RTM_NEWLINK 受信時に `m_ifindexOidMap.find(ifindex)` でポート名を解決してから `m_statePortTable.set(key, fvs)` を呼ぶ。マップに存在しない ifindex は `SWSS_LOG_INFO("Skip netlink event for unknown ifindex")` でスキップ。

### PortsOrch (portsorch.cpp)

- `portsorch.cpp:4345-4386`: warm start 時に `m_portTable->hget("PortConfigDone", "count")` と `m_portTable->get("PortInitDone")` で APPL_DB の起動フラグを確認。両フラグが揃わないと `cleanPortTable()` を呼んで cold start にフォールバック。
- `portsorch.cpp:3090`: ポート作成直後に `initPortSupportedSpeeds()` → STATE_DB へ書込み。
- `portsorch.cpp:2181-2207`: `initHostTxReadyState()` → STATE_DB `host_tx_ready` 書込み。

## 読み出し側（STATE_DB PORT_TABLE を参照するデーモン）

### portmgr.cpp:86-100 (PortMgr::isPortStateOk)

```cpp
bool PortMgr::isPortStateOk(const string &alias)
{
    vector<FieldValueTuple> temp;
    if (m_statePortTable.get(alias, temp))
    {
        auto stateOptional = swss::fvsGetValue(temp, "state", true);
        return stateOptional != std::nullopt;
    }
    return false;
}
```

`portmgr.cpp:40,73`: `doPortTask()` で admin_status / mtu 設定前に `isPortStateOk()` 呼び出し。false なら設定スキップ。

### teammgr.cpp:67-80 (TeamMgr::isPortStateOk)

```cpp
bool TeamMgr::isPortStateOk(const string &alias)
{
    ...
    if (!m_statePortTable.get(alias, temp))
        return false;
    ...
}
```

`teammgr.cpp:357`: `doPortChannelMemberTask()` で LAG メンバー追加前に各メンバーポートを `isPortStateOk()` で確認。

### intfmgr.cpp:37,46-47,686-695

- `intfmgr.cpp:37`: `m_statePortTable(stateDb, STATE_PORT_TABLE_NAME)` で STATE_DB PORT_TABLE を保持。
- `intfmgr.cpp:46-47`: `SubscriberStateTable(STATE_PORT_TABLE_NAME)` で変更を subscribe。RTM_NEWLINK で `state="ok"` が書かれると intfmgrd が通知を受け取る。
- `intfmgr.cpp:686-695`: `isIntfStateOk()` で `m_statePortTable.get(alias, temp)` を確認してから IP / VRF 設定を適用。

## oper_status は APPL_DB に書く（STATE_DB ではない）

- `portsorch.cpp:3916-3930`: `updateDbPortOperStatus()` は `m_portTable->set()` を使い **APPL_DB** `PORT_TABLE` に書く。`STATE_DB PORT_TABLE` の `netdev_oper_status` (linksync 書込み) とは独立。

## 起動シーケンスとの関係

```text
[起動時]
portsyncd → CONFIG_DB PORT を読む → APP_DB PORT_TABLE 書込み → m_ifindexOidMap 構築
  ↓
kernel RTM_NEWLINK 受信 → linksync → STATE_DB PORT_TABLE.state = "ok"
  ↓
portmgrd / teammgrd / intfmgrd が isPortStateOk() / subscribe 通知で設定適用開始
```

`RTM_DELLINK` → `m_statePortTable.del(key)` → エントリ削除 → 各デーモンがブロック状態に戻る。
