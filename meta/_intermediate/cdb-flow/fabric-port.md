# FABRIC_PORT — 例外条件分析

## consumer 一覧

| consumer | 用途 | ソースパス |
|---|---|---|
| orchagent / fabricportsorch.cpp | Fabric ポートの SAI オブジェクト生成・統計取得・状態管理 | sonic-swss/orchagent/fabricportsorch.cpp |

## 例外条件

### fabricportsorch: SAI ポート一覧取得失敗
- fabricportsorch.cpp:179 — `SAI_SWITCH_ATTR_NUMBER_OF_FABRIC_PORTS` 取得失敗時は `FABRIC_PORT_ERROR (0)` を返して初期化失敗。
- fabricportsorch.cpp:196 — `SAI_SWITCH_ATTR_FABRIC_PORT_LIST` 取得失敗時は `throw runtime_error("FabricPortsOrch get port list failure")` を送出。orchagent プロセスが異常終了する。

### fabricportsorch: レーン番号取得失敗
- fabricportsorch.cpp:212 — ポートごとのレーン番号取得失敗時は `throw runtime_error("FabricPortsOrch get port lane failure")` を送出。

### fabricportsorch: キュー数・キューリスト取得失敗
- fabricportsorch.cpp:280,296 — ポートキュー数またはキューリスト取得失敗時は `throw runtime_error(...)` を送出。

### fabricportsorch: remote id / remote port index 取得失敗
- fabricportsorch.cpp:384,396 — SAI から remote fabric port ID / remote port index が取得できない場合は `throw runtime_error(...)` を送出。

### fabricportsorch: CRC エラー率の乗算比較
- fabricportsorch.cpp:534-536 — エラー閾値比較は浮動小数点ではなく整数乗算で行い、ゼロ除算を回避する設計。`rxCells = 0` の場合はエラーなしと判断する。
