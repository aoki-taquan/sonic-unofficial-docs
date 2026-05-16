# MGMT_INTERFACE テーブル — 書込み順依存調査メモ (Phase B)

調査日: 2026-05-16
調査対象:
- `sonic-swss/cfgmgr/intfmgr.cpp`
- `sonic-swss/cfgmgr/intfmgrd.cpp`

---

## 1. 他テーブル先行必須

### MGMT_INTERFACE は intfmgrd の購読対象外

`intfmgrd.cpp:28-35` の購読テーブルリストに `MGMT_INTERFACE` は**含まれない**。管理インタフェース (`eth0`) の設定は `mgmtintfmgrd`（または同等デーモン）が担当し、Linux の management VRF 内で完結する。

```cpp
// intfmgrd.cpp:28-35
vector<string> cfg_intf_tables = {
    CFG_INTF_TABLE_NAME,
    CFG_LAG_INTF_TABLE_NAME,
    CFG_VLAN_INTF_TABLE_NAME,
    CFG_LOOPBACK_INTERFACE_TABLE_NAME,
    CFG_VLAN_SUB_INTF_TABLE_NAME,
    CFG_VOQ_INBAND_INTERFACE_TABLE_NAME,
};
```

### management VRF 関連の順序依存

| 先行テーブル / 条件 | 依存の内容 |
|------------------|-----------|
| `MGMT_VRF_CONFIG.mgmtVrfEnabled = true` | 管理 VRF 有効時、`ip route add ... table mgmt` でルートを management VRF テーブルに追加する |
| `MGMT_INTERFACE|eth0` 属性ロウ | IP プレフィクスロウより先に処理される必要がある（`isIntfCreated` パターン） |

### VRF_MGMT 定数

`intfmgr.cpp:26` で `VRF_MGMT = "mgmt"` と定義されている。`isIntfStateOk()` 内の `alias == VRF_MGMT` チェック（`intfmgr.cpp:677-684`）で `STATE_VRF_TABLE` を参照する。

---

## 2. MGMT_INTERFACE 設定順序

```
1. MGMT_VRF_CONFIG (mgmtVrfEnabled) 設定           (management VRF 利用時)
2. MGMT_INTERFACE|eth0 (属性ロウ) 投入             (IP/GW の設定より先)
3. MGMT_INTERFACE|eth0|<ip_prefix> 投入            (属性ロウ処理完了後)
4. ip address add <ip/plen> dev eth0               (デーモンが自動実行)
5. ip route add default via <gw> dev eth0          (gwaddr が有効 IPv4 の場合)
   または ip -6 route add default via <gw6>        (gwaddr が有効 IPv6 の場合)
```

management VRF 有効時は手順 4-5 が netns mgmt 内で実行される。

---

## 3. SAI 非経由の特記事項

- `MGMT_INTERFACE` は orchagent を経由しない（SAI に届かない）
- `gPortsOrch->getPort()` や `allPortsReady()` のチェックは適用されない
- Linux カーネルの management netns / VRF でのみ処理が完結する

---

## 4. まとめ（書込み順依存一覧）

| 依存カテゴリ | 必須順序 | 備考 |
|------------|---------|------|
| MGMT_VRF_CONFIG → MGMT_INTERFACE | VRF 有効化後に IP 設定 | management VRF 利用時のみ |
| 属性ロウ → IP prefix | `MGMT_INTERFACE|eth0` 先 → IP prefix ロウ後 | isIntfCreated パターン |
| orchagent 依存 | **なし** | SAI 非経由 |
| gwaddr ファミリ一致 | IPv4 gwaddr は IPv4 prefix と対応 | ファミリ不一致 → ERROR + スキップ |
