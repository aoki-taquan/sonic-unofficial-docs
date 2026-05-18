# DASH_PREFIX_TAG_TABLE — Phase H プラットフォーム差異スキャンノート

## スキャン対象
- `sonic-swss/orchagent/dash/dashaclorch.cpp`
- `sonic-swss/orchagent/dash/dashtagmgr.cpp`
- `sonic-swss/orchagent/orchdaemon.cpp`
- `sonic-swss/orchagent/main.cpp`

## 1. DPU (SmartSwitch) 専用動作

`DashAclOrch` (および内包される `DashTagMgr`) は `DpuOrchDaemon::init()`
(`orchdaemon.cpp:1322`) の内部でのみ生成される。`main.cpp:990` にて
`gMySwitchType == "dpu"` の場合のみ `DPU_APPL_DB` / `DPU_APPL_STATE_DB` に
接続して `DpuOrchDaemon` を起動するため、`DASH_PREFIX_TAG_TABLE` は
DPU (SmartSwitch) 上でのみ有効。

- 通常スイッチ (`switch`)、VoQ シャーシ、Fabric モードでは `DashAclOrch` /
  `DashTagMgr` 自体が存在しない。
- SmartSwitch の DPU 側でのみ有効。NPU 側の通常スイッチは対象外。

コード箇所:
```
main.cpp:990:
    if (gMySwitchType == "dpu")
    {
        dpu_app_db = make_shared<DBConnector>("DPU_APPL_DB", 0, true);
        orchDaemon = make_shared<DpuOrchDaemon>(...);

orchdaemon.cpp:1371-1379:
    vector<string> dash_acl_tables = {
        APP_DASH_PREFIX_TAG_TABLE_NAME,
        APP_DASH_ACL_IN_TABLE_NAME, ...
    };
    DashAclOrch *dash_acl_orch = new DashAclOrch(m_dpu_appDb, dash_acl_tables, ...);
```

## 2. ZMQ トランスポートの feature flag 制御

`orchdaemon.cpp:1329`:
```cpp
if (get_feature_status(ORCH_NORTHBOND_DASH_ZMQ_ENABLED, true))
    dash_zmq_server = m_zmqServer;
```

`ORCH_NORTHBOND_DASH_ZMQ_ENABLED` STATE_DB フィーチャーが `false` の場合、
`DashAclOrch` は `ZmqServer=nullptr` で構築され、Redis subscribe フォールバックになる。
デフォルト値は `true` のため通常環境では ZMQ が有効。

`DASH_PREFIX_TAG_TABLE` エントリは ZMQ 経由でコントローラから送信される protobuf
(`PrefixTag`) で届く。Redis フォールバック時も `ZmqOrch` → `ConsumerBase`
の共通インターフェースで処理される。

## 3. SAI 非依存 — ASIC 無関係

`DashTagMgr` はタグを orchagent 内メモリ (`m_tag_table`) にのみ保持し、
SAI API を一切呼び出さない。したがって ASIC 種別（Broadcom / Mellanox /
Marvell 等）による挙動差異は存在しない。

ASIC 依存が発生するのはタグを参照する ACL rule を SAI ACL エントリに
書き込む `DashAclGroupMgr` 側であり、`DASH_PREFIX_TAG_TABLE` 自体は ASIC と無関係。

## 4. IPv4 / IPv6 差異

タグの `ip_version` フィールドにより IPv4 / IPv6 タグが区別されるが、
これは SAI API 種別の選択ではなく orchagent 内メモリ上の属性として扱われる。
`to_sai(IpVersion)` が値 `0` (proto3 デフォルト) を拒否するため、
`ip_version` の明示指定が必須（コード由来制約、ASIC 非依存）。

## 5. multi-asic / VOQ / Fabric

multi-asic 構成・VOQ シャーシ・Fabric モードでは `DashAclOrch` は起動しない。
`gMySwitchType == "dpu"` 専用であり、namespace の iterate や
non-0 asic インデックス対応は実装されていない。

## 結論

| 観点 | 結果 | 根拠 |
|------|------|------|
| ASIC 種別 (Broadcom / Mellanox / Marvell 等) | 無関係 | `DashTagMgr` は SAI 非呼び出し。タグはメモリ保持のみ |
| DPU (SmartSwitch) 専用 | 通常スイッチでは無効 | `gMySwitchType == "dpu"` のみ `DpuOrchDaemon` → `DashAclOrch` を生成 (main.cpp:990, orchdaemon.cpp:1378) |
| multi-asic | 非対応 | DPU 専用構成のため namespace iterate なし |
| VOQ chassis / Fabric | 無効 | `DashAclOrch` は DPU モード限定 |
| ZMQ transport | feature flag `ORCH_NORTHBOND_DASH_ZMQ_ENABLED` で制御 | デフォルト有効。無効化で Redis fallback (orchdaemon.cpp:1329) |
| IPv4 / IPv6 | orchagent メモリ属性のみ、ASIC 非依存 | `to_sai(IpVersion)` が 0 を拒否。SAI 呼び出しなし (dashtagmgr.cpp:11-14) |
