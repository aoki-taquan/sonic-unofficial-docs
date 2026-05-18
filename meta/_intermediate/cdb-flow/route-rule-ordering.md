# DASH_ROUTE_RULE_TABLE — 書込み順依存調査メモ (Phase B)

調査日: 2026-05-18
対象テーブル: `DASH_ROUTE_RULE_TABLE` (APP_DB / ZMQ)
対応ページ: `docs/reference/config-db/route-rule.md`
担当ハンドラ: `DashRouteOrch::doTaskRouteRuleTable()` → `addInboundRouting()`
ソース: `sonic-swss/orchagent/dash/dashrouteorch.cpp` @ 4305596156d70e9797e8a881b3d19b46de0bce0d

---

## SET 時の先行必須テーブル

### 依存 1: DASH_ENI_TABLE (ENI が存在しない → リトライ)

`addInboundRouting()` の冒頭で ENI の存在確認を行う (dashrouteorch.cpp:425-428):

```cpp
if (!dash_orch_->getEni(ctxt.eni))
{
    SWSS_LOG_INFO("Retry as ENI entry %s not found", ctxt.eni.c_str());
    return false;
}
```

`return false` はループの `it++`（次サイクルで再試行）に対応。
ENI が登録済みになれば自動的にリトライが成功する。

### 依存 2: DASH_VNET_TABLE (`vnet` フィールド指定時のみ → リトライ)

protobuf メッセージに `vnet` フィールドが存在する場合のみ確認 (dashrouteorch.cpp:430-433):

```cpp
if (ctxt.metadata.has_vnet() && gVnetNameToId.find(ctxt.metadata.vnet()) == gVnetNameToId.end())
{
    SWSS_LOG_INFO("Retry as vnet %s not found", ctxt.metadata.vnet().c_str());
    return false;
}
```

`vnet` フィールドを指定しない場合は `DASH_VNET_TABLE` の有無は無関係。

---

## DEL 時の順序制約

`removeInboundRouting()` は依存テーブルの存在チェックを行わず、SAI entry を直接削除する。
`DASH_ENI_TABLE` / `DASH_VNET_TABLE` を先に削除しても問題は生じない。

---

## 書込み順序まとめ

| # | 依存関係 | 条件 | 失敗時の挙動 |
|---|----------|------|------------|
| 1 | `DASH_ENI_TABLE` の ENI エントリが先行必須 | 常時 | `false` を返し it++ でリトライ（自動） |
| 2 | `DASH_VNET_TABLE` の VNET エントリが先行必須 | `vnet` フィールドがある場合のみ | `false` を返し it++ でリトライ（自動） |

---

## 起動時シーケンス

```
DashOrch (dashorch.cpp) が DASH_ENI_TABLE を処理し ENI 登録
  ↓
DashRouteOrch が DASH_ROUTE_RULE_TABLE を処理可能になる
  ↓
vnet フィールドがある場合: DashVnetOrch が DASH_VNET_TABLE を処理し gVnetNameToId に登録
  ↓
DASH_ROUTE_RULE_TABLE のエントリが SAI へ反映される
```

---

## 調査終了状態

- Phase B 完了: 書込み順依存特定
- `docs/reference/config-db/route-rule.md` に `<!-- ordering -->` セクション追加予定
