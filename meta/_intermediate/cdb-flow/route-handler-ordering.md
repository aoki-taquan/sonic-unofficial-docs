# ROUTE_TABLE handler (fpmsyncd / RouteSync) — Phase B 書込み順依存スキャンノート

生成日: 2026-05-18
対象ページ: `docs/reference/config-db/route-handler.md`

## 訪問ファイル・関数一覧

| ファイル | 関数/セクション | 目的 |
|---------|---------------|------|
| `sonic-swss/fpmsyncd/fpmsyncd.cpp` | `main()` | FpmLink.accept() / netlink 登録 / warm-restart 初期化順序 |
| `sonic-swss/fpmsyncd/routesync.cpp` | `RouteSync::onMsg()` L2053-2103 | master デバイス判定（VRF/VNET 分岐）順序依存 |
| `sonic-swss/fpmsyncd/routesync.cpp` | `RouteSync::onRouteMsg()` L2111-2303 | mgmt VRF スキップ / eth0-docker0-eth1-midplane DEL 変換 |
| `sonic-swss/fpmsyncd/routesync.h` | コンストラクタ L156-162 | ProducerStateTable 初期化順序 |

---

## 検出した順序依存・タイミング依存

### 1. FRR (zebra) FPM 接続: fpmsyncd が accept() するまでメッセージ受信なし

`fpmsyncd.cpp:139-140`:
```cpp
cout << "Waiting for fpm-client connection..." << endl;
fpm.accept();
```

FpmLink.accept() が完了するまで RouteSync への FPM メッセージは届かない。FRR (zebra) 側が FPM クライアントとして接続してきてはじめてメッセージが流れ始める。

**順序**: `zebra` が起動して FPM クライアント接続 → `fpmsyncd` accept() 完了 → `onMsg()`/`onMsgRaw()` へのメッセージ受信開始。

evidence: `fpmsyncd/fpmsyncd.cpp:139-143`

---

### 2. netlink link cache: master デバイス名解決に先行必須

`RouteSync::onMsg()` は `nl_cache_refill()` を呼んで link cache を更新し、VRF/VNET 分岐のために master デバイス名 (`rtnl_link_get_name(master_link)`) を取得する (`routesync.cpp:2076-2086`):

```cpp
if (RTM_NEWLINK == nlmsg_type || RTM_DELLINK == nlmsg_type) {
    nl_cache_refill(sk, m_link_cache);
    return;
}
// ...
master_link = rtnl_link_get(m_link_cache, rtnl_route_get_iif(route_obj));
```

link cache が空/古い場合、master_link が NULL になり VRF/VNET 判定が正常動作しない可能性がある。`RTM_NEWLINK` を受信するたびに cache が更新されるため、インタフェース作成後に経路メッセージが来ることが前提。

**順序**: netlink RTNLGRP_LINK 登録 → インタフェース作成に伴う `RTM_NEWLINK` 受信 → link cache 更新 → VRF/VNET 経路の master 判定。

evidence: `routesync.cpp:2053-2103`; `fpmsyncd.cpp:93-94` (`netlink.registerGroup(RTNLGRP_LINK)`)

---

### 3. VRF プレフィックス前提: VNET/VRF 経路書込みの前提

`onMsg()` の master デバイス名に基づく分岐 (`routesync.cpp:2092-2103`):

```cpp
if (memcmp(master, VNET_PREFIX, strlen(VNET_PREFIX)) == 0)
    onVnetRouteMsg(nlmsg_type, nl_object, master);
else
    onRouteMsg(nlmsg_type, nl_object, master);
```

さらに `onRouteMsg()` は VRF 名が `mgmt` で始まる場合に即スキップ (`routesync.cpp:2125-2136`):

```cpp
if (memcmp(vrf, MGMT_VRF_PREFIX, strlen(MGMT_VRF_PREFIX)) == 0)
    return;  // mgmt VRF 経路は APPL_DB に書き込まれない
```

**ADD 順序**:
1. VNET インタフェース (名前が `Vnet` で始まる) を作成 → link cache 更新 → VNET_ROUTE_TABLE に書き込まれる
2. VRF インタフェース (名前が `Vrf` で始まる) を作成 → link cache 更新 → ROUTE_TABLE (VRF スコープ) に書き込まれる
3. 管理 VRF (`mgmt*`) 経路は fpmsyncd がスキップ → APPL_DB に入らない（意図的）

evidence: `routesync.cpp:2092-2136`

---

### 4. suppress-fib-pending: CONFIG_DB|DEVICE_METADATA に先行依存

`fpmsyncd.cpp:113-120`:
```cpp
deviceMetadataTable.hget("localhost", "suppress-fib-pending", suppressionEnabledStr);
if (suppressionEnabledStr == "enabled")
{
    routeResponseChannel = ...;
    sync.setSuppressionEnabled(true);
}
```

`suppress-fib-pending=enabled` の設定は fpmsyncd 起動時に一度だけ読む。後から CONFIG_DB を変更しても実行中の fpmsyncd には反映されない（再起動が必要）。

**順序**: `CONFIG_DB|DEVICE_METADATA|localhost suppress-fib-pending` の設定 → `fpmsyncd` 起動。起動後の変更は次回 fpmsyncd 再起動時に有効。

evidence: `fpmsyncd.cpp:112-121`

---

### 5. warm-restart: APPL_DB 書込みが orchagent 処理前に行われる

warm-restart 有効時 (`setRouteWithWarmRestart()`):

```cpp
// routesync.cpp:172-196
void RouteSync::setRouteWithWarmRestart(FieldValueTupleWrapperBase & fvw, ProducerStateTable & table)
{
    bool warmRestartInProgress = m_warmStartHelper.inProgress();
    if (!warmRestartInProgress)
        table.set(fvw.key, fvw.fieldValueTupleVector());
    else
        m_warmStartHelper.insertRefMap(fvw.key, fvw.fieldValueTupleVector());
}
```

warm-restart 進行中: APPL_DB への直接書き込みは行わず `insertRefMap()` でキャッシュ。warm-restart 完了後 (EOIU タイムアウト + hold interval) にまとめて APPL_DB に反映し、orchagent が未変更経路をそのまま維持する（reconciliation）。

**順序（warm-restart あり）**: fpmsyncd が FPM から経路受信 → refMap キャッシュ → EOIU タイムアウト → reconciliation 実行 → APPL_DB 書込み → orchagent RouteOrch が処理。

evidence: `routesync.cpp:172-200`; `fpmsyncd.cpp:148-220`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | FRR zebra FPM 接続 → RouteSync メッセージ受信開始 | 強制先行 (accept() ブロック) | zebra の FPM クライアント設定と fpmsyncd の起動順序を systemd で制御 |
| 2 | netlink link cache 更新 → VRF/VNET master 名判定 | 実質先行 (RTM_NEWLINK で自動更新) | インタフェース作成後に経路プッシュされるのが通常フロー |
| 3 | VNET/VRF インタフェース作成 → 対応経路書込み | 実質先行 (master 名が先に存在) | mgmt VRF 経路は意図的スキップ（APPL_DB に入らない） |
| 4 | DEVICE_METADATA suppress-fib-pending 設定 → fpmsyncd 起動 | 起動時 1 回読み (再起動要) | 変更時は fpmsyncd を再起動 |
| 5 | warm-restart 中は経路を refMap キャッシュ → EOIU 後に APPL_DB 反映 | warm-restart 特有 (通常は即書込み) | warm-restart タイマー期間 (デフォルト 120 秒) を適切に設定 |
