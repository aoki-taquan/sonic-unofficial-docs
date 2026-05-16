# BGP_GLOBALS_AF — Phase B 書込み順依存 調査メモ

対象ページ: `docs/reference/config-db/bgp-globals-af.md`
調査日: 2026-05-16

## 調査対象ファイル

| ファイル | 役割 |
|---------|------|
| `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py` | `BGPConfigDaemon` — BGP_GLOBALS_AF SET/DEL ハンドラ本体 |
| `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-bgp-global.yang` | YANG: VRF leafref 制約 |

---

## 検出した書込み順依存

### 1. `BGP_GLOBALS.local_asn` 先行必須（VRF based table ガード）

`__update_bgp()` L2658-2662:

```python
if self.__vrf_based_table(table):
    vrf = prefix
    local_asn = self.__get_vrf_asn(vrf)
    if local_asn is None and (table != 'BGP_GLOBALS' or 'local_asn' not in data):
        syslog.syslog(syslog.LOG_DEBUG, 'ignore table {} update because local_asn for VRF {} was not configured')
        continue
```

`BGP_GLOBALS_AF` は `vrf_tables` セット (`frrcfgd.py:2136`) に含まれる。対象 VRF の `local_asn` が `self.bgp_asn` に格納されていない限り、`BGP_GLOBALS_AF` の SET / DEL は **`continue` で黙って捨てられる**。

- **順序制約**: `BGP_GLOBALS|<vrf>` (`local_asn` 含む) → `BGP_GLOBALS_AF|<vrf>|<af>`。
- evidence: `frrcfgd.py:2136-2140, 2658-2662`

### 2. `default` VRF は `DEVICE_METADATA.bgp_asn` が代替（`BGP_GLOBALS` 不要な例外）

`__get_vrf_asn()` L2442-2447:

```python
def __get_vrf_asn(self, vrf):
    if vrf in self.bgp_asn:
        return self.bgp_asn[vrf]
    if vrf == self.DEFAULT_VRF and self.metadata_asn is not None:
        return self.metadata_asn
    return None
```

`default` VRF のみ、`DEVICE_METADATA|localhost|bgp_asn` が設定されていれば `BGP_GLOBALS|default` を書かなくても `BGP_GLOBALS_AF|default|<af>` が処理される。ただし `BGP_GLOBALS.local_asn` が後から設定されると `bgp_asn[vrf]` が上書きされる。

- **注意**: `default` VRF 以外（非 default VRF）では `DEVICE_METADATA.bgp_asn` は代替として機能しない。
- evidence: `frrcfgd.py:2162-2166, 2442-2447`

### 3. `BGP_GLOBALS_AF` は `BGP_GLOBALS` より後に処理される（frrcfgd 登録順）

frrcfgd handler 登録順 (`frrcfgd.py:2296-2297`):

```python
('BGP_GLOBALS',    self.bgp_global_handler),
('BGP_GLOBALS_AF', self.bgp_af_handler),
```

テーブル列挙順でも `vrf_tables` 定義 (L2136-2140) が `BGP_GLOBALS` → `BGP_GLOBALS_AF` の順を保持する。frrcfgd の初期スキャン（起動時 CONFIG_DB 全テーブル取得）では、この登録順に従い `BGP_GLOBALS` が先に処理される。

- **意味**: 起動順序として `BGP_GLOBALS` の処理が先行し、`local_asn` が確立してから `BGP_GLOBALS_AF` が投入される。
- evidence: `frrcfgd.py:2136-2140, 2296-2297`

### 4. `bgpd` 起動・接続待ち（frrcfgd が `BgpdClientMgr` を先行起動）

`main()` L3970-3981:

```python
bgpd_client = BgpdClientMgr()
bgpd_client.start()
daemon = BGPConfigDaemon()
daemon.start()
```

`BgpdClientMgr.__create_frr_client()` は `/run/frr/bgpd.vty` への Unix socket 接続を最大 100 回 (2 秒間隔) リトライし (`frrcfgd.py:L186-200`)、`bgpd` が起動していない間はブロックし続ける。`BGPConfigDaemon` は `BgpdClientMgr.start()` の完了後に初めて購読を開始する。

- **順序制約**: `bgpd` プロセスが `/run/frr/bgpd.vty` ソケットを公開してから frrcfgd の CONFIG_DB 購読が始まるため、`bgpd` 起動 → frrcfgd 購読開始 → `BGP_GLOBALS_AF` 投入 の順が保証される。
- evidence: `frrcfgd.py:183-204, 3970-3981`

### 5. `BGP_GLOBALS_AF` 内の `address-family` コンテキスト先行（bgpd CLI 順）

`__update_bgp()` L2769-2779 の BGP_GLOBALS_AF 処理:

```python
elif table == 'BGP_GLOBALS_AF':
    af, ip_type = key.lower().split('_')
    self.tmp_cache_key = 'BGP_GLOBALS_AF&&{}|{}'.format(vrf, key.lower())
    cmd_prefix = ['configure terminal',
                  'router bgp {} vrf {}'.format(local_asn, vrf),
                  'address-family {} {}'.format(af, ip_type)]
    if not key_map.run_command(self, table, data, cmd_prefix):
        syslog.syslog(syslog.LOG_ERR, 'failed running BGP global AF config command')
        continue
```

frrcfgd が FRR vtysh に送出するコマンドは必ず `configure terminal` → `router bgp <asn> [vrf <vrf>]` → `address-family <af> <safi>` の順で積み上げてから AF フィールドを投入する。

- **意味**: bgpd の CLI モード遷移（config → router-bgp → address-family）に従った固定順。`router bgp <asn>` が存在しない状態で `address-family` を発行すると bgpd 内部でルーターインスタンスが暗黙に生成される副作用があるが、frrcfgd は `local_asn` ガード (#1) により事前にこれを防ぐ。
- evidence: `frrcfgd.py:2769-2779`

### 6. `distance bgp` / `bgp dampening` の comb_attr_list 順序制約

`bgp_af_handler()` L3938-3941:

```python
def bgp_af_handler(self, table, key, data):
    self.bgp_table_handler_common(table, key, data, [
        {'ebgp_route_distance', 'ibgp_route_distance', 'local_route_distance'},
        {'route_flap_dampen_reuse_threshold', 'route_flap_dampen_suppress_threshold', 'route_flap_dampen_max_suppress'}
    ])
```

`__add_op_to_data()` (L3886-3888) の comb_attr_list 制約: 各セットのフィールドが**すべて同一 SET 操作に含まれない**場合、そのセット全体が `data` から除去される。個別フィールドのみの UPDATE では FRR コマンドが生成されない。

- **順序制約**:
  - `distance bgp` を設定するには `ebgp_route_distance` / `ibgp_route_distance` / `local_route_distance` の 3 フィールドを**同一の SET** に含めること。
  - `bgp dampening` の引数を設定するには `route_flap_dampen_reuse_threshold` / `route_flap_dampen_suppress_threshold` / `route_flap_dampen_max_suppress` を**同一の SET** に含めること。
  - 分割して複数回 SET しても後続 SET でフィールドが補完されない（comb_attr_list は同一操作内のみ検査する）。
- evidence: `frrcfgd.py:3938-3941`

### 7. DEL 操作: `BGP_GLOBALS_AF` は `BGP_GLOBALS` より先に削除推奨

`data is None` のとき `del_table=True` で AF を FRR から削除する。しかし `DEL BGP_GLOBALS|<vrf>` を送出すると FRR 側は `no router bgp <asn> [vrf <vrf>]` でルーターインスタンスごと削除し、配下の address-family も消去される。その後 CONFIG_DB に `BGP_GLOBALS_AF` エントリが残っていると、frrcfgd が再起動時にそれらを読み込んで FRR に再投入しようとするが、`local_asn` が消えているため skip される。

- **推奨順序**: `BGP_GLOBALS_AF|<vrf>|<af>` DEL → `BGP_GLOBALS|<vrf>` DEL の順で CONFIG_DB を整理する。
- evidence: `frrcfgd.py:2689-2692, 2449-2470`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 重大度 |
|---|----------|------|--------|
| 1 | `BGP_GLOBALS|<vrf>.local_asn` → `BGP_GLOBALS_AF|<vrf>|<af>` | 強制先行 (skip) | 必須 |
| 2 | `DEVICE_METADATA.bgp_asn` → `BGP_GLOBALS_AF|default|<af>` (default VRF のみ代替) | 代替パス | 条件付き |
| 3 | frrcfgd 起動時: `BGP_GLOBALS` → `BGP_GLOBALS_AF`（登録・初期スキャン順） | 自動 | 保証済み |
| 4 | `bgpd` 起動 → frrcfgd 購読開始 | bgpd socket 待ち | 保証済み (retry) |
| 5 | bgpd CLI: `configure terminal` → `router bgp` → `address-family` → AF フィールド | 固定順 | 保証済み |
| 6 | `distance bgp` 3 フィールド / `bgp dampening` 3 フィールドは同一 SET 必須 | comb_attr_list | 必須 |
| 7 | DEL: `BGP_GLOBALS_AF` → `BGP_GLOBALS` | 推奨 | 推奨 |
