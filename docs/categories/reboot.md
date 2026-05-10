---
title: Warm-Reboot / Fast-Reboot 関連
area: categories
verification: meta
last_verified: 2026-05-10
---

# Warm-Reboot / Fast-Reboot 関連

## 概要

Warm Reboot、Fast Reboot、warm restart、kexec、docker / SWSS 再起動、Multi-ASIC reboot を横断して追う入口です。

主要キーワード: `warm reboot`, `fast reboot`, `warm restart`, `kexec`, `SWSS`, `docker`

## 関連ページ

- [reboot / fast-reboot / warm-reboot コマンド](../reference/cli/reboot-fast-warm.md) (area: `reference`, verification: `code-verified`)
- [VRF Ansible テストプラン（T0 上で BGP/ACL/loopback/warm-reboot 含む E2E 検証）](../routing/vrf-feature-ansible-test-plan-omit-in-toc.md) (area: `routing`, verification: `hld-only`)
- [Warm-reboot 中の LACP retry count 拡張（LACP version 0xf1 / 新規 TLV）](../switching/increasing-lacp-pdu-timeout-during-warm-reboot.md) (area: `switching`, verification: `code-verified`)
- [ProducerStateTable の view switching（warm reboot 用の差分適用）](../switching/view-switching-in-producerstatetable.md) (area: `switching`, verification: `code-verified`)
- [Fast-reboot Flow Improvements（finalizer / reconciliation）](../system/fast-reboot-flow-improvements-hld.md) (area: `system`, verification: `hld-only`)
- [kdump（kexec ベース kernel crash dump / makedumpfile）](../system/kdump.md) (area: `system`, verification: `code-verified`)
- [Multi-ASIC warm reboot（namespace 横断の協調 shutdown / boot）](../system/multi-asic-warm-reboot.md) (area: `system`, verification: `code-verified`)
- [libsairedis API idempotence（warm restart 用 OID キャッシュと duplicate 抑止）](../system/sonic-libsairedis-api-idempotence-support.md) (area: `system`, verification: `discrepancy-found`)
- [SWSS docker warm restart（state restore / consistency / sync up）](../system/sonic-swss-docker-warm-restart.md) (area: `system`, verification: `code-verified`)
- [SONiC Warm Reboot（要件・順序・docker 別 warm restart）](../system/sonic-warm-reboot.md) (area: `system`, verification: `code-verified`)
- [SWSS docker の Warm Restart 実装メモ（開発時リファレンス）](../system/swss-docker-warm-restart-code-reference.md) (area: `system`, verification: `discrepancy-found`)
- [Warm Reboot 開発フェーズと OID 復元戦略（idempotent libsairedis vs syncd view comparison）](../system/what-are-the-development-phases-and-scope-for-warm-reboot.md) (area: `system`, verification: `code-verified`)

## 関連カテゴリ

- [Multi-ASIC / VOQ chassis 関連](multi-asic.md)
- [Container / Build system 関連](container-build.md)
- [SmartSwitch 関連](smartswitch.md)
- [SAI 拡張属性追加系](sai-extensions.md)
