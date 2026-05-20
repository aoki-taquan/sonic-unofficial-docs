---
title: SSH 接続時の「Too many authentication failures」エラー
area: system
tags: [ssh, host-services, authentication, sshd, security]
description: SONiC デバイスへの SSH 接続で Too many authentication failures が発生する原因と対処法。
source_issues:
  - https://github.com/sonic-net/sonic-host-services/issues/134
verification: issue-confirmed
last_verified: 2026-05-20
---

# SSH 接続時の「Too many authentication failures」エラー

## 概要

SONiC デバイスへ SSH 接続する際、`Too many authentication failures` エラーが発生して接続できない場合がある。

```
Received disconnect from <ip> port 22:2: Too many authentication failures
Authentication failed.
```

## 原因

OpenSSH クライアントは、接続時にローカルの SSH エージェントや `~/.ssh/` 以下に登録されている**すべての秘密鍵**を順番に試行する。秘密鍵の数が `MaxAuthTries`（sshd の設定値、デフォルト 6）を超えると、サーバーが接続を切断する。

SONiC の `sshd` 設定では `MaxAuthTries` が比較的小さく設定されている場合があり、多数の SSH キーを管理しているクライアント環境で発生しやすい。

## 対処方法

### 方法 1: 公開鍵認証を無効にして接続する

```bash
ssh -o PubkeyAuthentication=no admin@<sonic-ip>
```

パスワード認証のみで接続される。

### 方法 2: 使用する鍵を明示的に指定する

```bash
ssh -i ~/.ssh/id_rsa_sonic -o IdentitiesOnly=yes admin@<sonic-ip>
```

`IdentitiesOnly=yes` を指定することで、`-i` で指定した鍵のみを試行する。

### 方法 3: ~/.ssh/config で設定する

```
Host sonic-device
    HostName <sonic-ip>
    User admin
    IdentityFile ~/.ssh/id_rsa_sonic
    IdentitiesOnly yes
```

### 方法 4: SSH エージェントの登録数を確認・削除する

```bash
# 現在エージェントに登録されている鍵を確認
ssh-add -l

# 不要な鍵をエージェントから削除
ssh-add -d ~/.ssh/unnecessary_key

# 全鍵を一時的に削除
ssh-add -D
```

## SONiC 側の設定確認

SONiC デバイス側で `MaxAuthTries` を確認・変更するには。

```bash
# 現在の sshd 設定を確認
sudo grep MaxAuthTries /etc/ssh/sshd_config

# 変更する場合（再起動が必要）
sudo sed -i 's/#MaxAuthTries 6/MaxAuthTries 20/' /etc/ssh/sshd_config
sudo systemctl restart sshd
```

ただし、`MaxAuthTries` を大きくするとブルートフォース攻撃への耐性が下がるため、管理ネットワーク内の接続に限定した上で検討すること。

## 詳細な接続ログの確認

問題を診断するには、クライアント側で詳細ログを有効にする。

```bash
ssh -vvv admin@<sonic-ip>
```

出力の中で試行している鍵の一覧が表示され、どの時点でリトライ上限に達したかを確認できる。

## 関連

- GitHub Issue: [sonic-net/sonic-host-services#134](https://github.com/sonic-net/sonic-host-services/issues/134)
