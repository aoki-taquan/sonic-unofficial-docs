# DHCP_SERVER_IPV4 — Phase G: Redis PUBSUB / keyspace / SubscriberStateTable

対象ページ: `docs/reference/config-db/dhcp-server-ipv4.md`
調査日: 2026-05-15
Evidence:
- `sonic-buildimage/src/sonic-dhcp-utilities/dhcp_utilities/common/dhcp_db_monitor.py`
- `sonic-buildimage/src/sonic-dhcp-utilities/dhcp_utilities/dhcpservd/dhcpservd.py`
- `sonic-swss-common/common/subscriberstatetable.cpp`

---

## 概要

`dhcpservd` は `swss::SubscriberStateTable` を使って複数の CONFIG_DB テーブルを購読する。
`dhcp_db_monitor.py` が各テーブルの `ConfigDbEventChecker` サブクラスを抽象化し、`DhcpServdDbMonitor` が
`swsscommon.Select` (5000 ms ポーリング) で束ねる。
APPL_DB / STATE_DB への中間書き込みは行わず、設定変更を `kea-dhcp4.conf` 全量再生成 + `SIGHUP` で反映する。
ConsumerStateTable / NotificationConsumer / ProducerStateTable は一切使用しない。

---

## 購読テーブルとチェッカー一覧

`dhcpservd.py:main()` が初期化する `ConfigDbEventChecker` サブクラス:

| チェッカークラス | 購読テーブル | 発火条件 | キー: `table_name` |
|---|---|---|---|
| `DhcpServerTableCfgChangeEventChecker` | `DHCP_SERVER_IPV4` | enabled_dhcp_interfaces に含まれる key への変更、または `state=enabled` への遷移 | `DHCP_SERVER_IPV4` |
| `DhcpPortTableEventChecker` | `DHCP_SERVER_IPV4_PORT` | `<vlan>` が enabled_dhcp_interfaces に含まれる場合 | `DHCP_SERVER_IPV4_PORT` |
| `DhcpOptionTableEventChecker` | `DHCP_SERVER_IPV4_CUSTOMIZED_OPTIONS` | option 名が used_options に含まれる場合 | `DHCP_SERVER_IPV4_CUSTOMIZED_OPTIONS` |
| `DhcpRangeTableEventChecker` | `DHCP_SERVER_IPV4_RANGE` | range 名が used_range に含まれる場合 | `DHCP_SERVER_IPV4_RANGE` |
| `VlanTableEventChecker` | `VLAN` | key が enabled_dhcp_interfaces に含まれる場合 | `VLAN` |
| `VlanIntfTableEventChecker` | `VLAN_INTERFACE` | vlan 部分が enabled_dhcp_interfaces に含まれ、かつ IPv4 変更の場合 | `VLAN_INTERFACE` |
| `VlanMemberTableEventChecker` | `VLAN_MEMBER` | `<vlan>` 部分が enabled_dhcp_interfaces に含まれる場合 | `VLAN_MEMBER` |
| `MidPlaneTableEventChecker` | `MID_PLANE_BRIDGE` | DEL 操作、または `bridge` フィールドが enabled_dhcp_interfaces に含まれる場合 | `MID_PLANE_BRIDGE` |
| `DpusTableEventChecker` | `DPUS` | 常に発火 (SmartSwitch DPU 変更) | `DPUS` |

---

## 通信シーケンス

### 1. 初期化 — `main()` (dhcpservd.py:126-148)

```
dhcpservd プロセス起動
  └─ DhcpDbConnector(redis_sock="/var/run/redis/redis.sock")
       ├─ config_db = DBConnector("CONFIG_DB", 0)   ← Redis DB #4 (UNIX socket 経由)
       └─ state_db  = DBConnector("STATE_DB", 0)    ← Redis DB #6 (SERVER_IP 書き込み用)
  └─ sel = swsscommon.Select()
  └─ checkers = [ DhcpServerTableCfgChangeEventChecker(sel, config_db),
                  DhcpPortTableEventChecker(sel, config_db),
                  DhcpOptionTableEventChecker(sel, config_db),
                  DhcpRangeTableEventChecker(sel, config_db),
                  VlanTableEventChecker(sel, config_db),
                  VlanIntfTableEventChecker(sel, config_db),
                  VlanMemberTableEventChecker(sel, config_db),
                  DpusTableEventChecker(sel, config_db),
                  MidPlaneTableEventChecker(sel, config_db) ]
  └─ DhcpServdDbMonitor(db_connector, sel, checkers, select_timeout=5000)
  └─ DhcpServd.start()
       └─ dump_dhcp4_config()         ← 起動時全量生成 (SIGHUP なし)
            └─ dhcp_cfg_generator.generate()
                 → used_ranges, enabled_dhcp_interfaces, used_options, enable_checker
            → monitor.enable_checkers(enable_checker)
                 └─ 各 checker.enable():
                      └─ SubscriberStateTable(config_db, table_name)
                           └─ PSUBSCRIBE __keyspace@4__:<table_name>|*
                      └─ sel.addSelectable(subscriber_state_table)
       └─ _update_dhcp_server_ip()   ← STATE_DB DHCP_SERVER_IPV4_SERVER_IP|eth0 に ip 書き込み
       └─ _signal_readiness()        ← /tmp/dhcpservd_ready に PID 書き込み (kea-dhcp4 gate 解除)
```

### 2. keyspace notification パターン

`ConfigDbEventChecker.enable()` (dhcp_db_monitor.py:69-71) が `SubscriberStateTable` を生成する際に、
内部で以下の PSUBSCRIBE が発行される:

```
PSUBSCRIBE __keyspace@4__:DHCP_SERVER_IPV4|*
PSUBSCRIBE __keyspace@4__:DHCP_SERVER_IPV4_PORT|*
PSUBSCRIBE __keyspace@4__:DHCP_SERVER_IPV4_CUSTOMIZED_OPTIONS|*
PSUBSCRIBE __keyspace@4__:DHCP_SERVER_IPV4_RANGE|*
PSUBSCRIBE __keyspace@4__:VLAN|*
PSUBSCRIBE __keyspace@4__:VLAN_INTERFACE|*
PSUBSCRIBE __keyspace@4__:VLAN_MEMBER|*
PSUBSCRIBE __keyspace@4__:DPUS|*
PSUBSCRIBE __keyspace@4__:MID_PLANE_BRIDGE|*
```

- `@4__` は CONFIG_DB の Redis DB 番号 (通常 4)
- `notify-keyspace-events = "KEA"` が Redis サーバで有効 (sonic-swss-common の dbinterface.cpp が設定)

### 3. 動的チェッカー有効化 / 無効化

チェッカーは起動時に `generate()` の結果に応じて選択的に有効化される:

```python
# dhcpservd.py:57-61
if self.enabled_checker is not None and self.enabled_checker != enable_checker:
    self.dhcp_servd_monitor.disable_checkers(self.enabled_checker - enable_checker)
    self.dhcp_servd_monitor.enable_checkers(enable_checker - self.enabled_checker)
self.enabled_checker = enable_checker
```

`enable_checker` は `dhcp_cfg_generator.generate()` が返す「現在 active なチェッカー名の set」。
kea-dhcp4 設定が変化すると次回 `dump_dhcp4_config()` で更新されるため、使われていない
range/option/port を無駄に購読しない設計になっている。

### 4. Select ループ — `DhcpServd.wait()` (dhcpservd.py:114-123)

```python
while True:
    db_snapshot = {
        "enabled_dhcp_interfaces": self.enabled_dhcp_interfaces,
        "used_range": self.used_range,
        "used_options": self.used_options
    }
    res = self.dhcp_servd_monitor.check_db_update(db_snapshot)
    if res:
        self.dump_dhcp4_config()    # 全量再生成 + SIGHUP
```

`DhcpServdDbMonitor.check_db_update()` (dhcp_db_monitor.py:515-534):

```python
state, _ = self.sel.select(self.select_timeout)   # 5000 ms タイムアウト
if state == Select.TIMEOUT or state != Select.OBJECT:
    return False
need_refresh = False
for checker in self.checker_dict.values():
    if not checker.is_enabled():
        continue
    if need_refresh:
        checker.clear_event()         # 先に refresh 決定済みなら残イベントを drain
    else:
        need_refresh |= checker.check_update_event(db_snapshot)
return need_refresh
```

- `Select.select()` は epoll ベース。5000 ms タイムアウトで blocking。
- タイムアウト時は False を返してループし続ける (busy wait なし)
- いずれか 1 つのチェッカーが `True` を返した時点で残チェッカーのイベントを drain して返す
- `dump_dhcp4_config()` は 1 回の "need_refresh=True" 判定につき 1 回だけ呼ばれる

### 5. `dump_dhcp4_config()` — 全量再生成と SIGHUP (dhcpservd.py:51-68)

```
dump_dhcp4_config()
  └─ dhcp_cfg_generator.generate()    ← CONFIG_DB 全件読み直し (snapshot ではなく live read)
       → kea_dhcp4_config (JSON 文字列)
       → used_ranges, enabled_dhcp_interfaces, used_options, enable_checker
  └─ (チェッカー差分があれば enable/disable)
  └─ write kea-dhcp4.conf             ← /etc/kea/kea-dhcp4.conf 上書き
  └─ _notify_kea_dhcp4_proc()
       └─ psutil.process_iter() で kea-dhcp4 を探して SIGHUP 送信
            → kea-dhcp4 が kea-dhcp4.conf を再読込 (reload)
```

---

## 重要な特性まとめ

| 特性 | 内容 |
|------|------|
| 通知種別 | Redis keyspace notification (PUBSUB PSUBSCRIBE) |
| SWSS abstraction | `swss::SubscriberStateTable` |
| 購読テーブル数 | 最大 9 テーブル (enable_checker により動的に変化) |
| Select timeout | 5000 ms (DEFAULT_SELECT_TIMEOUT) |
| 起動時スナップショット | なし — `generate()` で CONFIG_DB から live 読み取り |
| 実行時変更反映 | `check_update_event()` が True → `dump_dhcp4_config()` 全量再生成 + SIGHUP |
| ConsumerStateTable | 不使用 |
| NotificationConsumer | 不使用 |
| ProducerStateTable | 不使用 |
| APPL_DB 中継 | なし (kea-dhcp4.conf ファイル経由) |
| SAI 経由 | なし (Linux ユーザー空間 DHCP) |
| TTL / expire | 不使用 |
| STATE_DB 書き込み | `DHCP_SERVER_IPV4_SERVER_IP|eth0` に dhcpservd の eth0 IPv4 を書き込む (起動時 1 回) |
| 再起動耐性 | stateless (毎回 generate)。kea-lease.csv は永続化 |

---

## チェッカーの発火判定ロジック詳細

### DhcpServerTableCfgChangeEventChecker (dhcp_db_monitor.py:173-184)

```
key in enabled_dhcp_interfaces  → True  (有効 IF の変更は常に再生成)
op == "SET" and state == "enabled" → True  (新たに enabled になる場合)
その他 → False
```

### DhcpServerTableIntfEnablementEventChecker (dhcp_db_monitor.py:200-214)

dhcprelayd 向けのチェッカー。dhcpservd は使用しない。

### DhcpPortTableEventChecker (dhcp_db_monitor.py:230-236)

```
key.split("|")[0] in enabled_dhcp_interfaces → True
```
PORT テーブルキーは `<vlan>|<port>` 形式。vlan 部分が enabled なら再生成。

### DhcpRangeTableEventChecker (dhcp_db_monitor.py:252-257)

```
key in used_range → True
```
使用中の range のみ監視対象。未使用 range の変更は無視。

### DhcpOptionTableEventChecker (dhcp_db_monitor.py:273-278)

```
key in used_options → True
```
使用中のカスタムオプションのみ監視対象。

### VlanIntfTableEventChecker (dhcp_db_monitor.py:315-324)

```
vlan_name in enabled_dhcp_interfaces and ip_address is not None
    and ipaddress.ip_address(ip_address).version == 4 → True
```
IPv4 アドレス変更のみを捕捉 (IPv6 変更は無視)。

---

## 参照コード

| ファイル | 行 | 内容 |
|---|---|---|
| `dhcpservd.py` | 126-148 | `main()` — チェッカー初期化、DhcpServdDbMonitor 生成 |
| `dhcpservd.py` | 51-68 | `dump_dhcp4_config()` — 全量再生成 + SIGHUP |
| `dhcpservd.py` | 114-123 | `wait()` — Select ループ本体 |
| `dhcp_db_monitor.py` | 20-158 | `ConfigDbEventChecker` 基底クラス |
| `dhcp_db_monitor.py` | 160-184 | `DhcpServerTableCfgChangeEventChecker` |
| `dhcp_db_monitor.py` | 217-236 | `DhcpPortTableEventChecker` |
| `dhcp_db_monitor.py` | 239-257 | `DhcpRangeTableEventChecker` |
| `dhcp_db_monitor.py` | 260-278 | `DhcpOptionTableEventChecker` |
| `dhcp_db_monitor.py` | 281-299 | `VlanTableEventChecker` |
| `dhcp_db_monitor.py` | 302-324 | `VlanIntfTableEventChecker` |
| `dhcp_db_monitor.py` | 327-346 | `VlanMemberTableEventChecker` |
| `dhcp_db_monitor.py` | 349-368 | `MidPlaneTableEventChecker` |
| `dhcp_db_monitor.py` | 371-385 | `DpusTableEventChecker` |
| `dhcp_db_monitor.py` | 488-534 | `DhcpServdDbMonitor.check_db_update()` |
| `sonic-swss-common/common/subscriberstatetable.cpp` | 17-43 | `SubscriberStateTable` ctor — PSUBSCRIBE + 起動時スナップショット |
| `sonic-swss-common/common/subscriberstatetable.cpp` | 95-165 | `pops()` — keyspace event バッファ処理 |
