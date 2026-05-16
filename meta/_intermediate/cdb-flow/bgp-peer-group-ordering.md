# BGP_PEER_GROUP — 書込順依存 (Phase B)

生成日: 2026-05-16
ソース:
- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py`

---

## 1. BGP_GLOBALS 先行必須

`frrcfgd.__update_bgp()` (L2658-2662) は `BGP_PEER_GROUP` イベントを処理する際、まず対象 VRF の `local_asn` を `__get_vrf_asn(vrf)` で取得する。`local_asn` が未設定（`None`）の場合、イベント全体を `LOG_DEBUG` のみで **silently drop** する（`continue`）。

```
# frrcfgd.py L2658-2662
local_asn = self.__get_vrf_asn(vrf)
if local_asn is None and (table != 'BGP_GLOBALS' or 'local_asn' not in data):
    syslog.syslog(LOG_DEBUG, 'ignore table {} update because local_asn for VRF {} was not configured'.format(table, vrf))
    continue
```

**結論**: `BGP_GLOBALS|<vrf>` に `local_asn` が書き込まれてから `BGP_PEER_GROUP|<vrf>|<pg_name>` を書き込まなければならない。順序が逆だと peer-group 設定が無音で失われる。

---

## 2. frrcfgd ハンドラ起動順（table_handler_list の位置）

`table_handler_list` (L2293-2338) の登録順序:

```
位置 1:  VRF
位置 2:  DEVICE_METADATA
位置 3:  BGP_GLOBALS        ← frrcfgd が VRF ASN を確立するハンドラ
位置 4:  BGP_GLOBALS_AF
...
位置 11: BGP_PEER_GROUP     ← peer-group ハンドラ (BGP_GLOBALS の後)
位置 12: BGP_NEIGHBOR
```

frrcfgd の初期化時 (`config_mode == "unified"`) は `table_handler_list` の順番に CONFIG_DB を replay する（L2344-2348）。これにより起動時リプレイでも `BGP_GLOBALS` → `BGP_PEER_GROUP` の順が保証される。

---

## 3. peer-group 自動作成と属性設定の順序

`frrcfgd.py` L2793-2802 に示す通り、SET 受信時に FRR 内に peer-group が存在しなければ属性設定コマンドより先に `neighbor <pg_name> peer-group` を vtysh 実行する。

```
# frrcfgd.py L2793-2802
if is_peer_group:
    if key not in self.bgp_peer_group.setdefault(vrf, {}):
        rc = self.__run_command(table, ['vtysh', '-c', ..., '-c', 'neighbor {} peer-group'.format(key)])
        if not rc:
            syslog.syslog(LOG_ERR, 'failed to create peer-group %s for VRF %s' % (key, vrf))
            continue   # 属性設定全体を skip
        self.bgp_peer_group[vrf][key] = BGPPeerGroup(vrf)
```

**結論**: FRR への発行順は ① `neighbor <pg> peer-group`（グループ宣言）→ ② 属性コマンド群。この内部順序は frrcfgd が自動保証するが、VRF ASN（BGP_GLOBALS）が確立済みでなければ ① も実行されない。

---

## 4. bgpcfgd ハンドラ起動順（BGPPeerMgrBase）

`bgpcfgd/managers_bgp.py` の `BGPPeerMgrBase.__init__()` (L89-157) は以下の依存を宣言:

```python
deps = [
    ("CONFIG_DB", CFG_DEVICE_METADATA_TABLE_NAME, "localhost/bgp_asn"),  # ASN 依存
    ("CONFIG_DB", CFG_DEVICE_METADATA_TABLE_NAME, "localhost/type"),
    ("CONFIG_DB", CFG_LOOPBACK_INTERFACE_TABLE_NAME, "Loopback0"),
    ("CONFIG_DB", CFG_BGP_DEVICE_GLOBAL_TABLE_NAME, "tsa_enabled"),
    ...
]
```

`Manager` 基底クラスは `deps` が全て解決するまで `set_handler()` を保留する。つまり `DEVICE_METADATA.bgp_asn`（= BGP_GLOBALS と同源の ASN 情報）が先に CONFIG_DB に存在することを要求する。

また `add_peer()` (L181) で `self.post_dependencies_init_complete` フラグを確認し、初回のみ追加 loopback テンプレートを解決してから peer-group テンプレートを更新する:

```python
# managers_bgp.py L181-182
if not self.post_dependencies_init_complete:
    self.post_dependencies_init()
```

**結論**: bgpcfgd 経路でも `DEVICE_METADATA.bgp_asn` → `BGP_PEER_GROUP` の書込順が必要。`post_dependencies_init_complete` フラグにより初回ピアは追加 loopback 解決後に peer-group テンプレートが確定する。

---

## 5. vtysh (FRR CLI) 発行順

bgpcfgd の `update_pg()` (L54-73) が FRR に発行するコマンド列:

```
router bgp <asn> [vrf <vrf>]
  <peer-group.conf.j2 render 結果>
  <tsa_routemaps>
  <idf_isolation_routemaps>
exit
```

FRR bgpd が `router bgp` コマンドを受け付けるには BGP プロセスが対象 VRF・ASN で既に起動済みである必要がある。これは BGP_GLOBALS の `local_asn` が frrcfgd / bgpcfgd によって FRR に反映済みであることと等価。

---

## 6. まとめ: 書込順依存の全体像

```
CONFIG_DB 書込順（必須）:

1. BGP_GLOBALS|<vrf>  (local_asn を含む)
      ↓  frrcfgd: VRF ASN 確立・FRR に router bgp <asn> vrf <vrf> 発行
      ↓  bgpcfgd: DEVICE_METADATA.bgp_asn deps 充足
2. BGP_PEER_GROUP|<vrf>|<pg_name>
      ↓  frrcfgd: neighbor <pg> peer-group 自動発行 → 属性コマンド群
      ↓  bgpcfgd: BGPPeerMgrBase.set_handler() → peer_group_mgr.update() → FRR
3. BGP_NEIGHBOR|<vrf>|<ip>  (peer_group_name を参照する場合)
      ↓  frrcfgd: neighbor <ip> peer-group <pg> を発行
```

順序違反時の挙動:
- BGP_GLOBALS 未設定で BGP_PEER_GROUP を書くと frrcfgd が silently drop（LOG_DEBUG のみ）
- BGP_PEER_GROUP 未作成で BGP_NEIGHBOR の peer_group_name を参照すると vtysh エラー（peer-group 未存在）
