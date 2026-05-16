# BREAKOUT_CFG テーブル 暗黙参照スキャン (Phase C)

`docs/reference/config-db/breakout-cfg.md` の Phase C (暗黙参照) ブロック裏付け資料。

ソースは `sonic-utilities/config/main.py` (breakout CLI パス)、`sonic-utilities/config/config_mgmt.py` (ConfigMgmtDPB)、および `sonic-buildimage/src/sonic-yang-models/yang-models/*.yang` の leafref 解析。

## スキャン手順

```bash
# YANG leafref で PORT を参照するテーブル一覧
grep -rn "path.*PORT_LIST.*name" \
    .cache/sonic-sources/sonic-buildimage/src/sonic-yang-models/yang-models/*.yang \
  | grep -v "PORTCHANNEL\|MGMT_PORT" | sed 's|.*/\([^/]*\.yang\):.*|\1|' | sort -u

# YANG モデルなしテーブルへの警告パス
grep -n "tablesWithOutYang\|breakout_warnUser_extraTables" \
    .cache/sonic-sources/sonic-utilities/config/config_mgmt.py \
    .cache/sonic-sources/sonic-utilities/config/main.py

# 依存解決ロジック
grep -n "find_data_dependencies\|_deletePorts\|breakOutPort\|deps" \
    .cache/sonic-sources/sonic-utilities/config/config_mgmt.py | head -40
```

## 検出された暗黙参照テーブル

### A. YANG leafref 依存による cascade 削除対象 (YANG モデルあり)

DPB (`breakOutPort()`) は `ConfigMgmtDPB._deletePorts()` 内で `SonicYang.find_data_dependencies()` を呼び出す。この関数は YANG の `leafref` を辿って `PORT` を参照している全エントリを検出し、削除対象ポートに依存するエントリを返す (`config_mgmt.py` L488-495)。

`force=False` 時は依存一覧を表示して中断、`force=True`（`--force-remove-dependencies`）時はこれらを **cascade 削除** してから PORT エントリ自体を削除する。

| テーブル (YANG) | YANG ファイル | leafref パス | 削除契機 |
|---|---|---|---|
| `PORT` | `sonic-port.yang` | — | 親テーブル。breakout 時に子ポートを del/add |
| `BUFFER_PG` | `sonic-buffer-pg.yang` L43 | `/prt:sonic-port/prt:PORT/prt:PORT_LIST/prt:name` | 対象ポートの BUFFER_PG エントリが cascade 削除 |
| `BUFFER_QUEUE` | `sonic-buffer-queue.yang` L51 | `/prt:sonic-port/prt:PORT/prt:PORT_LIST/prt:name` | 対象ポートの BUFFER_QUEUE エントリが cascade 削除 |
| `INTERFACE` | `sonic-interface.yang` L58, L128 | `/port:sonic-port/port:PORT/port:PORT_LIST/port:name` | INTERFACE / INTERFACE_IPPREFIX エントリが cascade 削除 |
| `VLAN_MEMBER` | `sonic-vlan.yang` L292 | `/port:sonic-port/port:PORT/port:PORT_LIST/port:name` | VLAN_MEMBER_LIST エントリが cascade 削除 |
| `PORT_QOS_MAP` | `sonic-port-qos-map.yang` L78 | `/prt:sonic-port/prt:PORT/prt:PORT_LIST/prt:name` | QoS マッピングエントリが cascade 削除 |
| `BUFFER_PORT_INGRESS_PROFILE_LIST` | `sonic-buffer-port-ingress-profile-list.yang` L41 | `/prt:sonic-port/prt:PORT/prt:PORT_LIST/prt:name` | cascade 削除 |
| `BUFFER_PORT_EGRESS_PROFILE_LIST` | `sonic-buffer-port-egress-profile-list.yang` L41 | `/prt:sonic-port/prt:PORT/prt:PORT_LIST/prt:name` | cascade 削除 |
| `PFC_WD` | `sonic-pfcwd.yang` L38 | `/port:sonic-port/port:PORT/port:PORT_LIST/port:name` | PFC Watchdog エントリが cascade 削除 |
| `QUEUE` | `sonic-queue.yang` L67 | `/port:sonic-port/port:PORT/port:PORT_LIST/port:name` | QUEUE エントリが cascade 削除 |
| `CABLE_LENGTH` | `sonic-cable-length.yang` L47 | `/port:sonic-port/port:PORT/port:PORT_LIST/port:name` | ポート単位ケーブル長エントリが cascade 削除 |
| `STORM_CONTROL` | `sonic-storm-control.yang` L41 | `/prt:sonic-port/prt:PORT/prt:PORT_LIST/prt:name` | ストームコントロールエントリが cascade 削除 |
| `LLDP_PORT_TABLE` | `sonic-lldp.yang` L109 | `/prt:sonic-port/prt:PORT/prt:PORT_LIST/prt:name` | LLDP ポート設定が cascade 削除 |
| `DEVICE_NEIGHBOR` | `sonic-device_neighbor.yang` L55 | `/port:sonic-port/port:PORT/port:PORT_LIST/port:name` | 隣接デバイス情報が cascade 削除 |
| `SFLOW` (port sampler) | `sonic-sflow.yang` L110 | `/port:sonic-port/port:PORT/port:PORT_LIST/port:name` | sFlow ポートサンプラーエントリが cascade 削除 |
| `BGP_NEIGHBOR` | `sonic-bgp-neighbor.yang` L85 | `/port:sonic-port/port:PORT/port:PORT_LIST/port:name` | BGP neighbor の `local_addr` が port 指定の場合に cascade 削除 |
| `MIRROR_SESSION` | `sonic-mirror-session.yang` L149 | `/port:sonic-port/port:PORT/port:PORT_LIST/port:name` | ミラーセッションの `dst_port` が対象ポートの場合に cascade 削除 |

### B. YANG モデルなしテーブル — ユーザー警告対象 (extraTables)

YANG モデルが存在しないテーブルは `SonicYang.tablesWithOutYang` に収集され、`breakout_warnUser_extraTables()` (config/main.py:239) が該当ポートのエントリを持つ場合にユーザーへの確認プロンプトを表示する。自動削除はされない。

代表的な「YANG なしテーブル」:

| テーブル | 理由 | DPB での挙動 |
|---|---|---|
| `ACL_TABLE` | YANG モデル未実装 | ポートが `ACL_TABLE.ports` に含まれる場合、ユーザーに警告して確認要求。削除は行われない（手動対応必要） |
| `ACL_RULE` | 同上 | 同上（`ACL_TABLE` 依存で同時に警告対象になる可能性あり） |
| `MUX_CABLE` | YANG モデルなし | 該当ポートがある場合に警告 |
| `FLEX_COUNTER_TABLE` | YANG モデルなし | 同上 |

> `tablesWithOutYang` の具体的なリストはランタイムの CONFIG_DB に読み込まれたテーブルに依存する。上記は代表例。`ACL_TABLE` が最もよく遭遇する。

### C. 再作成時の参照先 (PORT 追加フェーズ)

breakout 後の新しい子ポートが PORT に追加されると、`loadDefConfig=True` 指定時に `_addPorts()` がデフォルト設定を注入する。この際に以下が暗黙的に再作成される:

| テーブル | 再作成契機 | ソース |
|---|---|---|
| `PORT` | 新子ポートのエントリを `platform.json` から生成 | `config_mgmt.py` L533, `portconfig.py` L350-390 |
| `BUFFER_PG` / `BUFFER_QUEUE` | `loadDefConfig=True` の場合、デフォルトバッファ設定が再注入 | `portconfig.py` (デフォルト設定 JSON) |

## まとめ — `breakout-cfg.md` Phase C 記載対象

| カテゴリ | テーブル |
|---|---|
| cascade 削除（YANG leafref、force 時） | `BUFFER_PG` / `BUFFER_QUEUE` / `INTERFACE` / `VLAN_MEMBER` / `PORT_QOS_MAP` / `BUFFER_PORT_INGRESS_PROFILE_LIST` / `BUFFER_PORT_EGRESS_PROFILE_LIST` / `PFC_WD` / `QUEUE` / `CABLE_LENGTH` / `STORM_CONTROL` / `LLDP_PORT_TABLE` / `DEVICE_NEIGHBOR` / `SFLOW` / `BGP_NEIGHBOR` / `MIRROR_SESSION` |
| 警告のみ（YANG モデルなし、手動対応必要） | `ACL_TABLE` / `ACL_RULE` / `MUX_CABLE` 他 |
| 再作成（PORT 追加フェーズ） | `PORT` / `BUFFER_PG` / `BUFFER_QUEUE` (デフォルト設定) |

## 検証コマンド

```bash
# YANG leafref で PORT を参照するファイル一覧
grep -rn "path.*PORT_LIST.*name" \
    .cache/sonic-sources/sonic-buildimage/src/sonic-yang-models/yang-models/*.yang \
  | grep -v "PORTCHANNEL\|MGMT_PORT" | sed 's|.*/\([^/]*\.yang\):.*|\1|' | sort -u

# cascade 削除ロジック
grep -n "_deletePorts\|find_data_dependencies\|deleteNode\|deps" \
    .cache/sonic-sources/sonic-utilities/config/config_mgmt.py

# extraTables 警告パス
grep -n "tablesWithOutYang\|breakout_warnUser" \
    .cache/sonic-sources/sonic-utilities/config/main.py \
    .cache/sonic-sources/sonic-utilities/config/config_mgmt.py
```

このスキャン結果から派生して `docs/reference/config-db/breakout-cfg.md` の `<!-- cross-refs -->` ブロックを生成する。
