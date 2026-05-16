# BGP_PEER_CONFIGURED_TABLE — Phase B 書込み順依存 調査メモ

対象ページ: `docs/reference/config-db/bgp-state.md`
調査日: 2026-05-16

## 調査対象ファイル

| ファイル | 役割 |
|---------|------|
| `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py` | `BGPPeerMgrBase` — `update_state_db()` の SET/DEL 書込み実装 |
| `sonic-buildimage/src/sonic-bgpcfgd/bgpmon/bgpmon.py` | `bgpmon` — `NEIGH_STATE_TABLE` の書込み実装 |

## 検出した書込み順依存

### 1. SET: FRR push 成功後にのみ STATE_DB へ書き込む（最重要依存）

`add_peer()` (managers_bgp.py:229-239):

```python
if cmd is not None:
    self.apply_op(cmd, vrf)          # FRR へコマンドを push
    key = (vrf, nbr)
    self.peers.add(key)
    self.update_state_db(vrf, nbr, data, "SET")   # STATE_DB への書き込みは FRR push 後
    log_info("Peer '(%s|%s)' has been scheduled to be added with attributes '%s'" % print_data)
```

`apply_op` は `self.cfg_mgr.push(cmd)` を呼び FRR へコマンドを送信する（managers_bgp.py:507）。
`update_state_db(..., "SET")` の呼び出しは `apply_op` の **直後** に固定されており、`cmd is not None`（FRR 設定生成に成功）した場合のみ実行される。

FRR テンプレートのレンダリングエラー（`jinja2.TemplateError`）が発生した場合は `return True` するが `update_state_db` は呼ばれない（managers_bgp.py:231-234）。

- **順序制約**: `apply_op`（FRR push） → `update_state_db SET`（STATE_DB 書き込み）
- **違反時の挙動**: テンプレートエラー時は FRR・STATE_DB ともに更新されない。apply_op 内で vtysh 異常が発生しても return True するため STATE_DB は書き込まれる（vtysh の失敗はログのみ）。
- evidence: managers_bgp.py:229-239

### 2. admin_status 変更: FRR push 成功確認後に STATE_DB 更新

`apply_admin_status()` (managers_bgp.py:341-356):

```python
ret_code = self.apply_op(self.templates[template_name].render(neighbor_addr=nbr), vrf)
if ret_code:
    self.update_state_db(vrf, nbr, data, "SET")   # ret_code=True のときのみ書き込む
    log_info("Peer '%s|%s' admin state is set to '%s'" % print_data)
else:
    log_err("Can't set peer '%s|%s' admin state to '%s'." % print_data)
```

`apply_op` は常に `True` を返すため（managers_bgp.py:508）、実質的にはネイバー追加と同様に FRR push 直後に STATE_DB が更新される。ただし `apply_op` が例外を投げた場合は更新されない。

- **順序制約**: FRR push（admin_status 変更） → STATE_DB SET の順。
- evidence: managers_bgp.py:341-356, 494-508

### 3. DEL: FRR push 成功後に STATE_DB からエントリを削除

`del_handler()` (managers_bgp.py:485-488):

```python
ret_code = self.apply_op(cmd, vrf)
if ret_code:
    self.update_state_db(vrf, nbr, {}, "DEL")   # FRR 側からネイバーを除去後に STATE_DB を削除
    log_info("Peer '(%s|%s)' has been removed" % (vrf, nbr))
    self.peers.remove(peer_key)
```

DEL 操作では:
1. （dynamic/sentinels のみ）`no bgp listen range ...` を先に FRR へ送信（FRR 10.1 以降の要件）
2. `no neighbor <addr>` を FRR へ push（`apply_op`）
3. **FRR push 成功後**（`ret_code=True`）に `update_state_db(..., "DEL")` を呼び STATE_DB のエントリを削除

`update_state_db` の DEL 側は `state_peer_table.get(key)` で存在確認してから `delete(key)` を呼ぶ（managers_bgp.py:292-295）。エントリが存在しない場合は `log_warn` のみで実際には何もしない。

- **順序制約**: FRR から `no neighbor` push → STATE_DB DEL の順。逆順（STATE_DB を先に削除してから FRR 操作）は起こらない。
- evidence: managers_bgp.py:459-489

### 4. DEL 前の listen range 除去（dynamic ピアのみ）

`del_handler()` (managers_bgp.py:461-472):

```python
if self.peer_type == 'dynamic' or self.peer_type == 'sentinels':
    ip_ranges = self.directory.get(self.db_name, self.table_name, vrf + '|' + nbr).get("ip_range")
    if ip_ranges is not None:
        ip_ranges = ip_ranges.split(',')
        for ip_range in ip_ranges:
            cmd = self.templates["no listen range"].render(ip_range=ip_range, peer_group=nbr)
            ret_code = self.apply_op(cmd, vrf)
```

FRR 10.1 以降、`listen range` が設定されたピアグループを削除するには先に listen range を除去する必要がある。STATE_DB の `BGP_PEER_CONFIGURED_TABLE` は listen range 除去 → peer group 削除 → STATE_DB DEL の順で更新される。

- **順序制約**: FRR `no bgp listen range` → FRR `no neighbor`（peer group 削除） → STATE_DB DEL
- evidence: managers_bgp.py:456-472, FRR 10.1 変更点

### 5. bgpmon: NEIGH_STATE_TABLE は起動時全削除後に再構築

`BgpStateGet.__init__()` (bgpmon.py:51):
```python
self.db.delete_all_by_pattern(self.db.STATE_DB, "NEIGH_STATE_TABLE|*")
```

bgpmon 起動時に全エントリを削除してから再スキャンする。したがって `NEIGH_STATE_TABLE` と `BGP_PEER_CONFIGURED_TABLE` は独立した書き込みデーモンが管理しており、両テーブル間の書込み順序依存はない。

- **順序制約**: NEIGH_STATE_TABLE と BGP_PEER_CONFIGURED_TABLE の書込み順序は互いに独立
- evidence: bgpmon.py:51

### 6. config reload 時: BGP_PEER_CONFIGURED_TABLE の全削除

`sonic-utilities/config/main.py:1613` (config reload 処理):
```python
# BGP_PEER_CONFIGURED_TABLE|* を全削除してから bgpcfgd が再投入する
```

`config reload` では CONFIG_DB の書き換えの前後で `BGP_PEER_CONFIGURED_TABLE|*` が全削除される。bgpcfgd が再起動して CONFIG_DB を replay するまでの間（数秒〜数十秒）、このテーブルのエントリは存在しない。SDN コントローラがこのテーブルを設定完了の目印として使う場合、reload 中の一時的な全エントリ消滅に注意が必要。

- **順序制約**: config reload → BGP_PEER_CONFIGURED_TABLE 全削除 → bgpcfgd 再起動 → 各ネイバー SET（FRR push 後）
- evidence: config/main.py:1613

## 順序依存サマリ

| # | 依存関係 | 方向 | 対象操作 | 違反時の挙動 |
|---|----------|------|---------|------------|
| 1 | FRR push（ネイバー追加） → STATE_DB SET | 強制後行 | add_peer / SET handler | テンプレートエラー時は STATE_DB 未書込（FRR も未設定） |
| 2 | FRR push（admin_status 変更） → STATE_DB SET | 強制後行 | change_admin_status | apply_op 例外時は STATE_DB 未更新 |
| 3 | FRR `no neighbor` → STATE_DB DEL | 強制後行 | del_handler / DEL handler | FRR から除去前に SDN が STATE_DB を参照するとエントリがまだ存在している |
| 4 | FRR `no listen range` → FRR `no neighbor` → STATE_DB DEL | 強制後行（dynamic のみ） | del_handler (dynamic/sentinels) | listen range 除去なしに peer group を削除すると FRR 10.1 以降はエラー |
| 5 | NEIGH_STATE_TABLE と BGP_PEER_CONFIGURED_TABLE は独立 | 無関係 | 全操作 | 両テーブルの書込み順序制約なし |
| 6 | config reload → 全削除 → bgpcfgd 再投入 | 一時断 | config reload | reload 中は SDN コントローラから見てエントリが存在しない |
