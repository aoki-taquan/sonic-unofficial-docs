# ports-status Phase B — 書込み順依存スキャンノート

対象: `STATE_DB PORT_TABLE|<port>` の書込み順序依存
調査コード: `portsyncd/linksync.cpp`, `orchagent/portsorch.cpp`, `cfgmgr/portmgr.cpp`, `cfgmgr/teammgr.cpp`, `cfgmgr/intfmgr.cpp`

## 検出された順序依存

### 依存 #1: portsyncd PortInitDone → PortsOrch 書込み開始

`portsyncd` が全設定ポートの netdev 作成を完了すると `APP_DB PORT_TABLE|PortInitDone` を publish する
(`portsyncd.cpp:134`)。`PortsOrch::doPortTask()` はこのメッセージを受信するまで `m_initDone=false` のまま
一切の設定処理を行わない (`portsorch.cpp:4613-4622`)。

`allPortsReady()` (`portsorch.cpp:1687`) は `m_initDone && m_pendingPortSet.empty()` を返し、
VLAN/LAG 等の処理もこのガードを経由する (`portsorch.cpp:6514, 9618`)。

**結果**: STATE_DB `PORT_TABLE|<port>.supported_speeds` / `host_tx_ready` 等の PortsOrch 由来フィールドは
PortInitDone 受信後に初めて書かれる。それ以前は STATE_DB エントリ自体が存在しない。

### 依存 #2: linksync RTM_NEWLINK → portmgrd / teammgrd / intfmgrd のアンロック

`portsyncd/linksync.cpp:196` が `PORT_TABLE|<port>` に `state="ok"` を書いた後、以下のデーモンが
`isPortStateOk()` のガードを解除してポート設定を進める:

| デーモン | guard | 参照箇所 |
|---------|-------|---------|
| `portmgrd` | `PortMgr::isPortStateOk()` — `state` フィールドが存在しない間は MTU/admin_status 設定をスキップ | `portmgr.cpp:86-100, 40, 73` |
| `teammgrd` | `TeamMgr::isPortStateOk()` — メンバー追加をスキップ | `teammgr.cpp:67-80, 357` |
| `intfmgrd` | `IntfMgr::isIntfStateOk()` — `statePortTable.get()` + `state` 確認後に IP アドレス設定 | `intfmgr.cpp:686-695` |

**結果**: カーネルが netdev を認識し linksync が `state="ok"` を書くまで、portmgrd/teammgrd/intfmgrd は
当該ポートへの設定を保留し `it++; continue;` で次イベントループに再試行する。

### 依存 #3: PortConfigDone → PortInitDone の 2 段階シーケンス

warm start 復元時、`PortsOrch` は `APP_DB PORT_TABLE|PortConfigDone` が存在し **かつ** `PortInitDone` が
存在する場合のみ既存データを `addExistingData()` で再読み込みする (`portsorch.cpp:4357`)。どちらか一方でも
欠けている場合は cold start フォールバックとして `cleanPortTable()` で全削除する。

### 依存 #4: SAI `create_port` → supported_speeds / host_tx_ready 書込み

`PortsOrch::addPort()` / `addPortBulk()` が SAI ポートを作成した後、`initPortSupportedSpeeds()` 
(`portsorch.cpp:3090`) が `supported_speeds` を STATE_DB へ書く。`initHostTxReadyState()` 
(`portsorch.cpp:2181-2207`) も同タイミングで `host_tx_ready="false"` を初期化する。

**結果**: SAI create_port が成功しない限り `supported_speeds` / `host_tx_ready` が STATE_DB に現れない。

### 依存 #5: gBufferOrch::isPortReady → PortsOrch ポート設定反映

`PortsOrch::doPortTask()` は各ポートについて `gBufferOrch->isPortReady(alias)` が false の間
`m_pendingPortSet` に追加して設定反映を保留する (`portsorch.cpp:4779-4788`)。BufferOrch のバッファプロファイル
適用が完了するまで `m_pendingPortSet.empty()` が false のため `allPortsReady()` が false を返し続ける。

## 線形時系列サマリ

```
portsyncd: 全 netdev 作成 → APP_DB PortConfigDone publish
linksync: RTM_NEWLINK → STATE_DB PORT_TABLE|<port>.state="ok" 書込み
  → portmgrd / teammgrd / intfmgrd がアンロック
PortsOrch: PortInitDone 受信 (m_initDone=true)
  + gBufferOrch::isPortReady=true (m_pendingPortSet.erase)
  → allPortsReady()=true
  → supported_speeds / host_tx_ready 初期化書込み
  → VLAN / LAG タスク処理開始
```
