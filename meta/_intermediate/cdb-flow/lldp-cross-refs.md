# LLDP テーブル 暗黙参照スキャン (Phase C)

`docs/reference/config-db/lldp.md` の Phase C (暗黙参照) ブロック裏付け資料。

ソースは `sonic-net/sonic-buildimage/dockers/docker-lldp/lldpmgrd` および同 `lldpd.conf.j2`。
`LLDP` / `LLDP_PORT` テーブル設定時に `lldpmgrd` が間接的に読み出す関連 CONFIG_DB テーブルを列挙する。

## スキャン手順

```
grep -n "subscribe\|Table\|CFG_\|lldp_process\|update_hostname\|update_mgmt\|lldp_get_mgmt" \
    .cache/sonic-sources/sonic-buildimage/dockers/docker-lldp/lldpmgrd
```

```
grep -n "DEVICE_METADATA\|MGMT_INTERFACE\|MGMT_PORT\|hostname\|mgmt_if\|LLDP\|PORT" \
    .cache/sonic-sources/sonic-buildimage/dockers/docker-lldp/lldpd.conf.j2
```

`lldpmgrd` の `__init__()` で生成される Table オブジェクト（L74-78）と `run()` で登録される
SubscriberStateTable（L301-310）、および `lldpd.conf.j2` のテンプレート参照（L1-33）から抽出。

## 検出された暗黙参照テーブル

### lldpmgrd — CONFIG_DB 購読対象 (run() L301-310)

`lldpmgrd` が直接 subscribe するテーブル。`LLDP` / `LLDP_PORT` ではなく以下のテーブルのみを購読する。

| テーブル | SubscriberStateTable | handler | 用途 | evidence |
|---|---|---|---|---|
| `APPL_DB: PORT_TABLE` | `sst_appdb` | `lldp_process_port_table_event()` | ポート `oper_status=up` を検知して `lldpcli configure ports` を発行。`PortInitDone` / `PortConfigDone` イベントで `lldpcli resume` を制御 | lldpmgrd:301,323-325 |
| `CONFIG_DB: MGMT_INTERFACE` | `sst_mgmt_ip_confdb` | `lldp_process_mgmt_info_change()` | 管理 IP (IPv4 優先、次点 IPv6) の変化を検知して `lldpcli configure system ip management pattern <ip>` を更新 | lldpmgrd:305,317-319 |
| `CONFIG_DB: DEVICE_METADATA` | `sst_device_confdb` | `lldp_process_device_table_event()` | `localhost` エントリの `chassis_hostname` / `hostname` フィールドを読み取り `lldpcli configure system hostname <name>` を更新 | lldpmgrd:308,320-322 |

### lldpmgrd — CONFIG_DB 読み出し (Table.get / getKeys)

subscribe に加えてポート設定生成時に一括読み出しを行うテーブル。

| テーブル | 参照箇所 | 用途 | evidence |
|---|---|---|---|
| `CONFIG_DB: PORT` | `self.port_table` — `generate_pending_lldp_config_cmd_for_port()` 内で `port_table_dict.get("alias")` / `port_table_dict.get("description")` を参照 | ポートエイリアス (`portidsubtype local <alias>`) とポート description を lldpcli コマンドに埋め込む | lldpmgrd:75,148-164 |
| `STATE_DB: PORT_TABLE` | `self.state_port_table` — `is_port_up()` 内で `netdev_oper_status` を参照 | ポートが up になるまで lldpcli コマンドをキューイング。up 確認後に発行 | lldpmgrd:78,122-134 |
| `CONFIG_DB: MGMT_INTERFACE` | `lldp_get_mgmt_ip()` — `mgmt_table.getKeys()` + key 分解で IPv4/IPv6 アドレスを抽出 | DEL イベント時に現在の管理 IP を再決定するためのフォールバック検索 | lldpmgrd:76,206-226 |

### lldpd.conf.j2 — 起動時テンプレート参照

`docker-lldp` コンテナ起動時に `sonic-cfggen` が展開する Jinja2 テンプレートが読み取る CONFIG_DB テーブル。

| テーブル | 参照箇所 | 用途 | evidence |
|---|---|---|---|
| `MGMT_INTERFACE` | L2-13: `{% for (mgmt_name, mgmt_prefix) in MGMT_INTERFACE\|pfx_filter %}` で IPv4/IPv6 アドレスを抽出 | 起動時の `configure system ip management pattern <ip>` 生成 | lldpd.conf.j2:2-13 |
| `MGMT_PORT` | L17: `MGMT_PORT[mgmt_if.port_name].alias` の有無で eth0 の `portidsubtype` を決定 | eth0 のポート ID として alias (あれば) / インタフェース名 (なければ) を使用 | lldpd.conf.j2:17-21 |
| `DEVICE_METADATA` | L29: `DEVICE_METADATA['localhost']['hostname']` | 起動時の `configure system hostname <name>` 生成 | lldpd.conf.j2:29 |

## 依存関係サマリ

```
LLDP|GLOBAL / LLDP_PORT|<ifname>
  ┣━━ lldpmgrd は購読しない（構造的 no-op）
  ┗━━ 実際に LLDP 動作を制御するのは以下の暗黙参照テーブル:

CONFIG_DB: DEVICE_METADATA|localhost
  └─► lldpmgrd.lldp_process_device_table_event()
       → lldpcli configure system hostname <chassis_hostname|hostname>

CONFIG_DB: MGMT_INTERFACE|<ifname>|<prefix>
  ├─► lldpmgrd.lldp_process_mgmt_info_change()
  │    → lldpcli configure system ip management pattern <ip>
  └─► lldpd.conf.j2 (起動時)
       → configure system ip management pattern <ip>

CONFIG_DB: MGMT_PORT|<ifname>
  └─► lldpd.conf.j2 (起動時)
       → configure ports eth0 lldp portidsubtype local <alias|port_name>

CONFIG_DB: PORT|<ifname>  (alias, description)
  └─► lldpmgrd.generate_pending_lldp_config_cmd_for_port()
       → lldpcli configure ports <ifname> lldp portidsubtype local <alias>
          [description <desc>]

APPL_DB: PORT_TABLE|<ifname>  (oper_status)
  └─► lldpmgrd.lldp_process_port_table_event()
       → PortInitDone / PortConfigDone → lldpcli resume

STATE_DB: PORT_TABLE|<ifname>  (netdev_oper_status)
  └─► lldpmgrd.is_port_up()
       → up になるまで lldpcli configure ports をキューイング
```

## まとめ — `lldp.md` Phase C 記載対象

| カテゴリ | テーブル |
|---|---|
| 購読 (subscribe) — ランタイム | `CONFIG_DB: DEVICE_METADATA` / `CONFIG_DB: MGMT_INTERFACE` / `APPL_DB: PORT_TABLE` |
| 読み取り (get/getKeys) — ランタイム | `CONFIG_DB: PORT` (alias/description) / `STATE_DB: PORT_TABLE` (netdev_oper_status) |
| 起動時テンプレート参照 (lldpd.conf.j2) | `MGMT_INTERFACE` / `MGMT_PORT` / `DEVICE_METADATA` |

## 検証コマンド

```bash
grep -n "Table\|SubscriberStateTable\|CFG_\|APP_\|STATE_" \
    .cache/sonic-sources/sonic-buildimage/dockers/docker-lldp/lldpmgrd

grep -n "DEVICE_METADATA\|MGMT_INTERFACE\|MGMT_PORT\|hostname\|management pattern" \
    .cache/sonic-sources/sonic-buildimage/dockers/docker-lldp/lldpd.conf.j2
```

このスキャン結果から派生して `docs/reference/config-db/lldp.md` の `<!-- cross-refs -->` ブロックを生成する。
