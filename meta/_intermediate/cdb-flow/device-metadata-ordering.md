# DEVICE_METADATA — Phase B 書込み順依存 調査メモ

対象ページ: `docs/reference/config-db/device-metadata.md`
調査日: 2026-05-14

## 調査対象ファイル

| ファイル | 役割 |
|---------|------|
| `sonic-swss/orchagent/main.cpp` | orchagent 起動エントリ。`getCfgSwitchType()` → `sai_switch_api->create_switch()` のパイプライン |
| `sonic-buildimage/dockers/docker-orchagent/orchagent.sh` | orchagent 起動シェル。`synchronous_mode` / `switch_type` / `async_swss_rec` を CONFIG_DB から読んでフラグ設定 |
| `sonic-buildimage/dockers/docker-orchagent/buffermgrd.sh` | `buffer_model` を読んで `buffermgrd` を起動引数付きで起動 |
| `sonic-buildimage/dockers/docker-orchagent/supervisord.conf.j2` | docker-orchagent 内 supervisord 起動順定義 |
| `sonic-buildimage/dockers/docker-fpm-frr/docker_init.sh` | FRR コンテナ起動時 J2 展開。`docker_routing_config_mode` / `frr_mgmt_framework_config` を参照 |
| `sonic-buildimage/dockers/docker-fpm-frr/frr/zebra/zebra.conf.j2` | `nexthop_group` / `zebra_nexthop` 参照 |
| `sonic-host-services/scripts/hostcfgd` | `hostname` / `timezone` / `syslog_with_osversion` の動的変更ハンドラ |
| `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py` | `suppress-fib-pending` を `bgp_asn` 依存で FRR に適用 |
| `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-device_metadata.yang:250` | `suppress-fib-pending` / `synchronous_mode` の `must` 制約 |

## 検出した書込み順依存

### 1. 他テーブル先行必須: `DEVICE_METADATA|localhost` は最初に書く必要がある

orchagent は起動直後 (`main.cpp:657`) に `getCfgSwitchType()` で `DEVICE_METADATA|localhost|switch_type` を **一度だけ** 読み取り、SAI `create_switch()` の引数として渡す。

- `switch_type` がこの時点で存在しない場合は `"switch"` (npu 扱い) として SAI を初期化する。
- 後から `switch_type` を書き込んでも SAI `create_switch` はすでに呼ばれており、**変更は反映されない**。

同様に `mac` / `asic_id` / `synchronous_mode` も起動スクリプト (`orchagent.sh`) が起動前に読み取るため、**swss コンテナの起動前に `DEVICE_METADATA|localhost` のキーが揃っている必要がある**。

順序制約: `config_db.json` / `minigraph` による `DEVICE_METADATA` の一括投入 → swss コンテナ起動 の順。swss コンテナ起動後に `switch_type` / `synchronous_mode` / `mac` を書き込んでもコンテナ再起動なしには反映されない。

### 2. SET 後 DEL 順: create-only フィールドは DEL しても戻らない

以下のフィールドは **create-only** — orchagent / FRR 起動時に一度だけ読み取られ、以後は ConsumerStateTable を購読しない。

| フィールド | 再起動必要コンテナ | evidence |
|---|---|---|
| `switch_type` | swss (orchagent) | `main.cpp:657`; `getCfgSwitchType()` は起動時のみ呼ばれる |
| `synchronous_mode` | swss (orchagent) | `orchagent.sh:37-40`; `swss_vars.j2` は起動時生成 |
| `nexthop_group` | bgp (FRR) | `zebra.conf.j2:19-22`; J2 展開は `docker_init.sh` 起動時のみ |
| `zebra_nexthop` | bgp (FRR) | `zebra.conf.j2:11-12` 同上 |
| `docker_routing_config_mode` | bgp (FRR) | `docker_init.sh:59-99`; モード別に frr.conf / 個別デーモン設定を生成 |
| `frr_mgmt_framework_config` | bgp (FRR) | `frr_vars.j2:3-7`; 起動時 J2 展開 |

- これらを `DEL` してから再 `SET` しても、対象コンテナを再起動しない限り変更は無効。
- `SET` のみで値を変更することも同様に無効（冪等性はないが、読み取りが起動時のみのため）。

### 3. Notification 順: bgpcfgd は `bgp_asn` が先行必須

`managers_bgp.py:119-120` で bgpcfgd は `DEVICE_METADATA|localhost|bgp_asn` と `type` を**依存フィールド**として登録する。`bgp_asn` がなければ BGP セッション設定（peer-group, address-family）はテンプレート展開されない（`managers_bgp.py:187-192`）。

また `suppress-fib-pending = enabled` を `SET` するとき (`managers_bgp.py:501-506`)、bgpcfgd は `bgp_asn` を読んで FRR に `router bgp <asn> / bgp suppress-fib-pending` を送る。`bgp_asn` が未設定のまま `suppress-fib-pending` を SET すると、bgpcfgd は即時適用せず、後で `bgp_asn` が届いた時点で再処理する。

Notification 順制約: `DEVICE_METADATA|localhost|bgp_asn` → `suppress-fib-pending = enabled` の順で SET すること。逆順でも最終的には一致するが、bgpcfgd の内部再試行を経るため FRR への反映が遅れる可能性がある。

### 4. restart 必要: `buffer_model` の buffermgrd 起動引数

`buffermgrd.sh:5-13` は起動時に `buffer_model` を読み取り、`buffermgrd` の起動引数 (`-a asic_table.json` or `-l pg_profile_lookup.ini`) を決定する。

- `buffer_model = dynamic` → `buffermgrd -a /etc/sonic/asic_table.json`
- それ以外 → `buffermgrd -l /usr/share/sonic/hwsku/pg_profile_lookup.ini`

**ランタイム変更の挙動**: BufferMgr 自体は ConsumerStateTable を購読し `buffer_model` の SET を受け取れるが（`buffermgr.cpp:390-406`）、buffermgrd の**起動引数**（計算エンジン）は変わらない。`dynamic` ↔ `traditional` の切り替えには **swss コンテナ再起動**が必要。

### 5. warm-reboot 影響

| フィールド | warm-reboot での挙動 |
|---|---|
| `switch_type` | 変更不可。SAI `create_switch` は cold-boot 時のみ呼ばれる。warm-reboot でも `switch_type` 変更は無効 |
| `buffer_model` フラグ | reconciling 後に再適用される (`buffermgr.cpp` の ConsumerStateTable replay) |
| `create_only_config_db_buffers` | reconciling 後に再適用される (`flexcounterorch.cpp:488-521`) |
| `synchronous_mode` | warm-reboot 前後で同じモードを維持する必要がある（orchagent.sh は再起動時に再読取り） |
| `hostname` / `timezone` | hostcfgd が再起動後に CONFIG_DB を読み直して再適用 |

warm-reboot 時に `switch_type` を変更しても、SAI `create_switch` は再呼び出しされないため反映されない。warm-reboot を使う場合は `switch_type` / `synchronous_mode` を変更してはならない。

### 6. 起動時 boot order 依存 (supervisord priority)

docker-orchagent 内の起動順序 (`supervisord.conf.j2`):

```
priority=1: rsyslogd
priority=3: portsyncd (通常 switch_type) / rsyslogd:running (fabric switch_type)
priority=4: orchagent (dependent_startup_wait_for=portsyncd:running OR rsyslogd:running)
priority=5: syncd
priority=6: buffermgrd, fdbsyncd
priority=7: neighsyncd
```

- `switch_type = fabric` のとき `supervisord.conf.j2:36-40` で orchagent の `dependent_startup_wait_for` が `portsyncd:running` → `rsyslogd:running` に変更される。これは `DEVICE_METADATA.switch_type` が起動前に CONFIG_DB に存在することが前提（J2 展開時に参照）。
- FRR コンテナ (`docker-fpm-frr`) は `docker_init.sh` 起動時に `docker_routing_config_mode` を読んで `frr.conf` 等を生成する。CONFIG_DB への接続タイミングより先に設定がなければ空のデフォルト値が使われる。

### 7. YANG must 制約による SET 拒否

`sonic-device_metadata.yang:250`:
```yang
must "((current() = 'disabled') or (current() = 'enabled' and ../synchronous_mode = 'enable'))"
```

`suppress-fib-pending = enabled` かつ `synchronous_mode != 'enable'` のとき、YANG バリデーションで SET が reject される。

順序制約:
1. `synchronous_mode = enable` を SET する（またはデフォルト `enable` を確認）
2. その後 `suppress-fib-pending = enabled` を SET する

逆順や同時 SET の場合、`yang_config_validation = enable` 環境では YANG バリデーションが reject を返す可能性がある。

### 8. `switch_type = dpu` による `synchronous_mode` 上書き

`orchagent.sh:38-39` で `switch_type = dpu` のとき `-z zmq_sync -k 65536` を強制設定する。この場合 `synchronous_mode` フィールドの値は**無視**され、ZMQ synchronous mode が強制される。

設定者の意図と実際の動作が乖離しやすい点として注意が必要。`switch_type = dpu` を使う場合、`synchronous_mode` フィールドは実質無意味。

## 順序依存サマリ

| # | 依存関係 | 影響フィールド | 修正方法 |
|---|----------|---------------|---------|
| 1 | `DEVICE_METADATA` は swss/bgp コンテナ起動前に完備 | `switch_type`, `synchronous_mode`, `mac`, `bgp_asn` 等全フィールド | config_db.json 一括投入 → コンテナ起動 の順 |
| 2 | create-only フィールドは SET/DEL 後コンテナ再起動必要 | `switch_type`, `synchronous_mode`, `nexthop_group`, `zebra_nexthop`, `docker_routing_config_mode`, `frr_mgmt_framework_config` | swss / bgp コンテナ再起動 |
| 3 | `bgp_asn` → `suppress-fib-pending` の順 | `bgp_asn`, `suppress-fib-pending` | bgp_asn を先に SET |
| 4 | `buffer_model` 変更はコンテナ再起動 | `buffer_model` | swss コンテナ再起動（計算エンジン切替え） |
| 5 | warm-reboot 時 `switch_type` 変更不可 | `switch_type` | cold-boot のみ変更可 |
| 6 | `synchronous_mode = enable` → `suppress-fib-pending = enabled` | `synchronous_mode`, `suppress-fib-pending` | YANG must 制約。逆順は YANG reject |
| 7 | `switch_type = dpu` のとき `synchronous_mode` は無視 | `synchronous_mode` (dpu 時) | dpu では synchronous_mode 設定不要 |
| 8 | `switch_type = fabric` でbootの orchagent 待ち先が変わる | `switch_type` (fabric) | supervisord J2 展開前に CONFIG_DB が揃っていること |
