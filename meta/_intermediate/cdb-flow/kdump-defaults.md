# KDUMP — Phase A: コード由来の暗黙デフォルト調査

## 対象ファイル（entry grep 一回）

- `sonic-host-services/scripts/hostcfgd` — KdumpCfg クラス (L1163–L1270)
- `sonic-utilities/scripts/sonic-kdump-config` — 各フィールドの read/write 実装
- `sonic-utilities/config/kdump.py` — CLI コマンド実装
- `sonic-buildimage/files/build_templates/init_cfg.json.j2` — ビルド時デフォルト
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-kdump.yang` — YANG 定義

---

## フィールド別デフォルト・挙動一覧

### `enabled`

| 層 | 値 | ソース |
|---|---|---|
| YANG default | なし（default 句なし） | sonic-kdump.yang L28–32 |
| init_cfg.json.j2 | `"false"`（cisco-8000 のみ `"true"`） | init_cfg.json.j2 |
| hostcfgd ハードコード | `"false"` | hostcfgd L1167 |
| /proc/cmdline からの上書き | `"true"` + 実際の crashkernel 値 | hostcfgd L1179–1207 |

**暗黙 reset+restore（プラットフォーム依存）**:
- `/proc/cmdline` に `crashkernel=` が存在する場合、hostcfgd 起動時に `kdump_defaults["enabled"] = "true"` へ上書きし、`config_db.mod_entry()` で CONFIG_DB に書き戻す
- つまり grub/bootloader で crashkernel を仕込んであれば、CONFIG_DB の `enabled` が `"false"` でも起動時に `"true"` に強制リセットされる
- これは **書き込み順依存** かつ **プラットフォーム依存** の挙動

**大文字小文字制約**:
- `kdump_update()` では `kdump_enabled.lower() == "true"` で判定 → 大小文字を正規化
- `load()` では `if not kdump_conf.get(row)` で空文字・None・`"0"` も falsy 扱いでデフォルト置換されるが、`"false"` は truthy なので置換されない（正しく動作）

---

### `memory`

| 層 | 値 | ソース |
|---|---|---|
| YANG default | なし（default 句なし） | sonic-kdump.yang L34–48 |
| init_cfg.json.j2 | `"0M-2G:256M,2G-4G:320M,4G-8G:384M,8G-:448M"` | init_cfg.json.j2 |
| hostcfgd ハードコード | `"0M-2G:256M,2G-4G:320M,4G-8G:384M,8G-16G:448M,16G-32G:768M,32G-:1G"` | hostcfgd L1168 |
| sonic-kdump-config fallback | `"0M-2G:256M,2G-4G:320M,4G-8G:384M,8G-:448M"` | sonic-kdump-config L398 |

**YANG-実装 discrepancy（3 つの不一致）**:
1. YANG に `default` 句なし → YANG レベルでは省略可
2. init_cfg.json.j2 と hostcfgd のハードコードが異なる: init_cfg は `8G-:448M`（2段）、hostcfgd は `8G-16G:448M,16G-32G:768M,32G-:1G`（4段）
3. sonic-kdump-config の `get_kdump_memory()` 内のフォールバックは `"0M-2G:256M,2G-4G:320M,4G-8G:384M,8G-:448M"` とさらに別の値

実質的に CONFIG_DB にエントリがない場合、hostcfgd が長い 4 段階値を書き込む。init_cfg 経由では 2 段階値。sonic-kdump-config のフォールバックはほぼ発動しない（CONFIG_DB が必ず存在する前提）。

**書き込み順依存**:
- hostcfgd `load()` が先に走ると L1168 の値が DB に入る
- init_cfg.json.j2 は `config load` 時に読まれるが、既存エントリを上書きしない

---

### `num_dumps`

| 層 | 値 | ソース |
|---|---|---|
| YANG default | なし（default 句なし） | sonic-kdump.yang L50–55 |
| YANG 範囲制約 | 1..9 | sonic-kdump.yang L51–53 |
| init_cfg.json.j2 | `"3"` | init_cfg.json.j2 |
| hostcfgd ハードコード | `"3"` | hostcfgd L1169 |
| sonic-kdump-config fallback | `3`（int） | sonic-kdump-config L416 |

**silent drop+fallback**:
- `load()` の `if not kdump_conf.get(row)` により、`num_dumps` が `None` または空文字の場合のみデフォルト `"3"` を書き込む
- CLI では `type=int` で受け取り DB には整数を渡すが（`mod_entry`）、Redis は文字列として保存する
- `kdump_update()` では `data.get("num_dumps")` が `None` の場合のみデフォルト使用 → `"0"` を渡すとそのまま通る

**dead field（部分的）**:
- YANG の `range "1 .. 9"` 制約は sonic-yang-mgmt 経由時のみ有効
- CLI（`config kdump num_dumps`）は `type=int` のみで範囲チェックなし → 0 や 10 も書ける

---

### `remote`

| 層 | 値 | ソース |
|---|---|---|
| YANG default | なし（default 句なし） | sonic-kdump.yang L57–61 |
| init_cfg.json.j2 | 記載なし（フィールドなし） | init_cfg.json.j2 |
| hostcfgd ハードコード | `"false"` | hostcfgd L1170 |
| CLI fallback | `"false"` | config/kdump.py L111 |

**init_cfg.json.j2 非記載**:
- `remote`、`ssh_string`、`ssh_path` は init_cfg に含まれない → hostcfgd のハードコードデフォルトのみが起動時に適用される

**前提条件依存（複合必須制約）**:
- `remote: false` の状態で `ssh_string`/`ssh_path` を設定しようとすると CLI が中断（`"Remote feature is not enabled"` エラー）
- DB に直接書いた場合は制約をバイパス可能 → hostcfgd はそのまま sonic-kdump-config に渡す

---

### `ssh_string`

| 層 | 値 | ソース |
|---|---|---|
| YANG default | なし | sonic-kdump.yang L63–68 |
| init_cfg.json.j2 | 記載なし | init_cfg.json.j2 |
| hostcfgd ハードコード | `"user@localhost"` | hostcfgd L1171 |
| sonic-kdump-config fallback | `None` | sonic-kdump-config L432 |

**silent substitution（危険）**:
- CONFIG_DB に `ssh_string` が未設定の場合、hostcfgd は `kdump_defaults["ssh_string"] = "user@localhost"` をフォールバックとして sonic-kdump-config に渡す
- `user@localhost` はプレースホルダー値（実用不可）だが、エラーにならず `/etc/default/kdump-tools` の `SSH=` 行に書き込まれる

**大文字小文字制約（YANG vs CLI 不一致）**:
- YANG パターン: `([a-zA-Z0-9._%+-]+@([a-zA-Z0-9.-]+|[0-9]{1,3}(\.[0-9]{1,3}){3}))` → ユーザー名先頭に `.` や `_` 等を許容
- CLI 検証（`is_valid_ssh_key()`）: `username.isalnum()` → 英数字のみ許容（より厳しい）
- sonic-kdump-config の `SSH_STRING_RE`: `^[a-zA-Z0-9][a-zA-Z0-9._%+-]*@...` → 先頭英数字必須

→ YANG は `_user@host` を許容するが CLI は拒否する。YANG-実装 discrepancy。

**書き込み時 vs 実行時乖離**:
- `hostcfgd.kdump_update()` は `ssh_string` を常に sonic-kdump-config に渡す（`remote` の ON/OFF に関係なく）
- sonic-kdump-config の `--remote` フラグ処理は別途 `cmd_kdump_remote()` に委譲され、実際の SSH/SSH_KEY の comment/uncomment はそこで行われる

---

### `ssh_path`

| 層 | 値 | ソース |
|---|---|---|
| YANG default | なし | sonic-kdump.yang L71–76 |
| init_cfg.json.j2 | 記載なし | init_cfg.json.j2 |
| hostcfgd ハードコード | `"/a/b/c"` | hostcfgd L1172 |
| sonic-kdump-config fallback | `None` | sonic-kdump-config L450 |

**ハードコード固定値（無効なプレースホルダー）**:
- `"/a/b/c"` は明らかにプレースホルダーだが、エラーにならず `/etc/default/kdump-tools` の `SSH_KEY=` 行に書き込まれる
- sonic-kdump-config の `write_ssh_path()` は `SSH_PATH_RE = re.compile(r'^(/[a-zA-Z0-9._-]+)+\Z')` で検証するが、`"/a/b/c"` はこの正規表現を通過する

**partial failure**:
- `ssh_path` に実在しないパスを指定した場合、CLI の `is_valid_ssh_path()` は `os.path.exists()` でチェックするが、sonic-kdump-config の `write_ssh_path()` は存在チェックなし
- つまり CLI 経由は厳しい、DB 直接書き込みや hostcfgd フォールバック経由は甘い

---

## 発見した暗黙デフォルト・落とし穴 サマリー

| フィールド | 検出種類 | 詳細 |
|---|---|---|
| `enabled` | プラットフォーム依存 + 暗黙 reset | `/proc/cmdline` に crashkernel= があれば起動時に `"true"` に強制書き戻し |
| `enabled` | init_cfg 依存（cisco-8000 のみ `"true"`） | cisco-8000 では init_cfg が `"true"` を注入 |
| `memory` | YANG-実装 discrepancy（3系統の不一致） | init_cfg / hostcfgd / sonic-kdump-config で 3 つの異なる初期値 |
| `memory` | 書き込み順依存 | hostcfgd が先に走るか init_cfg が先に入るかで値が変わる |
| `num_dumps` | dead consumer（YANG 範囲制約バイパス） | CLI は `type=int` のみ、0 や 10 も書き込み可 |
| `remote` | init_cfg 非記載 | init_cfg に含まれず hostcfgd ハードコードのみ |
| `ssh_string` | silent substitution（プレースホルダー） | 未設定時 `"user@localhost"` が /etc/default/kdump-tools に書かれる |
| `ssh_string` | YANG-実装 discrepancy | YANG パターン vs CLI `isalnum()` vs sonic-kdump-config 正規表現で 3 種の制約 |
| `ssh_path` | ハードコード固定値（プレースホルダー） | 未設定時 `"/a/b/c"` が書き込まれる |
| `ssh_path` | partial failure | CLI は `os.path.exists()` チェック、sonic-kdump-config はスキップ |
| 全フィールド | 書き込み時 vs 実行時乖離 | CONFIG_DB 変更は即時。grub/kdump kernel のロードは reboot 後 |

---

## 参照コミット

- `sonic-host-services`: hostcfgd (worktree HEAD)
- `sonic-utilities`: config/kdump.py, scripts/sonic-kdump-config (worktree HEAD)
- `sonic-buildimage`: init_cfg.json.j2, sonic-kdump.yang (9ea932ec2e18f35e58268ec2e4456b1d4afd65cd)
