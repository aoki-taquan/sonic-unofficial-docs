# DPU_STATE — Phase D 失敗挙動調査メモ

## 調査対象

- `sonic-platform-daemons/sonic-chassisd/scripts/chassisd`
- 主要クラス: `SmartSwitchModuleUpdater`, `DpuStateUpdater`, `DpuChassisdDaemon`, `DpuStateManagerTask`

## failure パターン

### 1. platform API NotImplementedError

`try_get()` (L125-139) が全 platform API 呼び出しをラップし、`NotImplementedError` / 任意例外時に `default` 値を返す。

代表的な呼び出しと default:
- `chassis.init_midplane_switch()` → `False` (midplane 無効化)
- `module.get_oper_status()` → `MODULE_STATUS_OFFLINE` (= `'down'`)
- `module.get_midplane_ip()` → `'0.0.0.0'`
- `module.is_midplane_reachable()` → `False`

### 2. DB 書き込みエラー (update_dpu_state)

L864-891: `except Exception as e: self.log_error(f"Unexpected error: {e}")` でログのみ。retry なし。
10 秒後のポーリングで自動再試行。

### 3. midplane_initialized = False

`init_midplane_switch()` が `False` → `check_midplane_reachability()` は即 return。
midplane スイッチ初期化失敗時は永続的にスキップ。

### 4. set_initial_dpu_admin_state 単一 DPU 例外

L1400-1401: ループ内 `except Exception` でログ。当該 DPU_STATE は未初期化。
次ポーリングで `check_midplane_reachability()` が補完。CP/DP は DPU 側 chassisd が担当。

### 5. DpuStateUpdater 評価エラー

例外が上位ループに伝搬 → supervisord が chassisd を非ゼロ exit 検出で再起動。
再起動後は `set_initial_dpu_admin_state()` から再実行。

## 設計意図

DPU_STATE は volatile な状態テーブルであり、次のポーリングサイクル (10 秒) で再評価・再書き込みされる。
単一サイクルの失敗は自己修復するため、retry キューは不要。
orchagent の `task_need_retry` / `task_failed` モデルとは根本的に異なる設計。

## supervisord 再起動

exit_code は `128 + sig` (SIGINT/SIGTERM 時) → supervisord が再起動。
SIGHUP はキャッチして無視 (graceful reload 相当)。
