# NAT_BINDINGS — プラットフォーム差調査

Task F Phase H: `NAT_BINDINGS` テーブル適用時のプラットフォーム/ASIC ベンダー差を `sonic-swss/orchagent/natorch.cpp` と関連ファイルから精読した結果。

## 結論

**Broadcom 専用の重要差分あり**。SAI NAT capability に基づく機能有無判定と、Broadcom ASIC 限定の DNAT ネクストホップトラッキングの 2 点でプラットフォーム依存が存在する。

## 根拠

### 1. SAI NAT capability チェック（gIsNatSupported）

`main.cpp:935-949` にて `SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY` を SAI Switch API に照会し、返値が 0 より大きい場合のみ `gIsNatSupported = true` を設定する。

`enableNatFeature()` (`natorch.cpp:2534-2581`) は `gIsNatSupported == false` の場合 `"NAT Feature is not supported in this Platform"` をログして即座に return する。これにより、SAI NAT をサポートしない ASIC では `admin_mode=enabled` を CONFIG_DB に書き込んでも SAI NAT オブジェクトが一切作成されない。

`maxAllowedSNatEntries` は同属性の取得値で初期化され (`natorch.cpp:111-122`)、動的 SNAT エントリ上限として使用される。上限到達時は新規 SNAT エントリを SAI に投入せず `AGEOUT-SINGLE-NAT` 通知を送出する (`natorch.cpp:1882-1889`)。

### 2. Broadcom 専用: DNAT ネクストホップトラッキング（gNhTrackingSupported）

`orchagent/orch.h:43` の `#define BRCM_PLATFORM_SUBSTRING "broadcom"` に基づき、NatOrch コンストラクタ (`natorch.cpp:144-148`) が環境変数 `platform` を確認する。`platform` に `"broadcom"` が含まれる場合のみ `gNhTrackingSupported = true` が設定される。

`gNhTrackingSupported=true` の場合（Broadcom）:
- DNAT エントリを `addDnatToNhCache()` でキャッシュし、NeighborOrch/RouteOrch からの解決通知後に `addHwDnatEntry()` を呼び出す遅延投入方式を採る。
- `enableNatFeature()` で `m_neighOrch->attach(this)` を呼び、NeighborOrch 変更通知を受信できるようにする。

`gNhTrackingSupported=false` の場合（非 Broadcom）:
- DNAT エントリを `addHwDnatEntry()` で即座に SAI に投入する。ネクストホップ未解決でも SAI に書き込まれるためブラックホールリスクがある（非 Broadcom ではそもそも NAT 自体が多くのプラットフォームで未サポート）。

### 3. 影響する処理範囲

`gNhTrackingSupported` は以下の全処理で分岐条件として使用される:
- `addNatEntry()`, `removeNatEntry()`: DNAT パス
- `addNaptEntry()`, `removeNaptEntry()`: DNAT NAPT パス
- `addTwiceNatEntry()`, `removeTwiceNatEntry()`: Double NAT パス
- `enableNatFeature()`, `disableNatFeature()`: NAT 機能の有効/無効化
- `updateNextHop()`, `updateNeighbor()`: ネクストホップ更新パス

### 4. 現行サポート状況まとめ

| 挙動 | 条件 |
|------|------|
| NAT 機能全体が有効 | `SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY > 0` → gIsNatSupported=true |
| NAT 機能全体が無効 | 上記属性が 0 または取得失敗 → gIsNatSupported=false |
| DNAT ネクストホップ追跡 | Broadcom ASIC のみ (gNhTrackingSupported=true) |
| DNAT 即時 SAI 投入 | 非 Broadcom (gNhTrackingSupported=false) |
| SNAT ハードウェア上限超過 | totalSnatEntries == maxAllowedSNatEntries → ageout 通知 |

現行 SONiC コミュニティ実装では **Broadcom ASIC のみが NAT ハードウェアオフロードを実運用レベルでサポートする**。

## 参照コード箇所

- `sonic-swss/orchagent/natorch.cpp` L107-149 (NatOrch コンストラクタ)
- `sonic-swss/orchagent/natorch.cpp` L1879-1934 (addNatEntry SNAT 上限・DNAT 分岐)
- `sonic-swss/orchagent/natorch.cpp` L2534-2581 (enableNatFeature)
- `sonic-swss/orchagent/main.cpp` L935-949 (gIsNatSupported 判定)
- `sonic-swss/orchagent/orch.h` L43 (BRCM_PLATFORM_SUBSTRING 定義)
