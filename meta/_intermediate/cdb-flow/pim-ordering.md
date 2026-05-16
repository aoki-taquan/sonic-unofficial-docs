# PIM_GLOBALS / PIM_INTERFACE — Phase B: 書込み順依存調査結果

調査日: 2026-05-16
対象ファイル:
- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`

---

## 1. 全体構造

`frrcfgd` (`BGPConfigDaemon`) が CONFIG_DB の `PIM_GLOBALS` および `PIM_INTERFACE` を購読し、
`bgp_table_handler_common` を通じて `__update_bgp()` で処理する（frrcfgd.py L2331-2332）。

処理フロー:
```
CONFIG_DB 更新 → bgp_table_handler_common → bgp_message queue
  → __update_bgp() → PIM_INTERFACE / PIM_GLOBALS 分岐 → key_map.run_command()
  → vtysh -c "configure terminal" -c "<cmd>" → pimd
```

## 2. `PIM_INTERFACE` における `mode` フィールドの必須性

frrcfgd.py L3787-3802:

```python
if 'mode' in data:
    modeval = data['mode']
    modeval_pim_mode = modeval.data
    modeval_op = modeval.op
    if (modeval_op == CachedDataWithOp.OP_DELETE):
        for dkey, dval in data.items():
            dval.status = CachedDataWithOp.STAT_SUCC
            dval.op = CachedDataWithOp.OP_DELETE
    if not key_map.run_command(self, table, data, cmd_prefix):
        syslog.syslog(syslog.LOG_ERR, 'failed running PIM config command')
        continue
```

`mode` が SET に含まれない場合、`key_map.run_command()` 自体が呼ばれない。
`dr-priority`, `hello-interval`, `bfd-enabled` を含む全フィールドが **silent drop** される。

## 3. `PIM_GLOBALS` の `ecmp-rebalance-enabled` 依存

`ecmp-rebalance-enabled = "true"` は `ecmp-enabled = "true"` を前提とする。
CONFIG_DB レベルの強制はなく、frrcfgd はそれぞれ独立したコマンドを発行する（frrcfgd.py L2068-2069）。
FRR pimd は ECMP が無効な状態では rebalance を無視する（FRR 実装依存）。

## 4. VRF 依存

`PIM_GLOBALS|<vrf>|<af>` および `PIM_INTERFACE|<vrf>|<af>|<interface>` はいずれも key に VRF 名を含む。
`frrcfgd` は VRF 存在確認を行わず、vtysh コマンドを直接発行する（frrcfgd.py L3805-3821）。
ただし FRR pimd がカーネルの VRF に対応した vrf コンテキストを持たない場合、
vtysh の `vrf <vrf>` コマンドが失敗し LOG_ERR が出力される。
実用上は `VRF|<vrf>` を先に設定しておくことが必要。

## 5. インタフェース依存

`PIM_INTERFACE|<vrf>|<af>|<interface>` の `<interface>` は、
vtysh コマンド `configure terminal` → `interface <if_name>` として発行される（frrcfgd.py L3778-3779）。
インタフェースが kernel 上に存在しない場合、FRR がコンテキスト生成に失敗して LOG_ERR となる可能性がある。
`PORT|<if>` / `VLAN|<vid>` 等のインタフェース設定を先行させること。

## 6. `PIM_GLOBALS` → `PIM_INTERFACE` の依存

`PIM_GLOBALS` と `PIM_INTERFACE` は互いに独立して frrcfgd が処理する（同一 bgp_message queue）。
PIM_INTERFACE の `mode = "sm"` を設定すると FRR で sparse-mode が有効化され、
その後 PIM_GLOBALS の `join-prune-interval` / `keep-alive-timer` 等がタイマーに反映される。
論理的には PIM_GLOBALS を先行させることが推奨されるが、frrcfgd はキューで逐次処理するため
到着順次第で中間状態（FRR デフォルト値で pimd が動作する区間）が生じ得る。

## 7. 削除順序

`PIM_INTERFACE` DEL:
- `mode = ""` (OP_DELETE) を含む場合、他フィールドのキャッシュをフラッシュ (`STAT_SUCC + OP_DELETE` に設定)
- `no ip pim` が発行され sparse-mode 無効化

`PIM_GLOBALS` DEL:
- 各フィールドが個別に `no ip pim <field>` として発行される

推奨削除順: `PIM_INTERFACE` の `mode` DEL → `PIM_INTERFACE` 全削除 → `PIM_GLOBALS` 全削除

## 8. まとめ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | `mode` を `PIM_INTERFACE` SET に含める | **必須**（欠如時 全フィールド silent drop） | なし |
| 2 | `VRF\|<vrf>` → `PIM_GLOBALS\|<vrf>\|...` / `PIM_INTERFACE\|<vrf>\|...` | 推奨先行 | VRF 欠如時 vtysh LOG_ERR |
| 3 | インタフェース先行 → `PIM_INTERFACE\|...\|<if>` | 推奨先行 | interface 未存在時 FRR LOG_ERR |
| 4 | `PIM_GLOBALS` 先行 → `PIM_INTERFACE` | 推奨（中間状態最小化） | FRR デフォルト値で動作継続 |
| 5 | `ecmp-enabled = "true"` → `ecmp-rebalance-enabled = "true"` | **必須**（FRR 実装依存で rebalance が無効化） | なし |
| 6 | `PIM_INTERFACE` DEL (mode) → `PIM_GLOBALS` DEL | 推奨（FRR 状態整合） | 逆順でも動作するが中間状態あり |
