# SYSTEM_DEFAULTS — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-18 (chore/q67-f-batch173-next)

## 調査概要

`SYSTEM_DEFAULTS` テーブルは "書き込み先" ではなく "読み取り元" として機能するため、
失敗挙動は「読み取り側ダエモンが不正値・エントリ不在を受け取ったとき」に現れる。

## 調査したコード

- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/main.py` L117-119
- `sonic-buildimage/src/sonic-config-engine/config_samples.py` L160-188
- `sonic-swss/orchagent/muxorch.cpp` L1388-1390
- `sonic-buildimage/files/build_templates/swss_vars.j2` L9,14
- `sonic-buildimage/dockers/docker-orchagent/orchagent.sh` L37-42

## SET 処理における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `status` に `enabled`/`disabled` 以外の値を書き込もうとする | YANG バリデーション層 | `admin_mode` enum 制約でブロック。CONFIG_DB には書き込まれない | YANG エラー | `sonic-system-defaults.yang` `admin_mode` typedef |
| `<name>` が YANG 定義に無い任意文字列 (`1..32`) | YANG — パスは通る | YANG 側制約なし (任意 string 許容)。コード側でキーを参照していなければ無視される | なし | `sonic-system-defaults.yang` key pattern |
| `tunnel_qos_remap.status=enabled` を orchagent 起動後に書き込む | `muxorch.cpp` L1388 (`hget` 1 回限り参照) | orchagent 再起動まで変更が反映されない。ランタイム中の書き込みは silent ignore | なし (コード側 warning なし) | `muxorch.cpp:1388-1390` |
| `mux_tunnel_egress_acl.status` がエントリ不在 | `muxorch.cpp` L1389-1390 — `hget` が false を返す | `value` が空文字列のまま。`is_ingress_acl_ = value != "enabled"` → `true`（ingress ACL として処理） | なし | `muxorch.cpp:1390` |
| `software_bfd.status` が `"enabled"` 以外または不在 | `bgpcfgd/main.py` L118 | `BfdMgr` を登録しない。BFD ソフトウェアセッション管理が無効のまま | なし | `bgpcfgd/main.py:118` |

## DEL 処理における失敗経路

| 失敗条件 | 検出箇所 | 結果 | evidence |
|---|---|---|---|
| エントリ DEL 後に読み取り側ダエモンが起動 | 各 daemon の `hget` / `get_table` | エントリ不在を `disabled` として扱う (safe fallback)。`KeyError` は発生しない | `config_samples.py:160-161`、`muxorch.cpp:1390` |
| テーブル全体が不在の状態で orchestrator 起動 | `config_samples.py` L160-161 | 空 dict を補完してテーブル不在を回避するが、`init_cfg.json` にエントリが無ければ各機能は disabled 扱い | `config_samples.py:160-161` |

## swss_vars.j2 / orchagent.sh の失敗経路

| 失敗条件 | 検出箇所 | 結果 | evidence |
|---|---|---|---|
| `SYSTEM_DEFAULTS.tunnel_qos_remap` 不在時に `swss_vars.j2` を展開 | `swss_vars.j2` L14 — Jinja2 `is defined` ガード | `dscp_remapping` が `"disable"` になる（フォールバック正常動作） | `swss_vars.j2:14` |
| `sonic-cfggen -d -t swss_vars.j2` 実行時に CONFIG_DB 接続失敗 | `orchagent.sh` L8 — `|| exit 1` | orchagent.sh が exit 1 で終了 → supervisord がコンテナを再起動 | `orchagent.sh:8` |
| `synchronous_mode` フィールドが `DEVICE_METADATA` に不在 | `swss_vars.j2` L9 — Jinja2 条件式 | Jinja2 が `None` を評価 → `"disable"` 以外扱いで `"enable"` を出力（デフォルト同期モード）。実際の `synchronous_mode` は `DEVICE_METADATA` テーブルを読む | `swss_vars.j2:9` |

## 補足

- **`SYSTEM_DEFAULTS` はイベント駆動ではない**: `ConsumerStateTable` / `SubscriberStateTable` 等の pub/sub 機構を使用しないため、値変更の失敗（pub 失敗）は概念として存在しない。
- **YANG バリデーション層のブロック**: `status` フィールドへの不正値書き込みは YANG で拒否されるため、不正値が CONFIG_DB に残存するシナリオは正規経路では発生しない。
- **`polaris` / `software_bfd`**: `config_samples.py` が SmartSwitch DPU プロファイル生成時に無条件で上書き注入する (`L179-188`)。`polaris` は Pensando hwsku の場合のみ設定される。不在の場合はコード参照先が存在しないため影響なし。
