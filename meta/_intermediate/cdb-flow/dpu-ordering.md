# DPU テーブル — Phase B 書込み順依存スキャンノート

対象テーブル: `DPU`
Consumer: `orchagent (DashEniFwdOrch)`, `caclmgrd`, `sonic-gnmi dpuproxy`, `chassisd`
ソース: `sonic-buildimage/src/sonic-config-engine/smartswitch_config.py`, `sonic-platform-daemons/sonic-chassisd/scripts/chassisd`
スキャン範囲: `smartswitch_config.py` 全行, `chassisd.set_initial_dpu_admin_state()`, `caclmgrd (swbus_port 参照)`, `resolver.go (gnmi_port 参照)`

---

## 検出した順序依存・タイミング依存

### 1. DPU テーブル書き込みは CHASSIS_MODULE 設定より先行必須

- `chassisd.set_initial_dpu_admin_state()` (chassisd:1364-1405) は起動時に `CHASSIS_MODULE` テーブルから `admin_status` を取得する。
- `DPU` テーブルは `smartswitch_config.py` / minigraph パーサが書き込む。
- **順序依存**: `DPU` テーブルエントリが CONFIG_DB に書き込まれた後、`CHASSIS_MODULE|DPU*` エントリが設定される流れが期待される。逆順（`CHASSIS_MODULE` が先）の場合、chassisd が起動時に `admin_status` を読み取る時点で DPU 情報が不完全な可能性がある。
- `smartswitch_config.py` の書き込み順序: `DPU_TABLE` (`platform_json` の `DPU` キー) → `DPUS_TABLE` (`platform_json` の `DPUS` キー) の順に CONFIG_DB へ書き込まれる (smartswitch_config.py:43-46)。
- evidence: `smartswitch_config.py:18-46`, `chassisd:1364-1405`

### 2. DPU.state フィールド — orchagent の必須先行条件

- `orchagent/DashEniFwdOrch` の `dpu_table_desc.required_attributes` に `state` と `pa_ipv4` が含まれる (dashenifwdorch.h:134-137)。
- **順序依存**: `DPU` エントリが `state` / `pa_ipv4` を持たない状態で DB に書き込まれると、`DashEniFwdOrch` は当該エントリを rejected として処理し、ENI フォワーディングルールが生成されない。`state` と `pa_ipv4` の同時書き込みが必要。
- evidence: `sonic-swss/orchagent/dash/dashenifwdorch.h:134-137`

### 3. caclmgrd の swbus_port 先行必須性

- `caclmgrd` は CONFIG_DB の `DPU` テーブルを購読し、`swbus_port` を参照して iptables ルールを生成する。
- `swbus_port` が存在しない場合: `"Received DPU configuration without swbus_port. Ignore it."` を出力して当該 DPU 設定を**完全スキップ**する (caclmgrd:1100)。
- **順序依存**: `swbus_port` は `DPU` テーブルエントリの書き込み時に同時に含める必要がある。後から追加する場合は caclmgrd が設定変更通知を受けて再処理するが、その間の DPU-to-DPU swbus 通信は iptables ルールが不完全なまま。
- evidence: `sonic-host-services/scripts/caclmgrd:~1100`

### 4. sonic-gnmi DPU proxy の gnmi_port フォールバック順序

- `dpuproxy/resolver.go` は `DPU.gnmi_port` を読み取り DPU への gNMI 接続先を決定する。
- `gnmi_port` が DB に存在しない場合のフォールバック: `DefaultGNMIPort = "50052"` → `["8080", "50052"]` の順に試行する (resolver.go:99,103-110)。
- **順序依存なし**: `gnmi_port` 欠如時は自動フォールバック。ただし実際の DPU gNMI サービスが `50052` 以外のポートで listen している場合は接続失敗。DPU エントリ書き込み時に正確な `gnmi_port` を含めることを推奨。
- evidence: `sonic-gnmi/pkg/interceptors/dpuproxy/resolver.go:99-110`

### 5. DPU テーブルの書き込み元と CHASSIS_APP_DB との非連携

- `DPU` テーブルは CONFIG_DB にのみ存在し、CHASSIS_APP_DB との直接連携はない。
- CHASSIS_APP_DB は VOQ 構成のラインカード間でのみ使用され、SmartSwitch DPU テーブルとは独立。
- SmartSwitch の chassisd は `SmartSwitchModuleUpdater` を使用し、CHASSIS_APP_DB への書き込みを行わない (chassisd:688-862 の SmartSwitchModuleUpdater には `_cleanup_chassis_app_db` 呼び出しなし)。
- evidence: `chassisd:688-862, 593-680`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | `DPU` テーブル書き込み → chassisd 起動 / `CHASSIS_MODULE` 設定 | DPU 先行推奨 | 逆順時は chassisd 起動時に DPU 情報不完全の可能性 |
| 2 | `DPU.state` + `DPU.pa_ipv4` の同時書き込み → orchagent ENI 生成 | 同時書き込み必須 | 欠如フィールドあり → request rejected |
| 3 | `DPU.swbus_port` 存在 → caclmgrd iptables 生成 | 書き込み時に含める必要 | 欠如時は当該 DPU を完全スキップ |
| 4 | `DPU.gnmi_port` → sonic-gnmi 接続先決定 | 任意（フォールバックあり） | 欠如時は `50052` を試行。ポート不一致で接続失敗 |
| 5 | DPU テーブル ↔ CHASSIS_APP_DB | 連携なし | SmartSwitch と VOQ は独立した DB セット |
