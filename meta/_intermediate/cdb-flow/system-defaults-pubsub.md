# SYSTEM_DEFAULTS — 通信メカニズム (Phase G) 中間調査

対象ページ: `docs/reference/config-db/system-defaults.md`
対象テーブル: `CONFIG_DB SYSTEM_DEFAULTS`

## 調査概要

`SYSTEM_DEFAULTS` は `ConsumerStateTable` / `SubscriberStateTable` による pub/sub 駆動の処理ハンドラを持たない。  
各サービスは**起動時に一度だけ** `ConfigDBConnector.get_entry()` / `Table::hget()` でエントリを読み取り、その後は再購読しない。  
そのため Redis PUBLISH/SUBSCRIBE チャネルを通じた動的変更通知は発生しない。

## 1. 読み取り側（Consumer）の通信方式

### 1.1 muxorch — Table::hget (ランタイム 1 回読み)

`sonic-swss/orchagent/muxorch.cpp:1388-1390`:

```cpp
unique_ptr<Table> m_systemDefaultsTable =
    unique_ptr<Table>(new Table(m_config_db.get(), "SYSTEM_DEFAULTS"));
m_systemDefaultsTable->hget("mux_tunnel_egress_acl", "status", value);
```

- **通信方式**: `swsscommon::Table::hget()` → Redis `HGET SYSTEM_DEFAULTS|mux_tunnel_egress_acl status`（同期 one-shot）
- **購読なし**: `SubscriberStateTable` / `ConsumerStateTable` は使用しない
- **タイミング**: `MuxAclHandler` コンストラクタ呼び出し時（MuxPort 初期化のたびに発生）

### 1.2 orchagent.sh / swss_vars.j2 — sonic-cfggen による起動前読み取り

`sonic-buildimage/files/build_templates/swss_vars.j2:14`:

```jinja2
"dscp_remapping": {% if SYSTEM_DEFAULTS is defined and SYSTEM_DEFAULTS.tunnel_qos_remap is defined
                      and SYSTEM_DEFAULTS.tunnel_qos_remap.status == "enabled" %}"enable"{% else %}"disable"{% endif %},
```

- **通信方式**: `sonic-cfggen -d -t swss_vars.j2` が `ConfigDBConnector.get_table("SYSTEM_DEFAULTS")` で全エントリをスナップショット取得
- **購読なし**: テンプレートレンダリングは 1 回限りの同期読み取り。完了後 orchagent.sh が orchagent プロセスを起動する
- **タイミング**: orchagent コンテナ起動スクリプト実行時（swss priority=4）

### 1.3 docker-fpm-frr supervisord.conf.j2 — コンテナ起動前テンプレート展開

`sonic-buildimage/dockers/docker-fpm-frr/frr/supervisord/supervisord.conf.j2:213`:

```jinja2
{% if SYSTEM_DEFAULTS is defined and SYSTEM_DEFAULTS.software_bfd is defined
      and SYSTEM_DEFAULTS.software_bfd.status is defined
      and SYSTEM_DEFAULTS.software_bfd.status == "enabled" %}
[program:bfdmon]
command=/usr/local/bin/bfdmon
{% endif %}
```

- **通信方式**: コンテナ起動前の Jinja2 テンプレート展開（`sonic-cfggen` 呼び出し）
- **購読なし**: 展開後は静的 supervisord.conf として保存され、実行中の変更反映は不可
- **タイミング**: docker-fpm-frr コンテナ起動前の entrypoint 処理

### 1.4 config_samples.py / minigraph.py — 設定生成時の同期参照

- `sonic-buildimage/src/sonic-config-engine/config_samples.py:160-188`
- `sonic-buildimage/src/sonic-config-engine/minigraph.py:2211-2215`

これらは `SYSTEM_DEFAULTS` を**読むのではなく書く**側であり、設定生成ツール（sonic-cfggen）実行時の Python 辞書操作。Redis pub/sub は関与しない。

## 2. 書き込み側（Producer）の通信方式

`SYSTEM_DEFAULTS` への書き込みは以下の経路のみ:

| 書き込み元 | 通信方式 | タイミング |
|-----------|---------|----------|
| `init_cfg.json.j2` 展開 → `sonic-cfggen -j init_cfg.json` | `ConfigDBConnector.mod_config_db_data()` (JSON 一括投入) | OS 初回起動時 |
| `config_samples.py` (SmartSwitch DPU profile 生成) | Python dict 操作 → `ConfigDBConnector.mod_config_db_data()` | `config-setup` 実行時 |
| `minigraph.py` (minigraph 変換) | Python dict 操作 → `ConfigDBConnector.mod_config_db_data()` | `sonic-cfggen -m minigraph.xml` 実行時 |

いずれも `ProducerStateTable` / `SubscriberStateTable` を経由しない。直接 HSET / HMSET で書き込む。

## 3. pub/sub チャネルまとめ

| 経路 | DB | チャネル | 使用有無 | 理由 |
|------|-----|---------|---------|------|
| CONFIG_DB `SYSTEM_DEFAULTS` → 任意ハンドラ | 4 | `SYSTEM_DEFAULTS_CHANNEL@4` | **使用なし** | Consumer ハンドラが存在しない |
| `SYSTEM_DEFAULTS` keyspace notification | 4 | `__keyspace@4__:SYSTEM_DEFAULTS\|*` | **使用なし** | どのプロセスも PSUBSCRIBE していない |
| muxorch → CONFIG_DB one-shot read | 4 | なし (同期 HGET) | 使用あり (read-only) | `Table::hget()` は pub/sub を使わない |
| sonic-cfggen → CONFIG_DB snapshot | 4 | なし (同期 KEYS+HGETALL) | 使用あり (read-only) | テンプレート展開時の一括読み取り |

## 4. 動的変更への非対応（設計上の制約）

`SYSTEM_DEFAULTS` は「起動時設定」として設計されている。実行中に値を変更しても：

- `muxorch` の `mux_tunnel_egress_acl` 参照: `MuxAclHandler` コンストラクタは**既存インスタンスに対して再実行されない**。ACL テーブルは作成時の値で固定される。
- `synchronous_mode` / `dscp_remapping`: orchagent 起動時に `swss_vars.j2` でレンダリング済みのため、orchagent 再起動なしには変更不可。
- `software_bfd`: supervisord.conf は静的ファイルとして生成済みのため、bfdmon の起動/停止は docker-fpm-frr コンテナの再起動を要する。

これらの制約は pub/sub の欠如に起因する設計上の選択であり、バグではない。

## 5. 参照

- `sonic-swss/orchagent/muxorch.cpp:1388-1390`（SHA `4305596156d70e9797e8a881b3d19b46de0bce0d`）
- `sonic-buildimage/files/build_templates/swss_vars.j2:14`（SHA `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`）
- `sonic-buildimage/dockers/docker-fpm-frr/frr/supervisord/supervisord.conf.j2:213`（SHA `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`）
- `sonic-buildimage/src/sonic-config-engine/config_samples.py:160-188`（SHA `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`）
- `sonic-buildimage/src/sonic-config-engine/minigraph.py:2211-2215`（SHA `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`）
