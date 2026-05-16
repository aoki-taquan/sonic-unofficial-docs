# DEVICE_METADATA 失敗挙動 (Phase D)

intermediate for `docs/reference/config-db/device-metadata.md` Phase D block.

## 調査対象ソース

- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_device_global.py`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/manager.py`
- `sonic-host-services/scripts/hostcfgd`
- `sonic-buildimage/dockers/docker-orchagent/orchagent.sh`
- `sonic-swss/fpmsyncd/fpmsyncd.cpp`
- `sonic-linkmgrd/src/DbInterface.cpp`

---

## consumer 別 retry / recovery メカニズム

### bgpcfgd (managers_bgp.py + manager.py)

`manager.py` の `Manager` 基底クラスが統一的な retry キューを実装。

1. `set_handler(key, data)` が `False` を返した場合 → `set_queue.append((key, data))` で後回し
2. deps 変化（Loopback0 IP 付与・bgp_asn 登録・DEVICE_NEIGHBOR_METADATA 追加等）のたびに `on_deps_change()` が呼ばれ、`set_queue` 全件を再試行
3. 再試行で `True` が返れば成功扱い（キューから除去）。再 `False` なら `new_queue` に残す

retry 間隔: 依存関係変化ドリブン（タイマーなし）
retry 上限: なし
backoff: なし

DEVICE_METADATA の依存として登録されているキー:
- `localhost/bgp_asn` (`managers_bgp.py:119`)
- `localhost/type` (`managers_bgp.py:120`)

---

## 失敗パス一覧

### 1. `bgp_asn` 未設定 — BGPPeerMgr が bgp_asn を KeyError で参照できない

`managers_bgp.py:192` の `directory.get_slot(...)["localhost"]["bgp_asn"]` は deps チェック (`localhost/bgp_asn` の登録) でガードされているため、bgp_asn 設定後まで `set_handler` 自体が呼ばれない。

- `managers_bgp.py:119` でdep として `("CONFIG_DB", CFG_DEVICE_METADATA_TABLE_NAME, "localhost/bgp_asn")` を登録
- bgp_asn が未設定の間は `directory.available_deps()` が False → `on_deps_change()` が即 return
- **効果**: BGP ピア追加処理全体が開始されない。bgp_asn 設定後に自動 replay

ログ: なし（deps 未充足時は silent）

---

### 2. `bgp_router_id` 未設定 + Loopback0 IPv4 未設定 → `return False` (retry)

`managers_bgp.py:186-189` — `add_peer()`:

```python
if (lo_ipv4 is None and "bgp_router_id"
    not in self.directory.get_slot("CONFIG_DB", CFG_DEVICE_METADATA_TABLE_NAME)["localhost"]):
    log_warn(loopback + " ipv4 address is not presented yet and bgp_router_id not configured")
    return False
```

- ログ: `LOG_WARN "Loopback0 ipv4 address is not presented yet and bgp_router_id not configured"`
- 効果: `set_queue` に追記。Loopback0 IP 付与または `bgp_router_id` 設定で `on_deps_change()` replay
- rollback: なし（FRR への操作未発行）

---

### 3. `switch_type` が syncd で hget 失敗 → 空文字で続行（例外なし）

syncd は起動時に `switch_type` を `hget` で取得するが、フィールド不在時は空文字のまま続行する（例外なし）。通常 `npu` として動作。

- ログ: なし
- 効果: npu モードで SAI 初期化

---

### 4. `mac` フィールド不在 → orchagent が eth0 MAC にフォールバック

`orchagent.sh:12-16`:

```bash
MAC_ADDRESS=$(echo $SWSS_VARS | jq -r '.mac')
if [ "$MAC_ADDRESS" == "None" ] || [ -z "$MAC_ADDRESS" ]; then
    MAC_ADDRESS=$(ip link show eth0 | grep ether | awk '{print $2}')
    logger "Mac address not found in Device Metadata, Falling back to eth0"
fi
```

- ログ: syslog に `"Mac address not found in Device Metadata, Falling back to eth0"` (logger コマンド)
- 効果: orchagent は eth0 の MAC アドレスを使って起動続行
- rollback: なし

---

### 5. `mac` フォーマット不正 → linkmgrd が `MUX_ERROR(ConfigNotFound)` をスロー (起動失敗)

`sonic-linkmgrd/src/DbInterface.cpp:575-577`:

```cpp
catch (const std::invalid_argument &invalidArgument) {
    throw MUX_ERROR(ConfigNotFound, "Invalid ToR MAC address " + mac);
}
```

`DbInterface.cpp:596-598`:

```cpp
} else {
    throw MUX_ERROR(ConfigNotFound, "ToR MAC address is not found");
}
```

- ログ: `MUX_ERROR(ConfigNotFound)` 例外（linkmgrd の致命的エラー）
- 効果: linkmgrd が起動失敗。DualToR 構成では mux 機能が完全に停止
- rollback: なし（linkmgrd は再起動待ち）

---

### 6. `sonic-cfggen` が DEVICE_METADATA から SWSS_VARS 生成失敗 → orchagent コンテナ起動中断

`orchagent.sh:8`:

```bash
SWSS_VARS=$(sonic-cfggen -d -y /etc/sonic/sonic_version.yml -t $SWSS_VARS_FILE) || exit 1
```

- ログ: sonic-cfggen のエラーログ
- 効果: `exit 1` → orchagent プロセス起動中断。supervisord が再起動を試みる
- 原因例: CONFIG_DB 接続失敗、SWSS_VARS_FILE テンプレート異常、`hostname`/`platform` 欠落

---

### 7. `hostname` が空 → hostcfgd が早期 return (hostname-config restart スキップ)

`hostcfgd:1516-1531`:

```python
if not new_hostname:
    syslog.syslog(syslog.LOG_ERR, 'Hostname was not updated: Empty not allowed')
elif new_hostname == self.hostname:
    syslog.syslog(syslog.LOG_INFO, 'Hostname was not updated: Already set up ...')
else:
    ...
    try:
        run_cmd(['sudo', 'service', 'hostname-config', 'restart'], True, True)
    except subprocess.CalledProcessError as e:
        syslog.syslog(syslog.LOG_ERR, 'DeviceMetaCfg: Failed to set new hostname: {}'.format(e))
        return
```

- ログ: `LOG_ERR "Hostname was not updated: Empty not allowed"` (空の場合) / `LOG_ERR "Failed to set new hostname: ..."` (restart 失敗時)
- 効果: hostname-config.service が再起動されない。ホスト名は変更されないまま
- retry: なし (次の CONFIG_DB 変更イベントで再試行)

---

### 8. `timezone` 不正 → hostcfgd が `OSError` をキャッチして LOG_ERR (timedatectl スキップ)

`hostcfgd:1563-1568`:

```python
except OSError as e:
    syslog.syslog(syslog.LOG_ERR, f'DeviceMetaCfg: Invalid timezone files for {ETC_LOCALTIME} {new_tz}: {e}')
except subprocess.CalledProcessError as e:
    syslog.syslog(syslog.LOG_ERR, f'DeviceMetaCfg: Failed to set-timezone {new_tz} and restart rsyslog: {e}')
except Exception as e:
    syslog.syslog(syslog.LOG_ERR, f'DeviceMetaCfg: Failed to apply timezone {new_tz}: {e}')
```

- ログ:
  - `LOG_ERR "DeviceMetaCfg: Invalid timezone files ..."` (tzdata ファイル不在)
  - `LOG_ERR "DeviceMetaCfg: Failed to set-timezone ... and restart rsyslog ..."` (timedatectl コマンド失敗)
- 効果: システムタイムゾーン変更されず、rsyslog も再起動されない
- retry: なし (例外捕捉後そのまま関数終了)

---

### 9. `suppress-fib-pending` + `synchronous_mode` 制約違反 → YANG バリデーションで reject

`sonic-device_metadata.yang:250`:

```yang
must "(current() = 'disabled') or (current() = 'enabled' and ../synchronous_mode = 'enable')";
```

- 効果: `config load` / CLI で `suppress-fib-pending = enabled` かつ `synchronous_mode != 'enable'` を設定しようとすると YANG バリデーションエラーで reject
- ログ: `sonic-yang` ライブラリのバリデーションエラーメッセージ
- rollback: CONFIG_DB への書き込み前に reject (書き込み自体が行われない)
- 実行時の fpmsyncd は suppress-fib-pending の値をそのまま読むだけなので、YANG ガード外からの直接 hset には無効

---

### 10. `yang_config_validation = enable` 時 — CLI 書き込みが GCU 経由に切り替わり YANG バリデーション失敗でロールバック

`validated_config_db_connector.py:13,96-110`:

```python
self.yang_enabled = device_info.is_yang_config_validation_enabled(self.connector)
# ...
GenericUpdater().apply_patch(patch=gcu_patch, ...)
# EmptyTableError → validated_delete_table()
# ValueError → logger.log_notice("Unable to remove entry ...")
```

- 効果: `yang_config_validation = enable` のとき、CLI `set_entry` / `mod_entry` / `delete_table` が `ValidatedConfigDBConnector` 経由になり、YANG 制約違反の変更は GCU が rollback して拒否
- `ValueError` 時: `log_notice` で通知するが例外を re-raise せず（CLI から見ると成功に見えるが CONFIG_DB は変更されない）
- rollback: GCU が YANG バリデーション前に dry_run で確認する設計（`sort=False` で高速化）

---

### 11. `DeviceGlobalCfgMgr.set_handler` でデータ null → `return False`

`managers_device_global.py:61-63`:

```python
if not data:
    log_err("DeviceGlobalCfgMgr:: data is None")
    return False
```

- ログ: `LOG_ERR "DeviceGlobalCfgMgr:: data is None"`
- 効果: `set_queue` に追記。次の BGP_DEVICE_GLOBAL 変更で replay
- rollback: なし

---

### 12. W-ECMP: 不正値 → `return False`

`managers_device_global.py:147-148`:

```python
if status not in ["true", "false"]:
    log_err("W-ECMP: invalid value({}) is provided".format(status))
    return False
```

- ログ: `LOG_ERR "W-ECMP: invalid value(X) is provided"`
- 効果: `set_queue` に追記。DEVICE_METADATA のフィールド値が "true"/"false" 以外だと永続キュー化（deps 変化がなければ再試行なし）

---

### 13. TSA: 不正値 → `return False`

`managers_device_global.py:187-188`:

```python
if tsa_status not in ["true", "false"]:
    log_err("TSA: invalid value({}) is provided".format(tsa_status))
    return False
```

- ログ: `LOG_ERR "TSA: invalid value(X) is provided"`
- 効果: TSA/TSB route-map が適用されない。W-ECMP と同様に永続キュー化

---

### 14. IDF: 不正値 → `return False`

`managers_device_global.py:257-258`:

```python
if idf_isolation_state not in ["unisolated", "isolated_withdraw_all", "isolated_no_export"]:
    log_err("IDF: invalid value({}) is provided".format(idf_isolation_state))
    return False
```

- ログ: `LOG_ERR "IDF: invalid value(X) is provided"`
- 効果: IDF isolation 設定が適用されない

---

### 15. Jinja2 テンプレートレンダリング失敗 (W-ECMP) → `return False`

`managers_device_global.py:159-162`:

```python
except jinja2.TemplateError as e:
    msg = "W-ECMP: error in template rendering"
    log_err("%s: %s" % (msg, str(e)))
    return False
```

- ログ: `LOG_ERR "W-ECMP: error in template rendering: ..."`
- 効果: `set_queue` に追記。ただしテンプレートファイル自体の破損なら replay しても同じ失敗を繰り返す

---

### 16. CHASSIS_APP_DB 接続失敗 → `log_err` + chassis_tsa_status=None で続行

`managers_device_global.py:248-249`:

```python
except Exception as e:
    log_err("Got an exception {}".format(e))
```

- ログ: `LOG_ERR "Got an exception ..."`
- 効果: chassis_tsa_status が None → `get_chassis_tsa_status()` が None を返す → TSA 判定で chassis 分が考慮されない
- rollback: なし

---

## STATE_DB / ERROR_TABLE への記録

- bgpcfgd: `BGP_PEER_CONFIGURED_TABLE` (STATE_DB) に成功時のみ書き込む。失敗 (`return False`) 時は未書き込み
- bgpcfgd: `ERROR_TABLE` は使用しない
- hostcfgd: CONFIG_DB への書き戻しなし（読み取り専用）
- fpmsyncd: DEVICE_METADATA の `suppress-fib-pending` 変更は runtime で動的に反映（restart なし）

---

## orchagent が起動できない条件まとめ

| 原因 | 失敗箇所 | 効果 |
|---|---|---|
| DEVICE_METADATA が CONFIG_DB に存在しない | `sonic-cfggen` (orchagent.sh:8) | `exit 1` → orchagent コンテナ起動失敗 |
| `mac` フィールド不在 | orchagent.sh:13-16 | eth0 MAC へフォールバック（起動続行） |
| `mac` フィールド不在かつ SAI get_switch_attribute 失敗 | main.cpp:877-884 | `handleSaiFailure(fatal=true)` → orchagent プロセス終了 |
| `mac` フォーマット不正 | DbInterface.cpp:576 | linkmgrd 起動失敗（MUX_ERROR） |
| `switch_type` 不正値 | main.cpp:260-264 | `SWSS_LOG_ERROR` + `"switch"` にフォールバック（起動続行、設定意図と乖離） |
| `hostname` 空 | hostcfgd:1517 | hostname-config restart スキップ |
| `timezone` 不正 | hostcfgd:1564 | timedatectl 失敗、rsyslog 再起動されず |
| `suppress-fib-pending=enabled` かつ `synchronous_mode!=enable` | sonic-device_metadata.yang:250 | YANG reject（書き込み前に拒否） |

---

## switchorch.cpp / main.cpp / cfgmgr 追加調査 (Task F Phase D 補完)

### 17. MAC 取得失敗 (SAI) → handleSaiFailure (fatal)

`sonic-swss/orchagent/main.cpp:877-884`:

```cpp
if (!gMacAddress)
{
    attr.id = SAI_SWITCH_ATTR_SRC_MAC_ADDRESS;
    status = sai_switch_api->get_switch_attribute(gSwitchId, 1, &attr);
    if (status != SAI_STATUS_SUCCESS)
    {
        SWSS_LOG_ERROR("Failed to get MAC address from switch, rv:%d", status);
        handleSaiFailure(SAI_API_SWITCH, "get", status, true);
    }
```

- 前提: `mac` フィールド不在 (`orchagent.sh` で eth0 フォールバック成功)、かつ SAI switchId の MAC 属性取得も失敗
- `handleSaiFailure(fatal=true)` → orchagent プロセス終了
- フロー: `orchagent.sh:13-16` (eth0 フォールバック) → `main.cpp:675` (`gMacAddress` チェック) → `main.cpp:877` (SAI get)

### 18. 不正 switch_type → "switch" フォールバック + SWSS_LOG_ERROR

`sonic-swss/orchagent/main.cpp:248-264` (`getCfgSwitchType()`):

```cpp
if (!cfgDeviceMetaDataTable.hget("localhost", "switch_type", switch_type))
    switch_type = "switch";   // 不在: silent fallback

// ...
if (switch_type != "voq" && switch_type != "fabric" && switch_type != "chassis-packet"
    && switch_type != "switch" && switch_type != "dpu")
{
    SWSS_LOG_ERROR("Invalid switch type %s configured", switch_type.c_str());
    switch_type = "switch";   // 不正値: error + fallback
}
```

- ログ: `SWSS_LOG_ERROR("Invalid switch type %s configured", ...)` (不正値のみ)
- フィールド不在時はサイレント (`"switch"` フォールバック)
- `system_error` 例外時も `"switch"` にフォールバック (main.cpp:256)
- 注: `hld.json`/`yang` では有効値は `chassis-packet/fabric/npu/voq/dpu/dummy-sup` だが、`main.cpp` の検証では `npu` ではなく `switch` を既知値として扱っている（コードと HLD の乖離）

### 19. platform (ASIC_VENDOR) 未設定 → buffermgrd (dynamic) 起動中断

`sonic-swss/cfgmgr/buffermgrdyn.cpp:68-73`:

```cpp
string platform = getenv("ASIC_VENDOR") ? getenv("ASIC_VENDOR") : "";
if (platform == "")
{
    SWSS_LOG_ERROR("Platform environment variable is not defined, buffermgrd won't start");
    return;
}
```

- `ASIC_VENDOR` はコンテナ起動時に `docker_image_ctl.j2` が `-e ASIC_VENDOR=<sonic_asic_platform>` でセットする環境変数
- 未設定 (`DEVICE_METADATA.platform` フィールドとは別物) → `return` で初期化中断
- Lua スクリプト (`buffer_headroom_<platform>.lua` 等) が読み込まれないため dynamic buffer 計算が機能しない
- static buffermgr (`buffermgr.cpp`) は `SWSS_LOG_WARN` のみで続行可能

### 20. buffer_model 不整合 → サイレント static モード

`sonic-swss/cfgmgr/buffermgr.cpp:390-406`:

```cpp
if (fvField(i) == "buffer_model")
{
    if (fvValue(i) == "dynamic")
        dynamic_buffer_model = true;
    else
        dynamic_buffer_model = false;
    break;
}
// ...
else if (op == DEL_COMMAND)
    dynamic_buffer_model = false;
```

- `buffer_model` が `"dynamic"` 以外（空値・`"traditional"` 以外の不正値を含む）→ `dynamic_buffer_model = false`
- ログ出力なし、エラーなし（完全サイレント）
- `dynamic_buffer_model = false` のとき `buffermgr` は `pg_profile_lookup.ini` ベースの static バッファ計算を使用
- `buffer_model = "dynamic"` を設定しても static buffermgr (`buffermgr.cpp`) は `dynamic_buffer_model = true` にするだけで、実際の dynamic 計算は `buffermgrdyn.cpp` が担当する（別プロセス分岐）
- `buffermgrd.sh:13-15` で `buffer_model == "dynamic"` のとき `buffermgrdyn` を起動し、そうでなければ `buffermgr` を起動するシェル分岐が存在する
