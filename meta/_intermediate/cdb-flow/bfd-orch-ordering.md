# BFD_SESSION_TABLE (bfdorch) — Phase B 書込み順依存スキャンノート

対象テーブル: APPL_DB `BFD_SESSION_TABLE`
Consumer: `BfdOrch::doTask(Consumer&)` (`sonic-swss/orchagent/bfdorch.cpp`)
スキャン範囲: L111-218 (`doTask`)、L270-303 (`register_bfd_state_change_notification`)、L305-574 (`create_bfd_session`)、L683-704 (`handleTsaStateChange`)、L755-791 (`offload_supported`)、L793-840 (`BgpGlobalStateOrch::doTask`) を精読

---

## 検出した順序依存・タイミング依存

### 1. PORT (PortsOrch) 先行必須 — `alias != "default"` 経路

- `create_bfd_session()` L482-490: `alias != "default"` のとき `gPortsOrch->getPort(alias, port)` を呼ぶ。失敗時は `SWSS_LOG_ERROR("Failed to locate port %s")` で **`return false`**（= `it++` で待機ループ、次イベントループで再試行）。
- bfdorch には PortsOrch readiness ガード（`allPortsReady()`）が**ない**ため、`alias == "default"`（hardware lookup）の純 L3 BFD は PORT 未初期化でも処理が進む。
- 順序依存: 出力インタフェース指定 BFD では `PORT|<alias>` が PortsOrch に登録済みであること。
- evidence: `bfdorch.cpp:482-490`

### 2. VRF (VRFOrch) 先行必須 — `vrf != "default"` 経路

- `create_bfd_session()` L530-541: `alias == "default"`（hardware lookup）かつ `vrf_name != "default"` のとき `VRFOrch::getVRFid(vrf_name)` を呼んで `SAI_BFD_SESSION_ATTR_VIRTUAL_ROUTER` を解決する。`getVRFid` は未登録 VRF に対して `SAI_NULL_OBJECT_ID` を返すため SAI create が失敗する。
- bfdorch 側に VRF 待機ループは無いため、未登録 VRF を指定すると SAI 失敗 → `retry_create_bfd_session` で 3 回まで再試行 → 最終的に `handleSaiCreateStatus` が `task_need_retry` を返せばイベントループ再試行で解消されうる。
- 順序依存: `VRF|<name>` が VRFOrch に登録済みである（hardware lookup ＋ 非 default VRF）こと。
- evidence: `bfdorch.cpp:530-541`, `bfdorch.cpp:546-560`

### 3. BgpGlobalStateOrch 先行と software BFD 経路切替

- `doTask()` L114-121: `gDirectory.get<BgpGlobalStateOrch*>()` の取得が成功すれば `getTsaState()` / `getSoftwareBfd()` を呼ぶ。失敗時は `tsa_enabled=false`, `use_software_bfd=true` をデフォルトとし**強制的に software 経路**になる。
- `BgpGlobalStateOrch` コンストラクタ (L729-736) で `bfd_offload = offload_supported(IPv4) && offload_supported(IPv6)` を **1 回だけ評価**する。`getSoftwareBfd()` は `!bfd_offload` を返す純粋関数。
- → 順序依存: `BgpGlobalStateOrch` が Orchagent 起動シーケンスで `bfdorch` より**先に**生成されていなければ、すべての BFD セッションが software 経路 (STATE_DB 転記のみ) に倒れる。
- 切替タイミング: hardware → software / software → hardware の動的切替は**不可能**。判定は orchagent (swss コンテナ) 起動時 1 回のみで、変更には swss 再起動が必要。
- evidence: `bfdorch.cpp:114-121, 729-736, 749-753, 755-791`

### 4. software BFD 経路の write 順序差分

- `doTask()` L131-139 (SET) / L180-188 (DEL): `use_software_bfd == true` のとき、SAI を呼ばずに `m_stateSoftBfdSessionTable->set/del(createStateDBKey(key), data)` のみ実行して即 erase する。
- このパスでは `create_bfd_session()` を通らないため PORT / VRF / SAI capability 依存はすべて回避される。代わりに **STATE_DB `SOFTWARE_BFD_SESSION_TABLE` の購読者 (`bgpcfgd/BfdMgr` 経由で FRR bfdd)** が後段で読み取る。
- 順序依存: software 経路では bfdorch 内に依存は無いが、`bgpcfgd` が STATE_DB を購読開始してから書き込まれた分のみ反映されるため、起動順 (`bgpcfgd` → `swss/bfdorch`) のレースに弱い。
- evidence: `bfdorch.cpp:131-139, 180-188, 706-727`

### 5. SAI state-change 通知ハンドラ登録（最初の SET で 1 回だけ）

- `create_bfd_session()` L307-315: 静的フラグ `register_state_change_notif` が false の間、最初の SET で `register_bfd_state_change_notification()` を呼ぶ。失敗時 `"BFD session for %s cannot be created"` を ERROR 出力して **`return false`**（= `it++` で再試行）。
- `register_bfd_state_change_notification()` (L270-303): `SAI_SWITCH_ATTR_BFD_SESSION_STATE_CHANGE_NOTIFY` の `set_implemented` が false の ASIC では永続的に false を返す → そのプラットフォームでは BFD セッションが **一切作成不能**。
- 順序依存: capability が false の ASIC では bfdorch は無限ループに陥らず即 `it++` 待機するが、ユーザー視点では「`BFD_SESSION` 書込みが反映されない」状態になる。
- evidence: `bfdorch.cpp:270-303, 305-315`

### 6. `bfd_session_cache` リプレイと TSA 状態遷移

- `doTask()` L141-178: SET 時に `shutdown_bfd_during_tsa == "true"` のエントリを `bfd_session_cache[key] = data` に**常に**コピーする。`tsa_enabled == false` なら通常通り `create_bfd_session()` を呼び、`tsa_enabled == true` なら `notify_session_state_down(key)` で Down 通知のみ送り **SAI セッションは作らない**。
- `BgpGlobalStateOrch::doTask()` L813-826: `BGP_DEVICE_GLOBAL|STATE` の `tsa_enabled` フィールド変化を検知して `BfdOrch::handleTsaStateChange(state)` を呼ぶ。
- `handleTsaStateChange()` L683-704: `bfd_session_cache` 全件を走査して
    - TSA enter (`tsaState == true`): `bfd_session_map` に存在するものを `notify_session_state_down` + `remove_bfd_session` で削除。
    - TSA exit (`tsaState == false`): `bfd_session_map` に**存在しない**ものを `create_bfd_session(it.first, it.second)` で**再投入**。
- → タイミング依存: TSA 解除時の cache replay 順序は `std::map<string, vector<FieldValueTuple>>` のキー辞書順。BFD セッション再生成中に SAI capability や PORT/VRF 状態が変動していれば create が失敗する可能性がある。
- → 順序依存: TSA 操作 (`BgpGlobalStateOrch::doTask` 経由) と `BFD_SESSION` の SET が同一 doTask サイクルで届くと、`bfd_session_cache` 更新と `handleTsaStateChange` の replay 双方で create_bfd_session を呼ぶことで二重 SET 競合の余地がある（コードは `bfd_session_map.find` で抑止）。
- evidence: `bfdorch.cpp:141-178, 683-704, 813-826`

### 7. DEL 時の cache クリーンアップ順序

- `doTask()` L190-209 (DEL): `bfd_session_cache` に存在するキーは **先に `erase`** してから `tsa_enabled == false` なら `remove_bfd_session` を呼ぶ。`tsa_enabled == true` の場合は cache から消すだけで SAI 操作なし（既に TSA enter 時に SAI 上は削除済み）。
- cache 未登録 (`shutdown_bfd_during_tsa != "true"`) の通常セッションは `remove_bfd_session` のみ。
- タイミング依存: DEL → SET（同一キー）を即連続で書くと、`remove_bfd_session` 内の `bfd_session_lookup.erase(bfd_session_id)` 完了後でないと次の SET の `bfd_session_map.find(key) != end` チェックが古い値を返して `"already exists"` で no-op 化する可能性。実コードは同一 doTask サイクル内で順次 erase → emplace するため通常は問題ない。
- evidence: `bfdorch.cpp:190-209, 622-635`

### 8. UDP 送信元ポート再試行ループ

- `create_bfd_session()` L546-552 → `retry_create_bfd_session()` L592-: SAI create 失敗時に `bfd_src_port()` を更新して最大 3 回 (`NUM_BFD_SRCPORT_RETRIES = 3`) 再試行。これは順序依存ではなくランダム生成された UDP src port が他セッションと衝突した場合のリカバリで、`doTask` 内で同期的に完結する（イベントループに再投入しない）。
- evidence: `bfdorch.cpp:546-552, 592-`

---

## 順序依存サマリ

| 依存項目 | スコープ | 解消メカニズム | evidence |
|---|---|---|---|
| PORT 初期化 | `alias != "default"` 経路のみ | `getPort` 失敗で `return false` → 次イベントループ再試行 | bfdorch.cpp:482-490 |
| VRF 登録 | hardware lookup ＋ 非 default VRF | `VRFOrch::getVRFid` 失敗 → SAI create 失敗 → `handleSaiCreateStatus` 再試行 | bfdorch.cpp:530-541 |
| BgpGlobalStateOrch 先行 | 起動時 1 回 | `gDirectory.get` 失敗で software 経路に強制 fallback | bfdorch.cpp:114-121, 729-736 |
| software/hardware 経路選択 | 起動時 1 回固定 | SAI capability 1 回照会、動的切替不可（swss 再起動必須） | bfdorch.cpp:749-791 |
| SAI state-change 通知 | 初回 SET 1 回 | capability false で永続 reject | bfdorch.cpp:270-315 |
| TSA cache replay | TSA enter/exit 時 | `bfd_session_cache` 全件を `handleTsaStateChange` で再投入 | bfdorch.cpp:141-178, 683-704 |
| DEL の cache クリーンアップ | 全セッション | cache `erase` → `remove_bfd_session` の順 | bfdorch.cpp:190-209 |
| UDP src port 衝突 | 同期再試行 | 最大 3 回内部再生成 | bfdorch.cpp:546-552 |

## 検証メモ

- bfdorch は `aclorch` のような `allPortsReady()` 早期 return ガードを**持たない**。PORT 未初期化のまま hardware lookup BFD (`alias=="default"`) は通る点に注意。
- `bfd_session_cache` は `shutdown_bfd_during_tsa == "true"` のセッションのみが対象。通常セッションは TSA 中も維持され、cache replay の対象外。
- software BFD 経路は SAI 依存が一切ないため、本ページの順序依存はほぼ無効化される（FRR bfdd 側の依存に置き換わる）。
