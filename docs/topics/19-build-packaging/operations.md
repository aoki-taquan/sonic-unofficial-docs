---
title: 設定 / 運用
area: topics
verification: meta
last_verified: 2026-05-11
sources: []
---

# 設定 / 運用

Application Extension は、3rd party / 任意の docker を inbox 機能と同じ管理面で扱うための枠組みである。運用面では `sonic-package-manager`（SPM）の CLI と、それが触る `FEATURE` テーブル、manifest、依存解決を押さえれば一通り読める。

## Extension lifecycle の全体像

| 段階 | 主な操作 | 触る場所 |
| --- | --- | --- |
| 配布 | docker registry に image を置く | 外部 registry |
| install | `sonic-package-manager install <pkg>` | SPM CLI、`FEATURE` テーブル |
| 有効化 | `config feature state <pkg> enabled` | `FEATURE`、`docker_image_ctl`、systemd |
| アップグレード | `sonic-package-manager upgrade <pkg>` | manifest 解決、再起動フック |
| 削除 | `sonic-package-manager uninstall <pkg>` | `FEATURE` 削除、image 廃棄 |

CLI の各サブコマンドの引数と挙動は [sonic-package-manager CLI リファレンス](../../reference/cli/sonic-package-manager.md) を参照する。manifest schema と依存解決のコア仕様は [Application Extension Infrastructure](../../architecture/sonic-application-extension-infrastructure.md) にある。

## 典型コマンドと出力例

### list / show

```
admin@sonic:~$ sonic-package-manager list
Name                  Repository                              Description           Version          Status
--------------------  --------------------------------------  --------------------  ---------------  -----------
swss                  docker-swss                             SWSS                  master.0-dirty   Built-In
syncd                 docker-syncd-mlnx                       SyncD                 master.0-dirty   Built-In
my-ext                registry.example.com/sonic/my-ext       My Extension          1.2.0            Installed

admin@sonic:~$ sonic-package-manager show package versions my-ext
1.0.0
1.1.0
1.2.0
1.3.0-rc1
```

### install / upgrade / uninstall

```
admin@sonic:~$ sudo sonic-package-manager install --from-repository \
    registry.example.com/sonic/my-ext --default-reference 1.2.0
admin@sonic:~$ sudo sonic-package-manager upgrade my-ext=1.3.0
admin@sonic:~$ sudo sonic-package-manager uninstall my-ext
```

install は manifest を引き出し、`FEATURE` テーブルへ登録し、systemd unit を生成する。enable は別操作。

### enable / disable

```
admin@sonic:~$ sudo config feature state my-ext enabled
admin@sonic:~$ show feature status my-ext
Feature        State     AutoRestart    HighMemAlert
-------------  --------  -------------  --------------
my-ext         enabled   enabled        disabled
admin@sonic:~$ systemctl status my-ext.service
```

## 既存 docker を Extension に移植する

inbox docker（例: dhcp_relay）を Extension 形式に変換する具体手順は、[Application Extension 開発・移植ガイド](../../management/sonic-application-extension-guide.md) にコミット例つきでまとまっている。要点は次の 3 つ。

- `manifest.json` を docker image に同梱して `sonic-package-manager` が読める形にする。
- inbox から外す場合は `sonic-buildimage` の build flow から該当 docker を除外し、registry 経由配布へ切り替える。
- `FEATURE` テーブルへの登録、warm reboot / fast reboot のフック、showtech / syslog 連携を inbox と同じインタフェースで揃える。

## バージョン互換と依存解決

extension の `manifest.json` には `version` / `depends` を書く。依存制約は semver で表現し、Redis DB スキーマを互換境界として使う方針が [OS / docker semver](../../system/sonic-os-sonic-docker-images-versioning.md) に詳しい。注意点として、HLD で例示される `"^1.0.0,^2.0.0"` のような並列 OR 表記や `SWSS_VERSION` 環境変数注入は **採用見送り** であり、原文 HLD と実装で差がある（裏取り済み）。

依存衝突は install / upgrade 時に SPM が解決を試み、解けない場合は次のように出る。

```
admin@sonic:~$ sudo sonic-package-manager install my-ext=1.3.0
Error: Package my-ext=1.3.0 conflicts with installed swss=master.0
       (requires swss >=2.0.0)
```

## 運用上よく見る場所

```
admin@sonic:~$ show feature status
admin@sonic:~$ docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'
admin@sonic:~$ ls /var/lib/sonic-package-manager/
database  packages
admin@sonic:~$ cat /var/lib/sonic-package-manager/database
admin@sonic:~$ systemctl status my-ext.service
admin@sonic:~$ journalctl -u my-ext.service --since "1 hour ago"
```

- `show feature status`: 各 extension が `FEATURE` で enabled か。
- `docker ps`: SPM が起動した extension docker の存在確認。
- `/var/lib/sonic-package-manager/`: パッケージ DB の場所。manifest / version / repository が記録される。
- `systemctl status <pkg>` / `journalctl -u <pkg>`: extension の systemd unit と起動ログ。

inbox 機能と extension の境界は **同じ管理面** に揃っているので、`config feature` 系コマンドは inbox 同様に効く。違いは「ビルド時に焼き込んだか、後から install したか」だけである。

## 異常検出と切り分け

| 症状 | 一次切り分け | 対処 |
| --- | --- | --- |
| `install` が registry 解決で失敗 | `docker pull <image>` を手で実行、proxy / DNS / 認証情報を確認 | `/etc/docker/daemon.json`、`docker login` |
| `install` 成功するが `docker ps` に出ない | `config feature state <pkg> enabled` が抜けている | enable する |
| enable しても unit が `failed` | `journalctl -u <pkg>` で entrypoint エラー確認 | manifest の `command` / `mounts` 修正、再 install |
| upgrade で依存衝突 | エラーメッセージで `requires <dep> <op> <ver>` を確認 | 依存 package を先に上げる、または対応版を選ぶ |
| warm reboot 後に extension が消える | `FEATURE` テーブルの persistence、`config_db.json` に保存されているか確認 | `config save` を上げ忘れた可能性、保存して reboot |
| `show techsupport` に出ない | manifest の `service.dump-info` 設定漏れ | manifest 修正 |

## ログの場所

| 経路 | ログ | grep キーワード |
| --- | --- | --- |
| SPM | `/var/log/sonic-package-manager.log`（無ければ stderr） | `install`、`upgrade`、`depends` |
| docker | `journalctl -u docker.service` | image pull 失敗、registry エラー |
| extension 本体 | `journalctl -u <pkg>.service` | container の起動 / クラッシュ |
| FEATURE 反映 | `/var/log/syslog` で `hostcfgd` | `FeatureHandler` |

## ビルド側の出口（参考）

extension を作る側で `sonic-buildimage` を触る場合、ビルド失敗の入口は以下。

```
$ make NOSTRETCH=1 KEEP_SLAVE_ON=yes target/docker-my-ext.gz
$ ls -lh target/docker-my-ext.gz
$ docker import target/docker-my-ext.gz registry.example.com/sonic/my-ext:1.3.0
$ docker push registry.example.com/sonic/my-ext:1.3.0
```

`KEEP_SLAVE_ON=yes` のままにしておけば失敗時に slave コンテナへ入って原因を追える。

## warm reboot / fast reboot と extension

extension は inbox 同様、warm reboot / fast reboot のフックを `manifest.json` から宣言する。フックが欠けていると、reboot のたびに extension がコールドスタートになり、データプレーン継続性が失われる。

```
admin@sonic:~$ jq '.service' /var/lib/sonic-package-manager/packages/my-ext/manifest.json
{
  "name": "my-ext",
  "warm-shutdown": {
    "after": ["swss"]
  },
  "fast-shutdown": {
    "after": ["swss"]
  },
  "dependent-of": ["swss"]
}
```

reboot 後、extension が期待どおり warm/fast を完了したかは syslog で確認する。

```
admin@sonic:~$ grep -E "warm-?reboot|fast-?reboot" /var/log/syslog | tail
admin@sonic:~$ docker exec <pkg> cat /var/log/<svc>.log | grep -iE "warm|fast"
```

完全な warm reboot の挙動と要件は [Reboot / Upgrade / Lifecycle 章](../11-reboot/index.md) を参照する。

## CI / 開発時のチェックリスト

extension を CI に乗せる場合、毎回確認したい最小項目:

| 項目 | 確認方法 |
| --- | --- |
| image が pull できる | `docker pull <registry>/<image>:<tag>` |
| manifest が valid | `sonic-package-manager show package manifest <pkg>` |
| install / uninstall が冪等 | 連続 install / uninstall を流して `docker ps` 差分なし |
| enable / disable が反映 | `show feature status` で state 推移 |
| warm / fast reboot 完走 | `sudo warm-reboot` 後 `show warm_restart state` で WARM_RESTART_TABLE の state が `reconciled` |
| `show techsupport` に dump が入る | tar 内に extension の log と redis dump が含まれる |

## 関連ページ

- [Application Extension Infrastructure](../../architecture/sonic-application-extension-infrastructure.md)
- [Application Extension 開発・移植ガイド](../../management/sonic-application-extension-guide.md)
- [sonic-package-manager CLI リファレンス](../../reference/cli/sonic-package-manager.md)
- [OS / docker semver](../../system/sonic-os-sonic-docker-images-versioning.md)
- [Reboot / Upgrade / Lifecycle 章](../11-reboot/index.md)（warm/fast reboot とのフック整合）
- [SWSS / SAI / Redis 章](../20-swss-sai-redis/index.md)（FEATURE と sysmonitor の関係）
