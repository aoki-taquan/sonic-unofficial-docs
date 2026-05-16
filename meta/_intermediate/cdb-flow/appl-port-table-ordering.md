# APPL_DB PORT_TABLE — Phase B 書込み順依存スキャンノート

対象テーブル: `PORT_TABLE`
Consumer: `PortsOrch::doTask(Consumer&)` (`sonic-swss/orchagent/portsorch.cpp`)
スキャン範囲: portsorch.cpp L1687-1704, L2186-2350, L4340-4400, L4600-4630, L4720-5520, L6420-6730
ref: `4305596156d70e9797e8a881b3d19b46de0bce0d`

---

## 検出した順序依存・タイミング依存

### 1. PortConfigDone → 一括ポート作成 → PortInitDone の 3 段階遷移

- L4752 `setPortConfigState(PORT_CONFIG_DONE)`: portsyncd が `PORT_TABLE:PortConfigDone` に `count` を書くと、PortsOrch は CONFIG_DB の `PORT` テーブルからレーン情報を集めて **bulk add** を実行し (`addPortBulk` / `initPortsBulk`, L4744-4749)、`m_portConfigState` を `PORT_CONFIG_DONE` に遷移させる。
- L4754-4771: `PORT_CONFIG_DONE` 到達後の追加 PORT_TABLE エントリ（breakout 後の追加ポート等）は個別に `addPortBulk` で逐次作成される。
- L4772-4777: `PORT_CONFIG_DONE` 未到達のまま個別 PORT_TABLE エントリが来た場合、`continue` で `m_toSync` に保留され retry される（順序違反は再試行で吸収）。
- L4613-4626: `PORT_TABLE:PortInitDone` を portsyncd から受信すると `m_initDone = true` 遷移（同時に `addSystemPorts()` を一度だけ実行）。これ以降 `isInitDone()` が true となり、BufferOrch / IntfsOrch 等の後段 orch が動き出す（`bufferorch.cpp:2079-2091` 等で参照）。
- L1687-1704: `isConfigDone()` と `isInitDone()` の判定境界。`isConfigDone()` は `PORT_CONFIG_DONE` 状態のみを見るが、`isInitDone()` は `m_initDone && m_pendingPortSet.empty()`、つまり PortInitDone 受信に加えて全ポートが `gBufferOrch->isPortReady()` を通過していることを要求する。
- 順序依存: **PortConfigDone → 個別 PORT_TABLE entry → PortInitDone** の portsyncd 側送出順は契約。個別 entry が PortConfigDone 前に到達しても `taskMap` で永続保留される。
- evidence: `portsorch.cpp:1687-1704, 4344-4395, 4598-4626, 4744-4777`

### 2. gBufferOrch->isPortReady() ガード（buffer 適用先行必須）

- L4779-4789: 各ポートの本設定（autoneg / speed / FEC / MTU / TPID / admin_status）に進む前に `gBufferOrch->isPortReady(pCfg.key)` を確認。false なら `m_pendingPortSet.emplace(...)` + `continue` で保留。
- BufferOrch 側（`bufferorch.cpp:254-275`）は BUFFER_PG / BUFFER_QUEUE の SAI bind 完了で `m_ready_list[port]` を `true` 化する。
- 順序依存: **BUFFER_PG / BUFFER_QUEUE の bind 完了 → PortsOrch のポート属性適用**。違反時はそのポートだけ `m_pendingPortSet` で保留され、`isInitDone()` も false のままになる（後段全 orch が止まる）。
- evidence: `portsorch.cpp:4779-4789, 1685-1688`

### 3. speed / FEC / autoneg / interface_type / adv_speeds / adv_interface_types の admin-down 要件

- speed (L5019-5078): `p.m_admin_state_up && !p.m_autoneg` なら `setPortAdminStatus(p, false)` を呼んで明示的にポートを落としてから `setPortSpeed()` を実行。autoneg が ON なら admin down せず speed を直接設定する。
- FEC (L5312-5379): `p.m_admin_state_up` なら無条件に admin down → `setPortFec()`。autoneg 無関係。
- autoneg (L4808-4869): `p.m_admin_state_up` なら admin down してから `setPortAutoNeg()`。
- interface_type (L5132-5180): `p.m_admin_state_up && !p.m_autoneg` なら admin down → `setPortInterfaceType()`。
- adv_speeds (L5080-5130): `p.m_admin_state_up && p.m_autoneg` （autoneg ON 限定）で admin down → `setPortAdvSpeeds()`。
- adv_interface_types (L5203-5251): `p.m_admin_state_up && p.m_autoneg` で admin down → `setPortAdvInterfaceTypes()`。
- L5494-5520 で全属性適用完了後に「`Restore admin status if the port was brought down`」コメント付きで `admin_status` を元値に戻す（L5500-5511, `Last step set port admin status` コメント L5506）。
- 順序依存: **(SAI で port が admin up のまま) speed/FEC/autoneg 等を書くと SAI ベンダ実装によっては reject される**ため、orchagent 側で必ず `admin down → 属性適用 → admin up restore` の 3 ステップを内部実行する。外部から見える APPL_DB `admin_status` は変化しない（最終値に戻る）が、SAI レイヤでは一時的に DOWN を経由する。
- evidence: `portsorch.cpp:4808-4869, 5019-5078, 5080-5130, 5132-5180, 5203-5251, 5312-5379, 5494-5520`

### 4. setHostTxReady の admin_state 前置同期

- L2196-2256 `setPortAdminStatus()`: admin_state を **false** にする場合は SAI `SAI_PORT_ATTR_ADMIN_STATE` を叩く**前**に `setHostTxReady(port, "false")` を STATE_DB に書く（L2202, L2219 コメント「Update the host_tx_ready to false before setting admin_state, when admin state is false」）。
- admin_state を **true** にする場合は SAI 呼び出し**後**に `setHostTxReady(port, "true")` を書く（L2256）。SAI 失敗時は `"false"` を書き戻す（L2222, L2236, L2248）。
- L6723 ポート初期化時の `setHostTxReady(port, hostTxReadyStr)`、L9724 SAI からの host_tx_ready 通知時の書き戻し。
- 順序依存: **admin down 方向は STATE_DB host_tx_ready の DOWN 反映が先**（trans/optics 側の TX を切ってから admin を落とす）。**admin up 方向は SAI 成功確認後**（ハードがリンク準備できてから host_tx_ready を true 化）。
- evidence: `portsorch.cpp:2196-2256, 2264-2300, 6720-6730, 9720-9730`

### 5. warm reboot 時の APPL_DB スナップショット要件

- L4342-4395 `bake()`: warm restart 起動時、PortsOrch は APPL_DB `PORT_TABLE` から `PortConfigDone` と `PortInitDone` の 2 キーを必須として確認 (L4345, L4350)。片方でも欠ければ `cleanPortTable()` で APPL_DB を一掃して cold start にフォールバック (L4357-4361)。
- `PortConfigDone:count` の値と APPL_DB に残るポートキー数 (`keys.size() - 2`) が一致しないと invalid と判断して同じく cold start (L4366-4374)。
- L4376-4384: 残ったポートキー全部を `m_pendingPortSet` に積む → buffer / 各属性が再適用されるまで `isInitDone()` は false。
- L753, L6428: コンストラクタで `m_isWarmRestoreStage = WarmStart::isWarmStart()` を採り、warm restore 完了通知 (`m_isWarmRestoreStage = false`) を境にしてポート初期化経路を分岐。
- L4076: 非 warm restore stage の場合に `cleanPortTable()` 等の cold path を実行（warm 中は APPL_DB を消さない）。
- L6617-6647 (oper_status の bake): warm reboot 時は `m_portTable->get()` で既存 `oper_status` を読み戻し、SAI 初期値の代わりに使う（前世代の up/down を保存）。
- L6655-6656: flap_count も warmboot 時は既存値を読み戻して継続。
- 順序依存: **portsyncd → PortConfigDone / PortInitDone を APPL_DB に書き終えてから orchagent を再起動**。順序違反（PortInitDone 欠落 / count 不一致）は即 cold start フォールバックで warmboot 失敗扱い。
- evidence: `portsorch.cpp:753, 4076, 4338-4395, 6420-6430, 6617-6660`

### 6. m_isWarmRestoreStage を見た bridge port / VLAN restore

- L4076-4080 `initializePort()` 系: 非 warm restore 経路のみ、`oper_status="down"` の初期書き込み（L6643）や各種初期化を実行。warm restore 中は APPL_DB に残るスナップショット値を温存する。
- L5499-5511 `Restore admin status if the port was brought down` コメント周辺: 警告は admin の最終回復のことだが、warm restore 中の値復元と挙動が連携する。
- 順序依存: warm restore 経路では「APPL_DB スナップショット読み戻し → SAI 状態再構築 → m_isWarmRestoreStage を false に落とす（L6428）」の順。

### 7. 個別属性の retry 経路（収束）

- speed / FEC / autoneg / interface_type / adv_speeds / adv_interface_types / MTU / TPID / serdes / media_type など全属性は `task_need_retry` 戻りで `it++` (taskMap erase せず) → 次回 `doTask` で再試行。
- 永久失敗系（auto FEC 非サポート、speed 非サポート、autoneg 非サポート 等）は `taskMap.erase(it)` で破棄しログ出力。
- 順序依存: 外部書込側が「全フィールドを同一 hset で投入」「個別 hset で逐次投入」どちらでも、orchagent は属性間順序を内部で再現する（admin down → 各属性 → admin restore）。

---

## まとめ: 外部書込側が守るべき順序

| 順序 | 操作 | 違反時 |
|---|---|---|
| 1 | portsyncd: `PortConfigDone:count` を書く | PortsOrch の `m_portConfigState` が PORT_CONFIG_DONE に上がらず、個別 PORT_TABLE エントリは保留される |
| 2 | portsyncd: 個別 `PORT_TABLE:<alias>` を書く (CONFIG_DB の全フィールド転写) | PortConfigDone 前は無視（保留）。同時投入可 |
| 3 | BufferOrch: `BUFFER_PG` / `BUFFER_QUEUE` SAI bind 完了 → `isPortReady(alias)=true` | false の間は本ポートの属性適用全部が保留 |
| 4 | portsyncd: `PortInitDone` を書く | `m_initDone` が立たず後段全 orch が止まる |
| 5 | warmboot 時: APPL_DB に `PortConfigDone` / `PortInitDone` / count 一致を残してから orchagent 再起動 | `cleanPortTable()` で APPL_DB 全削除 → cold start フォールバック |

orchagent 内部では、個別属性の admin-down 前置と admin restore は `PortsOrch::doTask()` が自動再現する。外部からは「admin_status と同時に speed/FEC 等を投入してよい」「最終 admin_status は守られる」が契約。

## grep カバレッジ

- `m_portConfigState` / `PORT_CONFIG_DONE` / `PortConfigDone`: L1240, L1245, L1696, L1704, L4345, L4378, L4598-4604, L4752, L4754
- `m_initDone` / `PortInitDone`: L1687, L1693, L4350, L4378, L4613-4626
- `m_isWarmRestoreStage` / `WarmStart::isWarmStart`: L753, L4076, L6428
- `gBufferOrch->isPortReady`: L4779
- `setPortAdminStatus(p, false)` (admin-down 前置): L4827, L5038, L5087, L5139, L5210, L5342（6 箇所すべて確認）
- `setHostTxReady`: L2202, L2222, L2236, L2248, L2256, L2264, L6723, L9724（8 hit、全精読）
- `Bring port down before applying`: 6 hit（autoneg/speed/adv_speeds/intf_type/adv_intf/fec）
- `Last step set port admin status`: L5506
