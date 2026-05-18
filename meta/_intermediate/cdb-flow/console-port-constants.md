# CONSOLE_PORT — Phase E: ハードコード定数調査

## 対象ファイル

- `sonic-utilities/consutil/lib.py` — consutil コアライブラリ
- `sonic-utilities/config/console.py` — CLI コマンド定義

---

## 1. エラーコード定数 (consutil/lib.py L17-21)

| 定数名 | 値 | 用途 |
|-------|----|------|
| `ERR_DISABLE` | `1` | console switch 機能が無効時の終了コード |
| `ERR_CMD` | `2` | コマンドエラー (root 権限不足等) |
| `ERR_DEV` | `3` | デバイス / ライン不在エラー |
| `ERR_CFG` | `4` | 設定エラー (baud_rate 未設定等) |
| `ERR_BUSY` | `5` | ラインが接続中 (busy) 時の終了コード |

## 2. テーブル名定数 (consutil/lib.py L23-24)

| 定数名 | 値 | 用途 |
|-------|----|------|
| `CONSOLE_PORT_TABLE` | `"CONSOLE_PORT"` | CONFIG_DB テーブル名 |
| `CONSOLE_SWITCH_TABLE` | `"CONSOLE_SWITCH"` | CONFIG_DB テーブル名 |

## 3. STATE_DB フィールド名 (consutil/lib.py L39-44)

| 定数名 | 値 | 用途 |
|-------|----|------|
| `STATE_KEY` | `"state"` | STATE_DB の接続状態フィールド名 |
| `PID_KEY` | `"pid"` | STATE_DB の接続プロセス PID フィールド名 |
| `START_TIME_KEY` | `"start_time"` | STATE_DB の接続開始時刻フィールド名 |
| `BUSY_FLAG` | `"busy"` | STATE_DB `state` フィールドの "接続中" 値 |
| `IDLE_FLAG` | `"idle"` | STATE_DB `state` フィールドの "待機" 値 |

## 4. picocom 動作定数 (consutil/lib.py L47-52)

| 定数名 | 値 | 用途 |
|-------|----|------|
| `PICOCOM_READY` | `"Terminal ready"` | picocom 起動成功の判定文字列 |
| `PICOCOM_BUSY` | `"Resource temporarily unavailable"` | picocom がデバイスを取れなかった判定文字列 |
| `TIMEOUT_SEC` | `0.2` | picocom の起動待機タイムアウト (秒) |
| `UDEV_PREFIX_CONF_FILENAME` | `"udevprefix.conf"` | プラットフォーム固有デバイスプレフィックス設定ファイル名 |

## 5. デバイスパス定数 (consutil/lib.py L297)

| 定数名 | 値 | 用途 |
|-------|----|------|
| `SysInfoProvider.DEVICE_PREFIX` | `/dev/ttyUSB` (デフォルト) | シリアルデバイスパスのプレフィックス。プラットフォームの `udevprefix.conf` が存在する場合は上書き可能 |

## 6. CONFIG_DB フィールドキー名 (consutil/lib.py L29-35)

| 定数名 | 値 | 用途 |
|-------|----|------|
| `BAUD_KEY` | `"baud_rate"` | CONSOLE_PORT のボーレートフィールド名 |
| `DEVICE_KEY` | `"remote_device"` | CONSOLE_PORT の接続先デバイス名フィールド |
| `FLOW_KEY` | `"flow_control"` | CONSOLE_PORT のフロー制御フィールド名 |
| `FEATURE_KEY` | `"console_mgmt"` | CONSOLE_SWITCH テーブルのエントリキー名 |
| `FEATURE_ENABLED_KEY` | `"enabled"` | CONSOLE_SWITCH の有効化フラグフィールド名 |
| `DEFAULT_FEATURE_ESCAPE_KEY` | `"default_escape_char"` | CONSOLE_SWITCH のデフォルトエスケープ文字フィールド名 |
| `FEATURE_ESCAPE_KEY` | `"escape_char"` | CONSOLE_PORT のポート個別エスケープ文字フィールド名 |

## 注記

- `DEVICE_PREFIX` は起動時に `SysInfoProvider.init_device_prefix()` が呼ばれた場合のみプラットフォーム固有値に更新される。プラットフォームが `udevprefix.conf` を持たない場合は `/dev/ttyUSB` のまま。
- `TIMEOUT_SEC = 0.2` は picocom が `"Terminal ready"` を出力するまでの最大待機時間であり、非常に短い。低速な USB-serial アダプタではこの値で false negative (接続失敗誤報) が起こりうる。
