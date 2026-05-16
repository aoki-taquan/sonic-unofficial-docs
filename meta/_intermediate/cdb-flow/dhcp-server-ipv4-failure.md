# DHCP_SERVER_IPV4 失敗挙動 (Phase D)

intermediate for `docs/reference/config-db/dhcp-server-ipv4.md` Phase D block.

調査日: 2026-05-15

## 調査対象ソース

- `src/sonic-dhcp-utilities/dhcp_utilities/dhcpservd/dhcp_cfggen.py`（全行精読）
- `src/sonic-dhcp-utilities/dhcp_utilities/dhcpservd/dhcpservd.py`（全行精読）
- `src/sonic-dhcp-utilities/dhcp_utilities/dhcprelayd/dhcprelayd.py`（94-98行）
- `dockers/docker-dhcp-server/cli/config/plugins/dhcp_server.py`（54, 105行）

---

## 失敗パス一覧

### 1. dhcpservd 起動: hook lib 未検出 → sys.exit(1)

`dhcpservd.py:main()` — `find / -name libdhcp_run_script.so` の結果が空の場合:

```
LOG_ERR "Cannot find hook lib for kea-dhcp4"
sys.exit(1)
```

**retry なし・rollback なし。即プロセス終了。**

### 2. dhcpservd 起動: hostname 取得失敗 → Exception + プロセス終了

`dhcp_cfggen.py:170-175` — `_parse_hostname()`:
- `DEVICE_METADATA|localhost` の `hostname` フィールドが存在しない場合:

```
LOG_ERR "Cannot get hostname"
raise Exception("Cannot get hostname")
```

Exception は `dhcpservd.start()` 経由で未捕捉のまま上位に伝播し、プロセス終了。

### 3. dhcpservd 起動: readiness flag 書込み失敗 → sys.exit(1)

`dhcpservd.py:102-112` — `_signal_readiness()`:
- `/tmp/dhcpservd_ready` への書き込みが OSError の場合:

```
LOG_ERR "Failed to write readiness flag /tmp/dhcpservd_ready: ..., exiting"
sys.exit(1)
```

`wait_for_dhcpservd.sh` が gate できなくなり kea-dhcp4 も起動しない。

### 4. dhcpservd 起動: eth0 IP アドレス取得失敗 → 10 回 retry → sys.exit(1)

`dhcpservd.py:70-87` — `_update_dhcp_server_ip()`:
- コンテナ内 `eth0` インタフェースから IPv4 アドレスが取得できない場合:
  - `LOG_WARNING "Cannot get ip address of eth0, retry in 5s"` を最大 10 回
  - 10 回全失敗後:

```
LOG_ERR "Failed to get ip address of eth0 after 10 retries, exiting"
sys.exit(1)
```

**retry 回数: 10, retry 間隔: 5s**

### 5. dhcp_cfggen: `state` 欠如または `enabled` 以外 → そのインタフェースを silent skip

`dhcp_cfggen.py:199` — `_construct_obj_for_template()`:
- `DHCP_SERVER_IPV4` エントリに `state` フィールドが存在しないか `enabled` 以外の値の場合:
  - `continue` — **LOG なし・silent skip**
  - そのインタフェースは kea-dhcp4 設定に含まれず DISCOVER に無応答

### 6. dhcp_cfggen: `DHCP_SERVER_IPV4_PORT` エントリなし → LOG_WARNING + skip

`dhcp_cfggen.py:204-207` — PORT モード:
- `state=enabled` のインタフェースに対応する PORT テーブルエントリが存在しない場合:

```
LOG_WARNING "Cannot get DHCP port config for {dhcp_interface_name}"
continue
```

**そのインタフェースは enabled_dhcp_interfaces に記録されるが subnet の pools が空になり DISCOVER に無応答。**

### 7. dhcp_cfggen: カスタムオプション未定義参照 → LOG_WARNING + skip

`dhcp_cfggen.py:213-215` — `customized_options`:
- `DHCP_SERVER_IPV4.customized_options` で参照したオプション名が `DHCP_SERVER_IPV4_CUSTOMIZED_OPTIONS` に存在しない場合:

```
LOG_WARNING "Customized option {option} configured for {dhcp_interface_name} is not defined"
continue
```

そのオプションのみスキップ、他のオプションや設定は継続。

### 8. dhcp_cfggen: 未サポートオプション ID → LOG_ERR + skip

`dhcp_cfggen.py:128-130` — `_parse_customized_options()`:
- `DHCP_SERVER_IPV4_CUSTOMIZED_OPTIONS.id` が標準オプションにも customized オプションにも存在しない場合:

```
LOG_ERR "Unsupported option: {id}"
continue
```

### 9. dhcp_cfggen: 標準オプション型不一致 → LOG_WARNING + 期待型で処理継続

`dhcp_cfggen.py:133-137`:
- standard option の `type` が期待型と異なる場合:

```
LOG_WARNING "Option type [{config_type}] is not consistent with expected dhcp option type [{expected}], will honor expected type"
```

**スキップせず期待型を優先して処理継続（上書き）。**

### 10. dhcp_cfggen: 未サポートオプション型 → LOG_ERR + skip

`dhcp_cfggen.py:140-143`:
- `option_type` が `SUPPORT_DHCP_OPTION_TYPE` 外 (`binary`, `boolean`, `ipv4-address`, `string`, `uint8`, `uint16`, `uint32` 以外):

```
LOG_ERR "Unsupported type: {type}, currently only support {SUPPORT_DHCP_OPTION_TYPE}"
continue
```

### 11. dhcp_cfggen: オプション値型不整合 → LOG_ERR + skip

`dhcp_cfggen.py:144-147`:
- `validate_str_type(option_type, value)` が False の場合:

```
LOG_ERR "Option type [{type}] and value [{value}] are not consistent"
continue
```

### 12. dhcp_cfggen: 文字列オプション値が 253 文字超 → LOG_ERR + skip

`dhcp_cfggen.py:148-150`:
- `type=string` かつ `len(value) > 253` の場合:

```
LOG_ERR "String option value too long: {option_name}"
continue
```

### 13. dhcp_cfggen: VLAN に IPv4 アドレスなし → LOG_WARNING + skip

`dhcp_cfggen.py:432-433` — `_parse_port()`:
- `DHCP_SERVER_IPV4_PORT` エントリの VLAN が `VLAN_INTERFACE` に IPv4 アドレスを持たない場合:

```
LOG_WARNING "Interface {dhcp_interface_name} doesn't have IPv4 address"
continue
```

そのポートへの IP プール割当なし。VLAN が `enabled` でも subnet 未定義 → DISCOVER 無応答。

### 14. dhcp_cfggen: PORT が VLAN メンバー未登録 → LOG_WARNING + skip

`dhcp_cfggen.py:424-426` — `_parse_port()`:
- `DHCP_SERVER_IPV4_PORT` で指定したポートが `VLAN_MEMBER` に存在しない場合:

```
LOG_WARNING "Port {port} is not in {vlan}"
continue
```

そのポートへの IP プール割当なし。

### 15. dhcp_cfggen: `ips` と `ranges` 同時指定 → LOG_WARNING + ポートスキップ

`dhcp_cfggen.py:418-421`:
- ポート設定に `ips`（非空）と `ranges`（非空）が両方存在する場合:

```
LOG_WARNING "Port config for {port_key} contains both ips and ranges, skip"
continue
```

### 16. dhcp_cfggen: 存在しない range 参照 → LOG_WARNING + range スキップ

`dhcp_cfggen.py:452-454`:
- `DHCP_SERVER_IPV4_PORT.ranges` で参照した range 名が `DHCP_SERVER_IPV4_RANGE` に存在しない場合:

```
LOG_WARNING "Range {range_name} is not in range table, skip"
continue
```

### 17. dhcp_cfggen: DHCP_SERVER_IPV4_RANGE の range 長 不正 → LOG_WARNING + skip

`dhcp_cfggen.py:332-334` — `_parse_range()`:
- `range` フィールドの要素数が 0 または 3 以上の場合:

```
LOG_WARNING "Length of {curr_range} is {list_length}, which is invalid!"
continue
```

### 18. dhcp_cfggen: range の start > end → LOG_WARNING + skip

`dhcp_cfggen.py:338-340`:
- `address_start > address_end` の場合:

```
LOG_WARNING "Start of {curr_range} is greater than end, skip it"
continue
```

### 19. CLI: dhcp_server feature 未有効 → ctx.fail() でコマンド終了

`dhcp_server.py:54` — `config dhcp_server` グループ入口:
- `FEATURE|dhcp_server.state != "enabled"` の場合:

```
ctx.fail("dhcp_server feature is not enabled")
```

全 CLI サブコマンドが即時失敗。CONFIG_DB への書き込みは行われない。

### 20. dhcprelayd: DHCP_SERVER_IPV4 有効化 VLAN でリレー除外

`dhcprelayd.py:94-98`:
- `DHCP_SERVER_IPV4|<vlan>.state=enabled` が存在する場合:
  - その VLAN を dhcrelay 起動対象から除外
  - LOG_WARNING なし (silent)
  - **DHCP relay と DHCP server の排他制御**

---

## 障害記録・rollback 動作

| シナリオ | STATE_DB 記録 | rollback |
|---|---|---|
| dhcpservd プロセス異常終了 | なし（dhcpservd は STATE_DB に書き込まない）| supervisord による自動 restart |
| dhcp_cfggen generate エラー（各種 skip） | なし | kea-dhcp4 は古い設定のまま稼働継続 |
| kea-dhcp4 設定ファイル更新後 SIGHUP 失敗 | なし | kea-dhcp4 は SIGHUP 受信まで旧設定で動作 |
| CLI ctx.fail() | なし | CONFIG_DB への書き込みなし |

## partial failure (部分成功)

- 複数 VLAN の DHCP_SERVER_IPV4 エントリのうち、1 つが `state=disabled` / VLAN_INTERFACE 未設定でも、他の `state=enabled` かつ VLAN_INTERFACE 設定済みエントリは正常に kea-dhcp4 設定に含まれる
- 個別オプション/ポート/レンジのスキップは他エントリに影響しない
- dhcpservd の generate 失敗は基本的にエントリ単位のスキップで、プロセス継続

## orchagent/SAI 関与

なし。`dhcpservd` / `kea-dhcp4` は Linux ユーザー空間の DHCP サーバ。APPL_DB 中継なし、SAI 非経由。
