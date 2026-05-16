# BGP_MONITORS — Phase A: 暗黙デフォルト調査メモ

作成: 2026-05-14  
対象: `docs/reference/config-db/bgp-monitors.md`

## 調査方法

1. entry grep 1回: `grep -rln "BGP_MONITORS" .cache/sonic-sources/`
2. 以下ファイルを全行精読:
   - `sonic-bgp-monitor.yang`
   - `sonic-bgp-common.yang` (grouping `sonic-bgp-cmn-neigh`)
   - `bgpcfgd/managers_bgp.py` (597 行)
   - `bgpcfgd/main.py` (L89: monitors 登録)
   - `bgpd/templates/monitors/instance.conf.j2`
   - `bgpd/templates/monitors/peer-group.conf.j2`
   - `bgpd/templates/monitors/policies.conf.j2`
   - `tests/data/monitors/instance.conf/param_all.json` + result
   - `tests/data/monitors/peer-group.conf/param_all.json` + results
   - `constants.yml` (monitors peer_type 設定)

## フィールド一覧 (sonic-bgp-cmn-neigh)

| フィールド | YANG type | YANG default | 備考 |
|-----------|-----------|-------------|------|
| `addr` (key) | inet:ip-address | — | key フィールド |
| `name` | string | — | BGPMonitor 固定 (must 制約) |
| `asn` | uint32 0..4294967295 | — | 必須ではない (YANG mandatory なし) |
| `holdtime` | uint16 | — | YANG default なし |
| `keepalive` | uint16 | — | YANG default なし |
| `local_addr` | inet:ip-address | — | YANG default なし; 欠如時は warn のみ |
| `nhopself` | uint8 0..1 | — | YANG default なし |
| `rrclient` | uint8 0..1 | — | YANG default なし |
| `admin_status` | admin_status (up/down) | — | YANG default なし |

## 暗黙デフォルト（コード由来）

### instance.conf.j2 ハードコード値

テンプレートが CONFIG_DB フィールドに依存せず固定値を注入する:

| FRR コマンド | 由来 | 証跡 |
|------------|------|------|
| `neighbor <addr> remote-as <bgp_asn>` | DEVICE_METADATA localhost/bgp_asn から取得 | instance.conf.j2:4 |
| `neighbor <addr> peer-group BGPMON` | peer_group 固定 `BGPMON` | instance.conf.j2:5 |
| `neighbor <addr> activate` (IPv4 + IPv6 両方) | 無条件に有効化 | instance.conf.j2:7,9 |

### peer-group.conf.j2 ハードコード値

| FRR コマンド / 挙動 | 条件 | 証跡 |
|-------------------|------|------|
| `neighbor BGPMON update-source Loopback4096` | switch_type=voq または chassisdb.conf 存在 | peer-group.conf.j2:10 |
| `neighbor BGPMON update-source <lo0_ipv4>` | loopback0_ipv4 が存在する (通常ケース) | peer-group.conf.j2:12 |
| update-source なし | Loopback0 IPv4 未設定 (`result_without_lo0_ipv4.conf` で確認) | peer-group.conf.j2:9-13 |
| `maximum-prefix 1` | IPv4 AF に無条件適用 | peer-group.conf.j2:20 |
| `maximum-prefix 1` (IPv6) | VoQ/chassis-packet のみ | peer-group.conf.j2:29 |
| `route-map FROM_BGPMON in` | 無条件 (policies.conf.j2: deny 10) | peer-group.conf.j2:17 |
| `route-map TO_BGPMON out` | 無条件 (policies.conf.j2: permit 10) | peer-group.conf.j2:18 |
| `send-community` | 無条件 | peer-group.conf.j2:19 |

### policies.conf.j2 固定ルート

| route-map | アクション | 証跡 |
|-----------|---------|------|
| `FROM_BGPMON` | deny 10 (全受信拒否) | policies.conf.j2:4 |
| `TO_BGPMON` | permit 10 (全送信許可) | policies.conf.j2:6 |

### managers_bgp.py ランタイム挙動

| 挙動 | デフォルト/フォールバック | 証跡 |
|------|----------------------|------|
| `local_addr` 欠如 | `log_warn` のみ、処理続行 (interface 紐付けなし) | L194-195 |
| `name` 欠如 | `tag = nbr` (IP アドレスをタグに使用) | L226 |
| `check_neig_meta=False` | DEVICE_NEIGHBOR_METADATA チェックをスキップ | main.py:L89 |
| `bgp suppress-fib-pending` | 全 vrf に無条件注入 | apply_op() L502-504 |

### YANG default vs 実装 discrepancy

| フィールド | YANG | 実装 | 乖離 |
|-----------|------|------|------|
| `admin_status` | デフォルトなし | 欠如しても peer 追加は続行 (shutdown コマンドなし) | soft discrepancy: YANG は up/down 必須を強制しないが、実装は欠如時でも `up` 扱い相当 |
| `local_addr` | 必須なし | 欠如時 warn のみ→ update-source 設定なし | YANG は optional、実装も optional だが FRR の update-source が未設定になる |
| `asn` | 0..4294967295 (0 許可) | instance.conf.j2 は `remote-as <bgp_asn>` を DEVICE_METADATA から取得 (CONFIG_DB の `asn` フィールドは使わない) | **重大 discrepancy**: CONFIG_DB の `asn` フィールドは FRR 設定に反映されない。remote-as は常にローカル ASN |

## 重大発見: `asn` フィールドの非使用

`sonic-bgp-cmn-neigh` grouping の `asn` フィールドは CONFIG_DB に書けるが、
`instance.conf.j2` では `bgp_asn`（= `DEVICE_METADATA/localhost/bgp_asn`）を使う:

```
neighbor {{ neighbor_addr }} remote-as {{ bgp_asn }}
```

CONFIG_DB の `BGP_MONITORS|<addr>|asn` は **bgpcfgd に無視される**。
テスト `param_all.json` に `asn` フィールドなし (`bgp_asn: "555"` のみ) で確認済み。

## 結論

- YANG default は全フィールド未設定
- 実装デフォルト: `remote-as` = DEVICE_METADATA bgp_asn、`maximum-prefix` = 1、`send-community` 有効、FROM_BGPMON deny / TO_BGPMON permit 固定
- CONFIG_DB `asn` フィールドは実装上 dead field
- `admin_status` 欠如は `up` 相当動作
- `local_addr` 欠如は update-source 未設定（warn のみ）
