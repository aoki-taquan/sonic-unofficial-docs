# suppress-pending-fib / fpmsyncd — Phase B 書込み順依存調査メモ

対象 slug: `suppress-pending-fib.md` / `fpmsync.md`
調査日: 2026-05-16
結論: **対象ドキュメント不在のため Phase B 適用スキップ**

---

## 調査結果

`docs/reference/config-db/suppress-pending-fib.md` および `docs/reference/config-db/fpmsync.md` は
いずれも存在しない。`suppress-fib-pending` フィールドは `DEVICE_METADATA|localhost` の一フィールドであり、
独立した CONFIG_DB テーブルではない。`fpmsyncd` はプロセス名であり、CONFIG_DB テーブルではない。

`DEVICE_METADATA` テーブルページ (`docs/reference/config-db/device-metadata.md`) の
`<!-- ordering -->` ブロック（L1272-L1342）がすでに `suppress-fib-pending` の
順序依存を網羅的に記述している。

---

## ソース調査: bgpcfgd と fpmsyncd の FIB pending 連携

### 1. bgpcfgd — `suppress-fib-pending` 反映経路

| ファイル | 役割 | 行 |
|---------|------|---|
| `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py` | `apply_op()` が `BGP_NEIGHBOR` SET 処理時に無条件で FRR へ `bgp suppress-fib-pending` コマンドを挿入 | L501-507 |

`apply_op()` は `DEVICE_METADATA|localhost.suppress-fib-pending` を直接参照せず、
BGP_NEIGHBOR の set_handler から呼ばれる `add_peer` / `peer_group_apply` 経由で FRR に
`bgp suppress-fib-pending` を毎回送出する（常に有効化）。
`DEVICE_METADATA|localhost.suppress-fib-pending` の値は bgpcfgd では参照されない
（fpmsyncd 側のみが参照する）。

### 2. fpmsyncd — `suppress-fib-pending` 起動時読み取りとランタイム購読

| 動作フェーズ | 処理 | ソース |
|------------|------|-------|
| 起動時 | `deviceMetadataTable.hget("localhost", "suppress-fib-pending", suppressionEnabledStr)` で初期値読み取り | `fpmsyncd.cpp:113` |
| 有効時 | `routeResponseChannel = make_unique<NotificationConsumer>(applStateDb, routeResponseChannelName)` で応答チャンネル作成 + `sync.setSuppressionEnabled(true)` | `fpmsyncd.cpp:116-117` |
| ランタイム変更 | `SubscriberStateTable deviceMetadataTableSubscriber` が `DEVICE_METADATA.localhost.suppress-fib-pending` 変化を受信 | `fpmsyncd.cpp:82,252-305` |
| enabled→disabled | `sync.markRoutesOffloaded(db)` で既存保留ルートを全 offloaded にマーク後に suppression を解除 | `fpmsyncd.cpp:298-302` |
| disabled→enabled | `routeResponseChannel` 新規作成 + `sync.setSuppressionEnabled(true)` + Select ループに追加 | `fpmsyncd.cpp:287-289` |

### 3. BGP 起動順序と FIB pending 連携の順序依存

| # | 依存関係 | 方向 | 根拠 |
|---|----------|------|------|
| 1 | `DEVICE_METADATA.localhost.synchronous_mode = enable` → `suppress-fib-pending = enabled` | **先行必須（YANG must 制約）** | `sonic-device_metadata.yang:250` の `must` 制約で reject |
| 2 | orchagent / syncd 起動（SAI ready）→ fpmsyncd 起動 → BGP コンテナ（FRR / bgpcfgd）起動 | **推奨順序** | fpmsyncd が suppression モードに入る前に FRR がルートを送り始めると、suppress なしでルートが FIB に書き込まれる |
| 3 | fpmsyncd が `suppress-fib-pending = enabled` で起動 → FRR zebra が FPM 接続確立 → BGP がルート計算・zebra に通知 | **理想的起動順序** | suppression が FPM 接続前に有効になっていれば、zebra から fpmsyncd へのルート送信開始と同時に suppression が機能する |
| 4 | `APPL_DB_ROUTE_TABLE_RESPONSE_CHANNEL` の存在 → fpmsyncd の `routeResponseChannel` 作成 | fpmsyncd が先にチャンネルを作成する（orchagent 側の応答チャンネルより先） | `fpmsyncd.cpp:78,116` |
| 5 | orchagent の `RouteOrch::doTask` 処理 → `APPL_STATE_DB_ROUTE_TABLE_RESPONSE_CHANNEL` への応答書込 → fpmsyncd の `onRouteResponse` 受信 | **シーケンシャル依存** | suppression 有効時にルートが FIB インストール成功した場合のみ zebra へ offload 通知が返る |
| 6 | `disabled → enabled` ランタイム切替 | 既存ルートが `markRoutesOffloaded()` で一括 offloaded 扱い → zebra が offload フラグを受信し BGP へ通知 → 短時間の状態不整合リスク | `routesync.cpp:3302; fpmsyncd.cpp:298` |

### 4. 主要制約

**YANG must 制約（依存 #1）**:
```yang
must "(current() = 'disabled') or (current() = 'enabled' and ../synchronous_mode = 'enable')"
```
`suppress-fib-pending = enabled` 設定時に `synchronous_mode != 'enable'` であれば YANG バリデーションで reject。
orchagent を非同期モード（`synchronous_mode = disable`）で動かしながら suppression を有効にすると、
orchagent からの応答チャンネルが信頼できない状態になる。

**起動順序（依存 #2, #3）**:
`suppressor` が機能するためには、fpmsyncd が suppression モードで起動した後に FRR が FPM 接続を確立する必要がある。
BGP コンテナの `supervisord.conf.j2` は `zebra:running` 確認後に `bgpd` / `fpmsyncd` を起動するが、
fpmsyncd と bgpd の起動順は supervisord の priority 設定に依存する。
通常は fpmsyncd が先に FPM listen ソケットを開き、zebra が接続しに来るシーケンス。

**`markRoutesOffloaded` の副作用（依存 #6）**:
`disabled → enabled` ランタイム切替時に `sync.markRoutesOffloaded(db)` が実行される。
これは APPL_DB の全 BGP ルートに対して `offload_bit = 1` を netlink 経由で zebra に通知するもので、
その後 zebra が BGP に経路選択を再通知する可能性がある（ECMP 等で短時間の Churn が発生しうる）。

---

## Phase B 適用先の推奨

`suppress-fib-pending` の順序依存は `DEVICE_METADATA` ページの
`<!-- ordering -->` ブロック（`device-metadata.md:1272-1342`）に統合済み。
独立した `suppress-pending-fib.md` / `fpmsync.md` を新規作成する場合は、
上記の依存 #1〜#6 を `<!-- ordering -->` ブロックとして適用すること。

evidence ファイル:
- `sonic-swss/fpmsyncd/fpmsyncd.cpp:82-118,252-305`
- `sonic-swss/fpmsyncd/routesync.cpp:3156-3162,3174,3302`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py:494-508`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-device_metadata.yang:250`
