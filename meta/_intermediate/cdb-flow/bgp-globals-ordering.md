# BGP_GLOBALS — Phase B 書込み順依存 調査メモ

対象ページ: `docs/reference/config-db/bgp-globals.md`
調査日: 2026-05-15

## 調査対象ファイル

| ファイル | 役割 |
|---------|------|
| `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py` | `BGPConfigDaemon` — BGP_GLOBALS SET/DEL ハンドラ本体 |
| `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-bgp-global.yang` | YANG: VRF leafref 制約 |

---

## 検出した書込み順依存

### 1. `local_asn` はエントリ内で最初に処理される（VRF ASN 登録の前提）

`bgp_global_handler()` → `bgp_table_handler_common()` → `__update_bgp()` (L2685-2727):

```python
if table == 'BGP_GLOBALS':
    if not del_table:
        if 'local_asn' in data:
            dval = data['local_asn']
            ...
            if prog_asn:
                command = ['vtysh', '-c', 'configure terminal', '-c',
                           'router bgp {} vrf {}'.format(dval.data, vrf), '-c', 'no bgp default ipv4-unicast']
                if self.__run_command(table, command):
                    self.bgp_asn[vrf] = dval.data
                    self.__apply_dep_vrf_table(vrf, 'ROUTE_REDISTRIBUTE')
        local_asn = self.__get_vrf_asn(vrf)
        if local_asn is None:
            syslog.syslog(syslog.LOG_ERR, 'local ASN for VRF %s was not configured' % vrf)
            continue
```

`local_asn` が SET に含まれない場合、`__get_vrf_asn(vrf)` が None を返すと残りのフィールド処理が `continue`（スキップ）される。

- **順序制約**: `BGP_GLOBALS|<vrf>` の最初の書き込みに `local_asn` を必ず含めること。`local_asn` を省いた UPDATE より先に他のフィールドを書いても FRR に反映されない。
- evidence: `frrcfgd.py:2685-2727`

### 2. VRF テーブル全体のガード（`local_asn` 未設定 VRF はスキップ）

`__update_bgp()` L2656-2662:

```python
if self.__vrf_based_table(table):
    vrf = prefix
    local_asn = self.__get_vrf_asn(vrf)
    if local_asn is None and (table != 'BGP_GLOBALS' or 'local_asn' not in data):
        syslog.syslog(syslog.LOG_DEBUG, 'ignore table {} update because local_asn for VRF {} was not configured')
        continue
```

`BGP_GLOBALS_AF`、`BGP_GLOBALS_AF_AGGREGATE_ADDR`、`BGP_GLOBALS_AF_NETWORK`、`BGP_GLOBALS_LISTEN_PREFIX` 等のサブテーブルはすべて VRF ベーステーブル (`vrf_tables`) であり、対象 VRF の `local_asn` が確立していない限り**一切無視**される。

- **順序制約**: `BGP_GLOBALS|<vrf>` (`local_asn` 含む) → 同 VRF のサブテーブル全般 (`BGP_GLOBALS_AF` 等)。
- evidence: `frrcfgd.py:2136-2140, 2656-2662`

### 3. `default` VRF は DEVICE_METADATA.bgp_asn でも解決可能（代替パス）

`__get_vrf_asn()` L2442-2447:

```python
def __get_vrf_asn(self, vrf):
    if vrf in self.bgp_asn:
        return self.bgp_asn[vrf]
    if vrf == self.DEFAULT_VRF and self.metadata_asn is not None:
        return self.metadata_asn
    return None
```

`default` VRF に限り、`DEVICE_METADATA|localhost|bgp_asn` が設定されていれば `BGP_GLOBALS|default` に `local_asn` が未設定でも処理が継続される。

- **注意**: `default` VRF の場合は `DEVICE_METADATA.bgp_asn` が先行代替となりうるが、`BGP_GLOBALS.local_asn` が設定されると `bgp_asn[vrf]` が優先（上書き）される。
- evidence: `frrcfgd.py:2162-2166, 2442-2447`

### 4. 非 default VRF は VRF テーブルより先に BGP_GLOBALS が必須

`__delete_vrf_asn()` L2449-2451 の条件（削除時の確認コード）からも分かるように、非 default VRF の BGP_GLOBALS は VRF オブジェクト（`bgp_asn` 辞書）が先に存在していなければ LOG_ERR + skip。

非 default VRF を使う場合の書き込み順序:

1. `VRF|<vrf>` を CONFIG_DB に書き込む（VRF オブジェクト作成）
2. `BGP_GLOBALS|<vrf>` (`local_asn` 含む) を書き込む（ASN 登録）
3. `BGP_GLOBALS_AF|<vrf>|<af>` 等のサブテーブルを書き込む

- evidence: `frrcfgd.py:2449-2451, 2136-2140`

### 5. `local_asn` の変更不可制約（UPDATE 時）

`__update_bgp()` L2694-2696:

```python
if dval.op == CachedDataWithOp.OP_UPDATE:
    syslog.syslog(syslog.LOG_ERR, 'local_asn could not be modified')
    prog_asn = False
```

`local_asn` は一度設定した後に変更（UPDATE）することができない。変更するには `BGP_GLOBALS|<vrf>` ごと削除（`local_asn` DEL → VRF インスタンス全削除）してから再設定する必要がある。

- **手順**: `local_asn` 変更は `DEL BGP_GLOBALS|<vrf>` → `SET BGP_GLOBALS|<vrf>` (新 ASN) の順序が必須。
- evidence: `frrcfgd.py:2694-2696, 2689-2692`

### 6. `keepalive` + `holdtime` は必ずセットで書き込む（comb_attr_list 制約）

`bgp_global_handler()` L3935-3936:

```python
def bgp_global_handler(self, table, key, data):
    self.bgp_table_handler_common(table, key, data, [{'keepalive', 'holdtime'}])
```

`comb_attr_list` に `{'keepalive', 'holdtime'}` が指定されており、片方のみ SET しても集合全体が除去され FRR コマンド (`timers bgp <k> <h>`) が生成されない。

- **順序制約**: `keepalive` と `holdtime` は同一 SET 操作に含めること。片方のみの書き込みは無効。
- evidence: `frrcfgd.py:3935-3936, 1820`

### 7. DEL 時は VRF インスタンス全削除（サブテーブル先削除推奨）

`DEL BGP_GLOBALS|<vrf>` を送出すると（`data is None`）、`local_asn` DEL として処理され `no router bgp <asn> [vrf <vrf>]` が FRR に送出される。FRR 側は VRF 全インスタンスを削除するため、サブテーブル (`BGP_GLOBALS_AF` 等) を先に削除しておかないと CONFIG_DB と FRR 間で整合性が取れなくなる（再起動後に再投入される）。

- **推奨順序**: `BGP_GLOBALS_AF` / `BGP_NEIGHBOR` 等のサブテーブルを DEL → `BGP_GLOBALS|<vrf>` を DEL。
- evidence: `frrcfgd.py:2689-2692, 2449-2470`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | `local_asn` を同一 SET に含む → その他フィールドも同時反映 | 必須（単独 SET では残フィールドを skip） | なし |
| 2 | `BGP_GLOBALS|<vrf>` (`local_asn`) → `BGP_GLOBALS_AF` 等サブテーブル | 強制先行（`local_asn` 未設定なら全 skip） | なし |
| 3 | `default` VRF: `DEVICE_METADATA.bgp_asn` が代替 ASN 源 | 代替パス（BGP_GLOBALS 先行なしでも可） | DEVICE_METADATA を先行設定 |
| 4 | `VRF|<vrf>` → `BGP_GLOBALS|<vrf>` → サブテーブル（非 default VRF） | 強制先行 | なし |
| 5 | `local_asn` 変更: DEL 全削除 → 再 SET | 必須（UPDATE 不可） | 変更時はメンテ窓で実施 |
| 6 | `keepalive` + `holdtime` を同一 SET に含む | 必須（片方は無効） | 両フィールドをセットで投入 |
| 7 | サブテーブル DEL → `BGP_GLOBALS` DEL | 推奨（CONFIG_DB 整合性） | FRR 側は VRF ごと削除するが DB 残留の恐れ |
