# mux-cable-port — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-19 (chore/q67-f-batch1072)

ソース:
- `sonic-net/sonic-swss/orchagent/muxorch.cpp` (ref: master)
- `sonic-net/sonic-platform-daemons/sonic-ycabled/ycable/ycable_utilities/y_cable_helper.py` (ref: master)
- `sonic-net/sonic-linkmgrd/src/DbInterface.cpp` (ref: master)

対象ページ: `docs/reference/config-db/mux-cable-port.md`
対象テーブル: `MUX_CABLE|<ifname>` (CONFIG_DB)

<!-- failure -->
## Phase D: 失敗挙動マトリクス

`MUX_CABLE|<ifname>` エントリは `MuxOrch::handleMuxCfg()` → `addOperation()` の呼出し連鎖で処理される。以下にコンポーネントごとの失敗パターンを整理する。

### A. orchagent (MuxOrch) の失敗パターン

| 失敗条件 | 検出箇所 | 結果 | retry | evidence |
|---|---|---|---|---|
| `server_ipv4` / `server_ipv6` が SET_COMMAND に欠落 | `handleMuxCfg()` L2206-2207 の `getAttrIpPrefix()` | `std::out_of_range` 例外 → `addOperation()` の catch ブロック (`runtime_error`) が握るが、`out_of_range` は `runtime_error` の派生でないため未捕捉で orchagent abort | なし (orchagent プロセス異常終了) | `muxorch.cpp:2206-2207, 2411` |
| `mux_peer_switch_.isZero()` — PEER_SWITCH 未設定 | `handleMuxCfg()` L2271 | `return false` → `m_toSync` 保留 | 自動 (PEER_SWITCH SET 後の次イベントループ) | `muxorch.cpp:2271` |
| `neighbor_mode` 変更試行（既存 mux ポートへの変更）| `handleMuxCfg()` L2258-2266 | `SWSS_LOG_ERROR` → `return false` → `m_toSync` 保留 → ただし `neighbor_mode` が存在する限り永続的に `return false` | なし (手動 DEL → 再 SET が必要) | `muxorch.cpp:2258-2266` |
| `isMuxExists(port_name) == true` (二重 SET) | `handleMuxCfg()` L2253 | `SWSS_LOG_INFO` → `return true`（冪等スキップ、エラーなし） | 不要 | `muxorch.cpp:2253-2254` |
| DEL 時: `isMuxExists(port_name) == false` | `handleMuxCfg()` L2323 | `SWSS_LOG_ERROR` → `return true`（エントリ不在でも成功扱い） | なし | `muxorch.cpp:2323` |
| `std::runtime_error` 例外（tunnel 作成失敗等） | `addOperation()` / `delOperation()` catch | `SWSS_LOG_ERROR` → `return true`（erase）| なし（恒久スキップ）| `muxorch.cpp:2411, 2435` |

!!! note "`out_of_range` は未捕捉"
    `addOperation()` は `std::runtime_error` のみ catch する (`muxorch.cpp:2408-2412`)。`getAttrIpPrefix()` が `server_ipv4` / `server_ipv6` 欠落で `std::out_of_range` を投げた場合、上位の catch が存在せず orchagent プロセスが abort する。これは `MuxOrch` 固有の危険な欠落で、`minigraph.py` 経由では両フィールドが必ず補完されるため実運用での発生は少ないが、手動投入時は必ず注意する。

### B. ycabled の失敗パターン

| 失敗条件 | 検出箇所 | 結果 | retry | evidence |
|---|---|---|---|---|
| CONFIG_DB から `port_tbl[asic_index].get(port)` が `status=False`（エントリ不在）| `check_mux_cable_port_type()` L297 | `(False, None)` を返し呼出し元でポートをスキップ | なし（ループ内で別ポートに進む）| `y_cable_helper.py:297-301` |
| `"state"` キーが MUX_CABLE エントリに存在しない | `check_mux_cable_port_type()` L308 | `(False, None)` を返しポートをスキップ（DEBUG ログのみ）| なし | `y_cable_helper.py:317-320` |
| `"soc_ipv4"` キーが欠落（active-active ポート） | `retry_setup_grpc_channel_for_port()` L363 条件不成立 | gRPC チャネルセットアップをスキップ、active-active 制御不能 | `retry_setup_grpc_channel_for_port()` は呼出し元スレッドが定期的に再試行 | `y_cable_helper.py:363` |
| gRPC チャネル確立失敗（`channel is None or stub is None`） | `retry_setup_grpc_channel_for_port()` L371 | `NOTICE` ログ → `return False`（呼出し元スレッドが次周期で再試行）| 自動（定期スレッド） | `y_cable_helper.py:373-375` |

### C. linkmgrd の失敗パターン

| 失敗条件 | 検出箇所 | 結果 | retry | evidence |
|---|---|---|---|---|
| `"state"` フィールドが CONFIG_DB MUX_CABLE テーブルに存在しない（起動時 getPortMuxMode）| `DbInterface.cpp` L996 | `MUXLOGERROR` → 当該ポートを `PortToMuxModeConfigMapping` に追加せず処理続行 | なし（起動時 1 回のみ）| `DbInterface.cpp:994-997` |
| `cable_type` / `prober_type` / `server_ipv4` / `soc_ipv4` 欠落（起動時一括読込） | 各 getter の `cit == fieldValues.cend()` 分岐 | フォールバック値または no-op で続行。ログレベルは ERROR（`state`）または DEBUG（その他） | なし | `DbInterface.cpp:827, 880-881, 910-946, 968-1001` |

### D. 失敗ケースの全体サマリー

| ケース | 最悪の結果 | 回復方法 |
|---|---|---|
| `server_ipv4` / `server_ipv6` 欠落 | orchagent プロセス abort（systemd 再起動） | 両フィールドを含む CONFIG_DB エントリを事前投入 |
| `neighbor_mode` 変更試行 | 当該ポートの MUX_CABLE 処理が永続的に保留 | 該当ポートを DEL → 再 SET |
| `PEER_SWITCH` 未設定 | MUX_CABLE エントリが `m_toSync` で無制限保留 | PEER_SWITCH エントリを先に設定（自動回復） |
| ycabled `state` / `soc_ipv4` 欠落 | gRPC チャネル未確立で active-active 制御不能 | フィールドを CONFIG_DB に追記後、ycabled 定期スレッドが自動再試行 |
| linkmgrd 起動時 `state` 欠落 | 当該ポートの mux mode 未設定で linkmgrd ステートマシン停止 | CONFIG_DB に `state` フィールドを追記後 linkmgrd 再起動 |

<!-- /failure -->
