# DPU — Phase D 失敗挙動スキャンノート

対象テーブル: `DPU`
Consumer: `orchagent` (`DashEniFwdOrch` / `DpuRegistry`), `caclmgrd`, `sonic-gnmi` DPU proxy
スキャン範囲: `sonic-swss/orchagent/dash/dashenifwdorch.cpp`, `sonic-swss/orchagent/dash/dashenifwdorch.h`,
             `sonic-host-services/scripts/caclmgrd`, `sonic-gnmi/pkg/interceptors/dpuproxy/resolver.go`

---

## 検出した失敗挙動

### 1. orchagent — required_attributes 欠如時の request reject

- `dpu_table_desc.required_attributes` に `state` と `pa_ipv4` の両方が宣言されている
  (`dashenifwdorch.h:136`).
- `DPU` エントリが `state` または `pa_ipv4` を欠いた状態で書き込まれた場合、
  `Orch2` フレームワークの `parseRequest()` が要求 reject を行い、ENI フォワーディングルール
  は生成されない。
- **サイレント失敗**: reject 時は `SWSS_LOG_ERROR` ではなく、フレームワーク内部の parse 失敗
  として処理されるため上位ログが出にくい。
- evidence: `dashenifwdorch.h:129-137`

### 2. orchagent — DPU.state=down 時のスキップ

- `DpuRegistry::processDpuTable()` は `state` フィールドが存在し値が `"down"` の場合、
  当該 DPU を `dpus_name_map_` に登録しない (`dashenifwdorch.cpp:244-251`)。
- その結果、`VDPU.main_dpu_ids` からその DPU を参照しても `getDpuId()` が `false` を返し、
  ENI→VDPU→DPU の名前解決チェーンが切断される。
- ログ: `SWSS_LOG_INFO("Skipping LOCAL DPU %s as its state is down", key.c_str())`
  （INFO レベル、操作ログ以上には出ない）。
- evidence: `dashenifwdorch.cpp:244-251`

### 3. orchagent — parse 例外時の個別スキップ

- `DpuRegistry::processDpuTable()` / `processRemoteDpuTable()` / `processVdpuTable()` は
  各エントリを `try-catch(exception& e)` で囲む。
- parse に失敗した個別エントリは `SWSS_LOG_ERROR` を出力して次エントリに進む
  （処理は継続、orchagent は終了しない）。
- evidence: `dashenifwdorch.cpp:262-265`, `301-304`, `342-345`

### 4. orchagent — VDPU が DPU を参照できない場合の WARN

- `processVdpuTable()` で `vdpu.main_dpu_ids` に含まれる DPU 名が
  `dpus_name_map_` に存在しない場合、WARN を出力して当該 DPU を VDPU マップから除外する。
- `SWSS_LOG_WARN("Invalid DPU ID: %s, not found in DPU/REMOTE_DPU table", dpu_id.c_str())`
- ENI フォワーディング解決が不完全になるが、orchagent は継続動作する。
- evidence: `dashenifwdorch.cpp:338`

### 5. orchagent — VIP_TABLE 欠如時の THROW

- `EniFwdCtxBase::getVip()` は `VIP_TABLE` にエントリが存在しない場合
  `SWSS_LOG_THROW("Invalid Config: VIP info not populated")` を発する。
- これは orchagent クラッシュに繋がる（`SWSS_LOG_THROW` は例外を投げ supervisord が再起動）。
- `DPU` テーブルの直接的な失敗ではないが、DPU フォワーディング初期化経路で依存する。
- evidence: `dashenifwdorch.cpp:502`

### 6. caclmgrd — swbus_port 欠如時の完全スキップ

- `update_dash_ha_rules()` は SET 時に `swbus_port` フィールドが存在しない場合、
  iptables ルールを追加せずに返る。
- ログ: `self.log_info("Received DPU configuration without swbus_port. Ignore it.")`
  （INFO レベル、syslog への影響が小さい）。
- 結果: DPU-to-DPU swbus 通信を許可する `iptables -I INPUT -p tcp --dport <port>` ルールが
  生成されない → swbus 接続が Linux netfilter によって DROP される可能性がある。
- evidence: `caclmgrd:1096-1100`

### 7. caclmgrd — iptables コマンド失敗時のサイレント継続

- `run_commands()` は各コマンドの戻り値を `log_output()` で確認するが、失敗時のログ出力のみで
  例外は発生しない。後続コマンドへの影響はない（iptables ルールが一部未適用のまま継続）。
- evidence: `caclmgrd:226-238`

### 8. sonic-gnmi proxy — DPU が STATE_DB に存在しない場合のエラー返却

- `DPUResolver.GetDPUInfo()` は `CHASSIS_MIDPLANE_TABLE|DPU<n>` が STATE_DB に存在しない場合、
  `error: "DPU%s not found in StateDB"` を返す。
- gNMI リクエストは `rpc error: code = NotFound` として呼び出し元に返る。
- CONFIG_DB の `DPU` テーブルが存在しても STATE_DB が未更新であれば gNMI proxy は失敗する
  （STATE_DB はシステム起動後に `chassisd` / `pmon` が書き込む）。
- evidence: `resolver.go:67-76`

### 9. sonic-gnmi proxy — ip_address フィールド欠如

- `CHASSIS_MIDPLANE_TABLE|DPU<n>` が存在しても `ip_address` フィールドがない場合、
  `error: "DPU%s missing ip_address field in StateDB"` を返す。
- CONFIG_DB の `gnmi_port` は参照される前に STATE_DB チェックで失敗する。
- evidence: `resolver.go:80-83`

### 10. sonic-gnmi proxy — CONFIG_DB gnmi_port 欠如はデフォルト使用（非エラー）

- `DPU|dpu<n>` の `gnmi_port` フィールドが CONFIG_DB に存在しない場合はエラーにならず、
  `DefaultGNMIPort = "50052"` を使用する。
- ポートが実際の DPU サービスと一致しない場合、接続試行は失敗するが resolver 自体は成功を返す。
- evidence: `resolver.go:97-100`

---

## 失敗挙動サマリ

| # | 失敗条件 | コンポーネント | 結果 | ログレベル | 自動復旧 |
|---|----------|--------------|------|-----------|---------|
| 1 | `state` / `pa_ipv4` のいずれかが欠如した DPU エントリ書き込み | orchagent | request reject、ENI ルール未生成 | (parse 内部) | なし（フィールド追加後に再 SET が必要） |
| 2 | `DPU.state = "down"` | orchagent | DpuRegistry に未登録、ENI→DPU 名前解決不可 | INFO | `state` を `up` に更新すれば orchagent 再起動または HA 再初期化で復旧 |
| 3 | 個別エントリ parse 例外 | orchagent | 当該エントリをスキップ・処理継続 | ERROR | なし（エントリ修正後に orchagent 再起動または再 SET） |
| 4 | `VDPU.main_dpu_ids` に不正な DPU 名 | orchagent | ENI→VDPU→DPU 解決失敗、WARN 出力 | WARN | なし（DPU 名修正後に再起動） |
| 5 | `VIP_TABLE` エントリ不在 | orchagent | THROW → orchagent クラッシュ + supervisord 再起動 | (THROW=CRIT) | supervisord が orchagent を再起動、VIP_TABLE 書き込みで解消 |
| 6 | `swbus_port` フィールド欠如 | caclmgrd | iptables ルール未生成、swbus 通信遮断の可能性 | INFO | `swbus_port` を含む再 SET で iptables ルール追加 |
| 7 | iptables コマンド失敗 | caclmgrd | 部分的なルール未適用、処理継続 | ERROR | 次回更新時に再試行なし（手動 iptables 操作が必要） |
| 8 | DPU が STATE_DB に不在 | sonic-gnmi | gNMI request が NotFound エラー | (gRPC ERROR) | chassisd / pmon が STATE_DB を書き込むと自動解消 |
| 9 | STATE_DB に ip_address フィールドなし | sonic-gnmi | gNMI request が NotFound エラー | (gRPC ERROR) | STATE_DB 更新後に自動解消 |
| 10 | CONFIG_DB に gnmi_port なし | sonic-gnmi | DefaultGNMIPort `50052` を使用（非エラー） | なし | ポート不一致なら接続試行が失敗するが resolver は成功を返す |
