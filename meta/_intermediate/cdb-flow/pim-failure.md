# PIM_GLOBALS / PIM_INTERFACE — Phase D 失敗挙動スキャンノート

対象テーブル: `PIM_GLOBALS`, `PIM_INTERFACE`
Consumer: `frrcfgd` (`BGPConfigDaemon`) — `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`
スキャン範囲: PIM ハンドラ (L3772-3821), `key_map.run_command()` (L655-779), `g_run_command()` (L47-62), `hdl_set_pim_hello_parms` (L462-465)

---

## retry / recovery の仕組み

`frrcfgd` の PIM テーブルハンドラ (`bgp_table_handler_common` → `__update_bgp()`) は **retry キューを持たない**。  
SET / DEL のいずれも 1 回の `key_map.run_command()` 呼び出しで完結し、失敗した場合は `LOG_ERR` を出力して `continue`（次イベントへ進む）するだけで **自動 retry は発生しない**。  
これは BGP の bgpcfgd (`set_queue` ベース deps-driven retry) とは異なる設計である。

```
CONFIG_DB SET/DEL → bgp_table_handler_common → __update_bgp() キュー
  → PIM ハンドラ → key_map.run_command() → g_run_command() → vtysh
  失敗時: LOG_ERR + continue（retry なし）
```

---

## SET 処理における失敗経路

### 1. `PIM_INTERFACE`: `mode` フィールド欠如 — silent drop

- **条件**: `PIM_INTERFACE` の SET に `mode` フィールドが含まれない
- **検出箇所**: frrcfgd.py L3787 `if 'mode' in data:` — 条件不成立で全フィールドをスキップ
- **結果**: `key_map.run_command()` が呼ばれず、`dr-priority` / `hello-interval` / `bfd-enabled` を含む全フィールドが FRR に未反映 (**silent drop**)
- **ログ出力**: なし（LOG_ERR も LOG_DEBUG も出ない）
- **recovery**: なし。次回 `mode` を含む SET を送ることで全フィールドが再送される
- evidence: frrcfgd.py L3787-3802

### 2. `PIM_INTERFACE` / `PIM_GLOBALS`: vtysh コマンド失敗

- **条件**: FRR pimd が vtysh コマンドを拒否（値域外・VRF 未存在・インタフェース未存在・pimd 未起動等）
- **検出箇所**: `g_run_command()` L52 — `bgpd_client.run_vtysh_command()` が `False` を返す  
  → `syslog.syslog(LOG_ERR, 'command execution failure. Command: ...')`  
  → `key_map.run_command()` 内 L763 `LOG_ERR 'failed running FRR command: %s'`  
  → PIM ハンドラ L3802 / L3821 `LOG_ERR 'failed running PIM config command'`
- **結果**: `continue` で次イベントへ進む。失敗したフィールドの `data[key].status` は `STAT_SUCC` に更新されず、frrcfgd の内部キャッシュに **stale エントリが残存**する可能性がある
- **ログ出力**: LOG_ERR × 3 系統（g_run_command / run_command / PIM ハンドラ）
- **recovery**: なし（自動 retry なし）。VRF / インタフェースが後から作成されても PIM 設定は自動再送されない。手動で SET を再送する必要がある
- evidence: frrcfgd.py L47-62, L755-779, L3802, L3821

### 3. `PIM_GLOBALS`: `join-prune-interval` / `keep-alive-timer` 値域外

- **条件**: `join-prune-interval` < 60 または > 600、`keep-alive-timer` < 31 または > 60000 等、FRR CLI が値域エラーを返す
- **検出箇所**: `g_run_command()` で vtysh が非 0 終了コードを返す
- **結果**: LOG_ERR 出力 + `continue`（該当フィールドのみ未反映）
- **ログ出力**: LOG_ERR（"command execution failure. Command: ..."）
- **frrcfgd の検証**: frrcfgd はフィールド値を検証せずそのまま vtysh に渡す。値域チェックは FRR CLI 側でのみ行われる
- evidence: frrcfgd.py L47-62, frrcfgd.py L284-295 (constants section)

### 4. `PIM_INTERFACE`: `hello-interval` カンマ区切り解析失敗

- **条件**: `hello-interval` の値が `"<n>,<m>"` 形式でない不正文字列（例: `"abc"`, `"30,"`）
- **検出箇所**: `hdl_set_pim_hello_parms()` (L462-465) → `get_command_cmn()` → 最終的に vtysh へ不正値が渡る
- **結果**: vtysh が失敗 → LOG_ERR + `continue`。`hello-interval` のみ未反映。`mode` / `dr-priority` 等は `key_map.run_command()` 内で独立したコマンドとして処理されるため影響を受けない
- **ログ出力**: LOG_ERR（vtysh 失敗）
- evidence: frrcfgd.py L462-465, frrcfgd.py L941-942

### 5. pimd デーモン未起動

- **条件**: docker-fpm-frr 内で pimd が `autostart=false` のため起動していない状態で SET が発行された場合
  - supervisord.conf.j2 L135-148: `pimd` は `autostart=false`、`dependent_startup_wait_for=zebra:running` (priority=5)
  - pimd は `frr_mgmt_framework_config = true` のときのみ起動する Jinja2 条件付きブロック内
- **条件**: `DEVICE_METADATA.localhost.frr_mgmt_framework_config != "true"` かつ pimd が起動していない
- **検出箇所**: `bgpd_client.run_vtysh_command()` — pimd への接続失敗 → `False` を返す
- **結果**: LOG_ERR + `continue`。PIM 設定は未反映
- **recovery**: pimd が起動した後に SET を再送することで反映される（自動 replay なし）
- evidence: supervisord.conf.j2 L135-148, frrcfgd.py L47-62

### 6. `frrcfgd` 自体が未起動 (`frr_mgmt_framework_config = false`)

- **条件**: `DEVICE_METADATA.localhost.frr_mgmt_framework_config` が `"true"` でない場合、frrcfgd は起動せず `bgpcfgd` が起動する
  - supervisord.conf.j2 L163-169: `{% if frr_mgmt_framework_config == "true" %}[program:frrcfgd]{% else %}[program:bgpcfgd]{% endif %}`
- **結果**: `PIM_GLOBALS` / `PIM_INTERFACE` の購読者が存在せず、CONFIG_DB への書き込みは完全に無視される
- evidence: supervisord.conf.j2 L163-178

---

## DEL 処理における失敗経路

### 7. `PIM_INTERFACE`: `mode` の OP_DELETE — 他フィールドキャッシュのフラッシュ

- **動作**: `mode` の OP_DELETE 受信時、frrcfgd.py L3790-3796 が **他フィールドのキャッシュを `STAT_SUCC + OP_DELETE` にフラッシュ**する
- **意図**: sparse-mode 無効化時に dr-priority / hello-interval / bfd-enabled を FRR から削除するため
- **失敗条件**: `no ip pim` コマンドが vtysh 失敗した場合 → LOG_ERR + `continue`。FRR はまだ sparse-mode が有効な状態を保持する。しかし frrcfgd 内部キャッシュはフラッシュ済みのため、次回 SET 時に全フィールドを再送しないと FRR との不整合が生じる
- evidence: frrcfgd.py L3787-3802

### 8. VRF キャッシュ孤立（VRF 削除後の DEL）

- **動作**: `vrf_handler` (frrcfgd.py L2413-2440) は BGP/static-route キャッシュを整合するが **PIM テーブルのキャッシュは対象外**
- **条件**: `VRF|<vrf>` を削除した後に `PIM_GLOBALS|<vrf>|<af>` または `PIM_INTERFACE|<vrf>|<af>|<if>` を DEL する場合
- **結果**: frrcfgd 内部キャッシュに孤立 PIM エントリが残存する可能性がある。vtysh は対応 VRF が存在しないため LOG_ERR を出す
- **推奨**: VRF 削除前に PIM テーブルエントリを先に DEL する
- evidence: frrcfgd.py L2413-2467

---

## 失敗挙動サマリ

| # | 失敗条件 | 検出箇所 | 結果 | ログ出力 | recovery |
|---|---------|---------|------|---------|---------|
| 1 | `PIM_INTERFACE` SET に `mode` 欠如 | frrcfgd.py L3787 | 全フィールド silent drop | なし | 次回 mode 含む SET で回復 |
| 2 | vtysh コマンド失敗（VRF 未存在/インタフェース未存在等） | g_run_command L47-62 | LOG_ERR + continue（retry なし） | LOG_ERR × 3 | 手動 SET 再送 |
| 3 | フィールド値域外（join-prune-interval / keep-alive-timer 等） | g_run_command L47-62 | 該当フィールドのみ未反映 | LOG_ERR | 正しい値で再 SET |
| 4 | `hello-interval` 不正フォーマット | hdl_set_pim_hello_parms → vtysh | `hello-interval` のみ未反映 | LOG_ERR | 正しい値で再 SET |
| 5 | pimd デーモン未起動 | bgpd_client.run_vtysh_command | 全 SET 失敗 | LOG_ERR | pimd 起動後に手動再 SET |
| 6 | frrcfgd 未起動 (frr_mgmt_framework_config != true) | — | CONFIG_DB 書き込みが完全無視 | なし | frr_mgmt_framework_config 設定変更 + frrcfgd 起動 |
| 7 | mode OP_DELETE 後の no ip pim vtysh 失敗 | frrcfgd.py L3790-3802 | FRR はまだ pim 有効; キャッシュはフラッシュ済 | LOG_ERR | 全フィールドを含む SET 再送 |
| 8 | VRF 削除後の PIM DEL | frrcfgd.py vrf_handler | frrcfgd キャッシュに孤立エントリ | LOG_ERR (vtysh) | VRF 削除前に PIM エントリを先行 DEL |
