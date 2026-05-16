# LOOPBACK_INTERFACE テーブル — 書込み順依存調査メモ (Phase B)

調査日: 2026-05-16
調査対象:
- `sonic-swss/cfgmgr/intfmgr.cpp`

---

## 1. 他テーブル先行必須

### Loopback は STATE_DB 依存なし

`intfmgrd` の `isIntfStateOk()` はエイリアスが `Loopback` プレフィクスで始まる場合に**即 `true` を返す**（`intfmgr.cpp:696-699`）。PORT / PORTCHANNEL / VLAN など他テーブルへの STATE_DB 依存は一切存在しない。

```cpp
// intfmgr.cpp:696-699
else if (!alias.compare(0, strlen(LOOPBACK_PREFIX), LOOPBACK_PREFIX))
{
    return true;
}
```

唯一の例外は `vrf_name` 指定時。この場合 `isIntfStateOk(vrf_name)` で `STATE_VRF_TABLE` を参照する。

| 先行テーブル / 条件 | 確認先 STATE_DB | 依存の内容 | コード根拠 |
|------------------|----------------|-----------|-----------|
| 依存なし | — | `isIntfStateOk("Loopback*")` は常に `true` | `intfmgr.cpp:696-699` |
| `VRF` + vrfmgrd が `STATE_VRF_TABLE` に書く | `STATE_VRF_TABLE` | `vrf_name` 指定時のみ。未 ready → retry | `intfmgr.cpp:839-842` |
| Loopback 属性ロウが `STATE_INTERFACE_TABLE` に存在 | `STATE_INTERFACE_TABLE` | `isIntfCreated()` が false → IP プレフィクスロウをスキップ | `intfmgr.cpp:1115` |

---

## 2. Loopback 生成順序 (kernel netlink)

`doIntfGeneralTask()` SET パス（Loopback 向け、`intfmgr.cpp` L772–1054）:

```
Step  コマンド / 操作                                     条件
1     is_lo = true                                      alias が "Loopback" で始まる
2     ip link add <name> mtu 65536 type dummy           新規 Loopback 作成時
3     ip link set <name> master <vrf>                   vrf_name 指定時
      または ip link set <name> nomaster                VRF 除去時
4     ip link set <name> address <mac>                  mac_addr 指定時
5     ip link set <name> up/down                        adminStatus (デフォルト "up")
6     m_appIntfTableProducer.set(alias, data)           APP_DB INTF_TABLE SET
7     m_stateIntfTable.hset(alias, "vrf", vrf_name)    STATE_DB 書込み
```

`doIntfAddrTask()` SET パス（IP プレフィクスロウ、`intfmgr.cpp` L1099–1170）:

```
Step  コマンド / 操作
1     isIntfStateOk(alias) && isIntfCreated(alias) ガード  (属性ロウ完了確認)
2a    ip address add <ip/plen> [broadcast <bcast>] dev <alias>   (IPv4)
2b    ip -6 address add <ip/plen> [metric 256] dev <alias>       (IPv6; VoQ 時 metric 256)
3     m_appIntfTableProducer.set(appKey, {scope, family})        APP_DB
4     m_stateIntfTable.hset("<alias>|<ip>", "state", "ok")       STATE_DB
```

---

## 3. SET 後 DEL 順依存

```
DEL 順序: LOOPBACK_INTERFACE|<name>|<ip_prefix> → LOOPBACK_INTERFACE|<name>
```

`intfmgr.cpp:1058-1063`:
```cpp
/* make sure all ip addresses associated with interface are removed */
if (getIntfIpCount(alias))
{
    return false;
}
```

IP カウントが 0 でなければ DEL を受け付けない → retry。

VRF 変更は `intfmgr.cpp:846-849` のチェックにより直接変更不可（2 ステップ必須）。

---

## 4. cold / warm-reboot 影響

### cold restart

`flushLoopbackIntfs()` で既存 Loopback を Linux からすべて削除してから再作成する（`intfmgr.cpp:57`）。削除後は CONFIG_DB からの再投入待ちになる。

### warm-start

`buildIntfReplayList()` が CONFIG_DB の `LOOPBACK_INTERFACE` キーを `m_pendingReplayIntfList` に収集する（`intfmgr.cpp:280`）。replay 完了で `REPLAYED` → `RECONCILED`（reconciliation ロジックなし）。

---

## 5. まとめ（書込み順依存一覧）

| 依存カテゴリ | 必須順序 | ソース |
|------------|---------|-------|
| PORT / LAG / VLAN → Loopback | **依存なし**（isIntfStateOk 常 true） | `intfmgr.cpp:696-699` |
| VRF → LOOPBACK_INTERFACE | `VRF` + vrfmgrd STATE_VRF_TABLE ready が先 | `intfmgr.cpp:839-842` |
| 属性ロウ → IP prefix | `LOOPBACK_INTERFACE|<name>` SET → STATE_INTF 反映後に IP prefix SET | `intfmgr.cpp:1115` |
| IP prefix DEL → 属性ロウ DEL | すべての IP prefix を DEL してから属性ロウを DEL | `intfmgr.cpp:1060-1063` |
| VRF 変更 2 ステップ | unbind (vrf_name="") → rebind (vrf_name=新VRF) | `intfmgr.cpp:846-849` |
| cold restart | flushLoopbackIntfs() で全削除 → 再作成 | `intfmgr.cpp:57` |
