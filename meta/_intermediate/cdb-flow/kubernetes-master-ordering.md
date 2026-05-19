# KUBERNETES_MASTER — Phase B 書込み順依存スキャンノート

対象テーブル: `KUBERNETES_MASTER`
Consumer: `ctrmgrd` (`src/sonic-ctrmgrd/ctrmgr/ctrmgrd.py`)
スキャン範囲: `init()`, `MainServer.__init__()`, `RemoteServerHandler.__init__()`, `handle_update()`, `do_join()`, `do_reset()`, `FeatureTransition.on_config_update()` 全行精読

---

## 検出した順序依存・タイミング依存

### 1. `/etc/sonic/remote_ctr.config.json` の先読み → `remote_ctr_config` 上書き

- `ctrmgrd.init()` (ctrmgrd.py:169) は起動時に `/etc/sonic/remote_ctr.config.json` が存在すれば `remote_ctr_config` を上書きする。
- `remote_ctr_config` は `JOIN_LATENCY`（デフォルト 10 秒）、`JOIN_RETRY`（デフォルト 10 秒）など JOIN タイミングを制御する定数を保持する。
- **順序依存**: `KUBERNETES_MASTER` に `ip` を書き込んでも、`remote_ctr_config` の読み込み（起動時の 1 回のみ）が先に完了している前提で動作する。`init()` は CONFIG_DB 読み込みより前に実行される（ctrmgrd.py:688-689）。
- evidence: `ctrmgrd.py:23,169-173,688-689`

### 2. `STATE_DB:KUBERNETES_MASTER|SERVER.update_time` の有無 → JOIN_LATENCY 適用分岐

- `RemoteServerHandler.__init__()` (ctrmgrd.py:328-356) は起動時に `STATE_DB:KUBERNETES_MASTER|SERVER.update_time` を読む。
- 値が空（初回起動）の場合: `JOIN_LATENCY`（デフォルト 10 秒）後に初回 `handle_update()` を timer 登録する。その間は `ip`/`disable` 変更が CONFIG_DB に書き込まれても `pending = True` のまま join は抑制される。
- 値が存在（再起動・再設定）の場合: latency なしで即時 `handle_update()` を呼ぶ。
- **順序依存**: 初回起動時に `KUBERNETES_MASTER|SERVER.ip` を CONFIG_DB に書いても、`STATE_DB:KUBERNETES_MASTER|SERVER.update_time` が空であれば `JOIN_LATENCY` 秒間は kubelet join が行われない。運用上は再起動後の即時 join を期待する場合、前回の STATE_DB エントリが保持されていることが前提となる。
- evidence: `ctrmgrd.py:339-356`

### 3. `ip` の存在 + `disable=false` が揃ってから `do_join()` 実行

- `handle_update()` (ctrmgrd.py:392-413) は `disable == true` または `ip` が空の場合に `do_reset()` を呼び、それ以外で `do_join()` を呼ぶ。
- **順序依存**: `ip` フィールドを後から書き込む場合、それまでの間 `ctrmgrd` は `do_reset()` を繰り返し呼んで `STATE_DB:KUBERNETES_MASTER|SERVER.connected = "false"` を維持する。`ip` 書き込み後に CONFIG_DB 変化が `RemoteServerHandler.on_config_update()` 経由で検知され、`handle_update()` が再度呼ばれて初めて join が試みられる。
- `port` と `insecure` は `ip` があれば補完的に使われるため、`ip` が最後に書かれる場合は `port`/`insecure` 書き込み直後に余分な `do_reset()` は起きない（ip 不在 → reset）。
- evidence: `ctrmgrd.py:398-409`

### 4. `do_join()` 失敗時の JOIN_RETRY ループ

- `do_join()` (ctrmgrd.py:427-455) が失敗すると `JOIN_RETRY` 秒後に再試行 timer を登録する。
- この間に `KUBERNETES_MASTER|SERVER.ip` が変更された場合、`on_config_update()` が呼ばれるが `self.pending == True` のチェックにより重複呼び出しを抑制する（ctrmgrd.py:371-388）。
- **順序依存**: JOIN_RETRY 中に `ip` を更新した場合、既存タイマーがキャンセルされず次回 timer fire 時には**古い ip の timer が残りうる**（`register_timer` はキャンセル機構なし）。ただし `on_config_update()` は `pending = False` をセットして即時 `handle_update()` を呼ぶため、タイマー fire 前に最新 ip で join が試みられる（ctrmgrd.py:370-388）。
- evidence: `ctrmgrd.py:370-390,444-455`

### 5. `FEATURE` テーブルの `set_owner` → K8s モード切替順序

- `FeatureTransition.on_config_update()` (ctrmgrd.py:521-535) は `CONFIG_DB:FEATURE` の変化を購読し、`set_owner` が `kube` に変わったときに systemd service を restart する。
- **順序依存**: `KUBERNETES_MASTER` に `ip` が設定され `connected = true` の状態になる前に `FEATURE.set_owner = kube` を書くと、kubelet join 未完了のまま kube モードへの移行を試み、サービスが kube からのデプロイを待ち続けて応答なし状態になる可能性がある。
- 推奨書込み順: `KUBERNETES_MASTER.ip` → 接続完了確認（`STATE_DB:KUBERNETES_MASTER|SERVER.connected = "true"`）→ `FEATURE.set_owner = kube`。
- evidence: `ctrmgrd.py:467-511`

---

## まとめ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | `/etc/sonic/remote_ctr.config.json` 読み込み → `remote_ctr_config` 確定 | 起動時 1 回（強制先行） | ctrmgrd 起動前にファイルを配置する |
| 2 | `STATE_DB:KUBERNETES_MASTER.update_time` 有無 → JOIN_LATENCY 適用分岐 | 起動時評価 | 初回起動時は 10 秒の join latency を見込む |
| 3 | `ip` 書き込み → `disable=false` 確認 → `do_join()` 実行 | 強制先行 | `ip` を最後に書く、または同時に `disable=false` を保証する |
| 4 | JOIN_RETRY 中の `ip` 変更 → 旧タイマー残留 | 非自明（実害小） | `on_config_update()` が即時上書き join するため実害なし |
| 5 | `KUBERNETES_MASTER.connected=true` 確認 → `FEATURE.set_owner=kube` | 推奨先行 | STATE_DB を polling して `connected=true` を確認してから FEATURE を変更する |
