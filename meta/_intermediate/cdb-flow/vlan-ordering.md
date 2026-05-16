# VLAN — Phase B 書込み順依存スキャンノート

対象テーブル: `VLAN` / `VLAN_MEMBER`
Consumer: `vlanmgrd` (`sonic-swss/cfgmgr/vlanmgr.cpp`)
スキャン範囲: 全行精読 (L1-1009)

---

## 検出した順序依存・タイミング依存

### 1. gMacAddress 未確定ガード（VLAN テーブル処理の全ブロック）

- `doVlanTask()` L318-322: `isVlanMacOk()` = `!!gMacAddress` が false（スイッチ MAC が未確定）の間、全タスクを即 return してキューに残す。
- `gMacAddress` は vlanmgrd コンテナ起動時にグローバル変数として初期化される。syncd が起動して SAI がスイッチ MAC を確定させるまでは未確定になる場合がある。
- **順序依存**: syncd 起動によるスイッチ MAC 確定 → `gMacAddress` 有効化 → `VLAN` SET 処理開始。それまでの全 SET は保留される（キュー消費されない）。
- evidence: `vlanmgr.cpp` L311-322

### 2. PORT / LAG の STATE_DB ready 先行必須（VLAN_MEMBER 処理）

- `doVlanMemberTask()` L642-647: `isMemberStateOk(port_alias)` が false の場合、当該メンバータスクを `it++` でスキップ（リトライ待機）。
- `isMemberStateOk()` L491-514: 物理ポートは `STATE_PORT_TABLE` に state フィールドが存在すること、LAG は `STATE_LAG_TABLE` にエントリが存在することを確認。
- **順序依存**: `VLAN_MEMBER|Vlan<N>|Ethernet<X>` の SET 前に、当該ポートが STATE_DB `PORT_TABLE` に `state=ok` で登録されていること。portmgrd / teamd が ready を上げるまで VLAN_MEMBER SET は自動リトライ待機する。
- evidence: `vlanmgr.cpp` L491-514, L642-647

### 3. VLAN の STATE_DB ready 先行必須（VLAN_MEMBER 処理）

- `doVlanMemberTask()` L642: `isVlanStateOk(vlan_alias)` が false の場合も同様にスキップ。
- `isVlanStateOk()` L517-531: `STATE_VLAN_TABLE` に `Vlan<N>` エントリが存在することを確認。
- `STATE_VLAN_TABLE` には `doVlanTask()` が成功した後、L441-443 で `m_stateVlanTable.set(key, [("state","ok")])` が書き込まれる。
- **順序依存**: `VLAN_MEMBER` の SET より前に `VLAN` の SET が処理されていること（STATE_DB に `state=ok` が立っていること）。VLAN_MEMBER を先に書いた場合、VLAN SET の処理完了（STATE_DB 書込み）まで自動リトライ待機する。
- evidence: `vlanmgr.cpp` L437-443, L517-531, L642

### 4. DEL 順序（VLAN_MEMBER → VLAN の順序が必要）

- `doVlanTask()` DEL 処理 L456-471: `m_vlans` にエントリが存在する場合、`removeHostVlan()` → `m_appVlanTableProducer.del()` → `m_stateVlanTable.del()` を直ちに実行する。VLAN_MEMBER の残存チェックは**行わない**。
- **副作用**: VLAN を先に DEL すると、STATE_DB から `Vlan<N>` エントリが削除されるため、残存する `VLAN_MEMBER` エントリは `isVlanStateOk()` チェックで永遠に ready にならず滞留する。
- **順序依存**: VLAN を削除する場合は、先に全 `VLAN_MEMBER` を DEL してから `VLAN` を DEL する必要がある。逆順（VLAN 先 DEL）では VLAN_MEMBER タスクが孤立する。
- evidence: `vlanmgr.cpp` L456-471, L642

### 5. VLAN_INTERFACE との関係（intfmgr の待機ロジック）

- `intfmgr.cpp` L649-658: `isIntfStateOk()` は `VLAN_PREFIX` で始まるインタフェースに対し `STATE_VLAN_TABLE` にエントリが存在するかを確認する。
- `VLAN_INTERFACE|Vlan<N>|<prefix>` の SET 処理 (L1112-1117): `isIntfStateOk(alias)` が false の場合スキップ（リトライ待機）。
- **順序依存**: `VLAN_INTERFACE` を SET する前に `VLAN` の SET が処理されていること（STATE_VLAN_TABLE ready）。VLAN 未作成のまま VLAN_INTERFACE を書くと intfmgr がリトライ待機し、IP アドレス設定が保留される。
- evidence: `intfmgr.cpp` L649-658, L1112-1117

### 6. warm-restart / restart 影響

- `VlanMgr` コンストラクタ L41-75 (warm-start パス):
  - warm-start 検出時、`ip link show Bridge` が成功する場合はブリッジ再作成をスキップ（`"vlanmgrd warm start, skipping bridge create"`）。
  - `m_vlanReplay` / `m_vlanMemberReplay` セットを CONFIG_DB から事前構築し、replay を追跡する。
- `doVlanTask()` L371-378: STATE_DB に既存かつ `m_vlans` 未登録のエントリは「warm restart で既作成」と判断し `m_vlans.insert()` のみ行い、Linux VLAN 再作成をスキップ。
- `doVlanTask()` L479-488, `doVlanMemberTask()` L714-723: `m_vlanReplay` と `m_vlanMemberReplay` が両方空になったとき `WarmStart::REPLAYED` → `RECONCILED` に遷移。
- **warm-reboot 影響**: VLAN の Linux ブリッジはカーネル空間で維持されるため、swss docker restart 程度では消えない。ただし全停止型再起動（コールドリブート）ではブリッジが消えるため、CONFIG_DB からの全 VLAN/VLAN_MEMBER 再処理が必要。
- **restart 後の注意**: swss docker restart では SAI 側の VLAN は orchagent が再構築する。vlanmgrd は STATE_DB ベースで重複をスキップするため、基本的に自動復元する。
- evidence: `vlanmgr.cpp` L41-75, L371-378, L479-488

### 7. minigraph 経由のバルク投入と members@ フィールド

- `doVlanTask()` L451-454: `members@` フィールドが存在する場合、`processUntaggedVlanMembers()` を呼び VLAN_MEMBER の SET を内部的に挿入する。
- `processUntaggedVlanMembers()` L552-590: カンマ区切りのメンバーリストを `CFG_VLAN_MEMBER_TABLE_NAME` の consumer キューに直接投入し、即 `doTask()` を呼ぶ。
- **順序依存**: minigraph からのバルク投入では `VLAN` と `members@` が同時に書かれるため、VLAN 作成と VLAN_MEMBER 処理が同一ループ内で順序保証される。ただしポートが STATE_PORT_TABLE に ready 状態でなければ VLAN_MEMBER の処理は後回しになる。
- evidence: `vlanmgr.cpp` L408-410, L451-454, L552-590

### 8. Linux IF 設定順（addHostVlan / addHostVlanMember 内部コマンド順序）

`addHostVlan()` (`vlanmgr.cpp:118-143`):

1. `bridge vlan add vid <N> dev Bridge self` — dot1q ブリッジへの VLAN ID 登録
2. `ip link add link Bridge up name Vlan<N> address <gMacAddress> type vlan id <N>` — VLAN インタフェース作成
3. `echo 0 > /proc/sys/net/ipv4/conf/Vlan<N>/arp_evict_nocarrier` — arp_evict_nocarrier 無効化（ベストエフォート）

ステップ 1→2 は `&&` チェーンで実行。ステップ 2 失敗は `EXEC_WITH_ERROR_THROW` で例外→プロセスクラッシュ。ステップ 3 は `swss::exec` でソフト実行（失敗しても継続）。

`addHostVlanMember()` (`vlanmgr.cpp:233-273`):

1. `ip link set <port_alias> master Bridge` — ポートをブリッジに収容
2. `bridge vlan del vid 1 dev <port_alias>` — デフォルト VLAN 1 削除
3. `bridge vlan add vid <N> dev <port_alias> [pvid untagged]` — 指定 VLAN 追加

同じく `&&` チェーン。PortChannel は失敗時に `false` を返してリトライ、Ethernet は `EXEC_WITH_ERROR_THROW` 再実行→クラッシュ。

- **順序依存**: ステップ 1 完了（ブリッジ VLAN ID 登録）→ ステップ 2（インタフェース作成）は内部順序保証。外部からの介入で任意順序変更は不可。
- evidence: `vlanmgr.cpp` L118-143, L233-273

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | gMacAddress 確定 (syncd/SAI) → VLAN SET 処理 | 強制先行 | なし（自動リトライ）|
| 2 | STATE_PORT_TABLE ready → VLAN_MEMBER SET 処理 | 強制先行 | portmgrd/teamd ready まで自動リトライ |
| 3 | VLAN SET 完了 (STATE_VLAN_TABLE ready) → VLAN_MEMBER SET 処理 | 強制先行 | VLAN 先書き推奨、VLAN_MEMBER は自動リトライ |
| 4 | VLAN_MEMBER DEL 完了 → VLAN DEL | 必須（逆順 NG）| VLAN_MEMBER を先に DEL してから VLAN を DEL |
| 5 | VLAN SET 完了 (STATE_VLAN_TABLE ready) → VLAN_INTERFACE SET 処理 | 強制先行 | VLAN 先書き推奨、intfmgr が自動リトライ |
| 6 | warm-restart: Linux ブリッジ既存 → ブリッジ作成スキップ | 自動スキップ | warm-reboot では影響なし、コールドリブートは全再処理 |
| 7 | VLAN SET 完了 → members@ 経由 VLAN_MEMBER 処理 | 同一ループ内順序保証 | minigraph バルク投入では自動処理 |
| 8 | addHostVlan: bridge vlan add → ip link add → arp_evict_nocarrier | 内部コマンド順序（固定） | 変更不可、外部から干渉手段なし |
| 9 | addHostVlanMember: ip link set master → bridge vlan del vid 1 → bridge vlan add | 内部コマンド順序（固定） | 変更不可、PortChannel のみリトライ |
