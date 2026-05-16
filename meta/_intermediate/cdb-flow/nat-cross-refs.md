# NAT_GLOBAL / NAT_POOL — 暗黙参照 (Phase C) 調査メモ

調査日: 2026-05-15
対象ソース:
- `sonic-swss/cfgmgr/natmgr.cpp`
- `sonic-swss/cfgmgr/natmgrd.cpp`
- `sonic-swss/orchagent/natorch.cpp`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-nat.yang`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-interface.yang`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-portchannel.yang`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-vlan.yang`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-loopback-interface.yang`

---

## 検出した暗黙参照

### 1. INTERFACE テーブル — nat_zone フィールド (CONFIG_DB)

- **場所**: `natmgr.cpp:7384-7586`, `natmgrd.cpp:115`; YANG: `sonic-interface.yang:76-81`
- **方向**: `NAT_GLOBAL` ↔ `INTERFACE|<port>` を READ (nat_zone ゾーン値)
- **内容**: `natmgrd` は `CFG_INTF_TABLE_NAME` (`INTERFACE`) を購読テーブルとして登録する。`INTERFACE|<port>` に `nat_zone` フィールドが設定されると `doNatInterfaceTask()` が呼ばれ、その値に `+1` した整数を iptables の mangle ルール (`PREROUTING` / `POSTROUTING` に `MARK --set-mark`) として設定する。`INTERFACE.nat_zone` の変更は `setMangleIptablesRules()` によりシステムに即時反映される。nat_zone が未設定・"NULL" の場合はデフォルト `"1"` を使用。
- **YANG 依存**: `sonic-interface.yang` leaf `nat_zone` は型 `uint8`、range `0..3`。同様のフィールドが `sonic-portchannel.yang:187`、`sonic-vlan.yang:102`、`sonic-loopback-interface.yang:50` にも存在し、それぞれ LAG インタフェース・VLAN インタフェース・Loopback インタフェースで NAT ゾーン番号を設定できる。

### 2. PORTCHANNEL_INTERFACE テーブル — nat_zone フィールド (CONFIG_DB)

- **場所**: `natmgr.cpp:8178-8183`, `natmgrd.cpp:116`; YANG: `sonic-portchannel.yang:187-192`
- **方向**: `NAT_GLOBAL` 機能 ↔ `PORTCHANNEL_INTERFACE|<lag>` を READ
- **内容**: `natmgrd` は `CFG_LAG_INTF_TABLE_NAME` (`PORTCHANNEL_INTERFACE`) も同じ購読リストに含む。LAG インタフェースへの nat_zone 設定も同じ `doNatInterfaceTask()` で処理され、iptables mangle ルールが LAG 名で設定される。

### 3. VLAN_INTERFACE テーブル — nat_zone フィールド (CONFIG_DB)

- **場所**: `natmgr.cpp:8178-8183`, `natmgrd.cpp:117`; YANG: `sonic-vlan.yang:102-107`
- **方向**: `NAT_GLOBAL` 機能 ↔ `VLAN_INTERFACE|<vlan>` を READ
- **内容**: `natmgrd` は `CFG_VLAN_INTF_TABLE_NAME` (`VLAN_INTERFACE`) も購読。VLAN インタフェースへの nat_zone 設定が mangle ルールに反映される。

### 4. LOOPBACK_INTERFACE テーブル — nat_zone フィールド (CONFIG_DB)

- **場所**: `natmgr.cpp:8178-8183`, `natmgrd.cpp:118`; YANG: `sonic-loopback-interface.yang:50-55`
- **方向**: `NAT_GLOBAL` 機能 ↔ `LOOPBACK_INTERFACE|<lo>` を READ
- **内容**: `natmgrd` は `CFG_LOOPBACK_INTERFACE_TABLE_NAME` も購読。Loopback インタフェースへの nat_zone 設定も処理される。

### 5. STATIC_NAT テーブル (CONFIG_DB)

- **場所**: `natmgrd.cpp:110`, `natmgr.cpp:6492 以降の doStaticNatTask()`
- **方向**: `NAT_GLOBAL.admin_mode` → `STATIC_NAT|<global_ip>` の処理を制御 (READ)
- **内容**: `natmgrd` は `CFG_STATIC_NAT_TABLE_NAME` を購読。`STATIC_NAT` エントリの処理は `admin_mode == enabled` かつ対象 IP が割り当てられたインタフェースが存在することを確認してから行う。`NAT_POOL` の `nat_ip` と `STATIC_NAT` の `global_ip` が重複する場合は NAT_POOL 追加時に silent drop (`natmgr.cpp:6771`)。

### 6. STATIC_NAPT テーブル (CONFIG_DB)

- **場所**: `natmgrd.cpp:111`, `natmgr.cpp:doStaticNaptTask()`
- **方向**: `NAT_GLOBAL.admin_mode` → `STATIC_NAPT|<global_ip>|<protocol>|<global_port>` の処理を制御 (READ)
- **内容**: `natmgrd` は `CFG_STATIC_NAPT_TABLE_NAME` を購読。STATIC_NAT と同様に admin_mode と L3 インタフェース readiness に依存する。STATIC_NAPT キーは 5 パーツ（global_ip, proto, global_port, internal_ip, internal_port）で構成されるが、orchagent 側はキーサイズ 5 以外をエラーとして扱う。

### 7. ACL_TABLE テーブル (CONFIG_DB) — NAT 用 L3 ACL バインディング

- **場所**: `natmgrd.cpp:119`, `natmgr.cpp:7750-7900`
- **方向**: `NAT_BINDINGS` → `ACL_TABLE|<table_id>` を参照 (READ)
- **内容**: `natmgrd` は `CFG_ACL_TABLE_TABLE_NAME` も購読。NAT dynamic rule の適用に使う ACL テーブルを追跡するために `doNatAclTableTask()` が呼ばれる。`type = L3`、`stage = INGRESS` の ACL テーブルのみが対象。`ports` フィールドでインタフェース名と ACL を紐付け、`m_natAclTableInfo[aclId] = interface` としてキャッシュする。その後 `NAT_BINDINGS` の dynamic ルール生成時にこのキャッシュを参照する。

### 8. ACL_RULE テーブル (CONFIG_DB)

- **場所**: `natmgrd.cpp:120`, `natmgr.cpp:doNatAclRuleTask()`
- **方向**: `NAT_BINDINGS` → `ACL_RULE|<table_id>|<rule_id>` を参照 (READ)
- **内容**: `natmgrd` は `CFG_ACL_RULE_TABLE_NAME` を購読。ACL RULE が追加・削除されると NAT binding の有効性を再評価し、iptables の MASQUERADE / SNAT ルールを更新する。

### 9. STATE_PORT_TABLE / STATE_LAG_TABLE / STATE_VLAN_TABLE / STATE_INTERFACE_TABLE (STATE_DB)

- **場所**: `natmgr.cpp:97-155` `isPortStateOk()` / `isIntfStateOk()`
- **方向**: NAT エントリ追加時に STATE_DB の各テーブルを READ
- **内容**: `NatMgr` が STATIC_NAT / STATIC_NAPT / NAT_POOL / NAT_BINDINGS のエントリを追加する前に、対象インタフェースが「ready」状態であることを確認する。ポート名プレフィクスに応じて `STATE_PORT_TABLE` (Ethernet)、`STATE_LAG_TABLE` (PortChannel)、`STATE_VLAN_TABLE` (Vlan)、`STATE_INTERFACE_TABLE` を参照する。未 ready の場合は処理をスキップ（Consumer キューに残す）。

### 10. APP_PORT_TABLE (APPL_DB) — 起動時ポート初期化待ち

- **場所**: `natmgr.cpp:76-92` `isPortInitDone()`; `natmgrd.cpp:139`
- **方向**: `natmgrd` 起動直後に APPL_DB `APP_PORT_TABLE_NAME` の `PortInitDone` キーを READ
- **内容**: `natmgrd` は起動後に `isPortInitDone()` をブロッキングで呼び、ポート初期化が完了するまで 1 秒ごとにポーリングする。PortInitDone が存在しない間は全 NAT 設定の処理を開始しない。

### 11. NAT_POOL → NAT_BINDINGS (YANG leafref)

- **場所**: `sonic-nat.yang:271` `path "../../../NAT_POOL/NAT_POOL_LIST/name"`
- **方向**: `NAT_BINDINGS.nat_pool` が `NAT_POOL.name` を leafref (READ)
- **内容**: YANG レベルでの強制参照整合性。`NAT_BINDINGS` を追加する際、`nat_pool` に指定した名前が `NAT_POOL` に存在しなければ YANG バリデーションで拒否される。実装レベルでも `natmgr.cpp:isPoolMappedtoBinding()` で逆参照を追跡する。

---

## 参照タイプ別サマリ

| 参照先テーブル | DB | 方向 | 契機 | 備考 |
|--------------|-----|------|------|------|
| `INTERFACE` (`nat_zone`) | CONFIG_DB | READ | 購読テーブル | Ethernet ポートの NAT ゾーン設定 |
| `PORTCHANNEL_INTERFACE` (`nat_zone`) | CONFIG_DB | READ | 購読テーブル | LAG ポートの NAT ゾーン設定 |
| `VLAN_INTERFACE` (`nat_zone`) | CONFIG_DB | READ | 購読テーブル | VLAN インタフェースの NAT ゾーン設定 |
| `LOOPBACK_INTERFACE` (`nat_zone`) | CONFIG_DB | READ | 購読テーブル | Loopback の NAT ゾーン設定 |
| `STATIC_NAT` | CONFIG_DB | READ | 購読テーブル | admin_mode + L3 intf 依存で処理制御 |
| `STATIC_NAPT` | CONFIG_DB | READ | 購読テーブル | admin_mode + L3 intf 依存で処理制御 |
| `ACL_TABLE` (type=L3, stage=INGRESS) | CONFIG_DB | READ | 購読テーブル | Dynamic NAT の ACL バインディング |
| `ACL_RULE` | CONFIG_DB | READ | 購読テーブル | Dynamic NAT ルール再評価 |
| `STATE_PORT_TABLE` | STATE_DB | READ | NAT エントリ追加前 | Ethernet readiness ガード |
| `STATE_LAG_TABLE` | STATE_DB | READ | NAT エントリ追加前 | PortChannel readiness ガード |
| `STATE_VLAN_TABLE` | STATE_DB | READ | NAT エントリ追加前 | Vlan readiness ガード |
| `STATE_INTERFACE_TABLE` | STATE_DB | READ | NAT エントリ追加前 | L3 インタフェース readiness ガード |
| `APP_PORT_TABLE` (`PortInitDone`) | APPL_DB | READ | natmgrd 起動時 | ポート初期化完了待ちブロック |
| `NAT_POOL` (leafref) | CONFIG_DB | READ | YANG バリデーション | `NAT_BINDINGS.nat_pool` 参照整合性 |
