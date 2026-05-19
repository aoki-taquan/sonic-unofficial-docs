# nat-state Phase H — プラットフォーム差

## 調査対象

- `sonic-swss/orchagent/natorch.cpp`
- `sonic-swss/natsyncd/natsync.cpp`
- `sonic-buildimage/dockers/docker-nat/restore_nat_entries.py`
- `sonic-swss/orchagent/orch.h`

## 発見事項

### 1. DNAT ネクストホップ追跡 (Broadcom 専用)

`natorch.cpp:144-148` で `getenv("platform")` を確認し、`"broadcom"` を含む場合のみ `gNhTrackingSupported = true` にセット。`BRCM_PLATFORM_SUBSTRING` は `orch.h:43` で `"broadcom"` と定義。

`gNhTrackingSupported == true` の場合、DNAT エントリの追加は即時 SAI プログラムではなくネクストホップ解決待ちキャッシュ経由となる (`natorch.cpp:1923-1932`)。これにより `COUNTERS_NAT` への書き込みがネクストホップ解決後に遅延する。

### 2. MAX_NAT_ENTRIES — SAI サポート依存

`natorch.cpp:111-122` で `SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY` を問い合わせる。失敗時は `"0"` を `COUNTERS_GLOBAL_NAT|Values.MAX_NAT_ENTRIES` に書き込む。SAI 実装がこの属性をサポートしないプラットフォームでは `"0"` となる。

### 3. NAT_RESTORE_TABLE — warm reboot 専用

`restore_nat_entries.py` が warm reboot 時のみ実行される。NAT 機能が無効なプラットフォームでは `NAT_RESTORE_TABLE|Flags.restored` が書き込まれず、`natsyncd` の reconciliation が開始されない。
