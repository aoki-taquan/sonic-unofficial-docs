# IPv6 Link-local 失敗挙動メモ (Phase D)

## intfmgr.cpp の失敗パターン

### SET_COMMAND 時

1. **インターフェース未 ready (isIntfStateOk false)**
   - `intfmgr.cpp:833-836`: `isIntfStateOk()` が false → `return false`（再キュー）
   - 再試行: 無制限（STATE_DB が ready になるまで待機）

2. **VRF 未 ready**
   - `intfmgr.cpp:839-842`: `!vrf_name.empty() && !isIntfStateOk(vrf_name)` → `return false`（再キュー）
   - 再試行: 無制限

3. **VRF 変更の直接切替禁止**
   - `intfmgr.cpp:846-849`: `isIntfChangeVrf()` → `SWSS_LOG_ERROR` + `return true`（silent drop）
   - 再試行: なし（エラーログのみ、処理済みとして破棄）

4. **`ipv6_use_link_local_only` 無効値**
   - `intfmgr.cpp:913-927`: `"enable"` / `"disable"` 以外は m_ipv6LinkLocalModeList を更新しないが、APP_DB には値をそのまま書く（バリデーションなし）
   - YANG スキーマバリデーションが通った場合のみ DB に到達するため実質的に不到達

### DEL_COMMAND 時

5. **IP アドレスがまだ存在する場合**
   - `intfmgr.cpp:1060-1063`: `getIntfIpCount(alias)` が非ゼロ → `return false`（再キュー）
   - IP アドレスを先に削除しないとインターフェース属性ロウ削除が保留される

### delIpv6LinkLocalNeigh の失敗挙動

6. **`ip neigh del` コマンド失敗**
   - `intfmgr.cpp:732-733`: `swss::exec()` のエラーを無視（戻り値チェックなし）
   - link-local neigh の削除失敗はサイレントに無視される

## neighsync の失敗パターン

7. **非対応インターフェース名プレフィックス**
   - `neighsync.cpp:221-224`: `Ethernet`/`Vlan`/`PortChannel` 以外 → `SWSS_LOG_INFO` + `return false`（silently drop）
   - link-local neigh は NEIGH_TABLE に書き込まれない

8. **CONFIG_DB エントリ不在**
   - `neighsync.cpp:199-219`: `m_cfgXxxInterfaceTable.get()` が false → `SWSS_LOG_INFO` + `return false`
   - `ipv6_use_link_local_only = enable` が設定されていないインターフェースへの link-local neigh は無視

## STATE_DB / ERROR_TABLE への影響

- `intfmgr` は `ipv6_use_link_local_only` 処理失敗時に STATE_DB も ERROR_TABLE も更新しない
- `m_appIntfTableProducer` への書き込みは `doIntfGeneralTask` の末尾（`return true` 前）に行われるため、途中 `return false` では APP_DB への書き込みが発生しない
