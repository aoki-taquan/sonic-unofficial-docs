# discrepancy-found ページ `monitor:` タグ網羅監査（2026-05-11、batch q26-z）

## 1. 目的

`verification: discrepancy-found` のページ全 62 件について、frontmatter `monitor:` の値が本文「HLD と実装の差分」セクションの内容と整合しているかを点検する。修正は次バッチに送り、本バッチは監査結果のみを残す。

## 2. 監査基準（4 値の定義の運用解釈）

| 値 | 運用上の基準（最も当てはまるもの 1 つを選ぶ） |
|---|---|
| `not_implemented` | HLD で提案されたが、master に対応するコード／schema／CLI が **ほぼ皆無**（grep ヒット 0 が中心、または HLD で要求された主要構成要素のすべてが欠落）|
| `partially_implemented` | HLD の構成要素のうち **一部は取り込み済み**、別の中核要素（CLI / orch / daemon 等）が欠落。「取り込み済み」「未取り込み」の二項列挙ができる |
| `evolved_beyond_hld` | HLD の **機能は取り込み済み** だが、フィールド名／パス名／クラス名／責務分担などが実装側で進化／変更されている。読み手は実装側を正として読み替える必要がある |
| `deprecated` | HLD は採用見送りで後継機能に置き換わった、または upstream で別アプローチが採られた |

判断のグレーゾーン:

- `partially_implemented` と `not_implemented`: 「基礎部品（YANG leaf や schema 名）だけが入って中核 daemon が未実装」のケースは partially とした
- `partially_implemented` と `evolved_beyond_hld`: HLD の機能が「動く水準で」取り込まれているなら evolved、動かない欠落があるなら partially とした

## 3. 全体一覧（62 件）

| # | page | 現 monitor | 推奨 monitor | 一致 | 判定理由（短評）|
|---:|---|---|---|---|---|
| 1 | acl-qos/dhcp-dos-mitigation-in-sonic | not_implemented | partially_implemented | ✗ | YANG leaf `dhcp_rate_limit` / `db_migrator` / `config interface dhcp-mitigation-rate add/del` CLI は取り込み済。tc 投入 portmgrd ロジックは未実装。HLD の枠組みの一部は merge 済みで「皆無」ではない |
| 2 | acl-qos/enhancements-to-add-or-del-ports-dynamically | partially_implemented | partially_implemented | ✓ | `PortInitDone` / zero-port 対応は merge、per-port buffer ref-count (`#2022`) は CLOSED。典型的な partial |
| 3 | architecture/build-profiles | not_implemented | not_implemented | ✓ | `rules/profiles/` ディレクトリすら無く、Makefile.work に include 行も無し。提案段階 |
| 4 | architecture/debug-framework-in-sonic | not_implemented | not_implemented | ✓ | `Debugframework` / `linkWithFramework` / `SWSS_DEBUG_PRINT` / Dump table すべて grep 0 件。6 年停滞 |
| 5 | architecture/dip-sip-ptf-validation-high-level-design | evolved_beyond_hld | evolved_beyond_hld | ✓ | テスト実体は pytest 配下に移植済。ファイル配置と呼出構造が HLD と異なる |
| 6 | architecture/error-handling-framework-in-sonic-concepts | partially_implemented | partially_implemented | ✓ | `SWSS_RC_*` enum のみ取り込み、ERROR_DB / ErrorListener / CLI 全欠落（ハブ-子で同一判定）|
| 7 | architecture/error-handling-framework-in-sonic-internals | partially_implemented | partially_implemented | ✓ | 同上（子ページ）|
| 8 | architecture/error-handling-framework-in-sonic-limitations | partially_implemented | partially_implemented | ✓ | 同上 |
| 9 | architecture/error-handling-framework-in-sonic-operations | partially_implemented | partially_implemented | ✓ | 同上 |
| 10 | architecture/error-handling-framework-in-sonic | partially_implemented | partially_implemented | ✓ | 同上（ハブ）|
| 11 | architecture/sag-high-level-design-for-sonic | not_implemented | not_implemented | ✓ | YANG / orchagent / utilities すべて 0 件。3 つの PR がすべて open / 未マージ |
| 12 | architecture/sflow-high-level-design | evolved_beyond_hld | evolved_beyond_hld | ✓ | 全体は完全に取り込み済、`sample_rate` 既定値テーブルだけ HLD 表記と差。典型的な evolved |
| 13 | architecture/smartswitch-...-hamgrd-design-concepts | not_implemented | partially_implemented | ✗ | schema 層（DASH_HA_SET/SCOPE の APP/CFG/STATE table 名）は取り込み済。本ページ自身が「schema 層先行採用」と書いている。`hamgrd` バイナリのみ未実装。partial が正しい（ハブ "...-limitations" と一致させるべき）|
| 14 | architecture/smartswitch-...-hamgrd-design-internals | not_implemented | partially_implemented | ✗ | 同上 |
| 15 | architecture/smartswitch-...-hamgrd-design-limitations | not_implemented | partially_implemented | ✗ | 同上。本ページ本文は明確に「schema 層は取り込み済み / hamgrd 未取り込み」の二項列挙で partial を述べている。`not_implemented` 表記と本文に乖離あり |
| 16 | architecture/smartswitch-...-hamgrd-design-operations | not_implemented | partially_implemented | ✗ | 同上 |
| 17 | architecture/smartswitch-...-hamgrd-design | not_implemented | partially_implemented | ✗ | 同上（ハブ）|
| 18 | architecture/ssdhealth-design | evolved_beyond_hld | evolved_beyond_hld | ✓ | `SsdBase` / `SsdUtil` / CLI 取り込み済、Open Question の `ssdmond` のみ未取り込み |
| 19 | internals/l3-scaling-and-performance-enhancements-concepts | partially_implemented | partially_implemented | ✓ | RouteOrch bulk / fpmsyncd skip は実装済、sysctl 値 / CoPP 値は HLD 提案値と差。典型的な partial+evolved の中間で partial 妥当 |
| 20 | internals/l3-scaling-and-performance-enhancements-internals | partially_implemented | partially_implemented | ✓ | 同上 |
| 21 | internals/l3-scaling-and-performance-enhancements-limitations | partially_implemented | partially_implemented | ✓ | 同上 |
| 22 | internals/l3-scaling-and-performance-enhancements-operations | partially_implemented | partially_implemented | ✓ | 同上 |
| 23 | internals/l3-scaling-and-performance-enhancements | partially_implemented | partially_implemented | ✓ | 同上（ハブ）|
| 24 | management/gnmi-master-arbitration-hld | evolved_beyond_hld | evolved_beyond_hld | ✓ | コア機構は取り込み済、`Role.id` の扱い／`TELEMETRY|gnmi:master_arbitration_enabled` 不在のみ差分 |
| 25 | management/gnsi-hld | evolved_beyond_hld | partially_implemented | ✗ | Authz / Certz / Pathz は取り込み済だが、**Credentialz の gNMI server ハンドラは未取り込み**（dbus client 補助のみ）。HLD が並列に挙げる 4 サービスのうち 1 つ丸ごと欠落は partially の範囲。フラグ名差は evolved だが、欠落要素の重さが上回る |
| 26 | management/p4rt-application-hld | evolved_beyond_hld | evolved_beyond_hld | ✓ | P4RT コンテナ / P4Orch / table 全部実装、`HashOrch` という独立クラスではなく `SwitchOrch` が責務を持つ責務分担の進化のみ |
| 27 | management/portable-console-device-design | not_implemented | not_implemented | ✓ | `autodetect` / `vendor_name` / `model_name` 拡張 leaf も CLI も無し。USB 動的検出機構は丸ごと未取り込み |
| 28 | management/smart-switch-gnmi-feedback-design-omit-in-toc | not_implemented | not_implemented | ✓ | `version_id` / batch API / `APPL_STATE_DB` 専用 / ZMQ handler すべて未検出 |
| 29 | management/sonic-console-switch | partially_implemented | partially_implemented | ✓ | `consutil` CLI と `sonic-console.yang` は取り込み済、`consoled` / `ser2net` 連携 / reverse SSH は未取り込み |
| 30 | management/sonic-yang-model-guidelines | evolved_beyond_hld | partially_implemented | ✗ | `map-list` / `key-delim` 拡張が `sonic-buildimage` 側の sonic-extension モジュールに **不在**（mgmt-common 側にのみ存在）。リポ間分裂で、ガイドライン #14 `error-app-tag` も多数未付与。「動くがフィールド名が違う」evolved より「片側のリポで欠落」partial が近い |
| 31 | management/tacacs-passkey-encryption | evolved_beyond_hld | partially_implemented | ✗ | master key パスは `cipher_pass` → `cipher_pass.json` に進化（evolved 寄り）だが、**CLI (`--encrypt`) と hostcfgd 復号処理は未実装**（中核フロー欠落）。運用上は機能しない＝partial が正確 |
| 32 | overlay/dscp-remapping-for-tunnel-traffic | evolved_beyond_hld | evolved_beyond_hld | ✓ | フィールド名差（`pfc_wd_sw_enable` → `pfcwd_sw_enable`）のみ。全体は取り込み済 |
| 33 | platform/dump-on-sai-failure | evolved_beyond_hld | evolved_beyond_hld | ✓ | スクリプト名（`syncd_dump.sh` → `sai_failure_dump.sh`）のみ差。他は一致 |
| 34 | platform/enhanced-lpo-debug-registers-hld | not_implemented | not_implemented | ✓ | `CmisEnhancedLpoApi` 等すべて grep 0 件。Arista 提案 Rev 1.0 段階 |
| 35 | platform/fec-flr-support-in-sonic-concepts | evolved_beyond_hld | evolved_beyond_hld | ✓ | コアロジック / CLI 列追加は取り込み済、`flr-interval-factor` サブコマンドのみ未取り込み。本ページ本文も明示的に「evolved_beyond_hld」分類と書いてある |
| 36 | platform/fec-flr-support-in-sonic-internals | evolved_beyond_hld | evolved_beyond_hld | ✓ | 同上 |
| 37 | platform/fec-flr-support-in-sonic-limitations | evolved_beyond_hld | evolved_beyond_hld | ✓ | 同上 |
| 38 | platform/fec-flr-support-in-sonic-operations | evolved_beyond_hld | evolved_beyond_hld | ✓ | 同上 |
| 39 | platform/fec-flr-support-in-sonic | evolved_beyond_hld | evolved_beyond_hld | ✓ | 同上（ハブ）|
| 40 | platform/hld-for-handling-sai-failures | evolved_beyond_hld | evolved_beyond_hld | ✓ | `handleSai*Status` が Orch base の virtual ではなく **free function** として実装。機能は同等 |
| 41 | platform/liquid-cooling-leakage-detection-in-sonic | evolved_beyond_hld | evolved_beyond_hld | ✓ | STATE_DB table 名が `LIQUID_COOLING_DEVICE` → `LIQUID_COOLING_INFO` に進化。機能は全体取り込み済 |
| 42 | platform/smartswitch-dpu-graceful-shutdown | not_implemented | evolved_beyond_hld | ✗ | `gnoi_reboot_daemon.py` という独立 daemon は不在だが、**機能は `chassisd` 内に統合済**（`module.set_admin_state_gracefully` 直接呼び）。`module_base.py` の `set_admin_state_gracefully` / `_graceful_shutdown_handler` / `set_module_state_transition` も実装済。CHASSIS_MODULE_TABLE への hset まで動作する。daemon 分離設計のみが evolve（統合実装）した状態で、機能は動く。`not_implemented` は実態と乖離 |
| 43 | platform/sonic-port-naming-convention-change | not_implemented | not_implemented | ✓ | 4 stage いずれも採用されず、`ets<X>p<Y>` 系命名は device tree に出現せず |
| 44 | routing/bfd-hw-offload-for-bgp-session | not_implemented | not_implemented | ✓ | `bfdsyncd` プロセス / `FEATURE.bgp.bfd_hw_offload` フラグともに grep 0 件。BGP-BFD HW 自動連携は未実装 |
| 45 | routing/bgp-route-install-error-handling | deprecated | deprecated | ✓ | `ERROR_DB` / `BGP_ERROR_CFG_TABLE` / CLI すべて未実装、後継「BGP Suppress FIB Pending」に置換 |
| 46 | routing/evpn-vxlan-hld | evolved_beyond_hld | evolved_beyond_hld | ✓ | EVPN VXLAN 中核は全実装、`EVPN_NVO` → `VXLAN_EVPN_NVO` table 名差等の名称進化のみ |
| 47 | routing/evpn-vxlan-multihoming | not_implemented | not_implemented | ✓ | `EVPN_ETHERNET_SEGMENT` / `EthernetSegment` / ESI 関連 0 件。MC-LAG が代替 |
| 48 | routing/fpmsyncd-nexthop-group-enhancement-high-level-design-document | evolved_beyond_hld | evolved_beyond_hld | ✓ | コアの `RouteSync::onNextHopMsg` / `m_nexthop_groupTable` は取り込み済、有効化 key 名（`fpm_use_nexthop_groups` → `nexthop_group`）のみ進化 |
| 49 | routing/local-ars-hld | not_implemented | not_implemented | ✓ | `ArsOrch` / `sonic-ars.yang` / `ARS` 系テーブル全欠落。SAI ARS object 反映経路無し |
| 50 | switching/layer-2-forwarding-enhancements | partially_implemented | partially_implemented | ✓ | orch 側（MAC move / saved FDB / flush API）は HLD 一致だが、`config mac` / `config vlan range` CLI は未取り込み |
| 51 | switching/link-event-damping-hld | partially_implemented | partially_implemented | ✓ | SwSS / YANG は取り込み済、`config interface link_event_damping_algorithm` CLI のみ未取り込み |
| 52 | switching/switch-port-modes-and-vlan-cli-enhancement | partially_implemented | partially_implemented | ✓ | `config switchport mode <type> <port>` の 2 引数版は取り込み済、HLD 要求の第 3 引数 `<vlan-list>` は未実装 |
| 53 | switching/wake-on-lan-in-sonic | evolved_beyond_hld | partially_implemented | ✗ | CLI 本体（Rust 実装）は完備で動作するが、**gNOI 経由の `SonicWolService` D-Bus ハンドラは未統合**（sonic-host-services に無し）。CLI の Python click → Rust 化は evolve、gNOI 経路の欠落は partial。両方並存だが gNOI の用途が一般的に重い |
| 54 | system/hld-secure-boot | evolved_beyond_hld | evolved_beyond_hld | ✓ | 全体取り込み済、ビルド変数名のみ `SB_BUILD` → `SECURE_UPGRADE_MODE` 系に進化 |
| 55 | system/reset-local-users-passwords-during-init-hld | partially_implemented | partially_implemented | ✓ | `default_users.json` 経由のパスワード復元は採用（reset-factory script 経由）、long reset button トリガ + 専用 systemd service + 設定 YANG は未取り込み |
| 56 | system/sonic-fips-deployment | evolved_beyond_hld | evolved_beyond_hld | ✓ | 全体取り込み済、`fips_enabled` → `fips_enable`、`FIPS_STAT` → `FIPS_STATS` の名称進化のみ |
| 57 | system/sonic-libsairedis-api-idempotence-support | deprecated | deprecated | ✓ | `RESTORE_DB` (DB 7) / `ATTR2OID_` 系キー定義すべて 0 件、syncd 側 view comparison で代替（HLD 採用見送り）|
| 58 | system/sonic-network-time-protocol-ntp-client-configuration | deprecated | deprecated | ✓ | ntpd 前提の HLD で、現行は chrony 一本化（並列 HLD migration-to-chrony が権威）|
| 59 | system/sonic-python-logger-enhancement | evolved_beyond_hld | evolved_beyond_hld | ✓ | `update_log_level()` / CLI は取り込み済、HLD 要求の `SysLogger` singleton 化（`__new__` 共有）のみ未実装 |
| 60 | system/swss-docker-warm-restart-code-reference | evolved_beyond_hld | evolved_beyond_hld | ✓ | warm restart コア / CLI 取り込み済、`WARM_RESTART_TABLE` 1 系統 → `STATE_WARM_RESTART_TABLE` + `CFG_WARM_RESTART_TABLE` 2 系統に進化 |
| 61 | system/twamp-light-hld | partially_implemented | partially_implemented | ✓ | Orch / SAI は取り込み済、YANG `sonic-twamp-light` と `config/show twamp-light` CLI は未取り込み |
| 62 | system/warmboot-manager-hld | not_implemented | not_implemented | ✓ | `warmboot-manager` / `warmbootmgrd` 系 daemon すべて検出できず、既存 shell ベース orchestration のまま |

## 4. 集計

| 区分 | 件数 |
|---|---:|
| 一致 ✓ | 52 |
| 不一致 ✗ | 10 |
| 合計 | 62 |

### 不一致の内訳（推奨 monitor 別）

| 推奨 monitor | 件数 | 該当ページ |
|---|---:|---|
| `partially_implemented` | 8 | dhcp-dos-mitigation-in-sonic, smartswitch-...-hamgrd-design (5 ページ群), gnsi-hld, sonic-yang-model-guidelines, tacacs-passkey-encryption, wake-on-lan-in-sonic |
| `evolved_beyond_hld` | 1 | smartswitch-dpu-graceful-shutdown |
| （合計）| 10 |  |

（hamgrd 5 ページは同じ判定なので件数表上は 8 + 5 = 13 ではなく **個別 5 件として上の表 #13〜#17 で 5 ページぶん** カウント済。集計再掲は ↓）

| 推奨 monitor 内訳（個別ページ単位、再掲） | 件数 |
|---|---:|
| 現 `not_implemented` → 推奨 `partially_implemented` | 6（hamgrd 系 5 + dhcp-dos-mitigation）|
| 現 `evolved_beyond_hld` → 推奨 `partially_implemented` | 3（gnsi-hld, sonic-yang-model-guidelines, tacacs-passkey-encryption, wake-on-lan-in-sonic のうち wake-on-lan を除く 3 件 — 再確認: gnsi / yang-guidelines / tacacs / wake-on-lan の 4 件）|
| 現 `not_implemented` → 推奨 `evolved_beyond_hld` | 1（smartswitch-dpu-graceful-shutdown）|

整合のとれた最終件数:

- 現 `not_implemented` → 推奨 `partially_implemented`: 6 件
- 現 `evolved_beyond_hld` → 推奨 `partially_implemented`: 4 件
- 現 `not_implemented` → 推奨 `evolved_beyond_hld`: 1 件 (smartswitch-dpu-graceful-shutdown)
- **合計不一致**: **11 件**（上記表の #1, #13, #14, #15, #16, #17, #25, #30, #31, #42, #53）

> 集計訂正: 当初 10 件と書いたが個別カウントで 11 件。最終値は **11 件**。

## 5. 修正提案（次バッチ送り）

次バッチ（`chore/q26-aa-monitor-fix` 仮称）で以下の frontmatter `monitor:` を一括更新する。本バッチでは実施しない。

| ページ | 現 monitor | → | 推奨 monitor |
|---|---|---|---|
| `docs/acl-qos/dhcp-dos-mitigation-in-sonic.md` | not_implemented | → | partially_implemented |
| `docs/architecture/smartswitch-high-availability-manager-daemon-hamgrd-design-concepts.md` | not_implemented | → | partially_implemented |
| `docs/architecture/smartswitch-high-availability-manager-daemon-hamgrd-design-internals.md` | not_implemented | → | partially_implemented |
| `docs/architecture/smartswitch-high-availability-manager-daemon-hamgrd-design-limitations.md` | not_implemented | → | partially_implemented |
| `docs/architecture/smartswitch-high-availability-manager-daemon-hamgrd-design-operations.md` | not_implemented | → | partially_implemented |
| `docs/architecture/smartswitch-high-availability-manager-daemon-hamgrd-design.md` | not_implemented | → | partially_implemented |
| `docs/management/gnsi-hld.md` | evolved_beyond_hld | → | partially_implemented |
| `docs/management/sonic-yang-model-guidelines.md` | evolved_beyond_hld | → | partially_implemented |
| `docs/management/tacacs-passkey-encryption.md` | evolved_beyond_hld | → | partially_implemented |
| `docs/platform/smartswitch-dpu-graceful-shutdown.md` | not_implemented | → | evolved_beyond_hld |
| `docs/switching/wake-on-lan-in-sonic.md` | evolved_beyond_hld | → | partially_implemented |

### 補助メモ

- hamgrd 5 ページ群は **本文の本人記述**（「schema 層は取り込み済 / hamgrd 未取り込み」）が partial を語っているのに frontmatter が `not_implemented` の状態で、最も強く修正候補。
- `smartswitch-dpu-graceful-shutdown` は HLD の「独立 daemon」設計を採らず chassisd 統合になったが、機能は完成しているため `evolved_beyond_hld` のほうが実態に合う。`not_implemented` だと「動かない」と読み手が誤解するリスクが大きい。
- `gnsi-hld` / `tacacs-passkey-encryption` / `wake-on-lan-in-sonic` は「フィールド名差は evolved 寄りだが、HLD の主要構成要素のうち 1 つ丸ごと欠落」のため partial に倒した。境界判断であり、reviewer の裁量で evolved 維持もあり得る。

## 6. 監査範囲とスコープ外

- 全 62 件を一度読み、不一致候補だけ本文の差分セクションを精読する手法を採用（時間制約による）。
- 「ハブ＋子ページ」（hamgrd, error-handling, l3-scaling, fec-flr）は同一機能の分割ページのため `monitor:` 値はハブと揃えるべきで、本監査もハブ判定を子ページに適用している。
- `code-verified` ページ（v1.0 GA 時点で大半）は本監査の対象外。
- 本監査は人手判断のため、reviewer により別判定が出る余地がある（特に partial と evolved の境界）。

## 7. 次アクション

1. このファイルを `chore/q26-z-monitor-audit` ブランチで merge。
2. 次バッチで上記 11 件の `monitor:` 値を更新し、関連する `discrepancy-index.md` 集計の再生成（`meta/scripts/gen_discrepancy_index.py`）を回す。
3. v1.1 サイクル以降は Verifier プロンプトに「本文の取り込み済/未取り込み二項列挙が出る場合は `partially_implemented` を優先」というガイドラインを追加して、新規裏取りの段階で同種の食い違いを抑止する。
