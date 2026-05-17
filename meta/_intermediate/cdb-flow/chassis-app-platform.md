# chassis-app — Phase H: プラットフォーム依存挙動

> 調査対象:
> - `sonic-platform-daemons/sonic-chassisd/scripts/chassisd` @ 4ba9612
> - `sonic-platform-daemons/sonic-chassisd/scripts/chassis_db_init` @ 4ba9612
> - `sonic-swss/orchagent/main.cpp` @ 4305596
> - `sonic-swss-common/common/dbconnector.h` @ 158de8d3463ff4b841653f6d57190bb142b80d9c
> 調査日: 2026-05-17

## 1. プラットフォーム API ロード (sonic_platform プラグイン)

CHASSIS_APP_DB への書き込みを行うプロセス群は、起動時にベンダー提供の `sonic_platform` パッケージをロードする。

### orchagent 側

orchagent は `sonic_platform` を直接呼び出さない。代わりに `/var/run/redis/sonic-db/database_config.json` を参照し `CHASSIS_APP_DB` キーの存在を確認する (`isChassisAppDbPresent()`, `main.cpp:278-287`)。このファイルは OS イメージ構築時にプラットフォーム固有の設定で生成される。

| 確認内容 | 実装 | 証跡 |
|---------|------|------|
| `CHASSIS_APP_DB` キーが `database_config.json` に存在するか | `isChassisAppDbPresent()` が `db_config["DATABASES"].contains("CHASSIS_APP_DB")` を確認 | `main.cpp:283-287` |
| `database_config.json` のデフォルトパス | `/var/run/redis/sonic-db/database_config.json` | `dbconnector.h:90` |

ファイルが存在しない、または `CHASSIS_APP_DB` キーが不在の場合、`isChassisAppDbPresent()` は `false` を返し `gMultiAsicVoq` は立たない（CHASSIS_APP_DB 未使用として動作）。

### chassisd 側

chassisd は起動時に `get_chassis()` を呼び出してプラットフォームオブジェクトを取得する:

```python
def get_chassis():
    try:
        import sonic_platform.platform
        return sonic_platform.platform.Platform().get_chassis()
    except Exception as e:
        self.log_error("Failed to load chassis due to {}".format(repr(e)))
        sys.exit(CHASSIS_LOAD_ERROR)  # exit code=1
```

`sonic_platform` パッケージが存在しない、または `Platform().get_chassis()` が例外を送出した場合は `CHASSIS_LOAD_ERROR=1` で即 exit する。

## 2. プラットフォーム種別分岐

chassisd は取得したシャーシオブジェクトのプラットフォーム種別を判定し、使用するモジュール更新クラスを切り替える:

| 条件 | 使用クラス | 主な違い |
|-----|-----------|---------|
| `chassis.is_smartswitch() == True` | `SmartSwitchModuleUpdater` | DPU 向け設定・状態管理、`dpu_reboot_timeout` を `platform.json` から読み取る |
| `chassis.is_smartswitch() == False` | `ModuleUpdater` | VoQ ラインカード/スーパーバイザー向け、`my_slot` / `supervisor_slot` を `get_my_slot()` / `get_supervisor_slot()` で取得 |

非 SmartSwitch の場合、`my_slot` または `supervisor_slot` が `INVALID_SLOT`（= `ModuleBase.MODULE_INVALID_SLOT`）のとき:
```
self.log_error("Chassisd not supported for this platform")
sys.exit(CHASSIS_NOT_SUPPORTED)  # exit code=2
```
（`chassisd:1424-1427`）

スーパーバイザーか否かの判定: `my_slot == supervisor_slot` が `True` なら supervisor (`_is_supervisor()`, `chassisd:510-511`)。supervisor のみが `ConfigManagerTask` を起動し CONFIG_DB の `CHASSIS_MODULE` テーブルを購読してモジュールの admin_state を制御する。

## 3. プラットフォーム設定ファイル

| ファイルパス | 用途 | 読み取りタイミング |
|------------|------|----------------|
| `/usr/share/sonic/platform/platform_env.conf` | `linecard_reboot_timeout`（秒）の上書き設定 | `ModuleUpdater.__init__()` 時に一度だけ読み取り（`chassisd:302-307`） |
| `/usr/share/sonic/platform/platform.json` | `dpu_reboot_timeout`（秒）の上書き設定 (SmartSwitch 用) | `SmartSwitchModuleUpdater.__init__()` 時に読み取り（`chassisd:722-729`） |
| `/var/run/redis/sonic-db/database_config.json` | `CHASSIS_APP_DB` 接続先（host/port/unix-socket）の定義 | orchagent 起動時の `isChassisAppDbPresent()` で読み取り |

`platform_env.conf` が存在しない場合は `DEFAULT_LINECARD_REBOOT_TIMEOUT=180` 秒がそのまま使用される。  
`platform.json` が存在しない、または `dpu_reboot_timeout` キーが不在の場合は `DEFAULT_DPU_REBOOT_TIMEOUT=360` 秒がそのまま使用される。

## 4. midplane スイッチ初期化

VoQ チャシス（SmartSwitch 含む）では、chassisd 起動直後に `chassis.init_midplane_switch()` を呼び出す:

```python
self.midplane_initialized = try_get(chassis.init_midplane_switch, default=False)
if not self.midplane_initialized:
    self.log_error("Chassisd midplane intialization failed")
```

`init_midplane_switch()` が `NotImplementedError` / `TimeoutError` を送出した場合は `try_get` が `False` を返す。`midplane_initialized = False` の場合、`check_midplane_reachability()` は即 return してミッドプレーン疎通チェックをスキップするが、**chassisd は終了しない**（エラーログのみ）。

CHASSIS_APP_DB の書き込み（orchagent 側）はミッドプレーン状態に依存しないが、midplane が未初期化の場合はラインカードが IP 到達不能となり CHASSIS_APP_DB の `redis_chassis` へ接続できず `gMultiAsicVoq` が立たない場合がある（接続タイムアウト次第）。

## 5. プラットフォーム API とテーブル書き込みの関係

chassisd は CHASSIS_APP_DB に**直接書き込まない**。CHASSIS_APP_DB へのアクセスはモジュール down 時の `_cleanup_chassis_app_db()` Lua スクリプト実行のみであり、クリーンアップのトリガはプラットフォーム API の `get_oper_status()` の返り値が `MODULE_STATUS_OFFLINE` / `MODULE_STATUS_EMPTY` に遷移したことで決まる（`chassisd:396-460`）。

| プラットフォーム API | 役割 | 関連 DB 操作 |
|-------------------|------|------------|
| `get_module(index).get_oper_status()` | モジュール動作状態を取得 | down 検知 → 30 分後に `_cleanup_chassis_app_db()` でパターン削除 |
| `get_module(index).get_name()` | モジュール名（例: `Linecard0`）取得 | クリーンアップ対象のキープレフィックス特定 |
| `get_module(index).get_midplane_ip()` | ミッドプレーン IP 取得 | CHASSIS_STATE_DB `CHASSIS_MIDPLANE_TABLE` に書き込み（CHASSIS_APP_DB とは無関係） |
| `is_midplane_reachable()` | ミッドプレーン到達性 | CHASSIS_STATE_DB `CHASSIS_MIDPLANE_TABLE` に書き込み（CHASSIS_APP_DB とは無関係） |
| `get_chassis()` (chassis_db_init) | シャーシ情報取得 | STATE_DB `CHASSIS_INFO` テーブルに `serial` / `model` / `revision` を書き込む（CHASSIS_APP_DB とは無関係） |

## 6. プラットフォーム非対応時の終了コード

| exit code | 定数 | 発生条件 |
|-----------|------|---------|
| `1` | `CHASSIS_LOAD_ERROR` | `sonic_platform.platform.Platform().get_chassis()` が例外を送出 |
| `2` | `CHASSIS_NOT_SUPPORTED` | 非 SmartSwitch 環境で `get_my_slot()` / `get_supervisor_slot()` が `INVALID_SLOT` を返す |
