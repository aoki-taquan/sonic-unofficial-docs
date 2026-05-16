# DHCP_SERVER_IPV4 書込み順依存 (Phase B)

対象: `DHCP_SERVER_IPV4|<name>`
Consumer: `dhcpservd` (sonic-dhcp-server パッケージ)
Evidence: sonic-buildimage `src/sonic-dhcp-utilities/dhcp_utilities/dhcpservd/dhcp_cfggen.py`, `dhcpservd.py`, `common/dhcp_db_monitor.py`, `dockers/docker-dhcp-server/cli/config/plugins/dhcp_server.py`

---

## 1. 他テーブル先行必須（依存テーブル順序）

### 1-1. VLAN / VLAN_INTERFACE が先行必須

`dhcp_cfggen.py` の `generate()` は CONFIG_DB から以下の順序でテーブルを読み込む:

1. `DEVICE_METADATA` — hostname・smart_switch 判定
2. `VLAN_INTERFACE` — VLAN の IPv4 サブネット取得 (`_get_vlan_ipv4_interface`)
3. `VLAN_MEMBER` — VLAN メンバーポート一覧
4. `DHCP_SERVER_IPV4`, `DHCP_SERVER_IPV4_CUSTOMIZED_OPTIONS`, `DHCP_SERVER_IPV4_RANGE`, `DHCP_SERVER_IPV4_PORT` — DHCP 設定

`VLAN_INTERFACE` に `<name>|<ipv4_prefix>` エントリが存在しない状態で `DHCP_SERVER_IPV4` を SET しても、
`_parse_port()` の `if dhcp_interface_name not in dhcp_interfaces` ブランチ (`dhcp_cfggen.py:432-433`) で
`LOG_WARNING` を出してそのインタフェースのプール設定をスキップする。
kea-dhcp4 は起動するが該当 VLAN のサブネット定義が生成されず DISCOVER に応答しない。

**推奨順序**:
```
SET VLAN|<name>
SET VLAN_INTERFACE|<name>|<ipv4_prefix>
SET VLAN_MEMBER|<name>|<port>
--- その後 ---
SET DHCP_SERVER_IPV4|<name>
```

CLI の `dhcp_server ipv4 add` も `VLAN_INTERFACE|<name>` の存在チェックを行い
(`dhcp_server.py:82`)、存在しない場合は `ctx.fail()` で即終了する。

### 1-2. DEVICE_METADATA.localhost.dhcp_server が先行必須

`dhcp_server.py:54` の `dhcp_server` グループ入口で
`FEATURE|dhcp_server` の `state` が `enabled` か確認し、有効でなければ CLI コマンドをすべて失敗させる。
`dhcpservd` プロセス自体も `dhcp_server` feature が有効でない限り起動しない。

**推奨順序**:
```
SET DEVICE_METADATA|localhost  dhcp_server=enabled  ← feature 有効化
--- その後 ---
SET DHCP_SERVER_IPV4|<name>
```

### 1-3. DHCP_SERVER_IPV4_RANGE が先行必須（mode=PORT + ranges 利用時）

CLI `dhcp_server ipv4 range add <range_name>` → `dhcp_server ipv4 bind <vlan> <port> --range <range>` という順序が強制される。
`bind` コマンド (`dhcp_server.py:281`) は `DHCP_SERVER_IPV4_RANGE|<r>` の存在チェックを行い、
存在しない場合は `ctx.fail()` する。

`dhcp_cfggen.py:452-454` でも `range_name not in ranges` の場合は `LOG_WARNING: "Range %s is not in range table, skip"` で
そのレンジをスキップする（他ポートは継続）。

**推奨順序**:
```
SET DHCP_SERVER_IPV4_RANGE|<range_name>
--- その後 ---
SET DHCP_SERVER_IPV4_PORT|<vlan>|<port>  (ranges@ フィールド参照)
```

### 1-4. DHCP_SERVER_IPV4_CUSTOMIZED_OPTIONS が先行必須（customized_options 使用時）

CLI `dhcp_server ipv4 option add <name>` → `dhcp_server ipv4 option bind <vlan> <option>` という順序が強制される。
`option bind` (`dhcp_server.py:409-411`) は `DHCP_SERVER_IPV4_CUSTOMIZED_OPTIONS|<name>` の存在チェックを行い、
存在しない場合は `ctx.fail()` する。

`dhcp_cfggen.py:213-215` では `option not in customized_option_keys` の場合に `LOG_WARNING` を出し
そのオプションをスキップする（DHCP 設定生成は継続）。

**推奨順序**:
```
SET DHCP_SERVER_IPV4_CUSTOMIZED_OPTIONS|<option_name>
--- その後 ---
SET DHCP_SERVER_IPV4|<name>  (customized_options@ フィールド参照)
```

---

## 2. SET/DEL 操作の順序依存

### 2-1. state=enabled を SET してから DEL する場合

`DhcpServerTableCfgChangeEventChecker._process_check()` (`dhcp_db_monitor.py:173-184`) の動作:
- `key in enabled_dhcp_interfaces` (現在 enabled の IF) → DEL でも即 `need_refresh=True`
- `op == "SET"` かつ `state == "enabled"` → `need_refresh=True`

enabled 状態の `DHCP_SERVER_IPV4` エントリを DEL すると、
dhcpservd は `generate()` を再実行して kea-dhcp4 に SIGHUP を送る。
kea-dhcp4 は新設定を読み込み、削除された IF のサブネットを除去する。
既存リース (`kea-lease.csv`) はリース期限まで有効のまま残る。

**副作用**: DEL 後、リース期限まで既存クライアントは IP を使い続ける（期限切れまで新規割当は受け付けない）。

### 2-2. state=disabled にしてから DEL する（安全パターン）

1. SET `state=disabled` → dhcpservd が regenerate して kea-dhcp4 がその IF の応答を停止
2. DEL エントリ → dhcpservd が再度 regenerate（実質 noop）

`dhcp_server ipv4 disable` → `dhcp_server ipv4 del` の CLI 順序がこれに対応する。

### 2-3. DHCP_SERVER_IPV4_RANGE を使用中に DEL する場合

`dhcp_sever_ipv4_range_del()` は `--force` なしの場合、
`DHCP_SERVER_IPV4_PORT*` を全スキャンして参照中の range であれば `ctx.fail()` する (`dhcp_server.py:256-259`)。

`--force` フラグで強制 DEL した場合、`dhcp_cfggen.py:452-454` で `LOG_WARNING` となり
そのレンジのプールは kea-dhcp4 設定から消える（次回 DISCOVER からそのレンジへの割当なし）。

**安全な DEL 順序**:
```
dhcp_server ipv4 unbind <vlan> <port> --range <range>
dhcp_server ipv4 range del <range_name>
```

### 2-4. DHCP_SERVER_IPV4_CUSTOMIZED_OPTIONS を参照中に DEL する場合

`dhcp_server_ipv4_option_del()` は `DHCP_SERVER_IPV4|*` を全スキャンして参照中のオプションは拒否する (`dhcp_server.py:390-393`)。

**安全な DEL 順序**:
```
dhcp_server ipv4 option unbind <vlan> <option>
dhcp_server ipv4 option del <option_name>
```

---

## 3. Notification / SIGHUP 順序

dhcpservd は `dump_dhcp4_config()` 内で:
1. `generate()` を呼んで kea-dhcp4.conf を上書き
2. `_notify_kea_dhcp4_proc()` で kea-dhcp4 プロセスに SIGHUP

kea-dhcp4 は SIGHUP 受信後に設定ファイルを再読み込みする。
設定ファイル書込みと SIGHUP の間にウィンドウがあるが、single-threaded で即時実行されるため
競合リスクは最小限。

CONFIG_DB への書込み → dhcpservd の `select()` がタイムアウト内 (5000 ms) で検知 →
`dump_dhcp4_config()` → SIGHUP の経路が 1 回の変更につき 1 回だけ発生する。

---

## 4. warm-reboot 影響

dhcpservd は stateless（CONFIG_DB から毎回全量 generate）。
warm-reboot で dhcpservd が再起動すると `start()` → `dump_dhcp4_config()` → kea-dhcp4 SIGHUP が
自動的に行われるため、CONFIG_DB の内容が整合していれば再起動後に設定が自動復元される。

kea-lease.csv は `/var/lib/kea/kea-lease.csv` に永続化されており、
warm-reboot 後も既存リース情報は引き継がれる。

---

## 5. restart 要否まとめ

| 操作 | dhcpservd restart | kea-dhcp4 restart |
|------|------------------|------------------|
| DHCP_SERVER_IPV4 SET/DEL | 不要（自動 SIGHUP） | 不要（SIGHUP で再読込） |
| DHCP_SERVER_IPV4_PORT SET/DEL | 不要 | 不要 |
| DHCP_SERVER_IPV4_RANGE SET/DEL | 不要 | 不要 |
| DHCP_SERVER_IPV4_CUSTOMIZED_OPTIONS SET/DEL | 不要 | 不要 |
| DEVICE_METADATA dhcp_server 変更 | 要（feature 有無で起動自体が変わる） | 要 |
| VLAN_INTERFACE ipv4_prefix 変更 | 不要（次回 generate で反映） | 不要 |
