# DPU テーブル — Phase C 暗黙参照抽出

**対象ページ**: `docs/reference/config-db/dpu.md`
**ソース調査対象**:
- `sonic-net/sonic-swss/orchagent/dash/dashenifwdorch.h`
- `sonic-net/sonic-swss/orchagent/dash/dashenifwdorch.cpp`
- `sonic-net/sonic-swss/orchagent/main.cpp`
- `sonic-net/sonic-swss/orchagent/orchdaemon.cpp`
- `sonic-net/sonic-platform-daemons/sonic-chassisd/scripts/chassisd`
- `sonic-net/sonic-buildimage/src/sonic-yang-models/yang-models/sonic-chassis-module.yang`
- `sonic-net/sonic-buildimage/src/sonic-yang-models/yang-models/sonic-device_metadata.yang`
- `sonic-net/sonic-buildimage/files/image_config/monit/container_checker`
- `sonic-net/sonic-buildimage/files/scripts/sonic-dpu-mgmt-traffic.sh`
**作成日**: 2026-05-16

---

## 1. CHASSIS_MODULE テーブルと DPU の暗黙依存

- **参照種別**: 双方向依存（CHASSIS_MODULE が DPU ライフサイクルを制御）
- **利用箇所**: `chassisd/scripts/chassisd` の `SmartSwitchConfigManagerTask.task_worker()` (行 1186-1228) が
  CONFIG_DB の `CHASSIS_MODULE` テーブルを `SubscriberStateTable` で購読する。
  キーが `DPU[0-9]+` で始まる場合のみ `SmartSwitchModuleConfigUpdater.module_config_update()` (行 235-256) に渡し、
  プラットフォーム API の `set_admin_state_gracefully()` を呼び出す。
- **YANG での対応**: `sonic-chassis-module.yang:23` の key pattern `"LINE-CARD[0-9]+|FABRIC-CARD[0-9]+|DPU[0-9]+"` により、
  CHASSIS_MODULE の key として `DPU0`〜`DPU7` が合法となっている。
- **影響**: `CHASSIS_MODULE|DPU<n>` の `admin_status: down` 書き込みが DPU のシャットダウン処理を起動する。
  逆に `DPU` テーブルの `state` フィールドはソフトウェア制御層であり、CHASSIS_MODULE の admin_status とは独立して存在する。
  証跡: `chassisd:235-256`, `sonic-chassis-module.yang:23`

## 2. DEVICE_METADATA.localhost.subtype と DPU の起動条件依存

- **参照種別**: 読み取り（実行時条件分岐）
- **利用箇所**: `orchagent/main.cpp:269` で `cfgDeviceMetaDataTable.hget("localhost", "subtype", switch_sub_type)` を呼び出し
  `gMySwitchSubType` グローバルに格納する。`orchdaemon.cpp:613` で
  `if (gMySwitchSubType == "SmartSwitch")` と判定し、`DashEniFwdOrch` を生成・登録する。
  `DashEniFwdOrch` が `DPU` テーブルを購読するため、`DEVICE_METADATA.localhost.subtype = "SmartSwitch"` が
  セットされていない環境では `DPU` テーブルの変化が orchagent に届かない。
- **YANG での対応**: `sonic-device_metadata.yang:191` の subtype pattern `"DualToR|SmartSwitch|Supervisor|UpstreamLC|DownstreamLC"` に `SmartSwitch` が含まれる。
  また `sonic-device_metadata.yang:115` の type pattern に `SmartSwitchDPU` が含まれ、DPU 側ノードの自己申告型として使われる。
- **影響**: `DEVICE_METADATA.localhost.subtype` が `SmartSwitch` でない場合、orchagent は DashEniFwdOrch を初期化しない。
  この状態では `DPU` テーブルへの書き込みは CONFIG_DB に格納されるが、ENI フォワーディングルールは生成されない。
  証跡: `orchagent/main.cpp:269`, `orchdaemon.cpp:613-618`

## 3. DPUS テーブルとの分業（同一 YANG モジュール内の姉妹テーブル）

- **参照種別**: 分業参照（DPUS は platform.json 由来の静的情報、DPU は minigraph 由来の動的情報）
- **利用箇所**: `container_checker` (行 117-121) は `config_db.get_table("DPUS")` を呼び出して SmartSwitch 上の
  DPU 数を取得し、`databasedpu<n>` コンテナが起動すべきかを判定する。
  `sonic-dpu-mgmt-traffic.sh` (行 111,145) も `redis-cli -n 4 keys DPUS*` と
  `redis-cli -n 4 hget "DPUS|$dpu" "midplane_interface"` を参照してトラフィック制御を行う。
  `DPUS` テーブルの `midplane_interface` は `sonic-smart-switch.yang:94` で定義される。
- **影響**: `DPU` テーブルと `DPUS` テーブルは同じ `sonic-smart-switch.yang` で定義されるが役割が異なる。
  `DPU` はネットワーク制御（ENI フォワーディング / iptables / gNMI）のための IP/port 情報を持ち、
  `DPUS` はコンテナ監視・トラフィック転送のための物理インタフェース情報（`midplane_interface`）を持つ。
  証跡: `container_checker:117-121`, `sonic-dpu-mgmt-traffic.sh:111,145`, `sonic-smart-switch.yang:81-106`

## 4. REMOTE_DPU / VDPU テーブルとの連携（DashEniFwdOrch 内）

- **参照種別**: 読み取り（初期化時に三者一括読み込み）
- **利用箇所**: `dashenifwdorch.cpp:215-344` のコメント `"Read DPU, VDPU, and Remote DPU tables, they are expected to be populated by the time HA is ready"` が示すように、
  `DPU`・`REMOTE_DPU`・`VDPU` の三テーブルは初期化時に一括取得される。
  `VDPU` テーブルの `main_dpu_ids` フィールドが各 `DPU`/`REMOTE_DPU` の識別子リストを参照し、
  ENI→VDPU→DPU の解決チェーンが形成される。
- **影響**: `VDPU` テーブルが未設定の場合や `main_dpu_ids` に不正な DPU 名が含まれる場合、
  `SWSS_LOG_WARN("Invalid DPU ID: %s, not found in DPU/REMOTE_DPU table", dpu_id.c_str())` が
  出力される（`dashenifwdorch.cpp:338`）。
  証跡: `dashenifwdorch.cpp:215-344`, `dashenifwdorch.h:63-65`

---

## 5. cross-refs ブロック（最終形）

以下を `docs/reference/config-db/dpu.md` の `<!-- /ordering -->` 直後に挿入する。

```markdown
<!-- cross-refs -->
## 暗黙参照テーブル (Phase C)

`DPU` テーブルは SmartSwitch 固有の CONFIG_DB テーブルとして他の複数テーブルと暗黙依存関係を持つ。
YANG `leafref` による明示的な参照は持たないが、orchagent / chassisd / monit の実行時コードが
以下のテーブルを連携して参照する。

| 依存方向 | 参照元フィールド / 参照元 | 参照先テーブル | 参照先キー形式 | 依存内容 | 証跡 |
|---------|------------------------|--------------|--------------|---------|------|
| 制御依存（被制御） | `CHASSIS_MODULE.admin_status` | `CHASSIS_MODULE`（被参照） | `CHASSIS_MODULE\|DPU<n>` | `chassisd` の `SmartSwitchConfigManagerTask` が `CHASSIS_MODULE` テーブルを購読。`admin_status=down` 書き込みで DPU のシャットダウン処理を起動する。YANG の key pattern `DPU[0-9]+` により `DPU0`〜`DPU7` が合法。`DPU.state` フィールドとは独立して動作する | `chassisd:1196-1228,235-256`, `sonic-chassis-module.yang:23` |
| 条件依存（起動ゲート） | `DEVICE_METADATA.localhost.subtype` | `DEVICE_METADATA` | `DEVICE_METADATA\|localhost` | `orchagent/main.cpp:269` が `subtype` フィールドを読み取り `gMySwitchSubType` に格納。`gMySwitchSubType == "SmartSwitch"` のときのみ `DashEniFwdOrch`（`DPU` テーブル購読者）が初期化される。この条件が満たされない環境では `DPU` テーブルへの書き込みが ENI ルール生成に繋がらない | `orchagent/main.cpp:269`, `orchdaemon.cpp:613-618`, `sonic-device_metadata.yang:191` |
| 分業参照（姉妹テーブル） | `container_checker` / `sonic-dpu-mgmt-traffic.sh` | `DPUS` | `DPUS\|<dpu_name>` | コンテナ監視（`container_checker`）は `DPUS` テーブルから DPU 名を取得して `databasedpu<n>` コンテナの必須起動判定を行う。`DPU` テーブルとは役割分担があり、`DPUS` は物理インタフェース（`midplane_interface`）情報を保持する | `container_checker:117-121`, `sonic-dpu-mgmt-traffic.sh:111,145`, `sonic-smart-switch.yang:81-106` |
| 連携参照（ENI 解決チェーン） | `DashEniFwdOrch` 初期化時の一括取得 | `REMOTE_DPU`, `VDPU` | `REMOTE_DPU\|<name>`, `VDPU\|<name>` | `dashenifwdorch.cpp:215-344` が `DPU`・`REMOTE_DPU`・`VDPU` を HA 準備完了時に一括取得。`VDPU.main_dpu_ids` フィールドが DPU 識別子リストを持ち、ENI→VDPU→DPU の名前解決チェーンを形成する。`VDPU` の `main_dpu_ids` に不正な DPU 名があると `WARN` ログが出力される | `dashenifwdorch.cpp:215-344`, `dashenifwdorch.h:63-65,80` |

### 依存解決タイミング

- **CHASSIS_MODULE → DPU 制御**: `chassisd` の `SmartSwitchConfigManagerTask` がリアルタイムに
  `CHASSIS_MODULE` の変化を購読。`admin_status` 変化のたびに DPU の admin state が更新される。
- **DEVICE_METADATA.subtype → DashEniFwdOrch 起動**: `orchagent` 起動時（`main.cpp:269`）に一度だけ読み取る。
  実行時の変化は反映されない（orchagent 再起動が必要）。
- **DPUS 参照**: `container_checker` は monit が定期実行するたびに `DPUS` テーブルを参照する。
  `DPU` テーブルと `DPUS` テーブルは別々に書き込まれるが、SmartSwitch では両方の整合が必要。
- **REMOTE_DPU / VDPU の一括読み込み**: HA セッション確立前に一括読み込みが行われる。
  `DPU`・`REMOTE_DPU`・`VDPU` が揃っていない状態での HA 初期化は `WARN` ログを伴う不完全な状態になる。
<!-- /cross-refs -->
```
