# PEER_SWITCH — Phase 6/7/8 中間ファイル

生成日: 2026-05-14 (batch cdb_batch_3)

<!-- derivation -->
## Phase 6: 自動派生代入スキャン

### minigraph.py — PEER_SWITCH 自動生成

```
# minigraph.py:2186
results['PEER_SWITCH'], mux_tunnel_name, peer_switch_ip = \
    get_peer_switch_info(linkmetas, devices)

# minigraph.py:2193 (クロス派生)
results['DEVICE_METADATA']['localhost']['peer_switch'] = \
    list(results['PEER_SWITCH'].keys())[0]
```

minigraph XML の `<PeerSwitch>` タグから `address_ipv4` を抽出し自動登録。DEVICE_METADATA の `peer_switch` フィールドも連動設定。

### config_samples.py — PEER_SWITCH 自動生成

```
# config_samples.py:232
data['PEER_SWITCH'] = {peer_switch_name: {'address_ipv4': peer_switch_ip}}
```

### db_migrator.py / init_cfg.json.j2 — 該当なし

<!-- /derivation -->

<!-- derivation -->
## Phase 7: 条件付き manager/orch 登録

MuxOrch (常時登録) が PEER_SWITCH テーブルを参照して対向スイッチの IP 取得。PEER_SWITCH エントリ不在時は DualToR モードを無効化。条件付き登録なし。

<!-- /derivation -->

<!-- handler-branching -->
## Phase 8: manager メソッド内 early return / dispatch

### MuxOrch — PEER_SWITCH ハンドラ

| 操作 | 処理 |
|------|------|
| SET | tunnel エンドポイントとして登録 |
| DEL | tunnel エンドポイント削除、MUX_CABLE の standby 転送停止 |

early return: `address_ipv4` フィールド欠如 → エントリ無効として return。

<!-- /handler-branching -->
