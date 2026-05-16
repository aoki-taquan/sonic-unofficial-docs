# dhcp-server-ipv4 副次 DB 書込調査 (Phase F)

調査日: 2026-05-16  
ソース: `sonic-buildimage/src/sonic-dhcp-utilities/`  
調査対象: `dhcpservd.py`, `dhcp_lease.py`, `dhcp_cfggen.py`

---

## 1. STATE_DB DHCP_SERVER_IPV4_LEASE

### 書き込みトリガー

`dhcpservd` 起動時に `LeaseManager(db_connector, KEA_LEASE_FILE_PATH)` を生成し `start()` を呼ぶ。
`KeaDhcp4LeaseHandler.register()` が `signal.signal(signal.SIGUSR1, self._update_lease)` を登録する。
kea-dhcp4 がリースイベント発生時に `lease_update.sh`（`/etc/kea/lease_update.sh`）経由で SIGUSR1 を dhcpservd に送信し、`update_lease()` が起動する。

ソース: `dhcp_lease.py:102-106`, `dhcp_cfggen.py:24,264`

### key 形式

通常 VLAN の場合:

```
DHCP_SERVER_IPV4_LEASE|Vlan<subnet_id>|<mac_address>
```

SmartSwitch の場合:

```
DHCP_SERVER_IPV4_LEASE|<midplane_bridge_name>|<mac_address>
```

ソース: `dhcp_lease.py:108-112`

### フィールド

| フィールド | 値 | 説明 |
|---|---|---|
| `ip` | IPv4 アドレス文字列 | クライアントに割り当てた IP アドレス (kea-lease.csv の address カラム) |
| `lease_start` | UNIX タイムスタンプ文字列 | `lease_end - valid_lifetime` で算出 |
| `lease_end` | UNIX タイムスタンプ文字列 | kea-lease.csv の expire カラム |

ソース: `dhcp_lease.py:140-144`

### 書き込み/削除ロジック

- `lease_start == lease_end` または `now >= lease_end` → 期限切れ → STATE_DB から DEL
- それ以外 → `hset(DHCP_SERVER_IPV4_LEASE|<key>, field, value)` で更新
- new_lease に存在しない old_lease_key → DEL（リリース済みリース掃除）

ソース: `dhcp_lease.py:79-92`

### レートリミット

`lease_update_interval = 2` 秒。直前の更新から 2 秒未満の場合は 2 秒 sleep して再判定。Lock による排他制御。

ソース: `dhcp_lease.py:63-68`

---

## 2. STATE_DB DHCP_SERVER_IPV4_SERVER_IP

dhcpservd 起動時（`start()` 内）に `_update_dhcp_server_ip()` が 1 回だけ実行される。

### key 形式

```
DHCP_SERVER_IPV4_SERVER_IP|eth0
```

### フィールド

| フィールド | 値 |
|---|---|
| `ip` | dhcp_server コンテナの eth0 IPv4 アドレス |

eth0 の IPv4 アドレスを `psutil.net_if_addrs()` から取得し `hset` で書き込む。取得失敗時は 5 秒間隔で最大 10 回リトライ。10 回失敗で `sys.exit(1)`。

ソース: `dhcpservd.py:70-87`

---

## 3. kea-dhcp4.conf ファイル書き込み

CONFIG_DB の変更を受けた `dump_dhcp4_config()` が `/etc/kea/kea-dhcp4.conf` を上書きする。

### ファイルパス

```
/etc/kea/kea-dhcp4.conf
```

### 書き込みフロー

```
CONFIG_DB 変更 (SubscriberStateTable keyspace event)
  └─ DhcpServdDbMonitor.check_db_update()
       └─ need_refresh=True
            └─ dump_dhcp4_config()
                 └─ DhcpServCfgGenerator.generate()
                      └─ kea_template.render(render_obj)  ← Jinja2
                 └─ open(KEA_DHCP4_CONFIG, "w").write(config)
                 └─ _notify_kea_dhcp4_proc() → SIGHUP → kea-dhcp4 設定再読込
```

ソース: `dhcpservd.py:51-68`, `dhcp_cfggen.py:155-162`

### テンプレート構造 (kea-dhcp4.conf.j2)

| セクション | 内容 |
|---|---|
| `option-def` | カスタム DHCP オプション定義 (customized_options) |
| `hooks-libraries` | `libdhcp_run_script.so` + `lease_update.sh` 経路 (SIGUSR1 トリガー) |
| `interfaces-config` | `eth0` 固定 |
| `lease-database` | `memfile` 型、`/var/lib/kea/kea-lease.csv`、lfc-interval=3600 |
| `subnet4` | enabled VLAN ごとのサブネット + pools + option-data + valid-lifetime |
| `client-classes` | PORT モードのポート-MAC クラス定義 |

ソース: `tests/test_data/kea-dhcp4.conf.j2`

---

## 4. ポート購読 (VlanMember)

`dhcpservd.main()` で `VlanMemberTableEventChecker` を初期化し `VLAN_MEMBER` テーブルを SubscriberStateTable で購読。
`dhcp_cfggen.generate()` 内で `vlan_member_table = get_config_db_table(VLAN_MEMBER)` として全量読み取り、ポートの VLAN 所属確認に使用する。

`_parse_port()` がポートの VLAN メンバー登録を確認し、未登録ポートは `LOG_WARNING "Port {port} is not in {vlan}"` でスキップ。

ソース: `dhcpservd.py:142`, `dhcp_cfggen.py:16,70-71,165-168`

---

## 5. kea-lease.csv (永続ファイル)

`/var/lib/kea/kea-lease.csv` は kea-dhcp4 が直接管理する。dhcpservd は読み取りのみ（SIGUSR1 受信時）。
warm-reboot 後も lease 情報は引き継がれる。lfc-interval=3600 秒で kea が自動 cleanup。

---

## Evidence 一覧

| コード | 内容 |
|---|---|
| `dhcp_lease.py:10-148` | DHCP_SERVER_IPV4_LEASE STATE_DB 書き込み全実装 |
| `dhcpservd.py:22,70-87` | DHCP_SERVER_IPV4_SERVER_IP STATE_DB 書き込み |
| `dhcpservd.py:51-68,97-98` | kea-dhcp4.conf 書き込み + LeaseManager 登録 |
| `dhcp_cfggen.py:16,24,70-71,155-162,264` | kea config 生成 + lease_update_script 設定 |
| `tests/test_data/kea-dhcp4.conf.j2` | kea-dhcp4 設定テンプレート全体 |
