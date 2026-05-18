# nat-state ハードコード定数調査メモ (Phase E)

## 調査対象ファイル

- `sonic-swss/orchagent/natorch.h`
- `sonic-swss/orchagent/natorch.cpp`
- `sonic-swss/cfgmgr/natmgr.h`
- `sonic-swss/cfgmgr/natmgr.cpp`

## 発見した定数

### カウンタポーリング周期 (natorch.h)

```
NAT_HITBIT_N_CNTRS_QUERY_PERIOD = 5      // 5秒 — m_natQueryTimer 発火周期
NAT_HITBIT_QUERY_MULTIPLE       = 6      // hit bit は 5×6=30秒ごとに取得
NAT_CONNTRACK_TIMEOUT_PERIOD    = 86400  // 1日 — m_natTimeoutTimer 発火周期
```

### タイムアウト定数 (natmgr.h)

```
NAT_TIMEOUT_DEFAULT      = 600     秒  (non-TCP/UDP)
NAT_TIMEOUT_MIN          = 300     秒
NAT_TIMEOUT_MAX          = 432000  秒 (5日)
NAT_TCP_TIMEOUT_DEFAULT  = 86400   秒 (1日)
NAT_TCP_TIMEOUT_MIN      = 300     秒
NAT_TCP_TIMEOUT_MAX      = 432000  秒 (5日)
NAT_UDP_TIMEOUT_DEFAULT  = 300     秒
NAT_UDP_TIMEOUT_MIN      = 120     秒
NAT_UDP_TIMEOUT_MAX      = 600     秒
NAT_ENTRY_REFRESH_PERIOD = 86400   秒 (1日) — dynamic NAT conntrack リフレッシュ
```

## COUNTERS_GLOBAL_NAT との関係

NatOrch コンストラクタ (`natorch.cpp:128-130`) が起動時に
`NAT_TIMEOUT_DEFAULT`, `NAT_UDP_TIMEOUT_DEFAULT`, `NAT_TCP_TIMEOUT_DEFAULT` を
`COUNTERS_GLOBAL_NAT|Values` の `TIMEOUT`/`UDP_TIMEOUT`/`TCP_TIMEOUT` に 1 回書き込む。
以降は CONFIG_DB が変わっても COUNTERS_GLOBAL_NAT は更新されない (静的フィールド)。
