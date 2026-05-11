---
title: 発展トピック
area: topics
verification: meta
last_verified: 2026-05-10
sources:
  - docs/platform/1-6t-support-in-sonic.md
  - docs/platform/sonic-port-naming-convention-change.md
  - docs/acl-qos/enhancements-to-add-or-del-ports-dynamically.md
---

# 発展トピック

ここでは、port / platform 章の中でも比較的新しい、または運用上の影響が大きい設計を 3 つ取り上げます。詳細は元 HLD に従い、本章では「ほかの章と何が変わるか」に絞ります。

## 1.6T 対応

[1.6T support in SONiC](../../platform/1-6t-support-in-sonic.md) は、1.6Tbps クラスの port をサポートするための拡張設計です。speed 値、lanes、FEC、buffer profile、optics、Gearbox など、port 章のほぼ全要素が影響を受けます。既存の `PORT` テーブルや YANG の制約値を見直す必要があるため、設定面・運用面の双方を再点検する観点で読むのが安全です。

## Port naming convention

[SONiC port naming convention change](../../platform/sonic-port-naming-convention-change.md) は、現行の `EthernetN` ベース命名から、より装置構造を反映した命名へ移行する提案です。

影響範囲が広く、CLI、CONFIG_DB、YANG、運用スクリプトのほぼすべてに波及します。新規スクリプトを書くときは、port 名を直接ハードコードせず、`PORT` テーブルのキー一覧から取得する書き方にしておくと変更耐性が上がります。

## Dynamic add / delete

[enhancements to add or del ports dynamically](../../acl-qos/enhancements-to-add-or-del-ports-dynamically.md) は、運用中に port を追加・削除する操作の整合性向上に関する設計です。breakout や 1.6T 対応と直接重なるテーマで、ACL bind や QoS buffer の付け替えが正しく走るかが論点になります。

dynamic add / delete を多用する運用 (ZTP や検証ラボなど) では、buffer / QoS / ACL 章の挙動とあわせてこの設計を読むと、副作用の予測がしやすくなります。

## どの章と相互参照するか

- breakout / 速度変更 → QoS / Buffer 章 (今後執筆) と、関連 reference の [PORT テーブル](../../reference/config-db/port.md)。
- ACL bind の付け替え → [ACL / CoPP / Mirror 章](../07-acl-copp-mirror/index.md)。
- LAG / VLAN とのメンバ整合 → [L2 / VLAN / LAG 章](../06-l2-vlan-lag/index.md)。

## 関連ページ

- [1.6T support in SONiC](../../platform/1-6t-support-in-sonic.md)
- [SONiC port naming convention change](../../platform/sonic-port-naming-convention-change.md)
- [enhancements to add or del ports dynamically](../../acl-qos/enhancements-to-add-or-del-ports-dynamically.md)
