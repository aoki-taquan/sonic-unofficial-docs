# BFD_SESSION — Phase B 書込み順依存スキャンノート

対象テーブル: `BFD_SESSION`
Consumer: `BfdOrch::doTask()` / `BfdOrch::create_bfd_session()` (`sonic-swss/orchagent/bfdorch.cpp`)
スキャン範囲: L1-841 全行精読 (L111-217 doTask, L305-574 create_bfd_session)

---

## 検出した順序依存・タイミング依存

### 1. PORT 初期化先行必須（hardware-lookup 無効モード）

- `create_bfd_session()` L482-489: `alias != "default"` (= interface 指定 = `SAI_BFD_SESSION_ATTR_HW_LOOKUP_VALID=false`) のとき `gPortsOrch->getPort(alias, port)` を呼び、port が見つからなければ `SWSS_LOG_ERROR("Failed to locate port %s")` で `return false`。
- 呼び出し元 `doTask()` L173-177 / L160-164 は `create_bfd_session()` が false を返した場合 `it++` で次のループへ持ち越し、次の Consumer 周回で**再試行**される（無限ポーリング）。
- 順序依存: `PORT|<alias>` が PortsOrch で初期化完了し `m_portList` に登録済みであること。
- evidence: `bfdorch.cpp:485-488`, `bfdorch.cpp:160-177`

### 2. VRF 先行必須（vrf 指定時、hardware-lookup 有効モード）

- `create_bfd_session()` L530-541: `alias == "default"`（hw lookup 有効）かつ `vrf_name != "default"` のとき `gDirectory.get<VRFOrch*>()->getVRFid(vrf_name)` を呼び、SAI 仮想ルータ OID を `SAI_BFD_SESSION_ATTR_VIRTUAL_ROUTER` に詰める。
- `getVRFid()` は VRF 未登録時に `SAI_NULL_OBJECT_ID` を返し、後段の `sai_bfd_api->create_bfd_session()` が失敗 → `retry_create_bfd_session()` 経由でも回復せず、最終的には `handleSaiCreateStatus()` で扱われる。
- doTask 側で false 返却時に `it++` する経路（依存 #1 と同じ）なので、**VRF 作成完了まで自動再試行**される。
- 順序依存: `VRF|<name>` が VRFOrch で SAI 作成完了していること。
- evidence: `bfdorch.cpp:530-541`, `bfdorch.cpp:160-177`

### 3. interface != "default" のとき VRF != "default" は拒否（順序ではなく排他制約）

- `create_bfd_session()` L498-503: `alias != "default"` かつ `vrf_name != "default"` のとき `"vrf is not supported when hardware lookup not valid"` で `return true`（再試行されずスキップ）。
- これは順序依存ではなく構成排他だが、operator が同時投入した場合に hw-lookup-off 経路が VRF を許容しない点を運用上意識する必要がある。
- evidence: `bfdorch.cpp:498-503`

### 4. dst_mac 必須/禁止条件（順序ではないが create 失敗ハンドリング）

- L491-496: `alias != "default"` で `dst_mac` 未指定 → `return true`（スキップ、再試行なし）。
- L523-528: `alias == "default"` で `dst_mac` 指定 → `return true`（スキップ、再試行なし）。
- これらは「正しいフィールドを揃えてから書け」というレコード内整合性。順序依存ではないが、Phase B の write-flow 観点では「不整合な SET は永続的に作成されない」点を併記しておく。
- evidence: `bfdorch.cpp:491-528`

### 5. local_addr 必須（src_ip_provided）

- L350, L379, L409-413: `local_addr` フィールドが SET に含まれていない場合 `src_ip_provided=false` のままで `SWSS_LOG_ERROR("source IP is not provided")` 出力し `return true`（スキップ、再試行なし）。
- これも順序ではなくフィールド内必須性。
- evidence: `bfdorch.cpp:350,379,409-413`

### 6. BGP_DEVICE_GLOBAL 先読みによる経路分岐（software vs hardware BFD）

- `doTask()` L114-121: 各イベント処理冒頭で `gDirectory.get<BgpGlobalStateOrch*>()` を取り、`getTsaState()` と `getSoftwareBfd()` を毎回読み出す。
- `use_software_bfd == true` のとき SAI を経由せず STATE_DB `SOFTWARE_BFD_SESSION_TABLE` に転記して終了（L133-138）。
- `BGP_DEVICE_GLOBAL.STATE.use_software_bfd` の書き換えタイミングと BFD_SESSION の SET タイミングが交錯すると、同一セッションが hardware/software 経路を行き来する可能性あり。**use_software_bfd を先に確定**してから BFD_SESSION を投入することが望ましい。
- evidence: `bfdorch.cpp:114-121, 133-138`

### 7. TSA (Traffic Shift Away) 状態遷移と shutdown_bfd_during_tsa の連動

- `doTask()` L155-169: `shutdown_bfd_during_tsa=true` のセッションは `bfd_session_cache[key]` に常にキャッシュされ、`tsa_enabled` のときは `notify_session_state_down()` のみで SAI 作成をスキップ。
- TSA が解除されると `BfdOrch::doTask(NotificationConsumer&)` 側で cache を replay して SAI 作成する設計（L220 以降）。
- 順序依存: TSA 状態と BFD_SESSION SET の到着順は **どちらが先でも自動調停**される（cache + notification 機構）。
- evidence: `bfdorch.cpp:141-178, 220+`

### 8. switch 初期化（gSwitchId / gVirtualRouterId）先行必須

- `create_bfd_session()` L533: `vrf == "default"` のときグローバル `gVirtualRouterId` を SAI 属性に詰める。L547: `sai_bfd_api->create_bfd_session(&bfd_session_id, gSwitchId, ...)`。
- これらは orchagent 起動時に SwitchOrch が初期化するグローバル。BfdOrch 自体が SwitchOrch より後段で生成されるため、通常運用では問題にならない。
- evidence: `bfdorch.cpp:27, 533, 547`

### 9. UDP 送信元ポート重複時の自動 retry（順序とは独立）

- `retry_create_bfd_session()` (`bfdorch.cpp` `NUM_BFD_SRCPORT_RETRIES = 3`): UDP src port 49152-65535 範囲で衝突した場合に最大 3 回まで自動再選択して create を再試行。
- 順序依存ではないが、同一ノードで大量の BFD セッションを同時投入したときの観測ポイントとして記録。
- evidence: `bfdorch.cpp` (NUM_BFD_SRCPORT_RETRIES マクロ周辺)

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | `PORT|<alias>` 初期化完了 → BFD_SESSION SET (`interface != "default"`) | 強制先行（自動再試行で調停） | doTask の `it++` で次周回再試行 |
| 2 | `VRF|<name>` SAI 作成完了 → BFD_SESSION SET (`vrf != "default"`) | 強制先行（自動再試行で調停） | SAI 失敗 → 次周回再試行 |
| 3 | `interface != "default"` と `vrf != "default"` の併用 | 排他（順序ではない） | 構成チェックでブロック（再試行なし） |
| 4 | `dst_mac` と `interface` のレコード内整合性 | 必須/禁止条件 | 不整合 SET は永続スキップ |
| 5 | `local_addr` 必須 | フィールド内必須性 | 未指定はエラーログのみ |
| 6 | `BGP_DEVICE_GLOBAL.STATE.use_software_bfd` 確定 → BFD_SESSION SET | 推奨先行（途中変更で経路移動） | use_software_bfd を先に確定 |
| 7 | TSA 状態遷移 ⇄ BFD_SESSION SET | 自動調停（cache + notification） | shutdown_bfd_during_tsa=true で cache 保持 |
| 8 | SwitchOrch (`gSwitchId`/`gVirtualRouterId`) 先行 | 強制先行（通常運用で自然満足） | orchagent 起動順で担保 |
| 9 | UDP src port 衝突 → 自動 retry | 自動（最大 3 回） | NUM_BFD_SRCPORT_RETRIES |
