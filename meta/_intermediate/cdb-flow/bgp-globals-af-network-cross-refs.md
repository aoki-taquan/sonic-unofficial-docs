# BGP_GLOBALS_AF_NETWORK — 暗黙参照調査 (Phase C)

調査対象: `sonic-net/sonic-buildimage` `src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`

## 調査方針

YANG leafref で宣言された構造的参照に加え、`frrcfgd.py` の `bgp_table_handler_common`
(`BGP_GLOBALS_AF_NETWORK` 分岐: L3169-3186) が FRR vtysh コマンドを構成する際に
**間接的に依存** するテーブル / フィールドを抽出する。

---

## 1. 下流参照（BGP_GLOBALS_AF_NETWORK が依存するテーブル/リソース）

### 1-1. BGP_GLOBALS (`local_asn`)

- **参照箇所**: `frrcfgd.py:2658-2662`
  - `__vrf_based_table` チェック → `__get_vrf_asn(vrf)` が `None` の場合 LOG_DEBUG で `continue` (silent drop)
- **参照箇所 2**: `frrcfgd.py:3180` — `router bgp {} vrf {}`.format(**local_asn**, vrf)
- **効果**: `BGP_GLOBALS.local_asn` が未設定の VRF に対する `BGP_GLOBALS_AF_NETWORK` 更新は全て無視される。  
  後から `local_asn` が設定されても `__apply_dep_vrf_table` は `ROUTE_REDISTRIBUTE` のみ再適用するため、  
  drop された `BGP_GLOBALS_AF_NETWORK` エントリは自動復旧しない (`frrcfgd.py:2704`)。
- **参照種別**: 実装上の必須依存（YANG leafref ではなく frrcfgd ロジック）

### 1-2. BGP_GLOBALS_AF (`vrf_name`, `afi_safi`)

- **参照箇所**: `frrcfgd.py:2297` — `table_handler_list` の並び順
  - `BGP_GLOBALS_AF` ハンドラ (L2297) は `BGP_GLOBALS_AF_NETWORK` ハンドラ (L2318) の前に登録される。
  - 起動時一括処理では AF 設定が先行して適用される（ランタイム更新では順序保証なし）。
- **効果**: `BGP_GLOBALS_AF` エントリが先に存在することで FRR `address-family` ブロックが確立済みとなる。
  `BGP_GLOBALS_AF_NETWORK` は `address-family {} {}` コマンドを自前で発行するため厳密な強制依存ではないが、  
  AF レベル属性（`max_ebgp_paths` 等）との整合性のため先行書き込みが推奨される。
- **参照種別**: 推奨順序依存（YANG leafref あり: `vrf_name` → `BGP_GLOBALS`, `afi_safi` 参照構造）

### 1-3. ROUTE_MAP (`policy` フィールド)

- **参照箇所**: `frrcfgd.py:af_network_key_map` → `network-policy` フォーマッタ (L922-924)
  ```python
  elif format == 'network-policy':
      if len(self.value) > 0:
          self.value = 'route-map %s' % self.to_str()
  ```
- **効果**: `policy` フィールドに route-map 名を指定した場合、FRR `bgpd` の名前空間でその route-map が
  解決される。CONFIG_DB の `ROUTE_MAP` テーブルに対応エントリが存在しない（= frrcfgd が FRR へ未投入）場合、  
  FRR は route-map を未定義として permit-any 相当で処理する（エラーにはならない）。
- **参照種別**: 暗黙の名前参照（YANG では文字列型のみ、leafref 強制なし）

### 1-4. DEVICE_METADATA|localhost|bgp_asn

- **参照箇所**: `frrcfgd.py:2162-2164` — `__init__` 時に `self.metadata_asn` へ読み込み
  ```python
  db_entry = self.config_db.get_entry('DEVICE_METADATA', 'localhost')
  if 'bgp_asn' in db_entry:
      self.metadata_asn = db_entry['bgp_asn']
  ```
- **参照箇所 2**: `frrcfgd.py:2371-2374` — `metadata_handler` で更新
- **効果**: `frrcfgd` デーモン起動条件の一つ。`bgpd.main.conf.j2` テンプレートでは `bgp_asn` 未設定時に
  `router bgp` ブロック自体が生成されない設計。`BGP_GLOBALS.local_asn` が VRF 別 ASN を上書きするが、
  デフォルト VRF では `metadata_asn` が fallback として参照される場合がある。
- **参照種別**: frrcfgd デーモン起動・デフォルト VRF ASN の暗黙参照

---

## 2. 上流参照（BGP_GLOBALS_AF_NETWORK を参照するコンポーネント）

| 参照元 | 参照機構 | 効果 |
|---|---|---|
| `frrcfgd` (`BGPConfigDaemon`) | `bgp_table_handler_common` 購読 (`frrcfgd.py:2318`) | CONFIG_DB 更新 → FRR `network <prefix> [route-map <name>] [backdoor]` コマンド列に変換 |
| `bgpd` (FRR) | vtysh 経由 | `network` ステートメントを BGP テーブルに注入、ピアへ広告 |
| `sonic-yang-mgmt` | YANG バリデーション (`sonic-bgp-global.yang`) | `vrf_name` の leafref チェック |

---

## 3. 証跡サマリ

| 参照先 | 参照種別 | ソース行 |
|---|---|---|
| `BGP_GLOBALS.local_asn` | 実装必須依存（silent drop） | `frrcfgd.py:2658-2662, 3180` |
| `BGP_GLOBALS_AF` | 推奨順序依存 | `frrcfgd.py:2297 vs 2318` |
| `ROUTE_MAP` (policy フィールド) | 暗黙名前参照 | `frrcfgd.py:922-924` |
| `DEVICE_METADATA.bgp_asn` | デーモン起動・fallback ASN | `frrcfgd.py:2162-2164, 2371-2374` |

---

生成日: 2026-05-16  
対象コミット: sonic-buildimage `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`
