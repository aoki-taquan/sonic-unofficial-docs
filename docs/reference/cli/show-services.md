---
title: show services サブコマンド
description: show services サブコマンド — show services は 稼働中の SONiC docker コンテナ全てに対して ps
  aux を一括実行して結果を結合表示するデバッグ用コマンド。各 docker サービスの中で動いているプロセスツリーをまとめて見られる。
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
- repo: sonic-net/sonic-utilities
  path: show/main.py
  ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
related:
  config_db: []
  cli:
  - show services
  - show feature status
  - show system-health
  yang:
  - sonic-feature
---

# show services サブコマンド

## 概要

`show services` は **稼働中の [SONiC](../../reference/glossary.md#term-sonic) docker コンテナ全てに対して `ps aux` を一括実行**して結果を結合表示するデバッグ用コマンド。各 docker サービスの中で動いているプロセスツリーをまとめて見られる[^1]。

## シグネチャ

```bash
show services
```

引数・オプションなし。`--verbose` も無い。

## 動作

実装は次の通り[^1]。

```python
@cli.command('services')
def services():
    """Show all daemon services"""
    cmd = ["sudo", "docker", "ps", "--format", '{{.Names}}']
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True)
    while True:
        line = proc.stdout.readline()
        if line != '':
            print(line.rstrip() + '\t' + "docker")
            print("---------------------------")
            cmd0 = ["sudo", "docker", "exec", line.rstrip(), "ps", "aux"]
            cmd1 = ["sed", '$d']
            _, stdout = getstatusoutput_noshell_pipe(cmd0, cmd1)
            print(stdout)
        else:
            break
```

挙動:

1. `sudo docker ps --format '{{.Names}}'` で **起動中の全コンテナ名**を列挙。
2. 各コンテナ名について以下を出力:
   - `<container>\tdocker` のヘッダ行
   - `---------------------------` の区切り
   - `sudo docker exec <container> ps aux | sed '$d'` の結果（末尾 1 行を `sed '$d'` で落とす）

`sed '$d'` で末尾行を捨てるのは、`docker exec` 経由の `ps aux` が出力末尾に空行や `ps` 自身のプロセス行を出すための整形目的。

## 注意点

- **コンテナが大量にあるシャーシ系・multi-[ASIC](../../reference/glossary.md#term-asic) では出力が非常に長くなる**。スクロールしたくない場合は `show services | less` を推奨。
- pager は内部で付かないため、デフォルトはそのまま stdout に流れる。
- `docker ps` で見える「停止中のコンテナ」は含まれない。停止中サービスの状態を見るには `show feature status` や `systemctl status` を使う。

## CONFIG_DB との接点

なし（docker daemon の API のみ）。

<!-- cli-mermaid -->
### データフロー (手動作成)

```mermaid
flowchart LR
  CLI["show services"]
  DK["docker ps + docker exec ps aux"]
  CN["各 SONiC コンテナ<br/>(swss / syncd / bgp / 等)"]
  CLI --> DK
  DK --> CN
```

!!! note "凡例"
    show 系 (CLI → docker → 各コンテナ) のミニ図。CONFIG_DB を直接介さないコマンドのため手動で記述。
<!-- /cli-mermaid -->

<!-- ref-triangle:start -->

## 関連リファレンス

- CLI: [show feature](show-feature.md) / [show system-health](show-system-health.md) / [show techsupport](show-techsupport.md)
- [YANG](../../reference/glossary.md#term-yang): [sonic-feature](../yang/sonic-feature.md)
- [CONFIG_DB](../../reference/glossary.md#term-config_db): [FEATURE](../config-db/feature.md)
- Topic: [リブート / アップグレード](../../topics/11-reboot/index.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: `services` コマンドは `show/main.py` L2252-L2267。<https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/show/main.py#L2252>

<!-- cli-sibling -->
### 関連 CLI コマンド

- [`config banner`](config-banner.md) — config banner サブコマンド
- [`config clock`](config-clock.md) — config clock サブコマンド
- [`config kdump`](config-kdump.md) — config kdump サブコマンド
- [`config ntp`](config-ntp.md) — config ntp サブコマンド
- [`config platform firmware`](config-platform-firmware.md) — config platform firmware サブコマンド

<!-- /cli-sibling -->

<!-- glossary-links-injected: ec18b66e3507 -->
