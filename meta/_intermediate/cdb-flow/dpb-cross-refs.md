# BREAKOUT_CFG (DPB) — Phase C 暗黙参照スキャンノート

対象テーブル: `BREAKOUT_CFG`
スキャン範囲: `sonic-utilities/config/main.py:5465-5564`, `sonic-utilities/show/interfaces/__init__.py:200-280`, `sonic-utilities/config/config_mgmt.py:414-466`

---

## 検出された暗黙参照テーブル・ファイル

### breakout コマンド実行時（config interface breakout）

`breakout()` CLI 関数は `BREAKOUT_CFG` 自身を読み書きするほか、以下の外部テーブル・ファイルを暗黙的に参照する。

| 参照先テーブル / リソース | 参照方向 | 条件 | evidence |
|--------------------------|---------|------|----------|
| `platform.json` (ファイルシステム) | 読込（モード検証・子ポート計算） | 常時必須。ファイル不在時は即 Abort | `main.py:5467-5471`, `main.py:5491`, `main.py:5496,5507` |
| `PORT` (CONFIG_DB) | 読込（ポート名バリデーション） | `del_intf_dict` の各ポートに対して `interface_name_is_valid()` を呼ぶ | `main.py:5517-5519` |
| `BREAKOUT_CFG` (CONFIG_DB) | 読込（現在モード取得）→ 書込み（新モード更新） | 常時。エントリ不在で Abort | `main.py:5479-5486`, `main.py:5554` |
| YANG モデル群 (`/usr/local/yang-models/`) | 読込（依存テーブル解析） | `ConfigMgmtDPB` 初期化時。依存テーブル（VLAN_MEMBER / BUFFER_PG 等）の探索に使用 | `config_mgmt.py:70-72` |
| `VLAN_MEMBER`, `ACL_TABLE`, `BUFFER_PG`, `BUFFER_QUEUE`, `INTERFACE`, `CABLE_LENGTH` 等 (CONFIG_DB) | 読込（依存テーブル列挙）→ DEL（force モード時） | `_deletePorts()` 内で Yang ツリーから依存テーブルを動的解決。`--force` 時に自動削除 | `config_mgmt.py:488-514` |
| ASIC_DB `ASIC_STATE:SAI_OBJECT_TYPE_PORT:*` | 読込（ポート削除完了確認） | ポート DELETE 後、最大 60 秒ポーリング | `config_mgmt.py:318,377-412,446-458` |

### show interfaces breakout コマンド時

`show interfaces breakout` は BREAKOUT_CFG を読み出すほか以下を参照する。

| 参照先 | 参照方向 | 条件 | evidence |
|--------|---------|------|----------|
| `platform.json` (ファイルシステム) | 読込（`breakout_modes` 一覧取得） | 常時 | `show/interfaces/__init__.py:218` |
| `hwsku.json` (ファイルシステム) | 読込（`default_brkout_mode` 取得） | 常時 | `show/interfaces/__init__.py:220-221` |
| `PORT` (CONFIG_DB) | 読込（子ポートの `speed` 取得） | 子ポートごとに `config_db.get_entry('PORT', port)` | `show/interfaces/__init__.py:248` |

### 起動時（sonic-cfggen）

| 参照先 | 参照方向 | evidence |
|--------|---------|----------|
| `hwsku.json` の `interfaces[*].default_brkout_mode` | 読込（初期 `brkout_mode` の源泉） | `portconfig.py:37-38,475-478` |
| `platform.json` の `interfaces[*].breakout_modes` | 読込（利用可能モード一覧） | `portconfig.py:441-450` |

---

## 参照方向サマリー

- `BREAKOUT_CFG` は `platform.json` / `hwsku.json`（プラットフォーム定義ファイル）を**暗黙的な前提**として持つ。これらが存在しない場合 DPB 機能全体が無効化される。
- `PORT` テーブルは BREAKOUT_CFG の直接の書込み対象ではないが、`breakout` コマンドは PORT テーブルを操作し BREAKOUT_CFG は最後に更新される（Phase B 参照）。
- `ASIC_DB` は読込専用（確認用）で書込みは行わない。
- `VLAN_MEMBER` / `BUFFER_PG` 等の依存テーブルは YANG モデルを介して動的に解決されるため、テーブル一覧はプラットフォームの設定状態に依存する。
