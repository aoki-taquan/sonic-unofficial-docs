# APPL_DB VRF_TABLE (VRFOrch) — 通信メカニズム調査 (Phase G)

## 調査対象
- `sonic-swss/orchagent/vrforch.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/orchagent/orchdaemon.cpp`
- `sonic-swss/cfgmgr/vrfmgr.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/cfgmgr/vrfmgr.h`
- `sonic-swss-common/common/schema.h` (ref: 158de8d3463ff4b841653f6d57190bb142b80d9c)

## APPL_DB への書込み側（vrfmgrd）

### ProducerStateTable 利用

`vrfmgr.h:46`:
```cpp
ProducerStateTable m_appVrfTableProducer;
```

`vrfmgr.cpp:303`: `m_appVrfTableProducer.set(vrf_name, fvVector)` で VRF エントリを書く。

ProducerStateTable は Lua EVALSHA でアトミックに:
- `SADD VRF_TABLE_KEY_SET <key>`
- `HSET _VRF_TABLE:<key> <fields>`
- `PUBLISH VRF_TABLE_CHANNEL@0 G`

DEL は:
- `SREM VRF_TABLE_KEY_SET <key>`
- `DEL _VRF_TABLE:<key>`
- `PUBLISH VRF_TABLE_CHANNEL@0 G`

## APPL_DB からの読取り側（VRFOrch）

### ConsumerStateTable 利用

`orchdaemon.cpp:283`:
```cpp
VRFOrch *vrf_orch = new VRFOrch(m_applDb, APP_VRF_TABLE_NAME,
                                 m_stateDb, STATE_VRF_OBJECT_TABLE_NAME);
```

VRFOrch は `Orch2` を継承し `Orch2(appDb, APP_VRF_TABLE_NAME, request_)` コンストラクタが `addConsumer(db, tableName)` を呼ぶ。APPL_DB に対しては `orch.cpp:1194` で `ConsumerStateTable` が選択される。

購読:
```
SUBSCRIBE VRF_TABLE_CHANNEL@0
```

`consumer_state_table_pops.lua` 実行:
1. `SPOP VRF_TABLE_KEY_SET` → key
2. `HGETALL _VRF_TABLE:<key>` → fields
3. Consumer::execute() → VRFOrch::addOperation() / delOperation()

## その他 Producer

`vrfmgrd` には他に:
- `m_appVnetTableProducer` → `APPL_DB::VNET_TABLE`
- `m_appVxlanVrfTableProducer` → `APPL_DB::VXLAN_VRF_TABLE`

これらは VRFOrch の購読対象外（VNETOrch / VxlanTunnelOrch が処理）。

## 購読者が 1 つのみである確認

`grep -r "VRF_TABLE_CHANNEL\|APP_VRF_TABLE_NAME" sonic-swss/orchagent/` で確認:
- `orchdaemon.cpp:283` の VRFOrch のみ。他の Orch クラスは APPL_DB VRF_TABLE を購読しない。

## 証跡コード箇所

- `vrfmgr.h:46` — `ProducerStateTable m_appVrfTableProducer`
- `vrfmgr.cpp:303` — `m_appVrfTableProducer.set()`
- `vrfmgr.cpp:330` — `m_appVrfTableProducer.del()`
- `orchdaemon.cpp:283` — `VRFOrch` 生成
- `orch.cpp:1194` — APPL_DB に対し `ConsumerStateTable` 選択
- `schema.h:80` — `APP_VRF_TABLE_NAME = "VRF_TABLE"`
