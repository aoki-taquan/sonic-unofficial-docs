# DASH_ROUTING_TYPE_TABLE — Phase B 書込み順依存スキャンノート

対象テーブル: `DASH_ROUTING_TYPE_TABLE`
Consumer: `DashOrch` (`sonic-swss/orchagent/dash/dashorch.cpp`)
参照元: `DashVnetOrch::addOutboundCaToPa()` (`dashvnetorch.cpp:300-410`)
スキャン範囲: `doTaskRoutingTypeTable()`, `addRoutingTypeEntry()`, `removeRoutingTypeEntry()`, `getRouteTypeActions()`, `DashVnetOrch::addOutboundCaToPa()` 全行精読

---

## 検出した順序依存・タイミング依存

### 1. DASH_ROUTING_TYPE_TABLE が DASH_VNET_MAPPING_TABLE より先行必須

`DashVnetOrch::addOutboundCaToPa()` (`dashvnetorch.cpp:313-319`) は冒頭で `DashOrch::getRouteTypeActions()` を呼び出す。
この関数は `routing_type_entries_` マップを参照し、該当エントリが存在しない場合 `false` を返す。
呼び出し元は `return false` を受けてリトライキューに戻す設計（implicit retry）。

**順序依存**: `DASH_VNET_MAPPING_TABLE` エントリを書き込む前に、参照先の routing type が `DASH_ROUTING_TYPE_TABLE` 経由で `routing_type_entries_` に登録されている必要がある。
登録がない場合、VNET マッピングは consumer キューに残り次の doTask() ループで自動再試行される。

> コード根拠: `dashvnetorch.cpp:313–319`

### 2. DASH_ROUTING_TYPE_TABLE は他のテーブルに依存しない（自立登録）

`addRoutingTypeEntry()` (`dashorch.cpp:441-455`) は `routing_type_entries_` マップへの単純な挿入のみを行う。
他の DASH テーブル (`DASH_APPLIANCE_TABLE`, `DASH_ENI_TABLE`, `DASH_VNET_TABLE` 等) の存在を確認しない。
つまり **DASH_ROUTING_TYPE_TABLE は最初に書き込める**テーブルであり、他テーブルへの先行依存はない。

> コード根拠: `dashorch.cpp:441–455`

### 3. DashRouteOrch のアウトバウンドルーティングは routing_type_entries_ を参照しない

`DashRouteOrch::addOutboundRoutingEntry()` (`dashrouteorch.cpp:70-160`) は `sOutboundAction` という静的マップ（コンパイル時定数）でルーティング型を SAI アクションに変換する。`DashOrch::getRouteTypeActions()` を呼ばないため、`DASH_ROUTE_TABLE` / `DASH_ROUTE_RULE_TABLE` / `DASH_ROUTE_GROUP_TABLE` は `routing_type_entries_` の存在に依存しない。

> コード根拠: `dashrouteorch.cpp:42–46, 103–106`

### 4. 既存エントリへの上書き不可（DEL → SET が必要）

`addRoutingTypeEntry()` は `routing_type_entries_.find()` で既存チェックを行い、存在する場合は `SWSS_LOG_WARN` を出して `return true` でサイレントスキップする (`dashorch.cpp:445-449`)。
Consumer キューからは削除されるため、orchagent 視点では「成功」として扱われるが、実際には**更新が反映されない**。

**運用上の順序依存**: routing type の変更が必要な場合、`DEL` を先に投入して `routing_type_entries_` から削除してから `SET` を再投入する必要がある。
DEL 後に即座に SET を投入しても、ZMQ Consumer のキュー処理順序上 DEL → SET の順が保証されていれば問題ない。

> コード根拠: `dashorch.cpp:445–449`, `dashorch.cpp:457–469`

### 5. 削除時の参照カスケード問題（実装上の注意）

`removeRoutingTypeEntry()` (`dashorch.cpp:457-469`) は `routing_type_entries_` からエントリを即時削除して `return true` を返す。
`DASH_VNET_MAPPING_TABLE` がその routing type を参照している場合でも、SAI レベルでのチェックはなく orchagent 側ではガードされない。

削除後に新たな `DASH_VNET_MAPPING_TABLE` 書き込みが来ると `getRouteTypeActions()` が `false` を返してリトライとなるが、既存のプログラム済み VNET マッピングは SAI / DPU ハードウェア側に残る（孤立エントリ）。

**推奨削除順序**:
```
[1] DASH_VNET_MAPPING_TABLE — DEL（全参照エントリを先に削除）
    ↓
[2] DASH_ROUTING_TYPE_TABLE — DEL
```

> コード根拠: `dashorch.cpp:457–469`, `dashvnetorch.cpp:313–319`

### 6. warm-reboot 時の再適用順序

`DashOrch` は `addOrchList` に登録されており (`orchdaemon.cpp:1414`)、`warmRestoreAndSyncUp()` の doTask() 3 イテレーションの対象となる。
`m_orchList` の登録順序は `DashAclOrch → DashVnetOrch → DashRouteOrch → DashOrch → ...` であり (`orchdaemon.cpp:1412-1420`)、`DashOrch` は **DashVnetOrch より後に処理される**。

warm-reboot 後のリプレイ時、SDN コントローラが再送する順序は `DASH_ROUTING_TYPE_TABLE` → `DASH_VNET_MAPPING_TABLE` の順であることが望ましい。
orchagent 側の `addOrchList` 登録順で `DashVnetOrch` が `DashOrch` より先に処理されるため、`DASH_VNET_MAPPING_TABLE` エントリが先にキューに積まれると `getRouteTypeActions()` miss でリトライが発生するが、次のイテレーションで `DashOrch` が `routing_type_entries_` を補充するため、3 イテレーション以内に解消する設計となっている。

> コード根拠: `orchdaemon.cpp:1412–1420`

---

## 順序依存サマリ

| # | 先行テーブル / 操作 | 後続テーブル / 操作 | 緩和策 |
|---|-------------------|-------------------|--------|
| 1 | `DASH_ROUTING_TYPE_TABLE` 登録 | `DASH_VNET_MAPPING_TABLE` 書込 | routing type 未登録 → VnetMap がリトライキューに残る |
| 2 | なし（先行依存なし） | `DASH_ROUTING_TYPE_TABLE` | 他テーブルへの依存ゼロ・任意のタイミングで書込可 |
| 3 | `DASH_ROUTING_TYPE_TABLE` DEL | `DASH_ROUTING_TYPE_TABLE` SET（変更時） | DEL 後に SET を再投入（DEL→SET 順守） |
| 4 | `DASH_VNET_MAPPING_TABLE` DEL | `DASH_ROUTING_TYPE_TABLE` DEL | 先に参照元 VNET マッピングを削除しないと孤立エントリが残る |
