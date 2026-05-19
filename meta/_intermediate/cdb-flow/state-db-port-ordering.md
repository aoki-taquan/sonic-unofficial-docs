# STATE_DB PORT_TABLE — Phase B 書込み順依存調査

調査日: 2026-05-19
ソース: sonic-swss portsyncd/linksync.cpp, orchagent/portsorch.cpp, cfgmgr/intfmgr.cpp, cfgmgr/buffermgrdyn.cpp, cfgmgr/teammgr.cpp, cfgmgr/natmgr.cpp, cfgmgr/macsecmgr.cpp

## portsyncd (linksync.cpp) の書込み前提条件

linksync.cpp:193-194: RTM_NEWLINK イベントが届いても、`m_portTable.get(key, temp)` が false を返す場合（APP_DB PORT_TABLE に該当ポートが未登録）、STATE_DB への書き込みはスキップされる。

### 順序: APP_DB PORT_TABLE → STATE_DB PORT_TABLE

portsyncd が STATE_DB に `state=ok` を書くためには、portsyncd 起動時に APP_DB `PORT_TABLE` にポートが登録済みであることが必須。APP_DB への登録は orchagent が CONFIG_DB `PORT` テーブルを処理して PortInitDone を発行した後。

```
CONFIG_DB PORT → orchagent/PortsOrch → APP_DB PORT_TABLE (PortInitDone)
    ↓
portsyncd が RTM_NEWLINK 受信 → STATE_DB PORT_TABLE|<name> set {state=ok, ...}
```

## consumer からの観測順序制約

### intfmgrd: PORT_TABLE.state=ok が前提ゲート

`intfmgr.cpp:649-695` の `isIntfStateOk()` は Ethernet インタフェースについて `m_statePortTable.get(alias, temp)` + `state` フィールドの存在を確認する。state フィールドが不在または PORT_TABLE エントリ自体が不在の場合は `false` を返し、IP アドレス付与（INTF_TABLE 書き込み）を保留する。

- **強制先行**: STATE_DB `PORT_TABLE|<name> state=ok` が書かれるまで、`intfmgrd` は当該ポートへの IP アドレス設定を開始しない
- コード根拠: `intfmgr.cpp:686-694` (isIntfStateOk) + `intfmgr.cpp:1115-1118` (setIntfIp ゲート)

### buffermgrdyn: supported_speeds で動的バッファ再計算トリガー

`buffermgrdyn.cpp:2224-2254` の `handlePortStateTable()` は `FLEX_COUNTER_STATUS enable` 後に STATE_PORT_TABLE の `supported_speeds` フィールドを監視し、autoneg 有効ポートのバッファ PG 再計算を起動する。

- **先行**: STATE_DB `PORT_TABLE|<name>` の `supported_speeds` フィールドが書かれた後に動的バッファ再計算が可能
- `supported_speeds` は PortsOrch が SAI `get_port_attribute(SAI_PORT_ATTR_SUPPORTED_SPEED)` 取得後に書き込む

### teammgrd: PORT_TABLE.state=ok でメンバー参加可否チェック

`teammgr.cpp:70-86` は LAG メンバーポートを追加する前に `m_statePortTable.get(alias, temp)` + `state` フィールドを確認する。存在しない場合はメンバーポート追加を保留。

### natmgr: PORT_TABLE エントリ存在で NAT エントリ有効化

`natmgr.cpp:119-126` は Ethernet ポートへの NAT 設定前に `m_statePortTable.get(port, temp)` を確認。エントリ未存在時は保留。

### macsecmgr: state=ok かつ netdev_oper_status=up で MACsec セッション開始

`macsecmgr.cpp:622-631` は `state=ok` AND `netdev_oper_status=up` の両条件が満たされた場合のみ MACsec セッション確立を開始する。`state=ok` 単独では不十分で oper up も必要。

## 書込み削除の順序

RTM_DELLINK 受信時は `m_statePortTable.del(key)` が即時実行される (linksync.cpp:183-185)。
この時点で各 consumer (intfmgrd / teammgrd / natmgrd / macsecmgrd) はポートが「not ready」状態として扱う。
対応する INTF_TABLE / LAG メンバー / NAT エントリ / MACsec セッションは consumer 側で個別に後続処理が行われる。

## 起動シーケンスの順序依存サマリ

```
1. CONFIG_DB PORT テーブル設定済み
   ↓
2. orchagent/PortsOrch: CONFIG_DB PORT を処理 → APP_DB PORT_TABLE に書き込み → PortInitDone
   ↓
3. portsyncd: カーネル netlink RTM_NEWLINK を受信
   → APP_DB PORT_TABLE にポートが存在することを確認
   → STATE_DB PORT_TABLE|<name> set {state=ok, admin_status, mtu, netdev_oper_status}
   ↓
4. intfmgrd / teammgrd / natmgrd / macsecmgrd / buffermgrdyn が STATE_DB を参照して後続処理を開始
   ↓
5. PortsOrch: SAI からの oper 情報（speed / fec / host_tx_ready）を追記書き込み
```

step 3 と step 5 は独立した非同期イベント（netlink vs SAI callback）のため、STATE_DB に `state=ok` が書かれた直後は `speed` / `fec` / `host_tx_ready` フィールドが未設定の可能性がある。
