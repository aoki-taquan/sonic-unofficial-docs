# BGP_MONITORS — Phase E: ハードコード定数調査

## 対象ファイル

- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py` — peer 追加・更新・削除ロジック
- `sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/templates/monitors/peer-group.conf.j2` — peer-group 定義テンプレート
- `sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/templates/monitors/instance.conf.j2` — 隣接インスタンス定義テンプレート
- `sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/templates/monitors/policies.conf.j2` — route-map 定義テンプレート
- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py` — BGP_MONITORS 定数なし（frrcfgd は monitors を直接処理しない）

---

## 1. peer-group 名（ハードコード）

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| peer-group 名 | `BGPMON` | monitors タイプの BGP 隣接が所属する peer-group。CONFIG_DB から取得されず、テンプレートに直書き | `peer-group.conf.j2:8`, `instance.conf.j2:5` |

**証跡**:
- `peer-group.conf.j2` L8: `neighbor BGPMON peer-group`
- `instance.conf.j2` L5: `neighbor {{ neighbor_addr }} peer-group BGPMON`

---

## 2. route-map 名（ハードコード）

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| 受信 route-map 名 | `FROM_BGPMON` | monitors peer への in-bound route-map（deny 10 = 全経路拒否） | `policies.conf.j2:4`, `peer-group.conf.j2:17` |
| 送信 route-map 名 | `TO_BGPMON` | monitors peer への out-bound route-map（permit 10 = 全経路許可） | `policies.conf.j2:6`, `peer-group.conf.j2:18` |

**証跡**:
- `policies.conf.j2` L4: `route-map FROM_BGPMON deny 10`
- `policies.conf.j2` L6: `route-map TO_BGPMON permit 10`
- `peer-group.conf.j2` L17-18: `neighbor BGPMON route-map FROM_BGPMON in` / `neighbor BGPMON route-map TO_BGPMON out`

---

## 3. address-family / maximum-prefix 固定値

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| IPv4 maximum-prefix | `1` | monitors peer-group に対して受信経路数を 1 に制限（実質全拒否の二重保護） | `peer-group.conf.j2:20` |
| IPv6 maximum-prefix | `1` | chassis/voq 環境での IPv6 AF でも同値適用 | `peer-group.conf.j2:29` |
| send-community | 無条件有効 | `neighbor BGPMON send-community` — CONFIG_DB フィールドなし | `peer-group.conf.j2:19,28` |

---

## 4. update-source（環境依存ハードコード）

| 条件 | 固定値 | ソース |
|------|--------|--------|
| `switch_type == 'voq'` または chassisdb.conf 存在 | `Loopback4096` | `peer-group.conf.j2:10` |
| 通常環境（Loopback0 IPv4 存在） | `loopback0_ipv4`（実行時変数） | `peer-group.conf.j2:12` |

> **注意**: `Loopback4096` は VoQ / chassis 環境専用の固定インターフェース名。CONFIG_DB フィールドから取得されない。

---

## 5. name フィールド固定値（YANG `must` 制約）

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `name` フィールド制約 | `BGPMonitor` | YANG `must "current() = 'BGPMonitor'"` により CONFIG_DB 書き込み時に強制。bgpcfgd 側での追加チェックなし | `sonic-bgp-monitor.yang:41` |

---

## 6. frrcfgd.py における BGP_MONITORS 定数

`frrcfgd.py` は `sonic-frr-mgmt-framework` の OpenConfig/gNMI 向けデーモンであり、`BGP_MONITORS` テーブルを直接処理しない。BGP_MONITORS の FRR 設定注入は `bgpcfgd`（`sonic-bgpcfgd`）が担当する。frrcfgd.py に BGP_MONITORS 固有の定数は存在しない。

---

## 7. まとめ: CONFIG_DB 非依存ハードコード定数一覧

| カテゴリ | 定数/固定値 | 備考 |
|---------|-----------|------|
| peer-group 名 | `BGPMON` | 変更不可（テンプレートハードコード） |
| 受信 route-map | `FROM_BGPMON deny 10` | 全受信経路を拒否（route-monitor 用途で意図的） |
| 送信 route-map | `TO_BGPMON permit 10` | 全送信経路を許可 |
| maximum-prefix | `1` (IPv4/IPv6 共通) | `peer-group.conf.j2` |
| update-source (chassis) | `Loopback4096` | VoQ/chassis 環境固定 |
| name 制約 | `BGPMonitor` | YANG `must` |
| TCP ポート | デフォルト 179 (BGP well-known) | bgpcfgd / FRR が OS レベルで使用。CONFIG_DB フィールドなし |
