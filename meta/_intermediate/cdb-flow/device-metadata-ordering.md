# DEVICE_METADATA — Phase B 書込み順依存調査メモ

対象テーブル: `DEVICE_METADATA` (`DEVICE_METADATA|localhost`)
調査日: 2026-05-15

## 調査対象ファイル

| ファイル | 役割 |
|---------|------|
| `sonic-buildimage/dockers/docker-orchagent/orchagent.sh` | orchagent 起動スクリプト — 起動時に `switch_type`/`synchronous_mode`/`mac`/`async_swss_rec`/`subtype`/`ring_thread_enabled` を読み取り |
| `sonic-swss/orchagent/main.cpp` | orchagent main — 起動時のみ `switch_type`/`subtype`/`switch_id`/`max_cores`/`hostname`/`asic_name` を hget |
| `sonic-swss/cfgmgr/buffermgrd.cpp` | buffermgrd — `doBufferMetaTask()` で `buffer_model` を動的購読 |
| `sonic-swss/orchagent/flexcounterorch.cpp` | FlexCounterOrch — 初期化時に `create_only_config_db_buffers` を hget、その後も ConsumerStateTable で購読 |
| `sonic-swss/fpmsyncd/fpmsyncd.cpp` | fpmsyncd main — 起動時に `suppress-fib-pending` を hget、ランタイム変更も SubscriberStateTable で購読 |
| `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py` | BGPPeerMgrBase — `bgp_asn`/`type`/`deployment_id` を依存リストに登録。欠如時は `return False` で処理待機 |
| `sonic-host-services/scripts/hostcfgd` | hostcfgd — `hostname`/`timezone`/`syslog_with_osversion` を ConsumerStateTable で購読 |

---

## 1. 起動時一括読み取りフィールド（create-only）

### orchagent.sh の読み取り順序

`orchagent.sh` は起動時に以下の順序で `DEVICE_METADATA|localhost` から値を読み取り、
orchagent の起動引数を組み立てる。**全フィールドは orchagent プロセス起動前に CONFIG_DB に存在している必要がある**。

```
1. mac         — sonic-cfggen による swss_vars.j2 展開 (L8-16)
2. switch_type — sonic-db-cli hget (L22)
3. synchronous_mode — sonic-cfggen / swss_vars.j2 経由 (L37)
4. asic_id     — sonic-cfggen / swss_vars.j2 経由 (L54)
5. async_swss_rec — sonic-db-cli hget (L66)
6. subtype     — sonic-db-cli hget (L106)
7. ring_thread_enabled — sonic-db-cli hget (L121)
```

`swss_vars.j2` テンプレートの展開 (`sonic-cfggen -d -t`) は**スクリプト冒頭の単一 invocation** で行われ、
その後の各 `sonic-db-cli hget` は別個のトランザクション。

**順序依存**: `DEVICE_METADATA|localhost` の `mac`/`switch_type`/`synchronous_mode`/`async_swss_rec`/`subtype`/`ring_thread_enabled` は
**orchagent コンテナ（swss）起動前に CONFIG_DB に書き込まれていること**。boot 時は `config_db.json` から redis に
ロードされる順序が先行する（`config-setup` service が swss より先に起動する）。

### orchagent/main.cpp の hget 順序

`main.cpp` は初期化フェーズで `getCfgSwitchType()` / `getCfgVoqMyInfo()` を呼び出す:

```
getCfgSwitchType() → hget switch_type, subtype
getCfgVoqMyInfo()  → hget switch_id, max_cores, hostname, asic_name
```

これらは `sai_switch_api->create_switch()` の**引数として使われる起動時処理**であり、ランタイム変更不可。

**順序依存**: `switch_type` / `switch_id` / `max_cores` が欠如している場合、
SAI create_switch は npu モードで起動し、後から変更することはできない。

---

## 2. ランタイム動的購読フィールド（mutable）

### fpmsyncd: suppress-fib-pending

`fpmsyncd.cpp:113` で起動時に `hget("localhost", "suppress-fib-pending")` を読み取り、
ランタイム中も `SubscriberStateTable` で同フィールドを監視する（L82-83, L265-305）。

- `enabled → disabled`: `sync.markRoutesOffloaded(db)` を実行してから suppression を解除する副作用あり
- `disabled → enabled`: `routeResponseChannel` を新規作成して抑制モードに入る

**順序依存**:
- 起動時に `suppress-fib-pending = enabled` を設定する場合は **orchagent/syncd が先に起動して SAI ready になっていること**（FRR がルートを送り始める前に fpmsyncd が suppression モードに入る必要がある）
- YANG `must` 制約: `suppress-fib-pending = enabled` かつ `synchronous_mode = enable` でなければ YANG バリデーションで reject される

### buffermgr: buffer_model

`buffermgrd.cpp:373-410` の `doBufferMetaTask()` は ConsumerStateTable で `buffer_model` の SET/DEL を動的に処理する。

- `buffer_model = dynamic` SET → `dynamic_buffer_model = true` → 以降の BUFFER_POOL/BUFFER_PG 処理をスキップ
- `buffer_model = traditional` SET / DEL → `dynamic_buffer_model = false` → BUFFER_POOL/BUFFER_PG を APPL_DB に転写

**順序依存**: `DEVICE_METADATA|localhost` の `buffer_model` SET が、
`BUFFER_POOL`/`BUFFER_PG`/`BUFFER_PROFILE` の SET より**先に届く必要がある**。
`buffer_model = dynamic` が先に届かないと、buffermgr が一時的にバッファ設定を APPL_DB に転写してしまい、
後から dynamic に切り替えても過去の転写は残る。
ただし `buffermgrd` 起動引数（`-a asic_table.json` vs `-l pg_profile_lookup.ini`）はスクリプト起動時に確定するため、
**計算エンジン自体の切り替えには swss コンテナ再起動が必要**。

### FlexCounterOrch: create_only_config_db_buffers

`flexcounterorch.cpp:114` で**コンストラクタ起動時に一度だけ `hget`** する。
その後も ConsumerStateTable で購読し、ランタイム更新が可能（L488-521）。

**順序依存**: 初回 orchagent 起動前に `create_only_config_db_buffers` が設定されていれば初期値として使われる。
ランタイム変更は即時反映される（コンテナ再起動不要）。

### hostcfgd: hostname / timezone / syslog_with_osversion

hostcfgd は ConsumerStateTable で `DEVICE_METADATA` の変化を監視し、
`hostname_update()` / `apply_timezone_if_needed()` / `rsyslog_config()` に委譲する。

**順序依存**:
- `hostname` 変更: `not new_hostname`（空）ガード → `hostname == self.hostname`（変更なし）ガード → `service hostname-config restart` + `monit reload`
- `timezone` 変更: `new_tz is None` ガード → `timedatectl set-timezone` + `systemctl restart rsyslog`
- これらはランタイム即時反映であり、boot 順序への依存はない

---

## 3. BGPPeerMgrBase の依存待機（bgpcfgd）

`managers_bgp.py:118-143` で BGPPeerMgrBase は以下の依存リストを宣言する:

```python
deps = [
    ("CONFIG_DB", CFG_DEVICE_METADATA_TABLE_NAME, "localhost/bgp_asn"),
    ("CONFIG_DB", CFG_DEVICE_METADATA_TABLE_NAME, "localhost/type"),
    ("CONFIG_DB", CFG_LOOPBACK_INTERFACE_TABLE_NAME, "Loopback0"),
    ("CONFIG_DB", CFG_BGP_DEVICE_GLOBAL_TABLE_NAME, "tsa_enabled"),
    ("CONFIG_DB", CFG_BGP_DEVICE_GLOBAL_TABLE_NAME, "idf_isolation_state"),
    ...
]
```

bgpcfgd の `Directory` 機構がこれらの依存が全て揃うまで `BGP_NEIGHBOR` SET の処理を保留する。

**順序依存**:
- `DEVICE_METADATA|localhost` の `bgp_asn` が設定されていないと、`BGP_NEIGHBOR` テーブルのエントリはすべて保留される
- `type` が未設定の場合は `switch_role = None` のまま処理継続（例外条件: managers_device_global.py:53）
- `deployment_id` は `use_deployment_id = true` の環境でのみ必須依存になる
- Loopback0 に IPv4 アドレスが付いていなければ `add_peer` が `return False` で待機する（`managers_bgp.py:186-189`）

書込み順序の要約:
```
DEVICE_METADATA|localhost (bgp_asn, type) → BGP_DEVICE_GLOBAL (tsa_enabled, idf_isolation_state)
→ LOOPBACK_INTERFACE|Loopback0|<ipv4_prefix> → BGP_NEIGHBOR 処理
```

---

## 4. warm-reboot / restart 影響

| フィールド | warm-reboot 影響 | 順序制約 |
|-----------|-----------------|---------|
| `switch_type` | **変更不可** — SAI `create_switch()` は一度のみ | warm-reboot 後も変更には swss 完全再起動が必要 |
| `synchronous_mode` | **変更不可** — orchagent 起動引数に依存 | 変更時は swss コンテナ再起動が必要 |
| `buffer_model` フラグ | **mutable** — buffermgr ConsumerStateTable で再適用 | buffermgrd 起動引数は再起動しないと切り替わらない |
| `create_only_config_db_buffers` | **mutable** — FlexCounterOrch が再処理 | warm-reboot 後に自動 reconcile |
| `suppress-fib-pending` | **mutable** — fpmsyncd が再購読 | warm-reboot 中に `enabled → disabled` 遷移が入るとルートが一時的に offloaded にマークされる |
| `hostname` | **mutable** — hostcfgd が再処理 | boot 順序依存なし |
| `mac` | **create-only** — orchagent 起動引数 | warm-reboot でも変更は swss 再起動が必要 |

---

## 5. 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | CONFIG_DB ロード → swss（orchagent）起動 | **必須先行** | `config-setup` service が swss より先に起動（systemd 依存） |
| 2 | `mac`/`switch_type`/`synchronous_mode` → orchagent 起動引数確定 | **create-only** | 変更時は swss コンテナ再起動が必要 |
| 3 | `buffer_model` SET → BUFFER_POOL/PG SET | **推奨先行** | 逆順でも最終収束するが過渡的な APPL_DB 転写が発生 |
| 4 | `bgp_asn`/`type` → BGP_NEIGHBOR SET | **bgpcfgd 依存待機** | Directory 機構で自動 hold（retry あり） |
| 5 | `bgp_asn` + Loopback0 IPv4 → BGP ピア追加 | **bgpcfgd 依存待機** | `return False` で自動 retry |
| 6 | `suppress-fib-pending = enabled` + `synchronous_mode = enable` の同時性 | YANG `must` 制約 | YANG バリデーション有効時に reject される |
| 7 | `suppress-fib-pending disabled → enabled` ランタイム変更 | **副作用あり** | `markRoutesOffloaded()` で既存ルートが offloaded にマークされる |
| 8 | `create_only_config_db_buffers` 初期値 | 起動時 hget + 動的更新 | warm-reboot 後も ConsumerStateTable で再適用 |
