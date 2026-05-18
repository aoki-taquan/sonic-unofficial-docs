# srv6-applb — Phase H プラットフォーム差異 調査ノート

## 調査対象

- `sonic-net/sonic-swss` `orchagent/srv6orch.cpp` @ 4305596156d70e9797e8a881b3d19b46de0bce0d
- APPL_DB テーブル: `SRV6_MY_SID_TABLE`, `SRV6_SID_LIST_TABLE`

## 検出されたプラットフォーム差異

### 差異 1: SAI が `sai_srv6_api` を提供しない / 未実装プラットフォーム

`Srv6Orch` は `sai_srv6_api->create_srv6_sidlist()` / `create_my_sid_entry()` を使用する。
VS (Virtual Switch) など SAI SRv6 API が stub 実装のプラットフォームでは、
これらの呼び出しが `SAI_STATUS_NOT_IMPLEMENTED` を返し、
`SRV6_SID_LIST_TABLE` SET は `task_failed` で破棄される。
`SRV6_MY_SID_TABLE` SET も同様に `false` を返してエントリが登録されない。

### 差異 2: DSCP モード設定が必要な MySID エントリ（IP-in-IP トンネル）

`mySidTunnelRequired()` が true の行動（DSCP モード設定を持つ MySID）では
`sai_tunnel_api->create_tunnel()` + `create_tunnel_term_table_entry()` を呼び出す。

- `SAI_TUNNEL_DSCP_MODE_UNIFORM_MODEL` または `SAI_TUNNEL_DSCP_MODE_PIPE_MODEL` の 2 種類のトンネルを共有参照カウント管理
- トンネル作成に失敗した場合、対応 MySID エントリも SAI に登録されない（`srv6orch.cpp:1558-1560`）
- `sai_tunnel_api` が未実装の場合も同様に失敗

### 差異 3: gTraditionalFlexCounter と COUNTERS_DB 登録遅延

`gTraditionalFlexCounter = true`（orchagent 起動引数 `-c traditional`）のとき、
MySID カウンタの FLEX_COUNTER_DB 登録は ASIC_DB `VIDTORID` テーブルで VID→RID 変換が
確認できるまで繰り返し待機する（`srv6orch.cpp:294-295`）。
これにより `COUNTERS:<oid>` 初回値の出現が遅延する可能性がある。

| モード | FLEX_COUNTER_DB 登録タイミング |
|--------|-------------------------------|
| デフォルト (`false`) | MySID 追加から最大 1 秒後（タイマー発火） |
| traditional (`true`) | ASIC_DB VIDTORID 確定後（追加遅延あり） |

### 差異 4: SRV6_SID_LIST_TABLE の sidlist type 制約

`sidlist_type_map` に定義された 4 種類 (`insert`, `insert.red`, `encaps`, `encaps.red`) のみ有効。
ただし SAI 実装によっては `insert` / `insert.red` が対応していない場合がある。
fpmsyncd 経由では常に `encaps.red`（デフォルト）が使用されるため通常は問題ない。

## サマリ

| 差異 | 条件 | 影響 | 回避策 |
|------|------|------|--------|
| SAI SRv6 API 未実装 | VS / stub SAI | SID LIST / MySID エントリ作成不可 | 対応ハードウェア・SAI を使用 |
| sai_tunnel_api 未実装 | DSCP モード設定あり MySID | MySID 自体が未作成 | DSCP モードなし構成を使用 |
| gTraditionalFlexCounter | 旧 Broadcom SDK 系 | COUNTERS_DB 反映に追加遅延 | デフォルトモードを使用 |
| sidlist type 非対応 | SAI 実装依存 | insert 系 type が失敗する場合あり | encaps.red を使用（fpmsyncd デフォルト） |
