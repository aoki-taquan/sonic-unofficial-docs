# BGP_PEER_RANGE テーブル 暗黙参照スキャン (Phase C)

`docs/reference/config-db/bgp-peer-range.md` の Phase C (暗黙参照) ブロック裏付け資料。

ソースは `bgpcfgd/managers_bgp.py`、`frrcfgd/frrcfgd.py`、`dockers/docker-fpm-frr/frr/bgpd/templates/dynamic/policies.conf.j2`。
`BGP_PEER_RANGE` テーブル変更時に `bgpcfgd` (`BGPPeerMgrBase`) が間接的に読み出す関連 CONFIG_DB テーブルを列挙する。

## スキャン手順

```
grep -nE 'CFG_DEVICE_METADATA_TABLE_NAME|BGP_GLOBALS|ROUTE_MAP|peer_group|deployment_id|BGP_BBR' \
    .cache/sonic-sources/sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py

grep -nE 'BGP_PEER_RANGE|BGP_GLOBALS|BGP_PEER_GROUP|ROUTE_MAP|DEVICE_METADATA' \
    .cache/sonic-sources/sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py

cat .cache/sonic-sources/sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/templates/dynamic/policies.conf.j2
```

## 検出された暗黙参照テーブル

### DEVICE_METADATA — bgp_asn・deployment_id・type の強制依存

`BGPPeerMgrBase.__init__()` が依存リスト (`deps`) に以下を登録する (managers_bgp.py:119-120)。

| フィールド | 参照タイミング | 必須度 | evidence |
|---|---|---|---|
| `localhost/bgp_asn` | `add_peer()` / `del_handler()` — `router bgp <asn>` コマンド生成 | 必須 | managers_bgp.py:119,192,501 |
| `localhost/type` | `add_peer()` の `kwargs` 経由でテンプレートに渡す | 必須 | managers_bgp.py:120,205 |
| `localhost/deployment_id` | `constants.bgp.use_deployment_id=true` の場合のみ dep 追加 | 条件付き必須 | managers_bgp.py:135-143 |
| `localhost/bgp_router_id` | Loopback0 IPv4 未設定時の fallback チェック | 準必須 | managers_bgp.py:186-188 |

`bgp_asn` が未設定だと `get_slot()["localhost"]["bgp_asn"]` が `KeyError` → `log_err` + `return True` (drop)。

### BGP_PEER_GROUP — 動的 peer-group の事前定義依存

`BGPPeerGroupMgr.update_pg()` が `managers_bgp.py:227` で呼ばれ、FRR に peer-group を定義してから `bgp listen range <prefix> peer-group <name>` を発行する。FRR 上に peer-group が存在しない状態で listen range を設定しようとすると FRR がエラーを返す。

CONFIG_DB の `BGP_PEER_GROUP` テーブルは `bgpcfgd` の別 Manager が管理するが、`BGP_PEER_RANGE` の設定は peer-group が事前定義済みであることを暗黙に前提とする。

| 参照形式 | 場所 | evidence |
|---|---|---|
| FRR peer-group 定義 (`peer-group.conf.j2` レンダリング) | `BGPPeerGroupMgr.update_pg()` | managers_bgp.py:27,61,156,227 |
| `no bgp listen range <prefix> peer-group <name>` 削除 | `del_handler()` の `"no listen range"` テンプレート | managers_bgp.py:109,467 |

### ROUTE_MAP — `FROM_BGP_SPEAKER` / `TO_BGP_SPEAKER` ハードコード参照

`dynamic/policies.conf.j2` が `bgpcfgd` テンプレートエンジン起動時に FRR に適用される。`BGP_PEER_RANGE` の peer-group には以下の route-map が**ハードコードで**適用される (CONFIG_DB に対応する `ROUTE_MAP` テーブルエントリは不要だが、route-map 名が固定であるため外部から変更できない)。

```
route-map FROM_BGP_SPEAKER permit 10
route-map TO_BGP_SPEAKER deny 1
```

| route-map | 方向 | 効果 | evidence |
|---|---|---|---|
| `FROM_BGP_SPEAKER` | inbound | dynamic neighbor からの経路を permit | dynamic/policies.conf.j2:4 |
| `TO_BGP_SPEAKER` | outbound | dynamic neighbor への経路広告を deny | dynamic/policies.conf.j2:6 |

### BGP_GLOBALS — frrcfgd.py 経由の間接参照

`frrcfgd.py` では `BGP_GLOBALS` と `BGP_GLOBALS_LISTEN_PREFIX` を `bgpd` に適用する管理テーブルとして登録している (frrcfgd.py:81,92)。`BGP_PEER_RANGE` が有効になる前提として `BGP_GLOBALS` で `router bgp <asn>` インスタンスが確立済みである必要がある。

| テーブル | 用途 | evidence |
|---|---|---|
| `BGP_GLOBALS` | BGP router インスタンス (`router bgp <asn>`) 確立 | frrcfgd.py:81,1806 |
| `BGP_GLOBALS_LISTEN_PREFIX` | `bgp listen range <prefix> peer-group <pg>` 直接管理 (frrcfgd 経由) | frrcfgd.py:92,1972 |

> **注**: `BGP_GLOBALS_LISTEN_PREFIX` は `BGP_PEER_RANGE` と**同一機能を別パス**で実現する。`bgpcfgd` (`managers_bgp.py`) と `frrcfgd` (`frrcfgd.py`) の両方が listen-range を FRR に投入できる構造になっている。

## まとめ

| 参照先 | DB | 参照方向 | YANG leafref | 必須度 | evidence |
|---|---|---|---|---|---|
| `DEVICE_METADATA\|localhost` (`bgp_asn`) | CONFIG_DB | 読み取り | なし | 必須 | managers_bgp.py:119,192,501 |
| `DEVICE_METADATA\|localhost` (`deployment_id`) | CONFIG_DB | 読み取り | なし | 条件付き必須 | managers_bgp.py:135-143 |
| `BGP_PEER_GROUP\|<vrf>\|<name>` | CONFIG_DB | 事前定義前提 | なし | 実質必須 | managers_bgp.py:156,227 |
| `ROUTE_MAP` (FROM_BGP_SPEAKER / TO_BGP_SPEAKER) | — (FRR 内部) | ハードコード適用 | なし | 固定 | dynamic/policies.conf.j2:4,6 |
| `BGP_GLOBALS` | CONFIG_DB | router bgp 確立前提 | なし | 実質必須 | frrcfgd.py:81 |
