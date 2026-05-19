# ports-status Phase F 調査ノート — SET/DEL 副次 DB 書込み

## 対象テーブル

`STATE_DB PORT_TABLE|<port>` — portsyncd/linksync と PortsOrch が書き込む

## 調査方針

このテーブルは「書き込まれる側」。副次効果は「他デーモンがこのテーブルの変化を読み取って自身の処理を進める」形で現れる。

## 副次効果一覧

### 1. portmgrd アンロック

- 検出コード: `portmgr.cpp:40-54, 73-82, 163`
- `isPortStateOk()` が `state` フィールドの存在を確認し、true なら netdev 設定コマンドを発行
- 出力: カーネル netdev (ip link set) — DB 書込みなし
- トリガーフィールド: `state = "ok"`

### 2. teammgrd アンロック

- 検出コード: `teammgr.cpp:67-80, 357`, `teammgrd.cpp:57-63`
- STATE_PORT_TABLE_NAME を TableConnector で購読
- `isPortStateOk(member)` が true なら addLagMember() → teamdctl 呼び出し
- 出力: teamd プロセス (カーネル LAG メンバー追加)
- トリガーフィールド: `state = "ok"`

### 3. intfmgrd アンロック

- 検出コード: `intfmgr.cpp:46-47, 686-695, 1183`
- STATE_PORT_TABLE_NAME を Consumer として購読
- `state = "ok"` 受信で IP/VRF 設定を適用
- 出力: APPL_DB INTF_TABLE (ProducerStateTable) + カーネル netdev
- トリガーフィールド: `state = "ok"`

### 4. sflowmgr 速度追従

- 検出コード: `sflowmgr.cpp:167-211, 414-418`, `sflowmgrd.cpp:32-38`
- STATE_PORT_TABLE_NAME を TableConnector で購読
- `speed` フィールド変化時に sflowProcessOperSpeed() でサンプリングレート再計算
- 出力: APPL_DB SFLOW_SESSION_TABLE (m_appSflowSessionTable.set())
- トリガーフィールド: `speed`

### 5. buffermgrdyn PG ヘッドルーム再計算

- 検出コード: `buffermgrdyn.cpp:2224-2255, 451`
- STATE_PORT_TABLE_NAME → handlePortStateTable にマップ登録
- `supported_speeds` 変化 + auto_neg + ケーブル長設定済み時に refreshPgsForPort()
- 出力: APPL_DB BUFFER_PG_TABLE (headroom 更新)
- トリガーフィールド: `supported_speeds`

## 読み取り専用（副次 DB 書込みなし）

- natmgr: m_statePortTable.get() で状態確認のみ
- macsecmgr: m_statePortTable.get() で状態確認のみ
- nbrmgr: 近隣設定前の状態確認のみ
- vlanmgr: m_statePortTable.get() で状態確認のみ

## ソースコミット

- sonic-swss ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
