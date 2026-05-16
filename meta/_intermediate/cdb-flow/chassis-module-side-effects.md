# CHASSIS_MODULE — 副次 DB 書込 (Phase F)

## 調査対象

- ソース: `sonic-platform-daemons/sonic-chassisd/scripts/chassisd`
- ソース: `sonic-utilities/config/chassis_modules.py`
- 調査日: 2026-05-16

## 副次 DB 書込の全貌

`chassisd` (chassismgr 相当) が CONFIG_DB の `CHASSIS_MODULE` テーブルを変更するとき、**4 種類の副次書込**が発生する。

---

## 1. STATE_DB — CHASSIS_MODULE_TABLE への oper_status 書込

### 書込先

```
STATE_DB  CHASSIS_MODULE_TABLE|<module_name>
  フィールド: name, desc, slot, oper_status, num_asics, serial, presence, model, is_replaceable
```

### 書込トリガーと経路

`ModuleUpdater.module_db_update()` (chassisd:364-478) が `CHASSIS_INFO_UPDATE_PERIOD_SECS=10` 秒間隔のポーリングで実行される。

| トリガー | 書込内容 | コード箇所 |
|---------|---------|-----------|
| 10 秒毎のポーリング | platform API から取得した最新状態 | chassisd:364-397 |
| Platform API 失敗 (`try_get` fallback) | `oper_status='Offline'`, `slot=-1`, 他 `'N/A'` | chassisd:480-530 |
| モジュール削除 (`deinit`) | `module_table._del(name)` でエントリ削除 | chassisd:319-334 |

`CONFIG_DB.CHASSIS_MODULE.admin_status` が `down` の場合でも STATE_DB への書込は継続される（`oper_status` の更新は admin_status 非依存）。

### CHASSIS_APP_DB クリーンアップ（副次効果）

`CHASSIS_DB_CLEANUP_MODULE_DOWN_PERIOD=30` 分経過後に CHASSIS_APP_DB (redis_chassis.server:6380, DB#12) の以下テーブルが削除される:
- `SYSTEM_NEIGH*` (当該モジュールホスト・ASIC 分)
- `SYSTEM_INTERFACE*`
- `SYSTEM_LAG_MEMBER_TABLE*`
- `SYSTEM_LAG_TABLE*` + `SYSTEM_LAG_ID_TABLE` + `SYSTEM_LAG_ID_SET` (LAG ID 返却)

(chassisd:593-680)

---

## 2. CHASSIS_STATE_DB — CHASSIS_ASIC_INFO_TABLE / CHASSIS_FABRIC_ASIC_INFO_TABLE への書込

### 書込先

```
CHASSIS_STATE_DB  CHASSIS_ASIC_TABLE|asic<N>           (Supervisor)
CHASSIS_STATE_DB  <module_name>|CHASSIS_ASIC_TABLE|asic<N>  (Linecard)
  フィールド: pci_address, name, asic_id_in_module
```

### 書込トリガーと経路

`ModuleUpdater.module_db_update()` (chassisd:447-457) が `admin_status != 'down'` かつ `oper_status == 'Online'` のモジュールについて ASIC エントリを書き込む。

| 条件 | 書込挙動 |
|------|---------|
| `oper_status == 'Online'` かつ `admin_status != 'down'` | 全 ASIC の `pci_address`・`name`・`asic_id_in_module` を書き込み |
| モジュールが `not Online` に遷移 | 対象モジュールの全 ASIC エントリを削除 (`asic_table._del(asic)`) |
| SmartSwitch: Supervisor 上 | `CHASSIS_FABRIC_ASIC_TABLE` に書き込み |

(chassisd:444-478)

---

## 3. STATE_DB — CHASSIS_MIDPLANE_INFO_TABLE への書込

### 書込先

```
STATE_DB  CHASSIS_MIDPLANE_INFO_TABLE|<module_name>
  フィールド: ip, access
```

### 書込トリガーと経路

`ModuleUpdater.midplane_status_update()` (chassisd:530-591) が 10 秒ポーリング毎に実行。

| フィールド | 値 | 条件 |
|-----------|---|------|
| `ip` | `midplane_ip` (platform API) または `'0.0.0.0'` (fallback) | 常時 |
| `access` | `True` / `False` | midplane 到達可否 |

linecard_reboot_timeout 経過後も midplane が未復旧の場合、警告ログを出力する (chassisd:585-586)。

---

## 4. systemd サービス制御（FABRIC-CARD 限定）

CONFIG_DB の `CHASSIS_MODULE.admin_status` 変化に連動して、FABRIC-CARD に限り **systemd サービスの起動・停止**が副次的に実行される。

### 制御対象

```
systemctl stop  swss@<asic>.service
systemctl start swss@<asic>.service
systemctl reset-failed swss@<asic>.service
```

### 実行経路

`config chassis_modules shutdown/startup FABRIC-CARD*` (`sonic-utilities/config/chassis_modules.py:94-131`) から:

1. CONFIG_DB に `admin_status: down/up` を書き込み
2. 最大 `TIMEOUT_SECS=10` 秒待機し chassisd の `set_admin_state()` 完了を確認
3. タイムアウト後 (または chassisd 未起動時) に `fabric_module_set_admin_status()` 経由で `systemctl` を強制実行

| 状態 | systemctl 操作 | コード箇所 |
|------|--------------|-----------|
| `state == 'down'` | `stop swss@<asic>.service` → サービス停止確認 → `CHASSIS_FABRIC_ASIC_TABLE` エントリ削除 | config:105-119 |
| `state == 'down'` (修復) | `reset-failed + start swss@<asic>.service` | config:123-127 |
| `state == 'up'` | `start swss@<asic>.service` | config:129-131 |

ASIC リストは `CHASSIS_STATE_DB.CHASSIS_FABRIC_ASIC_TABLE` から取得する (config:83-91)。

---

## Evidence

- `sonic-platform-daemons/sonic-chassisd/scripts/chassisd:364-478` — `module_db_update()` STATE_DB/CHASSIS_STATE_DB 書込
- `sonic-platform-daemons/sonic-chassisd/scripts/chassisd:530-591` — `midplane_status_update()` STATE_DB 書込
- `sonic-platform-daemons/sonic-chassisd/scripts/chassisd:593-680` — `_cleanup_chassis_app_db()` CHASSIS_APP_DB 削除
- `sonic-platform-daemons/sonic-chassisd/scripts/chassisd:667-681` — `module_down_chassis_db_cleanup()` 30 分タイマー
- `sonic-utilities/config/chassis_modules.py:83-131` — `fabric_module_set_admin_status()` systemd 制御
