# SWITCH — Phase B 書込み順依存スキャンノート

対象テーブル: `SWITCH` (APP_DB の `SWITCH_TABLE:switch` も含む)
Consumer: `orchagent` / `SwitchOrch` (`sonic-swss/orchagent/switchorch.cpp`)
スキャン範囲: コンストラクタ, `doAppSwitchTableTask()`, `setSwitchTunnelVxlanParams()`, `initAsicSdkHealthEventNotification()`, `setSwitchNonSaiAttributes()` 全行精読

---

## 検出した順序依存・タイミング依存

### 1. SwitchOrch コンストラクタ初期化順序 — SAI 問い合わせは起動時に固定順で実行

`SwitchOrch::SwitchOrch()` (switchorch.cpp:148-175) 内で以下の順に初期化が実行される:

1. `initAsicSdkHealthEventNotification()` — ASIC/SDK ヘルスイベントコールバック登録 (SAI 属性 `SAI_SWITCH_ATTR_SWITCH_ASIC_SDK_HEALTH_EVENT_NOTIFY`)
2. `set_switch_pfc_dlr_init_capability()` — PFC DLR INIT ケイパビリティ問い合わせ
3. `initSensorsTable()` — 温度センサーテーブル初期化
4. `querySwitchTpidCapability()` — TPID ケイパビリティ問い合わせ
5. `querySwitchPortEgressSampleCapability()` — エグレスサンプルケイパビリティ
6. `querySwitchPortMirrorCapability()` — ミラーケイパビリティ
7. `querySwitchHashDefaults()` — ECMP/LAG ハッシュデフォルト OID 取得 (`SAI_SWITCH_ATTR_ECMP_HASH` / `SAI_SWITCH_ATTR_LAG_HASH`)
8. `setSwitchIcmpOffloadCapability()` — ICMP オフロードケイパビリティ
9. `setFastLinkupCapability()` — FastLinkup ポーリング/ガードタイムアウト範囲取得

**順序依存**: これらの SAI 問い合わせは `gSwitchId` が有効である前提で実行される。`gSwitchId` は `orchagent` 起動時に SAI `create_switch` で生成されるが、SAI 初期化が完了する前に `SwitchOrch` が構築されると全問い合わせが失敗する。`orchagent` の起動シーケンスで SAI 初期化→`SwitchOrch` 構築の順序は固定されている。
evidence: `switchorch.cpp:148-175`

### 2. SAI `create_switch` — SAI レベル作成は orchagent 起動シーケンスで先行実施

実際の SAI スイッチオブジェクト作成 (`sai_switch_api->create_switch`) は `SwitchOrch` ではなく `orchagent` 本体 (`main.cpp`) が担当する。`SwitchOrch` はすでに存在する `gSwitchId` に対して属性を設定するのみ。

SAI create_switch 時に渡される主要属性 (main.cpp 参照):
- `SAI_SWITCH_ATTR_INIT_SWITCH` (true)
- `SAI_SWITCH_ATTR_SRC_MAC_ADDRESS` (システム MAC)
- `SAI_SWITCH_ATTR_SWITCH_STATE_CHANGE_NOTIFY`
- `SAI_SWITCH_ATTR_FDB_EVENT_NOTIFY`
- `SAI_SWITCH_ATTR_PORT_STATE_CHANGE_NOTIFY`
- `SAI_SWITCH_ATTR_PACKET_EVENT_NOTIFY`
- `SAI_SWITCH_ATTR_QUEUE_PFC_DEADLOCK_NOTIFY`

**順序依存**: CONFIG_DB の `SWITCH` テーブルエントリは `create_switch` 完了後にのみ `set_switch_attribute` で適用される。CONFIG_DB への書き込みは `create_switch` の前後どちらでも可能だが、適用タイミングは `SwitchOrch` が起動して APP_DB / CONFIG_DB を購読した後になる。
evidence: `switchorch.cpp:22-27` (extern gSwitchId)

### 3. `doAppSwitchTableTask()` 内の属性適用順序 — フィールドは宣言順に処理

`doAppSwitchTableTask()` (switchorch.cpp:595-748) では `kfvFieldsValues` のイテレーション順（APP_DB への書き込み順）に属性が処理される。同一キーの複数フィールドは**受信した順**に `set_switch_attribute` が呼ばれる。

属性ブランチの処理フロー:
1. `switch_non_sai_attribute_set` に含まれる場合 (`ordered_ecmp`) → `setSwitchNonSaiAttributes()` 呼び出し
2. `switch_attribute_map` に含まれる場合 → SAI 属性 ID に変換して `set_switch_attribute`
3. `switch_tunnel_attribute_map` に含まれる場合 (`vxlan_sport`, `vxlan_mask`, `vxlan_security`) → `setSwitchTunnelVxlanParams()` 呼び出し
4. いずれにも含まれない場合 → エラーログ出力後 `break`（以降のフィールドは処理されない）

**順序依存**: 不明属性が検出された場合 `break` で残りのフィールド処理が中断される。無効なフィールドを含むエントリを書き込む場合、そのフィールドより後に記述された有効なフィールドも適用されない。
evidence: `switchorch.cpp:610-634`

### 4. VxLAN スポートモード — `create_switch_tunnel` は最初の VxLAN 属性書き込み時に自動実行

`setSwitchTunnelVxlanParams()` (switchorch.cpp:508-593) は `m_vxlanSportUserModeEnabled` フラグを確認し、`false` の場合のみ `sai_switch_api->create_switch_tunnel()` を呼ぶ。

create_switch_tunnel 時に設定される属性:
1. `SAI_SWITCH_TUNNEL_ATTR_TUNNEL_TYPE` = `SAI_TUNNEL_TYPE_VXLAN`
2. `SAI_SWITCH_TUNNEL_ATTR_TUNNEL_VXLAN_UDP_SPORT_MODE` = `SAI_TUNNEL_VXLAN_UDP_SPORT_MODE_USER_DEFINED`
3. `SAI_SWITCH_TUNNEL_ATTR_VXLAN_UDP_SPORT_SECURITY` = `false` (ケイパビリティがある場合のみ)

create 後の個別属性設定順 (`set_switch_tunnel_attribute`):
- `vxlan_sport` → `SAI_SWITCH_TUNNEL_ATTR_VXLAN_UDP_SPORT`
- `vxlan_mask` → `SAI_SWITCH_TUNNEL_ATTR_VXLAN_UDP_SPORT_MASK`
- `vxlan_security` → `SAI_SWITCH_TUNNEL_ATTR_VXLAN_UDP_SPORT_SECURITY`

**順序依存**: `vxlan_sport` / `vxlan_mask` / `vxlan_security` のいずれか最初に到着したフィールドが `create_switch_tunnel` をトリガーする。`create_switch_tunnel` が失敗した場合は後続の属性設定もスキップされる（`return status` で即 return）。これらの属性は任意の順で書き込み可能だが、3 つすべてを揃えた後に書き込む方が安全。
evidence: `switchorch.cpp:515-552`

### 5. ECMP / LAG ハッシュオフセット — ケイパビリティ確認が各属性設定の前提

`SAI_SWITCH_ATTR_ECMP_DEFAULT_HASH_OFFSET` および `SAI_SWITCH_ATTR_LAG_DEFAULT_HASH_OFFSET` は `set_switch_attribute` 呼び出し前に `querySwitchCapability()` でサポート確認が行われる (switchorch.cpp:682-703)。

- サポートされていない場合: `unsupported_attr = true` → `continue` で**次のフィールドに進む**（`ecmp_hash_seed` や `lag_hash_seed` と異なり、スキップ扱い）
- `fdb_unicast/broadcast/multicast_miss_packet_action`: `packet_action_map` に存在しない値は `invalid_attr = true` → `break`（以降のフィールドをスキップ）

**順序依存**: サポートされないオフセット属性は silent skip されるが、不正なパケットアクション値は以降の全フィールド処理を中断する。パケットアクション属性は有効値 (`drop` / `forward` / `trap`) のみ書き込むこと。
evidence: `switchorch.cpp:647-720`

### 6. ASIC/SDK ヘルスイベント登録順序 — コンストラクタ内で severity 順に登録

`initAsicSdkHealthEventNotification()` (switchorch.cpp:207-299) 内での登録順:
1. `SAI_SWITCH_ATTR_SWITCH_ASIC_SDK_HEALTH_EVENT_NOTIFY` コールバック登録
2. `SAI_SWITCH_ATTR_REG_FATAL_SWITCH_ASIC_SDK_HEALTH_CATEGORY` (fatal)
3. `SAI_SWITCH_ATTR_REG_WARNING_SWITCH_ASIC_SDK_HEALTH_CATEGORY` (warning)
4. `SAI_SWITCH_ATTR_REG_NOTICE_SWITCH_ASIC_SDK_HEALTH_CATEGORY` (notice)

CONFIG_DB の `SUPPRESS_ASIC_SDK_HEALTH_EVENT` テーブルが参照される (switchorch.cpp:239-261): 登録時に抑制カテゴリが読み込まれ、抑制設定は SAI 登録と同時に適用される。

**順序依存**: `SUPPRESS_ASIC_SDK_HEALTH_EVENT` テーブルは `initAsicSdkHealthEventNotification()` 呼び出し時点 (コンストラクタ内) に読み込まれる。コンストラクタ呼び出し後に `SUPPRESS_ASIC_SDK_HEALTH_EVENT` を書き込んでも `doCfgSuppressAsicSdkHealthEventTableTask()` ハンドラで動的に更新されるが、初期 suppress 設定が必要な場合はコンストラクタ前に CONFIG_DB に書いておく必要がある。
evidence: `switchorch.cpp:207-299`

### 7. `ordered_ecmp` — non-SAI 属性は NexthopGroup orch との連携が必要

`setSwitchNonSaiAttributes()` (switchorch.cpp:449-505) で `ordered_ecmp` = `"true"` を設定する場合:
1. `NexthopGroup` Orch の capability フラグを確認
2. SAI `create_next_hop_group` を試行してサポートを検証
3. `m_orderedEcmpEnable = true` をセットし `SWITCH_CAPABILITY_TABLE` に書き込む

**順序依存**: `ordered_ecmp` 設定は `NexthopGroupOrch` が初期化済みであることが前提。orchagent 起動時の orch 初期化順で `SwitchOrch` は `NexthopGroupOrch` より先に初期化されることがあるため、初期化直後に `ordered_ecmp` を書き込んでも `NexthopGroupOrch` ポインタが NULL の場合は設定がスキップされる。
evidence: `switchorch.cpp:449-505`

---

## 起動シーケンス全体図

```
orchagent 起動
  │
  ├─ [1] SAI 初期化 (sai_api_initialize / profile 読み込み)
  │
  ├─ [2] sai_switch_api->create_switch(attrs)
  │        - SAI_SWITCH_ATTR_INIT_SWITCH = true
  │        - SAI_SWITCH_ATTR_SRC_MAC_ADDRESS (system MAC)
  │        - 各種コールバック属性
  │        → gSwitchId 確定
  │
  ├─ [3] SwitchOrch::SwitchOrch() コンストラクタ
  │        - initAsicSdkHealthEventNotification()
  │            → SUPPRESS_ASIC_SDK_HEALTH_EVENT テーブル参照
  │        - set_switch_pfc_dlr_init_capability()
  │        - initSensorsTable()
  │        - querySwitchTpidCapability()
  │        - querySwitchPortEgressSampleCapability()
  │        - querySwitchPortMirrorCapability()
  │        - querySwitchHashDefaults()
  │            → SAI_SWITCH_ATTR_ECMP_HASH / LAG_HASH OID 取得
  │        - setSwitchIcmpOffloadCapability()
  │        - setFastLinkupCapability()
  │
  ├─ [4] orchagent メインループ開始 (Consumer 購読)
  │
  └─ [5] APP_DB SWITCH_TABLE:switch に SET が来た場合
           doAppSwitchTableTask()
             ├─ ordered_ecmp → setSwitchNonSaiAttributes()
             ├─ switch_attribute_map 属性 → set_switch_attribute(gSwitchId, attr)
             │    順序: fdb_*_miss_packet_action → ecmp/lag_hash_seed →
             │           fdb_aging_time → debug_shell_enable →
             │           vxlan_port/router_mac → ecmp/lag_hash_offset
             └─ switch_tunnel_attribute_map 属性 → setSwitchTunnelVxlanParams()
                  ├─ [初回のみ] create_switch_tunnel()
                  │    SAI_SWITCH_TUNNEL_ATTR_TUNNEL_TYPE = VXLAN
                  │    SAI_SWITCH_TUNNEL_ATTR_TUNNEL_VXLAN_UDP_SPORT_MODE = USER_DEFINED
                  │    SAI_SWITCH_TUNNEL_ATTR_VXLAN_UDP_SPORT_SECURITY = false
                  └─ set_switch_tunnel_attribute(m_switchTunnelId, attr)
```

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | SAI create_switch → SwitchOrch コンストラクタ | 強制先行（orchagent 内部シーケンス固定） | orchagent が保証 |
| 2 | create_switch → set_switch_attribute (全属性) | 強制先行（gSwitchId 必要） | orchagent が保証 |
| 3 | 不明属性フィールド → 後続フィールドスキップ | break による中断 | 有効属性のみ書き込む |
| 4 | vxlan_sport/mask/security のうち最初到達 → create_switch_tunnel | 自動トリガー（順不同可） | 3 属性全部揃えてから書き込みが安全 |
| 5 | SUPPRESS_ASIC_SDK_HEALTH_EVENT → initAsicSdkHealthEventNotification | 先行推奨（コンストラクタ時参照） | 後追いは doCfgSuppressAsicSdkHealthEventTableTask で動的更新可 |
| 6 | 不正なパケットアクション値 → break で全フィールドスキップ | 即時 break | drop/forward/trap のみ使用 |
| 7 | NexthopGroupOrch 初期化 → ordered_ecmp 設定 | 先行必須（NULL チェック） | orchagent 初期化順に依存 |
