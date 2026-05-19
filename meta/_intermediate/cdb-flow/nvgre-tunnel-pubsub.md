# NVGRE_TUNNEL / NVGRE_TUNNEL_MAP — 通信メカニズム調査 (Phase G)

## 調査対象

- `sonic-swss/orchagent/orchdaemon.cpp` L361-364, L598-599
- `sonic-swss/orchagent/nvgreorch.h` L115-170
- `sonic-swss/orchagent/orch.h` L389-410 (Orch2 base class)
- `sonic-swss-common/common/orch.cpp` L1186-1196 (addConsumer)

## 購読登録経路

`orchdaemon.cpp:361` で `NvgreTunnelOrch *nvgre_tunnel_orch = new NvgreTunnelOrch(m_configDb, CFG_NVGRE_TUNNEL_TABLE_NAME)` を構築。
`orchdaemon.cpp:363` で `NvgreTunnelMapOrch *nvgre_tunnel_map_orch = new NvgreTunnelMapOrch(m_configDb, CFG_NVGRE_TUNNEL_MAP_TABLE_NAME)` を構築。

両クラスは `Orch2` ベース (`nvgreorch.h:115,155`)。`Orch2` コンストラクタが `Orch(db, tableName)` を呼び (`orch.h:392-395`)、`Orch::addConsumer()` (`orch.cpp:1186-1196`) が `m_configDb` の DB ID = CONFIG_DB を検出して **`SubscriberStateTable`** を選択する。

## チャンネル一覧

| 区間 | DB | テーブル名 | 購読クラス | 発行元 |
|---|---|---|---|---|
| CLI/CONFIG_DB → NvgreTunnelOrch | CONFIG_DB (dbId=4) | `NVGRE_TUNNEL` (`CFG_NVGRE_TUNNEL_TABLE_NAME`) | `SubscriberStateTable` | `config nvgre-tunnel add/del ...` (`sonic-utilities/config/plugins/nvgre_tunnel.py`) |
| CLI/CONFIG_DB → NvgreTunnelMapOrch | CONFIG_DB (dbId=4) | `NVGRE_TUNNEL_MAP` (`CFG_NVGRE_TUNNEL_MAP_TABLE_NAME`) | `SubscriberStateTable` | 同上 |
| NvgreTunnelOrch → syncd | ASIC_DB (syncd 経由) | — | SAI API 直接呼び出し | `sai_tunnel_api->create_tunnel()` 等 |

## SubscriberStateTable の動作

Redis keyspace 通知を購読。`HSET "NVGRE_TUNNEL|<name>" ...` が PUBLISH されると `NvgreTunnelOrch::doTask()` が `Orch2::doTask()` (`orch.cpp` Orch2 側) を経由して `addOperation()` を呼ぶ。

起動時スナップショット: `SubscriberStateTable` ctor は PSUBSCRIBE 直後に既存エントリを `SET_COMMAND` として buffer に充填する。orchagent 再起動時に残存する `NVGRE_TUNNEL|*` / `NVGRE_TUNNEL_MAP|*` エントリは遅延なく再配信される。

## ProducerStateTable は不使用

CONFIG_DB 経路では `ProducerStateTable` を使用しない。APPL_DB への中継もなし。
`NvgreTunnelOrch` / `NvgreTunnelMapOrch` は STATE_DB / APPL_DB への書込みを持たず (`<!-- side-effects -->` 参照)、SAI 直接呼び出しのみを行う。
