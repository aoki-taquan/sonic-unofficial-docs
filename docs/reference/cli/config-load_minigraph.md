---
title: config load_minigraph サブコマンド
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-utilities
    path: config/main.py
    ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
related:
  config_db: []
  cli:
    - config load_minigraph
    - config reload
  yang: []
---

# config load_minigraph サブコマンド

## 概要

`config load_minigraph` は **`/etc/sonic/minigraph.xml` を元に CONFIG_DB を再生成** し、Golden Config (`--override_config`) で上書きする運用フックを持つ。実装は `config/main.py:load_minigraph()`[^1]。`@try_lock(SYSTEM_RELOAD_LOCK, timeout=0)` で **同時実行をロック**。

## シグネチャ

```
config load_minigraph [-y|--yes]
                      [-n|--no_service_restart]
                      [-t|--traffic_shift_away]
                      [-o|--override_config]
                      [-p|--golden_config_path <PATH>]
                      [-b|--bypass-lock]
```

| オプション | 意味 |
|----|------|
| `-y`, `--yes` | 「Reload config from minigraph?」プロンプトをスキップ |
| `-n`, `--no_service_restart` | docker service の再起動を抑止 |
| `-t`, `--traffic_shift_away` | TSA (Traffic Shift Away) 状態のままメンテナンスモードで再構成 |
| `-o`, `--override_config` | Golden config 上書きを有効化 |
| `-p`, `--golden_config_path <PATH>` | Golden config の場所 (省略時 `DEFAULT_GOLDEN_CONFIG_DB_FILE` = `/etc/sonic/golden_config_db.json`) |
| `-b`, `--bypass-lock` | reload ロックを取らず実行 |

## 処理フロー

1. `--override_config` 指定時、Golden config の存在 + YANG validation (`config_file_yang_validation`) + table の hard dependency check
2. 必要なら `_stop_services()` で transceiver / BGP peer / 関連 docker を停止
3. 各 namespace で以下を行う
    - `ConfigDBConnector.connect()` → Redis client `flushdb()` で **CONFIG_DB を全消去**
    - `init_cfg.json` があれば `sonic-cfggen -H -m -j /etc/sonic/init_cfg.json -n <ns> --write-to-db`、なければ `-H -m --write-to-db` (minigraph.xml ベース)
    - `INIT_INDICATOR` を `1` にセット
4. `update_sonic_environment()` で `/etc/sonic/sonic-environment` を再生成
5. `/etc/sonic/acl.json` があれば `acl-loader update full ... --skip_action_validation`
6. (この後 port_config.json 読み込み、telemetry, system_health 再起動などが続く)

## 注意

- **CONFIG_DB を完全に flush する** ため、未保存の手動変更は失われる
- minigraph.xml が無い・壊れている場合 `sonic-cfggen` がエラー終了する
- multi-ASIC では全 namespace に対して同じ処理を順に実行
- ロック中に他の `load_minigraph` / `reload` が発火しても `try_lock` が `timeout=0` のため即時失敗する (`-b` で迂回可)

## CONFIG_DB との接点

CONFIG_DB を **flush + 再構築** する破壊的操作。再構築は `sonic-cfggen -H -m` (minigraph) + 任意の Golden config。

<!-- ref-triangle:start -->

## 関連リファレンス

- CLI: [`config save`](config-save.md), [`config load`](config-load.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: `load_minigraph()` 実装は `config/main.py` L2335-L2476。<https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/config/main.py#L2335>
