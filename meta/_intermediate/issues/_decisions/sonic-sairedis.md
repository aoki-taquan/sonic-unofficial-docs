# sonic-sairedis Issues — AI 判定 (28 件全件)

生成日: 2026-05-13  
担当: chore/q57-a-sairedis-issues  
対象リポ: sonic-net/sonic-sairedis

---

## 判定サマリ

| # | issue | 状態 | 判定 | 反映先 |
|---|-------|------|------|--------|
| 1 | #1545 build: CODE_COVERAGE_ENABLED macro 不足 | OPEN | **skip** – autoconf-archive 依存の build 環境バグ。ドキュメントへの反映対象なし |
| 2 | #1544 no saimetadata.h | OPEN | **skip** – debian パッケージ未インストール起因のビルドトラブル。ドキュメント変更不要 |
| 3 | #1429 warm-reboot: dummy SAI objects の削除失敗 → orchagent crash | OPEN | **apply** – warm reboot reconcile 失敗パターン（`SAI_STATUS_INVALID_PARAMETER` + dummy SAI objects）を operations / advanced に追記 |
| 4 | #1394 README build instruction 古い | OPEN | **skip** – 外部 README のメンテナンス問題。本 docs は build 手順を扱わない |
| 5 | #1387 show_techsupport / saidump の JSON parse error | CLOSED | **apply** – `saidump` が dump.json invalid 時に出す parse error と対処をトラブルシュートに追記 |
| 6 | #1376 `_sai_apis_t::icmp_echo_api` 初期化エラー | CLOSED | **skip** – ユーザ固有の local 変更が原因と確認。ドキュメント要素なし |
| 7 | #1361 warm-reboot: 次回 reboot が再度 warm remove_switch を呼ぶ | CLOSED | **apply** – `SAI_SWITCH_ATTR_RESTART_WARM` を warm reconcile 後に false に戻す必要という設計の落とし穴を advanced に追記 |
| 8 | #1357 VS: syncd が netlink messages を受け取れない | OPEN | **skip** – VS 環境固有の netlink race。VS 章がなく影響範囲外 |
| 9 | #1294 build: metadata の並列ビルド失敗 (race) | OPEN | **skip** – Makefile の並列化 race。ドキュメントへの反映対象なし |
| 10 | #1267 FDB learning が reboot 中に発生して orchagent crash | OPEN | **apply** – cold boot 中の FDB event → default bridge port remove 失敗パターンを operations に追記 |
| 11 | #958 README keyserver / パッケージ名が古い | OPEN | **skip** – build 環境ドキュメントは本プロジェクトのスコープ外 |
| 12 | #918 saidump が 40K route で遅い | CLOSED | **apply** – `saidump` のスケール限界（Lua スクリプト per-key）と workaround を operations に追記 |
| 13 | #899 warm-reboot: zero buffer profile attached queues で reconcile 失敗 | CLOSED | **apply** – performObjectSetTransition で属性リストが空の場合の reconcile 失敗パターンを advanced に追記 |
| 14 | #862 warm-reboot: FlexCounter が init view 後に新 VID を処理できない | CLOSED | **apply** – warm reboot 後の FlexCounter VID 再登録タイミングを internals / advanced に追記 |
| 15 | #801 armhf: CRM acl_resource_list polling で orchagent crash (libboost) | CLOSED | **skip** – armhf + libboost1.71 の platform 固有バグ。一般化不可 |
| 16 | #780 syncd-vs compile: `sai_query_attribute_capability` が libsai.so に未公開 | OPEN | **apply** – ベンダ SAI が `sai_query_attribute_capability` を expose しないと syncd コンパイル失敗という落とし穴を internals に追記 |
| 17 | #772 SAI/meta makefile build error (Ubuntu 20.04) | CLOSED | **skip** – 未解決のまま closed 扱い（原因不明）。ドキュメント要素なし |
| 18 | #745 SaiDiscovery と ViewTransition の役割に関する質問 | CLOSED | **apply** – SaiDiscovery が switch/port RID を列挙し apply_view_transition に渡す設計を internals に加筆（質問 → 概念説明化） |
| 19 | #697 sonic-sairedis compilation problem (SAI submodule 未 init) | CLOSED | **skip** – submodule 未 init のビルドエラー。ドキュメント範囲外 |
| 20 | #639 syncd restart が applyView で失敗（switch count 0 != temp switch count） | OPEN | **apply** – syncd 単体 restart 時に applyView が switch 0 問題で失敗するパターンと回避策（config reload 推奨）を operations に追記 |
| 21 | #578 libsairedis compile: `sai_object_type_get_availability` undefined ref | OPEN | **skip** – 古いブランチ (201911) 固有の SAI ヘッダ不整合ビルド問題 |
| 22 | #559 apt-get で libsairedis / syncd が見つからない | CLOSED | **skip** – パッケージリポジトリ設定の問題。インストール手順ドキュメントは範囲外 |
| 23 | #555 VS: admin down でも oper status が up のまま | CLOSED | **apply** – VS でのポート oper status 更新の遅延（PR #603 で fix 済）を VS 既知挙動として operations / internals に追記 |
| 24 | #466 orchagent が ASIC_DB に接続する仕組み（アーキテクチャ質問） | CLOSED | **apply** – orchagent ↔ sairedis ↔ ASIC_DB の接続経路説明を internals / concept に補強（sairedis API が中間レイヤ） |
| 25 | #449 warm-reboot: ACL Entry に誤った ACL Counter RID が SET される | CLOSED | **apply** – warm reboot 後の ACL counter OID マッピングズレ（fix 済）を advanced の known issues に追記 |
| 26 | #270 VS startup: `veth2tap_fun: failed to write to tap device` | CLOSED | **skip** – VS startup 時の既知ノイズ（Resolved）。ドキュメント要素なし |
| 27 | #235 syncd crash with port breakout | CLOSED | **skip** – orchagent の portListLaneMap 処理バグ（swss 側）。sairedis 主体でなく範囲が広い |
| 28 | #183 ports with linkDown status の oper status が nil | CLOSED | **skip** – 2017年の古いバグ、swss PR #224 で修正済。現行との乖離大きすぎ |

---

## apply 対象まとめ（10 件）

| issue | 反映先ファイル | 内容 |
|-------|--------------|------|
| #1429 | `docs/topics/20-swss-sai-redis/advanced.md` | warm reboot: dummy SAI objects (SAI_STATUS_INVALID_PARAMETER) の reconcile 失敗パターン |
| #1387 | `docs/topics/20-swss-sai-redis/operations.md` | saidump が dump.json invalid 時の parse error と対処 |
| #1361 | `docs/topics/20-swss-sai-redis/advanced.md` | warm reboot: SAI_SWITCH_ATTR_RESTART_WARM を reconcile 後に false に戻す必要 |
| #1267 | `docs/topics/20-swss-sai-redis/operations.md` | cold boot 中 FDB event → default bridge port remove 失敗パターン |
| #918 | `docs/topics/20-swss-sai-redis/operations.md` | saidump 40K route でのスケール限界（Lua per-key） |
| #899 | `docs/topics/20-swss-sai-redis/advanced.md` | warm reboot: buffer profile 属性リストが空の performObjectSetTransition 失敗 |
| #862 | `docs/topics/20-swss-sai-redis/advanced.md` | warm reboot: FlexCounter が init view 後に新 VID を扱えない問題と対処 |
| #780 | `docs/topics/20-swss-sai-redis/internals.md` | ベンダ SAI が sai_query_attribute_capability を非公開にすると syncd コンパイル失敗 |
| #745 | `docs/topics/20-swss-sai-redis/internals.md` | SaiDiscovery の役割（RID 列挙 → applyViewTransition への受け渡し） |
| #639 | `docs/topics/20-swss-sai-redis/operations.md` | syncd 単体 restart の applyView switch count 不一致と回避策 |
| #555 | `docs/topics/20-swss-sai-redis/operations.md` | VS: admin down 後も oper status が up のまま（fix 済、起票 hint）|
| #466 | `docs/topics/20-swss-sai-redis/internals.md` | orchagent ↔ sairedis ↔ ASIC_DB の接続経路補強 |
| #449 | `docs/topics/20-swss-sai-redis/advanced.md` | warm reboot 後の ACL counter OID マッピングズレ（fix 済） |
