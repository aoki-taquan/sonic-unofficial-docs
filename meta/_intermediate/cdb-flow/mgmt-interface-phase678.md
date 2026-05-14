# MGMT_INTERFACE — Phase 6/7/8 derivation & handler-branching

対象ページ: `docs/reference/config-db/mgmt-interface.md`
バッチ: cdb_batch_9

---

## Phase 6: 自動派生 (minigraph.py 代入)

<!-- derivation -->

### 1. `MGMT_INTERFACE` エントリの自動生成

**ソース**: `sonic-buildimage/src/sonic-config-engine/minigraph.py:2282,2297`

```python
results['MGMT_INTERFACE'] = {}
...
results['MGMT_INTERFACE'][(name, key[1])] = mgmt_intf[key]
```

- キーは `(interface_name, ip_prefix)` タプル形式（例: `("eth0", "192.168.1.1/24")`）。
- `mgmt_intf[key]` には `gwaddr`（デフォルトゲートウェイ）が含まれる場合がある。minigraph XML の `<ManagementInterface><ManagementIPAddress>` と `<Gateway>` から取得。

### 2. `mgmt_addr` と `mgmt_addr_v6` の DEVICE_METADATA への並行代入

**ソース**: `sonic-buildimage/src/sonic-config-engine/minigraph.py:676,678`

```python
device_data['mgmt_addr'] = mgmt_prefix
device_data['mgmt_addr_v6'] = mgmt_prefix_v6
```

- 同一 IP アドレスが `DEVICE_METADATA|localhost` の `mgmt_addr`/`mgmt_addr_v6` にも代入される。MGMT_INTERFACE テーブルと DEVICE_METADATA は同じ値を共有する。

### 3. `gwaddr` フィールドの条件付与

- XML に `<Gateway>` タグが存在する場合のみ `gwaddr` フィールドを付与。存在しない場合は省略（ゲートウェイ未設定扱い）。

<!-- /derivation -->

---

## Phase 7: 条件付き登録

<!-- derivation -->

該当なし。

`intfmgrd` が MGMT_INTERFACE を処理するが、`orchdaemon` の初期化時に無条件登録される。

<!-- /derivation -->

---

## Phase 8: manager メソッド内 early return / dispatch

<!-- handler-branching -->

### intfmgrd の doMgmtIntfTask() 分岐

**ソース**: `sonic-swss/cfgmgr/intfmgrd.cpp`

1. **op == "SET" (IP プレフィックスキー)**: `gwaddr` が設定されている場合 `ip route add default via <gwaddr> dev eth0 table <mgmt_vrf>` を発行。`gwaddr` が空の場合 default route 設定をスキップ。
2. **VRF バインディング確認**: `MGMT_VRF_CONFIG` で `mgmtVrfEnabled = true` の場合、`ip link set eth0 master mgmt` を実行してから IP を設定。`false` の場合は main VRF に直接設定（early return 分岐なし、フラグ参照のみ）。
3. **op == "DEL"**: IP アドレスと対応する default route を削除。VRF バインディングは解除しない（VRF テーブル DEL イベントが別途処理）。

<!-- /handler-branching -->
