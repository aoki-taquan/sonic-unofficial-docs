# LOOPBACK_INTERFACE — Phase 6/7/8 derivation & handler-branching

対象ページ: `docs/reference/config-db/loopback-interface.md`
バッチ: cdb_batch_9

---

## Phase 6: 自動派生 (minigraph.py 代入)

<!-- derivation -->

### 1. `Loopback0` エントリの自動生成

**ソース**: `sonic-buildimage/src/sonic-config-engine/minigraph.py:2298-2306`

```python
results['LOOPBACK_INTERFACE'] = {}
...
results['LOOPBACK_INTERFACE'][lo_intf[0]] = {}
```

- `Loopback0` と対応する IP プレフィックスキー `('Loopback0', '<ip>/32')` が minigraph XML の `<LoopbackInterface><IPAddress>` から自動生成される。
- `lo_addr` は `DEVICE_METADATA` → `results['DEVICE_METADATA']['localhost']['lo_addr']` にも代入される（minigraph.py:672）。

### 2. `Loopback4096` — VOQ 用 loopback の条件生成

**ソース**: `sonic-buildimage/src/sonic-config-engine/minigraph.py:2306`

```python
results['LOOPBACK_INTERFACE'][host_lo_intf[0]] = {}
```

- VOQ トポロジ（`chassis_type == CHASSIS_CARD_VOQ`）の場合のみ `Loopback4096` が生成される。
- `bgpcfgd` の `BgpPeerMgr` は `Loopback4096` の存在を依存チェックに使用する（managers_bgp.py:146）。

### 3. `lo_addr_v6` — IPv6 ループバックの条件付与

**ソース**: `sonic-buildimage/src/sonic-config-engine/minigraph.py:674`

```python
device_data['lo_addr_v6'] = lo_prefix_v6
```

- XML に IPv6 ループバックアドレスが定義されている場合のみ `LOOPBACK_INTERFACE|Loopback0|<ipv6>/128` エントリが追加される。

<!-- /derivation -->

---

## Phase 7: 条件付き登録

<!-- derivation -->

該当なし。

`intfmgrd` は `orchdaemon` の初期化時に無条件登録される。`LOOPBACK_INTERFACE` テーブルは `intfmgrd` が直接処理するが、VOQ 環境では `Loopback4096` の有無で後続の BGP manager の依存解決が変わる（間接的な条件付き登録効果）。

<!-- /derivation -->

---

## Phase 8: manager メソッド内 early return / dispatch

<!-- handler-branching -->

### intfmgrd の doLoopbackIntfTask() 分岐

**ソース**: `sonic-swss/cfgmgr/intfmgrd.cpp`

1. **op == "SET" (プレフィックスキー)**: IP アドレスが IPv4 か IPv6 かで `addLoopbackIntfAddress()` の内部パスが分岐。IPv6 リンクローカル (`fe80::/10`) は silent skip。
2. **op == "SET" (インターフェースキー)**: VRF バインディングがある場合 `setIntfVrf()` を呼び出す。VRF が存在しない場合は pending キューに追加して early return。
3. **op == "DEL"**: アドレスを削除する前に他のサービスが当該 Loopback を参照しているか確認。BGP が Loopback0 を next-hop に使用中の場合でも強制削除（SAI 側でのエラーはログのみ）。

<!-- /handler-branching -->
