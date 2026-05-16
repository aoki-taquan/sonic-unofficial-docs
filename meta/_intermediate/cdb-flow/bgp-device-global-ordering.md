# BGP_DEVICE_GLOBAL — Phase B 書込み順依存スキャンノート

対象テーブル: `BGP_DEVICE_GLOBAL` (キー: `STATE`, `CONFED`)
Consumer 1 (bgpcfgd 側): `DeviceGlobalCfgMgr` (`sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_device_global.py`)
Consumer 2 (orchagent 側): `BgpGlobalStateOrch` (`sonic-swss/orchagent/bfdorch.cpp` / `bfdorch.h`)
スキャン範囲:
  - `managers_device_global.py` 全行 (1-288)
  - `bfdorch.cpp` BgpGlobalStateOrch セクション (729-835)
  - `orchdaemon.cpp` 初期化部 (199-250)

---

## 検出した順序依存・タイミング依存

### 1. DEVICE_METADATA.localhost.type → IDF 適用判定 (先行必須)

- `DeviceGlobalCfgMgr.__init__` (managers_device_global.py:33) で
  `self.directory.subscribe([("CONFIG_DB", swsscommon.CFG_DEVICE_METADATA_TABLE_NAME, "localhost/type")], self.handle_type_update)`
  を登録。
- 初期値は `self.switch_role = ""` (managers_device_global.py:23)。
- `downstream_isolate_unisolate()` (managers_device_global.py:260-262):
  `if self.switch_role and self.switch_role not in ["SpineRouter", "LowerSpineRouter", "UpperSpineRouter"]: return True`
  → `switch_role == ""` の場合**条件が falsy になり IDF 適用がスキップされない**（適用に進む）。
- **順序依存**: `DEVICE_METADATA|localhost.type = "ToRRouter"` を `BGP_DEVICE_GLOBAL|STATE.idf_isolation_state` 書き込み前に CONFIG_DB に存在させないと、ToR でも IDF 設定が一旦反映される。後から `DEVICE_METADATA` が書き込まれて `handle_type_update()` が走っても、それまで適用された IDF 設定の取り消しトリガはない。
- evidence: `managers_device_global.py:23,33,51-55,253-275`

### 2. BgpGlobalStateOrch インスタンス化順序 (orchdaemon)

- `orchdaemon.cpp:239-244`:
  ```cpp
  BgpGlobalStateOrch* bgp_global_state_orch;
  bgp_global_state_orch = new BgpGlobalStateOrch(m_configDb, CFG_BGP_DEVICE_GLOBAL_TABLE_NAME);
  gDirectory.set(bgp_global_state_orch);

  gBfdOrch = new BfdOrch(m_applDb, APP_BFD_SESSION_TABLE_NAME, stateDbBfdSessionTable);
  gDirectory.set(gBfdOrch);
  ```
- `BgpGlobalStateOrch` を **`BfdOrch` よりも先に**構築して `gDirectory` に登録する必要がある（`BfdOrch::handleTsaStateChange` 経由のフィードバックで `gDirectory.get<BgpGlobalStateOrch*>()` を呼ぶ箇所が `bfdorch.cpp:114` にあるため双方向参照）。
- 一方 `BgpGlobalStateOrch::doTask` は `gDirectory.get<BfdOrch*>()` を呼ぶ（`bfdorch.cpp:821`）。**初回 TSA 変更が `BfdOrch` 登録前に届くと nullptr 経路で BFD 連動がスキップされる**。
- 緩和: 通常 `Select::select` のイベントループは Orch 全構築後に開始されるため、実運用では発火タイミング的に問題にならない。
- evidence: `orchdaemon.cpp:239-244`, `bfdorch.cpp:114,821-825`

### 3. BgpGlobalStateOrch constructor の SAI 呼び出し順序

- `BgpGlobalStateOrch::BgpGlobalStateOrch` (bfdorch.cpp:729-736) は constructor 内で `offload_supported(false)` / `offload_supported(true)` を呼び、`sai_query_attribute_capability` と `sai_switch_api->get_switch_attribute(gSwitchId, ...)` を実行する。
- **先行必須**: `gSwitchId` 有効化 (= `SwitchOrch` 構築完了 + SAI switch 作成完了) が `BgpGlobalStateOrch` 構築前に必要。`orchdaemon.cpp:213` で `gSwitchOrch` が先に作られている。
- ただし `SwitchOrch::doTask` で SAI switch が実際に create されるのはイベントループ開始後なので、constructor 内の SAI query は **`gSwitchId == 0` の状態で失敗する可能性**がある（`offload_supported` 失敗時は `bfd_offload = false`、ソフトウェア BFD パスに falls back）。
- evidence: `bfdorch.cpp:729-791`

### 4. BgpGlobalStateOrch::doTask 内の TSA トリガ順序

- `bfdorch.cpp:793-829`:
  ```
  if (type == "tsa_enabled") {
      bool state = ... value == "true" ...;
      if (tsa_enabled != state) {
          tsa_enabled = state;
          BfdOrch* bfd_orch = gDirectory.get<BfdOrch*>();
          if (bfd_orch) bfd_orch->handleTsaStateChange(state);
      }
  }
  ```
- 内部キャッシュ `tsa_enabled` を**先に更新**してから `BfdOrch::handleTsaStateChange` を呼ぶ → `BfdOrch` 側で `BgpGlobalStateOrch::getTsaState()` をコールバックしても一貫した値を返せる。
- 同一 doTask 呼び出しで複数フィールドが届いた場合は data ループ内の到着順に処理されるが、現状 `tsa_enabled` 以外は無視（W-ECMP / IDF / CONFED は orchagent 側で処理されない）。
- evidence: `bfdorch.cpp:793-829`

### 5. bgpcfgd set_handler の固定フィールド処理順序

- `set_handler` (managers_device_global.py:57-72):
  ```
  configure_tsa(data)   # TSA
  configure_wcmp(data)  # W-ECMP
  configure_idf(data)   # IDF
  ```
- 固定順序。同一 set イベントで複数フィールド変更がある場合も TSA → W-ECMP → IDF の順で処理される。
- TSA のみ `requires_update and chassis_tsa == "false"` の条件下で `self.cfg_mgr.commit()` と `self.cfg_mgr.update()` を呼び、その後 `isolate_unisolate_device(state)` を実行する（managers_device_global.py:106-109）。
- **副作用**: TSA 切替が走るタイミングで bgpcfgd 内に他 manager (BGPPeerMgr, BGPPeerGroupMgr 等) が `cfg_mgr.push()` したまま commit されていない設定がある場合、それらが TSA route-map 生成前に強制 commit される。これは `get_ts_routemaps()` が現在の running config を読む必要があるため意図的な挙動。
- W-ECMP / IDF は `cfg_mgr.push()` のみ（commit/update なし） → bgpcfgd 内バッファに溜まっていた未 commit 設定への影響なし。
- evidence: `managers_device_global.py:57-72,103-109,164,272`

### 6. Chassis TSA 優先と個別 TSA スキップ

- `configure_tsa()` (managers_device_global.py:100-111):
  ```
  self.chassis_tsa = self.get_chassis_tsa_status()
  ...
  if requires_update and self.chassis_tsa == "false":
      self.cfg_mgr.commit(); self.cfg_mgr.update()
      self.isolate_unisolate_device(state)
  ```
- `get_chassis_tsa_status()` は `CHASSIS_APP_DB|BGP_DEVICE_GLOBAL|STATE.tsa_enabled` を毎回読む。
- **順序依存**: シャーシ TSA を有効化中 (`CHASSIS_APP_DB.tsa_enabled = "true"`) は個別 LC の `BGP_DEVICE_GLOBAL|STATE.tsa_enabled` 書き込みでは `isolate_unisolate_device()` が呼ばれない。シャーシ TSA 解除後にも LC ローカル TSA を再適用するためには、再度 `BGP_DEVICE_GLOBAL|STATE` への明示的な書き込みが必要（自動再評価トリガなし）。
- evidence: `managers_device_global.py:100-111,238-251`

### 7. directory キャッシュ更新と is_update_required の整合性

- `is_update_required(key, value)` (managers_device_global.py:86-89) は `directory` キャッシュと比較。
- `configure_tsa` / `configure_wcmp` / `configure_idf` は **FRR push 成功後** に `directory.put` でキャッシュ更新する（順序保証あり）。
- TSA: `directory.put` (104) → `isolate_unisolate_device` (109)。**TSA だけは push 前にキャッシュ更新**する（他は push 成功後に put）。これは `isolate_unisolate_device` 内で再帰的に状態を参照するため。
- 結果: TSA push が失敗してもキャッシュは新値のまま → 次回同値書き込みで `is_update_required = False` → リトライ機会喪失。
- evidence: `managers_device_global.py:103-104,122-124,137-139`

### 8. DEL_COMMAND のサポート差

- bgpcfgd: `del_handler` (managers_device_global.py:74-84) は `data=None` で 3 つの configure_* を呼びデフォルト回帰を実行（TSB / W-ECMP off / IDF unisolated）。
- orchagent: `BgpGlobalStateOrch::doTask` (bfdorch.cpp:830-832) は `DEL_COMMAND` を受信すると `SWSS_LOG_ERROR("DEL on key %s is not expected.")` を出すだけで何もしない。
- **不整合**: DEL によって bgpcfgd 側は TSA off に回帰するが、orchagent 内部キャッシュ `tsa_enabled` は前値のまま残り、`BfdOrch` への通知も発生しない。CONFIG_DB の通常運用では DEL を使わない想定。
- evidence: `managers_device_global.py:74-84`, `bfdorch.cpp:830-832`

---

## まとめ

- 1 つの CONFIG_DB テーブルに対して **bgpcfgd (FRR vtysh) と orchagent (SAI/BfdOrch) の 2 経路**が並列購読するパターン。
- 強い先行必須依存:
  1. `DEVICE_METADATA.localhost.type` (IDF 適用判定)
  2. `BgpGlobalStateOrch` インスタンス化を `BfdOrch` より先に行う (orchdaemon 静的順序)
- TSA 連鎖: bgpcfgd 内では TSA → W-ECMP → IDF の固定順、orchagent 内では TSA → `BfdOrch::handleTsaStateChange` の同期 dispatch。
- 双方向参照 (`gDirectory.get<BfdOrch*>()` ⇄ `gDirectory.get<BgpGlobalStateOrch*>()`) があるが、`gDirectory.set()` 順序が orchdaemon で保証されているため runtime での問題は出ない。
- DEL 操作は bgpcfgd と orchagent で挙動が乖離する設計上の非対称性あり（通常運用では DEL を使わない想定）。
