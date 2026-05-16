# DASH_ACL_* テーブル — ordering (Phase B) 調査メモ

調査日: 2026-05-16  
ソース: sonic-swss orchagent/dash/dashaclorch.cpp, dashaclgroupmgr.cpp, dashtagmgr.cpp, orchdaemon.cpp

---

## 1. エントリ投入の必須順序（依存関係グラフ）

DASH ACL 処理でコード由来の強制依存がある順序は以下の通り。

```
[前提] DASH_ENI_TABLE (DashOrch) が先に存在すること
         ↓ (bindAclToEni が ENI lookup し task_need_retry を返す)

[1] DASH_PREFIX_TAG_TABLE   ← タグ名を src_tag / dst_tag で参照するルールより先に必要
         ↓ (createRule がタグ存在チェックし task_need_retry を返す)

[2] DASH_ACL_GROUP_TABLE    ← グループ ID が先に存在しないとルールが task_need_retry
         ↓ (createRule がグループ存在チェックし task_need_retry を返す)

[3] DASH_ACL_RULE_TABLE     ← ルールが 0 件だとバインドが task_failed
         ↓ (bind が m_rule_count == 0 をチェックし task_failed を返す)

[4] DASH_ACL_IN_TABLE / DASH_ACL_OUT_TABLE  ← ENI へのバインド（最後）
```

**task_need_retry vs task_failed の違い**:
- `task_need_retry`: キューに残し次回ループで再試行（順序依存は自動的に解消される）
- `task_failed`: キューから破棄。自動再試行なし → SDN コントローラが正しい順序で投入しないと永続的に失敗

| 違反した場合 | 結果 |
|---|---|
| グループより先にルール投入 | `task_need_retry`（グループ作成後に自動解消） |
| 参照タグより先にルール投入 | `task_need_retry`（タグ作成後に自動解消） |
| ENI 未作成でバインド | `task_need_retry`（ENI 作成後に自動解消） |
| ルール 0 件グループのバインド | `task_failed`（自動回復なし） |
| バインド中グループの削除 | `task_need_retry`（全バインド解除後に自動解消） |

---

## 2. ステージ番号と SAI マッピング

`getSaiStage()` (dashaclgroupmgr.cpp:94-128) が 4 次元タプル
`{direction, ip_family, stage}` → `SAI_ENI_ATTR_*` にマッピングする。

方向 × IP ファミリ × ステージ = 20 組の SAI 属性が 1:1 対応。

```
IN  × IPv4 × STAGE1 → SAI_ENI_ATTR_INBOUND_V4_STAGE1_DASH_ACL_GROUP_ID
IN  × IPv4 × STAGE2 → SAI_ENI_ATTR_INBOUND_V4_STAGE2_DASH_ACL_GROUP_ID
...（STAGE3〜5 同様）
IN  × IPv6 × STAGE1 → SAI_ENI_ATTR_INBOUND_V6_STAGE1_DASH_ACL_GROUP_ID
OUT × IPv4 × STAGE1 → SAI_ENI_ATTR_OUTBOUND_V4_STAGE1_DASH_ACL_GROUP_ID
...
OUT × IPv6 × STAGE5 → SAI_ENI_ATTR_OUTBOUND_V6_STAGE5_DASH_ACL_GROUP_ID
```

ステージは 1〜5 のみ。"0" や "6" を渡すと `lexical_convert` が `invalid_argument` をスローし `task_failed`。

---

## 3. ルール内の評価順序

- SAI へは `priority` 値を直接渡す（`SAI_DASH_ACL_RULE_ATTR_PRIORITY`）。
- **priority 値が小さいほど優先度が高い**（0 が最高優先度）。
- orchagent 側でのソートは行わない。優先度の評価は DPU ハードウェア / ASIC が担当。

---

## 4. タグ更新時のグループ再構築なし（重要）

`DashTagMgr::update()` はメモリ上のプレフィックスリストを更新するだけで、
既にバインド済みのグループ・ルールには再反映しない（SAI への再 SET なし）。

→ タグ更新後も実行中セッションの ACL ルールは旧プレフィックスで評価される。
新プレフィックスを反映するには、グループを解除 → ルール削除 → ルール再作成 → 再バインドが必要。

---

## 5. warm-reboot 挙動

DASH ACL orch (`DashAclOrch`) は `ZmqOrch` を継承しており、`m_orchList` には登録されない（`gDirectory.set()` のみ）。

`warmRestoreAndSyncUp()` の処理順:
1. `bake()` 全 orch
2. `doTask()` を最大 3 イテレーション（`m_orchList` 順）
3. `gMirrorOrch->doTask()` / `gAclOrch->doTask()` を最後に実行

**DASH ACL は m_orchList 非登録**のため、warm-reboot の 3 イテレーションループには含まれない。
ZmqOrch 系（DPU orchs）は ZmqServer 経由で別途メッセージを受信し、APP_DB から独立して再投入される。
→ DASH ACL の warm-reboot リストアは SDN コントローラ（gNMI 側）がエントリを再投入することで行われ、
  orchagent 自体が保存済み状態をリプレイする仕組みは実装されていない（ステートレス warm-reboot）。

---

## 6. 削除の逆順制約

削除は投入の逆順が必要:

```
[1] DASH_ACL_IN/OUT_TABLE (バインド解除) — DEL
       ↓
[2] DASH_ACL_RULE_TABLE — DEL（バインド中グループはルール削除不可）
       ↓
[3] DASH_ACL_GROUP_TABLE — DEL（バインド中は task_need_retry）
       ↓
[4] DASH_PREFIX_TAG_TABLE — DEL（グループに参照中は task_need_retry）
```

バインド解除前にグループを削除しようとすると `task_need_retry` でキューに残る。
