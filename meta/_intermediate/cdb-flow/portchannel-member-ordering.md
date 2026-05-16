# PORTCHANNEL_MEMBER — Phase B 書込み順依存スキャンノート

対象テーブル: `PORTCHANNEL_MEMBER`
Consumer: `TeamMgr` (`sonic-swss/cfgmgr/teammgr.cpp`)、`PortsOrch::doLagMemberTask()` (`sonic-swss/orchagent/portsorch.cpp`)
スキャン範囲: 全行精読

---

## 検出した順序依存・タイミング依存

### 1. STATE_LAG_TABLE ready 先行必須（TeamMgr 側）

- `doLagMemberTask()` L357: `!isLagStateOk(lag)` が true（LAG が STATE_DB 未登録）の場合、当該タスクを `it++` でスキップ（リトライ待機）。
- `isLagStateOk()` L89-102: `m_stateLagTable.get(alias, temp)` でエントリが存在しなければ `false` を返す。
- `STATE_LAG_TABLE` には `teammgrd` の `addLag()` が成功した後、teamd プロセスが起動して LAG インタフェースを作成したタイミングで登録される。
- **順序依存**: `PORTCHANNEL_MEMBER` の SET 前に、対象 LAG（`PORTCHANNEL` テーブルエントリ）の SET が処理されて STATE_DB に `STATE_LAG_TABLE` エントリが存在すること。PORTCHANNEL を先に書いていない場合、または teamd が未起動の場合は自動リトライ待機する。
- evidence: `teammgr.cpp:89-102, 357`

### 2. STATE_PORT_TABLE ready 先行必須（TeamMgr 側）

- `doLagMemberTask()` L357: `!isPortStateOk(member)` が true（物理ポートが STATE_DB 未登録）の場合も同様にスキップ。
- `isPortStateOk()` L67-87: `m_statePortTable.get(alias, temp)` でエントリが存在しなければ `false`。さらに `state` フィールドが存在しなければ `false`。
- **順序依存**: `PORTCHANNEL_MEMBER` の SET 前に、メンバーとなる物理ポートが `STATE_PORT_TABLE` に `state=ok` で登録されていること。portmgrd が STATE_DB に書くまで自動リトライ待機する。
- evidence: `teammgr.cpp:67-87, 357`

### 3. LAG 存在確認（PortsOrch 側 / APP_DB 経由）

- `PortsOrch::doLagMemberTask()` L6264: `getPort(lag_alias, lag)` が false（LAG ポートオブジェクトが未登録）の場合、`it++` でスキップ（暗黙のリトライ待機）。
- **順序依存**: `APP_LAG_MEMBER_TABLE` へのエントリ（teammgrd が書く）は、orchagent が LAG オブジェクトを登録済みであることを前提とする。PORTCHANNEL の orchagent 処理が先行する必要がある。
- evidence: `portsorch.cpp:6264-6278`

### 4. VLAN_MEMBER との排他制約（SET 前チェック）

- `PortsOrch::doLagMemberTask()` L6338-6343: メンバーポートが `m_portVlanMember[port.m_alias].size() > 0` の場合（VLAN_MEMBER に登録済みのポート）は SET をスキップ（デバッグログ出力 + `it++` でリトライ待機）。
- **順序依存 (実質的な排他)**: ポートが VLAN のメンバーとして登録されている間は PORTCHANNEL_MEMBER に追加できない。先に `VLAN_MEMBER` から当該ポートを削除（DEL）してから `PORTCHANNEL_MEMBER` を SET する必要がある。
- evidence: `portsorch.cpp:6337-6343`

### 5. MACsec SA ready 待機（TeamMgr 側）

- `doLagMemberTask()` L362-366: `isMACsecAttached(member)` が true かつ `isMACsecIngressSAOk(member)` が false の場合、タスクをスキップ（リトライ待機）。
- **順序依存 (MACsec 有効時のみ)**: MACsec が設定されたポートを PORTCHANNEL のメンバーに追加する場合、MACsec の Ingress SA が STATE_DB に登録されるまで SET が保留される。
- evidence: `teammgr.cpp:362-366`

### 6. teamdctl ポート add の retry（IFF_UP 競合）

- `addLagMember()` L769-781: `teamdctl <lag> port add <member>` が失敗した場合、ポートが IFF_UP（admin up）状態であれば `task_need_retry` を返してリトライする。
- 理由: teamdctl はポートを admin down にしてから enslave するが、portmgrd などの外部プロセスが同時に admin up を試みると競合が発生する。
- **順序依存**: admin up 操作中のポートはリトライで最終収束する。外部から強制的に admin up にしながら PORTCHANNEL_MEMBER に追加しようとすると収束に時間がかかる。
- evidence: `teammgr.cpp:769-781`

### 7. DEL 順序（PORTCHANNEL_MEMBER → PORTCHANNEL の順）

- `addLag()` でポートチャネルを削除する際（DEL）、teamd プロセスは `removeLagMember()` 処理後に `removeLag()` を呼ぶ。
- **推奨順序**: PORTCHANNEL を削除する前に、すべての `PORTCHANNEL_MEMBER` エントリを DEL する。逆順（PORTCHANNEL 先 DEL）では teamd プロセスが停止し、残存する PORTCHANNEL_MEMBER タスクが孤立する可能性がある。
- evidence: `teammgr.cpp:303` (`addLag`)、`removeLagMember` / `removeLag` の呼出し順

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | PORTCHANNEL SET + STATE_LAG_TABLE ready → PORTCHANNEL_MEMBER SET | 強制先行 | PORTCHANNEL 先書き推奨、PORTCHANNEL_MEMBER は自動リトライ |
| 2 | STATE_PORT_TABLE ready (portmgrd) → PORTCHANNEL_MEMBER SET | 強制先行 | portmgrd ready まで自動リトライ |
| 3 | PORTCHANNEL orchagent 処理完了 → APP_LAG_MEMBER_TABLE 処理 | 強制先行 | PORTCHANNEL 先書きで自動収束 |
| 4 | VLAN_MEMBER DEL → PORTCHANNEL_MEMBER SET（同ポート） | 排他制約 | VLAN_MEMBER を先に DEL してから PORTCHANNEL_MEMBER を SET |
| 5 | MACsec Ingress SA ready → PORTCHANNEL_MEMBER SET (MACsec 有効時) | 強制先行 | MACsec SA 確立まで自動リトライ |
| 6 | admin down 収束 → teamdctl port add（IFF_UP 競合時） | 自動リトライ | 外部プロセスの admin up 競合がなければ即時収束 |
| 7 | PORTCHANNEL_MEMBER DEL → PORTCHANNEL DEL | 推奨順序 | 逆順では PORTCHANNEL_MEMBER タスクが孤立リスク |
