---
title: 設定 / 運用
area: topics
verification: meta
last_verified: 2026-05-10
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

## 既存 docker を Extension に移植する

inbox docker（例: dhcp_relay）を Extension 形式に変換する具体手順は、[Application Extension 開発・移植ガイド](../../management/sonic-application-extension-guide.md) にコミット例つきでまとまっている。要点は次の 3 つ。

- `manifest.json` を docker image に同梱して `sonic-package-manager` が読める形にする。
- inbox から外す場合は `sonic-buildimage` の build flow から該当 docker を除外し、registry 経由配布へ切り替える。
- `FEATURE` テーブルへの登録、warm reboot / fast reboot のフック、showtech / syslog 連携を inbox と同じインタフェースで揃える。

## バージョン互換と依存解決

extension の `manifest.json` には `version` / `depends` を書く。依存制約は semver で表現し、Redis DB スキーマを互換境界として使う方針が [OS / docker semver](../../system/sonic-os-sonic-docker-images-versioning.md) に詳しい。注意点として、HLD で例示される `"^1.0.0,^2.0.0"` のような並列 OR 表記や `SWSS_VERSION` 環境変数注入は **採用見送り** であり、原文 HLD と実装で差がある（裏取り済み）。

## 運用上よく見る場所

- `show feature status`: 各 extension が `FEATURE` で enabled か。
- `docker ps`: SPM が起動した extension docker の存在確認。
- `/var/lib/sonic-package-manager/`: パッケージ DB の場所。
- `systemctl status <pkg>`: extension の systemd unit。

inbox 機能と extension の境界は **同じ管理面** に揃っているので、`config feature` 系コマンドは inbox 同様に効く。違いは「ビルド時に焼き込んだか、後から install したか」だけである。

## 関連ページ

- [Application Extension Infrastructure](../../architecture/sonic-application-extension-infrastructure.md)
- [Application Extension 開発・移植ガイド](../../management/sonic-application-extension-guide.md)
- [sonic-package-manager CLI リファレンス](../../reference/cli/sonic-package-manager.md)
- [OS / docker semver](../../system/sonic-os-sonic-docker-images-versioning.md)
