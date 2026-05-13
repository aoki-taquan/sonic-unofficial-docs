# AS_PATH_SET テーブル — consumer 例外条件分析

## Consumer: frrcfgd (sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py)

### 処理関数
- `bgp_table_handler_common` → `hdl_aspath_set()` (L1009)
- 初期ロード: L2248-2253

### 例外条件・特殊挙動

#### 1. as_path_set_member 空/DEL → 全エントリ削除
`as_path_set_member` が空リストまたは `OP_DELETE` の場合、FRR の `bgp as-path access-list <name>` を全削除してから再構築する。

```python
# frrcfgd/frrcfgd.py:1009-1026
def hdl_aspath_set(daemon, cmd_str, op, st_idx, args, data):
    if len(args) < 2:
        return None
    as_set_name = args[0]
    if as_set_name in daemon.as_path_set_list:
        cmd_list.append(...)  # 先に既存を全削除
    if op != CachedDataWithOp.OP_DELETE and len(args[1]) > 0:
        for asn in args[1]:
            cmd_list.append(...)  # 個々の permit を再投入
```

#### 2. args 不足 → None 返却 (スキップ)
`len(args) < 2` の場合は None を返し、コマンドリストへの追加をスキップ。
FRR への push は行われない。

#### 3. 既存セットの replace-all セマンティクス
更新時は先に既存の `bgp as-path access-list <name>` を `no` コマンドで削除してから再作成する。
つまり、メンバーの追加/削除ではなく常に全置換。途中の FRR コマンド失敗は syslog ERR に記録されるが処理は継続。

#### 4. FRR コマンド失敗時 → syslog ERR & continue
`frrcfgd` の共通ハンドラ部分で FRR コマンド実行に失敗した場合、`syslog.syslog(LOG_ERR, 'failed running BGP AS path set config command')` を出力して次のエントリへ continue。

#### 5. DEL 操作時の state 管理
DEL 時は `daemon.as_path_set_list.pop(as_set_name, None)` で内部キャッシュから除去。
存在しないキーを DEL しても KeyError にならない (pop の None デフォルト)。

#### 6. 初期ロード時の検証なし
起動時に `config_db.get_table('AS_PATH_SET')` で全エントリを読み込む際、`as_path_set_member` フィールドの存在のみをチェックし、メンバー値の正規表現検証は行わない (FRR 側がエラーを返す)。
