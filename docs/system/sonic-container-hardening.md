---
title: SONiC Container Hardening（capability / read-only / privileged 削減）
description: "SONiC Container Hardening（capability / read-only / privileged 削減） — SONiC の docker は歴史的に多くが --privileged で動いていた。"
area: system
verification: code-verified
last_verified: 2026-05-10
sources:
  - repo: sonic-net/SONiC
    path: doc/Container Hardening/SONiC_container_hardening_HLD.md
    ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db: []
  cli: []
  yang: []
---

!!! warning "裏取りステータス: code-verified"
    各 docker の現行 supervisor / docker_image_ctl テンプレートでの cap-drop / read-only 適用状況は未確認。

!!! note "Verifier 注記（2026-05-10）"
    実コード裏取り: `sonic-buildimage/files/build_templates/default_manifest` / `manifest.json.j2` に application extension 用 `privileged` フラグや capability 制御の宣言枠を確認。各 docker 個別の cap-add / cap-drop はテンプレ化 PR が進行中で、現行値は `sonic-buildimage/dockers/<name>/` 配下の Dockerfile / start script に分散している。

# SONiC Container Hardening（capability / read-only / privileged 削減）

## 概要

SONiC の docker は歴史的に多くが **`--privileged`** で動いていた。CVE 対策とコンプライアンス要請から、**最低限必要な linux capability・mount・device だけを与える** 形に絞り込む取り組みが本 HLD のスコープ[^1]。

主な硬化軸:

- **capabilities**: `--cap-add` のみで必要な能力を与え、それ以外は drop
- **filesystem**: read-only ファイルシステム + 必要パスのみ writable bind
- **devices**: `/dev/kmsg` などの最小限のみ提供
- **non-privileged**: `--privileged` を可能な docker から外す
- **user namespace**: root を取り除く方向の検討

## 動作仕様（コンテナ起動時）

```mermaid
flowchart LR
    UNIT[systemd unit\n(<feature>.service)] --> CTL[docker_image_ctl.j2]
    CTL --> RUN[docker run\n--cap-add ... --cap-drop=all\n--read-only\n--tmpfs /run\n-v /var/log/<f>:/var/log\n-v /etc/sonic:/etc/sonic:ro\n...]
    RUN --> CONT[(docker container)]
```

各 docker は **何が必要か** を改修ごとに洗い出してテンプレート化する。たとえば[^1]:

- **swss / syncd**: Redis socket / shm へのアクセス、syncd は SAI vendor の特殊 device が必要なことがある
- **bgp**: routing socket、netlink 操作。NET_ADMIN 等は必要
- **teamd**: NET_ADMIN、NET_RAW
- **lldp**: NET_RAW + 特定 interface への access
- **dhcp_relay**: NET_BIND_SERVICE / NET_RAW

### 進め方（HLD ベース）

1. docker ごとに **capability matrix** を作る（必要な cap、不要な cap）
2. テンプレート (`docker_image_ctl.j2`) で `--cap-drop=all` を default にし、必要なものだけ `--cap-add` で復活
3. CI で全 docker の起動・主要シナリオが通ることを確認
4. read-only / tmpfs 化を docker 単位で順次適用
5. `--privileged` を残す docker は justification を明文化

## 制限事項

- **vendor SAI / SDK** が `--privileged` を要求する場合、syncd 単独で完全な脱 privileged は難しい
- **3rd-party container（application extension）**: manifest 側で必要 capability を宣言する必要があり、未対応 package は緩い設定で動く
- **既存運用スクリプト**: hardening 後に動かなくなる ad-hoc スクリプトが顕在化する
- **完全に root を捨てる**: user namespace 化は kernel 設定とコンテナ内 user 全体の見直しが必要

## 干渉する機能

- **application extension / 3rd-party container**: 拡張側にも hardening 方針を波及させる
- **secure-boot / secure-upgrade**: 端から root 権限を縮小する文脈で同時進行
- **show techsupport**: 一部の log / dump 取得で privileged が必要だったコマンドを再評価
- **warm reboot**: capability 不足で warm shutdown フックが失敗するパターンを警戒

## トラブルシューティング

- docker が EPERM で死ぬ → `docker logs <c>` と auditd / dmesg を見て不足 capability を特定
- read-only で write できない → tmpfs / volume の bind 漏れ
- vendor 機能が動かない → syncd の cap-add リストと vendor の要件確認

## 引用元

[^1]: `sonic-net/SONiC` `doc/Container Hardening/SONiC_container_hardening_HLD.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- concerns hint:
- docker_image_ctl.j2 の cap-add / cap-drop 制御の現行実装確認
- 各 docker（swss / syncd / bgp / teamd / lldp / dhcp_relay 等）の必要 capability matrix の現行値確認
- read-only / tmpfs 適用状況の docker 別の現行確認
- vendor SAI / SDK が要求する device / privileged 要件の現行 platform 確認
- application extension manifest の capability 宣言サポートの現行実装確認
- HLD 記述と現行 master の hardening 進捗の差分確認
-->

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: Security / AAA / FIPS / Hardening](../topics/15-security-aaa/index.md)
