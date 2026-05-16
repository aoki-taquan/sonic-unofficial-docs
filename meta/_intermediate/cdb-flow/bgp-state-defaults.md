# bgp-state Phase A — STATE_DB BGP フィールドのコード由来デフォルト

## 対象ページ

`docs/reference/config-db/bgp-state.md`

## 対象テーブル

- `STATE_DB.NEIGH_STATE_TABLE`
- `STATE_DB.BGP_PEER_CONFIGURED_TABLE`

---

## Phase A: コード精読による default 特定

### ソース一次調査

**1. bgpmon.py — NEIGH_STATE_TABLE の書き込み元**

- ファイル: `sonic-buildimage/src/sonic-bgpcfgd/bgpmon/bgpmon.py`
- L70-76 `update_new_peer_states`:
  ```python
  self.new_peer_state[peer] = (peer_dict["peers"][peer]["state"],
                               peer_dict["peers"][peer]["remoteAs"],
                               peer_dict["peers"][peer]["localAs"])
  ```
- L163, L171 `update_neigh_states`:
  ```python
  peerType = "i-BGP" if self.new_peer_state[peer][1] == self.new_peer_state[peer][2] else "e-BGP"
  data[key] = {'state':state, 'peerType':peerType}
  ```
- L51: `self.db.delete_all_by_pattern(self.db.STATE_DB, "NEIGH_STATE_TABLE|*")` — 起動時全削除
- ポーリング間隔: `time.sleep(15)` — 15 秒周期

**2. managers_bgp.py — BGP_PEER_CONFIGURED_TABLE の書き込み元**

- ファイル: `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py`
- L286-289:
  ```python
  state_db = swsscommon.DBConnector("STATE_DB", 0)
  state_peer_table = swsscommon.Table(state_db, swsscommon.STATE_BGP_PEER_CONFIGURED_TABLE_NAME)
  state_peer_table.set(key, list(sorted(data.items())))
  ```
  - `data` は CONFIG_DB から渡されたネイバー設定の dict
  - フィールドは CONFIG_DB の内容をそのまま転写（固定デフォルトなし）

**3. schema.h — テーブル名定義**

- `STATE_BGP_PEER_CONFIGURED_TABLE_NAME = "BGP_PEER_CONFIGURED_TABLE"` (L511)

**4. HLD 参照**

- `snmp_ciscobgp4mib.md`: NEIGH_STATE_TABLE スキーマ定義
  ```
  NEIGH_STATE_TABLE {
      "<neigh_ip>" {
          "State" : "Idle/Idle (Admin)/Connect/Active/OpenSent/OpenConfirm/Established/Clearing"
      }
  }
  ```
  ※ 実装では `state` (小文字) を使用 (bgpmon.py L164)
- `Bgpcfgd-dyn-peer-modification-support.md`: BGP_PEER_CONFIGURED_TABLE スキーマ定義

---

## フィールド一覧とデフォルト値まとめ

### NEIGH_STATE_TABLE

| フィールド | 型 | デフォルト/初期値 | ソース |
|-----------|----|-----------------|----|
| `state` | string | FRR の BGP セッション状態 (固定デフォルトなし) | bgpmon.py L74 |
| `peerType` | string | `"i-BGP"` (remoteAs==localAs) / `"e-BGP"` (それ以外) | bgpmon.py L163, L171 |

### BGP_PEER_CONFIGURED_TABLE

| フィールド | 型 | デフォルト/初期値 | ソース |
|-----------|----|-----------------|----|
| 全フィールド | CONFIG_DB と同じ | CONFIG_DB の値をそのまま転写 | managers_bgp.py L289 |

---

## 特記事項

1. `NEIGH_STATE_TABLE` には YANG schema が存在しない。定義は HLD と bgpmon.py コードのみ。
2. bgpmon 起動時の全削除により、コンテナ再起動直後は最大 15 秒間エントリが空になる。
3. `peerType` フィールドは HLD (snmp_ciscobgp4mib.md) には記載されていないが、実装 (bgpmon.py L163, L171) に存在する。SNMP エージェント実装 (bgp4.py) では `peerType` を参照しておらず `state` のみ使用する。
4. `BGP_PEER_CONFIGURED_TABLE` は SDN コントローラ向けの設定完了確認テーブル。フィールドセットはピアタイプ (static/dynamic) によって異なる。

---

## 実装確認結果

- verification: code-verified
- discrepancy: なし (HLD スキーマと実装が一致。ただし HLD の `State` (大文字) vs 実装の `state` (小文字) の表記差あり)
