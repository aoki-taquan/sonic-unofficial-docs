---
title: 内部実装
verification: stub
---

# 内部実装

SwSS（orchagent / portsyncd / intfsyncd など）、syncd、SAI 実装、各 docker の構成など、コンポーネントレベルの内部実装を解説する章。

!!! info "準備中"
    このセクションは Phase の後半で着手予定です。

## 想定する内容

- orchagent の各 Orch クラスの責務（PortsOrch, IntfsOrch, RouteOrch, NeighOrch, AclOrch …）
- portsyncd / intfsyncd / fpmsyncd / teamsyncd / natsyncd 等の役割と通信経路
- syncd の動作とリスタート・ウォームブート
- Redis のテーブル間の参照・依存関係
