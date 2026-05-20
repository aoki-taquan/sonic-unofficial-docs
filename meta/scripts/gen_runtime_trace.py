#!/usr/bin/env python3
"""
Generate <!-- runtime-trace --> blocks for tier_low[:60] config-db pages.
Direction B: CDB → 実コンテナ動作までの 4 段階トレース
  段階 1: Consumer 登録 (誰が CONFIG_DB を購読するか)
  段階 2: CFG→APPL 翻訳 (APPL_DB テーブルへの変換、なければ "なし")
  段階 3: APPL→SAI (SAI API の呼び出し、なければ "なし" or "kernel/daemon")
  段階 4: タイミング+副作用 (いつ適用されるか、副作用)

Also writes meta/_intermediate/cdb-flow/<slug>-runtime-trace.md
"""

import json
import os

WT = "/home/coder/sonic-unofficial-docs"

# Runtime trace data per slug
# Format: (consumer, appl_table, sai_api, timing_notes)
TRACE_DATA = {
    "aaa": {
        "consumer": "`hostcfgd` (`sonic-host-services`) の `AaaHandler`",
        "appl": "なし (APPL_DB 中継なし)",
        "sai": "なし (SAI 非経由 — Linux PAM / NSS 設定ファイルを直接書き換える)",
        "timing": "CONFIG_DB の `AAA` エントリ変化を `ConfigDBConnector` で検知次第即時反映。PAM ファイル (`/etc/pam.d/common-auth` 等) の書き換えは同期的。次回ログイン試行から新設定が有効になる。",
        "side_effects": "PAM 設定ファイル上書き → 進行中セッションには影響なし（PAM は認証時にファイルを読む）。`tacacs+`/`radius` が選択された場合 `nslcd`/`radiusd` 設定も更新。",
        "stage1_note": "`hostcfgd` が起動時に `CONFIG_DB` を `select()` して購読。`TableConsumer` ではなく `ConfigDBConnector.subscribe()`。",
    },
    "as-path-set": {
        "consumer": "`bgpcfgd` (`sonic-bgpcfgd`)",
        "appl": "なし (FRR vtysh コマンドで直接 BGP デーモンに注入)",
        "sai": "なし (SAI 非経由 — FRR プロセス内部で AS-path フィルタとして使用)",
        "timing": "CONFIG_DB 変化を `bgpcfgd` が検知後、FRR `vtysh -c` コマンドを発行。FRR BGP デーモンは即時反映。",
        "side_effects": "FRR プロセスへの設定注入のみ。既存 BGP セッションには次回 UPDATE 送信時または policy soft-clear 実施時に適用。",
        "stage1_note": "`bgpcfgd` は `ConfigDBConnector.listen()` で `BGP_PEER_RANGE`/`BGP_GLOBALS` 等と合わせて購読。",
    },
    "auto-techsupport-feature": {
        "consumer": "`auto_techsupport_handler` (`sonic-host-services`)",
        "appl": "なし (APPL_DB 中継なし)",
        "sai": "なし (SAI 非経由 — syslog 監視・techsupport 生成をトリガー)",
        "timing": "CONFIG_DB の `AUTO_TECHSUPPORT_FEATURE` エントリ変化を検知次第即時反映。次回 core dump または syslog イベント発生時から新設定が有効。",
        "side_effects": "`techsupport` の自動生成をフィーチャー単位で ON/OFF。過去の coredump イベントには遡及しない。",
        "stage1_note": "`auto_techsupport_handler` は `hostcfgd` 内部のサブハンドラとして動作。",
    },
    "auto-techsupport": {
        "consumer": "`auto_techsupport_handler` (`sonic-host-services`)",
        "appl": "なし (APPL_DB 中継なし)",
        "sai": "なし (SAI 非経由 — global techsupport 設定)",
        "timing": "CONFIG_DB の `AUTO_TECHSUPPORT` エントリ変化を検知次第即時反映。次回 coredump または syslog イベント発生時から有効。",
        "side_effects": "`max_core_size`/`since` 等のグローバル制限を更新。既存 coredump ファイルの削除・保存には非遡及。",
        "stage1_note": "global テーブル (single key `GLOBAL`) と feature テーブルを同一ハンドラが購読。",
    },
    "banner-message": {
        "consumer": "`hostcfgd` の `BannerMessageHandler`",
        "appl": "なし (APPL_DB 中継なし)",
        "sai": "なし (SAI 非経由 — `/etc/issue` / `/etc/issue.net` / sshd banner ファイルを書き換え)",
        "timing": "CONFIG_DB 変化を検知次第即時にファイル書き換え。次回 SSH / console ログイン時から新 banner が表示される。",
        "side_effects": "既存セッションへの影響なし。`sshd` の再起動は不要（banner は接続時に読む）。",
        "stage1_note": "`BANNER_MESSAGE` テーブルの key は `login` / `logout` / `motd`。",
    },
    "bgp-aggregate-address": {
        "consumer": "`bgpcfgd`",
        "appl": "なし (FRR vtysh 経由)",
        "sai": "なし (FRR が APPL_DB `ROUTE_TABLE` に集約ルートを注入 → `RouteOrch` → `sai_route_api`)",
        "timing": "`bgpcfgd` が変化を検知後 FRR に `aggregate-address` コマンドを発行。BGP 経路集約は FRR の次回 BGP Update 送信タイミングで適用。",
        "side_effects": "集約ルートが FRR から BGP ピアに広告される。`summary-only` フラグ有無によりより細かいプレフィクスの withdraw が起こる。",
        "stage1_note": "`BGP_AGGREGATE_ADDRESS` は AF ごとの key `<vrf>|<prefix>` で管理。",
    },
    "bgp-allowed-prefixes": {
        "consumer": "`bgpcfgd`",
        "appl": "なし (FRR vtysh 経由)",
        "sai": "なし (FRR BGP フィルタのみ)",
        "timing": "`bgpcfgd` が変化を検知後 FRR prefix-list / route-map を更新。既存ピアには `soft clear` が必要な場合がある。",
        "side_effects": "許可プレフィクスの変更は既存 BGP セッションの UPDATE 再送を引き起こす可能性がある。",
        "stage1_note": "`BGP_ALLOWED_PREFIXES` テーブルは SONiC の内部フィルタ管理用。",
    },
    "bgp-device-global": {
        "consumer": "`BgpGlobalStateOrch` (orchagent 直接 CFG 購読)",
        "appl": "なし (orchagent が直接 SAI を呼び出す)",
        "sai": "`sai_switch_api` (TCP MD5 等のヒント設定、ECMP hash seed 等)",
        "timing": "orchagent 起動時および CONFIG_DB 変化時に即時反映。SAI call は同期的。",
        "side_effects": "Switch-global な BGP 関連パラメータ (ECMP) の変更は全 BGP ネクストホップに影響する。",
        "stage1_note": "`BGP_DEVICE_GLOBAL` は `BgpGlobalStateOrch` が `TableConsumer` で購読。",
    },
    "bgp-globals-af-aggregate-addr": {
        "consumer": "`bgpcfgd`",
        "appl": "なし (FRR vtysh 経由)",
        "sai": "なし (FRR BGP のみ)",
        "timing": "変化検知後 FRR に AF 固有の aggregate-address コマンドを発行。",
        "side_effects": "AF 毎の集約ルート広告が変化。`summary-only` 有効時は子プレフィクスが withdraw される。",
        "stage1_note": "`BGP_GLOBALS_AF_AGGREGATE_ADDR` は `<vrf>|<af>|<prefix>` の key 構造。",
    },
    "bgp-globals-af-network": {
        "consumer": "`bgpcfgd`",
        "appl": "なし (FRR vtysh 経由)",
        "sai": "なし (FRR BGP network コマンド)",
        "timing": "変化検知後 FRR に `network <prefix>` コマンドを発行。次回 BGP Update で広告開始。",
        "side_effects": "指定プレフィクスが BGP テーブルに inject されピアに広告される。ルートが存在しない場合 null-route が生成される可能性。",
        "stage1_note": "`BGP_GLOBALS_AF_NETWORK` は `<vrf>|<prefix>` の key 構造。",
    },
    "bgp-globals-af": {
        "consumer": "`bgpcfgd`",
        "appl": "なし (FRR vtysh 経由)",
        "sai": "なし (FRR BGP の AF レベル設定)",
        "timing": "変化検知後 FRR に AF の global 設定コマンドを発行。既存セッションへの影響は AF の再ネゴシエーションを要する場合がある。",
        "side_effects": "Maximum-paths, redistribute 設定など AF 全体の動作に影響。変更によっては BGP session reset が発生する。",
        "stage1_note": "`BGP_GLOBALS_AF` は `<vrf>|<af>` の key 構造。",
    },
    "bgp-globals": {
        "consumer": "`bgpcfgd`",
        "appl": "なし (FRR vtysh 経由)",
        "sai": "なし (FRR BGP グローバル設定)",
        "timing": "変化検知後 FRR に `router bgp <asn>` 等のグローバルコマンドを発行。AS 番号変更は BGP session reset を引き起こす。",
        "side_effects": "AS 番号・Router ID 変更は全 BGP ピアとの session リセットを引き起こす。graceful-restart 設定変更は次回ネゴシエーション時に有効。",
        "stage1_note": "`BGP_GLOBALS` は `<vrf>` の key 構造。",
    },
    "bgp-monitors": {
        "consumer": "`bgpcfgd`",
        "appl": "なし (FRR vtysh 経由)",
        "sai": "なし (BMP / FRR モニタリング設定)",
        "timing": "変化検知後 FRR に BGP モニタリング設定を注入。BMP セッションは設定適用後に確立を試みる。",
        "side_effects": "BMP サーバへの接続が開始/停止される。既存 BGP セッションには影響なし。",
        "stage1_note": "`BGP_MONITORS` は BMP target server を定義。`bmpcfgd` との連携もある。",
    },
    "bgp-neighbor-af": {
        "consumer": "`bgpcfgd`",
        "appl": "なし (FRR vtysh 経由)",
        "sai": "なし (FRR BGP ネイバー AF 設定)",
        "timing": "変化検知後 FRR にネイバー AF コマンドを発行。`activate`/`deactivate` は BGP session に影響する場合がある。",
        "side_effects": "ネイバーの AF 有効/無効化は該当 AF の route 交換を即座に停止/開始。policy 変更は soft-clear 後に有効。",
        "stage1_note": "`BGP_NEIGHBOR_AF` は `<vrf>|<neighbor>|<af>` の key 構造。",
    },
    "bgp-neighbor": {
        "consumer": "`bgpcfgd`",
        "appl": "なし (FRR vtysh 経由)",
        "sai": "なし (FRR BGP ネイバー管理)",
        "timing": "変化検知後 FRR にネイバー定義コマンドを発行。新規ネイバーは即座に接続試行を開始。削除は BGP session を即座に切断。",
        "side_effects": "ネイバー削除は該当 BGP session の NOTIFICATION 送信と経路削除を引き起こす。パスワード変更は session リセットを引き起こす。",
        "stage1_note": "`BGP_NEIGHBOR` は `<vrf>|<neighbor>` の key 構造。peer-group を参照する場合がある。",
    },
    "bgp-peer-group-af": {
        "consumer": "`bgpcfgd`",
        "appl": "なし (FRR vtysh 経由)",
        "sai": "なし (FRR BGP peer-group AF 設定)",
        "timing": "変化検知後 FRR に peer-group の AF コマンドを発行。peer-group メンバー全員に影響。",
        "side_effects": "peer-group の AF policy 変更はメンバー全 BGP session に波及。soft-clear が必要な場合がある。",
        "stage1_note": "`BGP_PEER_GROUP_AF` は `<vrf>|<pg_name>|<af>` の key 構造。",
    },
    "bgp-peer-group": {
        "consumer": "`bgpcfgd`",
        "appl": "なし (FRR vtysh 経由)",
        "sai": "なし (FRR BGP peer-group 設定)",
        "timing": "変化検知後 FRR に `neighbor <pg_name> peer-group` 等のコマンドを発行。peer-group 削除はメンバーネイバー全体への影響あり。",
        "side_effects": "peer-group 削除はメンバーの BGP session を切断。AS/password 変更はメンバー全 session リセット。",
        "stage1_note": "`BGP_PEER_GROUP` は `<vrf>|<pg_name>` の key 構造。",
    },
    "bgp-peer-range": {
        "consumer": "`bgpcfgd`",
        "appl": "なし (FRR vtysh 経由)",
        "sai": "なし (FRR BGP dynamic peer 設定)",
        "timing": "変化検知後 FRR に `bgp listen range <prefix> peer-group <pg>` を発行。指定プレフィクスからの接続を dynamic に受け入れ開始。",
        "side_effects": "指定プレフィクス内からの BGP 接続が自動的に対象 peer-group として処理される。既存の static ネイバーとは独立。",
        "stage1_note": "`BGP_PEER_RANGE` は `<vrf>|<prefix>` の key 構造。dynamic neighbor 機能。",
    },
    "bmp": {
        "consumer": "`bmpcfgd` (`sonic-bgpcfgd` パッケージ内)",
        "appl": "なし (FRR vtysh 経由で BMP 設定)",
        "sai": "なし (BMP は FRR の BGP モニタリングプロトコル、SAI 非経由)",
        "timing": "CONFIG_DB の `BMP` エントリ変化を検知後、FRR に BMP target station 設定を注入。BMP セッション確立は非同期。",
        "side_effects": "BMP サーバへの監視データ送信が開始/停止。FRR BGP 動作への影響なし。",
        "stage1_note": "`BMP` テーブルは BMP target server を定義。`bgpcfgd` と協調して動作。",
    },
    "breakout-cfg": {
        "consumer": "`xcvrd` / `portsyncd` (port breakout 処理)",
        "appl": "なし (breakout は `config reload` / `sonic-cfggen` 経由で PORT テーブル再生成)",
        "sai": "`sai_port_api` (port breakout — `SAI_PORT_ATTR_SPEED` / lane 再割り当て)",
        "timing": "BREAKOUT_CFG は `config interface breakout` コマンド実行時に CONFIG_DB に書き込まれる。実際の breakout は `config reload` または専用フローで PORT テーブルを再生成して適用。ダウンタイムが発生する。",
        "side_effects": "対象ポートの traffic が一時中断。breakout/un-breakout でポート名が変わる。関連する interface 設定も再設定が必要。",
        "stage1_note": "`BREAKOUT_CFG` は `platform.json` の breakout モード候補と照合される。",
    },
    "buffer-pg": {
        "consumer": "`buffermgrd` / `buffermgrdyn` → `BufferOrch` (APPL_DB 経由)",
        "appl": "`APP_BUFFER_PG_TABLE` (`BUFFER_PG_TABLE`) に書き込み",
        "sai": "`sai_buffer_api` — `sai_create_ingress_priority_group_attr` でポート毎の PG (Priority Group) バッファプロファイルを設定",
        "timing": "CONFIG_DB 変化を `buffermgrd(yn)` が検知後 APPL_DB に書き込み。`BufferOrch` が APPL_DB を購読して SAI call を発行。動的モードでは cable length / speed から自動計算。",
        "side_effects": "PG バッファ変更は ingress traffic の一時的な pause/drop に影響する可能性がある。warm-reboot では既存バッファ設定が保持される。",
        "stage1_note": "`BUFFER_PG` の key は `<port>|<pg_range>` (例: `Ethernet0|3-4`)。",
    },
    "buffer-pool": {
        "consumer": "`buffermgrd` / `buffermgrdyn` → `BufferOrch` (APPL_DB 経由)",
        "appl": "`APP_BUFFER_POOL_TABLE` に書き込み",
        "sai": "`sai_buffer_api` — `sai_create_buffer_pool` でバッファプール (ingress/egress, static/dynamic) を作成/更新",
        "timing": "CONFIG_DB 変化を `buffermgrd(yn)` が検知後 APPL_DB に書き込み。`BufferOrch` が SAI pool オブジェクトを作成/更新。既存プールの size 変更は即時反映。",
        "side_effects": "プールサイズ変更はそのプールを参照するすべてのプロファイルの実効バッファ量に影響。`xoff` 変更は PFC threshold に影響する。",
        "stage1_note": "`BUFFER_POOL` は `ingress_lossless_pool` / `egress_lossy_pool` 等の名前付きプール。",
    },
    "buffer-port-egress-profile-list": {
        "consumer": "`buffermgrd` → `BufferOrch` (APPL_DB 経由)",
        "appl": "`APP_BUFFER_PORT_EGRESS_PROFILE_LIST_TABLE` に書き込み",
        "sai": "`sai_port_api` — ポートの egress バッファプロファイルリストをバインド",
        "timing": "CONFIG_DB 変化を `buffermgrd` が検知後 APPL_DB に書き込み。`BufferOrch` が SAI port attribute を更新。",
        "side_effects": "対象ポートの egress バッファ割り当てが変更される。traffic に影響する可能性がある。",
        "stage1_note": "`BUFFER_PORT_EGRESS_PROFILE_LIST` の key は `<port>` (例: `Ethernet0`)。",
    },
    "buffer-port-ingress-profile-list": {
        "consumer": "`buffermgrd` → `BufferOrch` (APPL_DB 経由)",
        "appl": "`APP_BUFFER_PORT_INGRESS_PROFILE_LIST_TABLE` に書き込み",
        "sai": "`sai_buffer_api` / `sai_port_api` — ポートの ingress バッファプロファイルリストをバインド",
        "timing": "CONFIG_DB 変化を `buffermgrd` が検知後 APPL_DB に書き込み。`BufferOrch` が SAI port attribute を更新。",
        "side_effects": "対象ポートの ingress バッファ割り当てが変更される。PFC や lossless traffic に影響する可能性がある。",
        "stage1_note": "`BUFFER_PORT_INGRESS_PROFILE_LIST` の key は `<port>` (例: `Ethernet0`)。",
    },
    "buffer-profile": {
        "consumer": "`buffermgrd` / `buffermgrdyn` → `BufferOrch` (APPL_DB 経由)",
        "appl": "`APP_BUFFER_PROFILE_TABLE` に書き込み",
        "sai": "`sai_buffer_api` — `sai_create_buffer_profile` でバッファプロファイル (xon/xoff/size/dynamic_th) を作成",
        "timing": "CONFIG_DB 変化を `buffermgrd(yn)` が検知後 APPL_DB に書き込み。`BufferOrch` が SAI buffer profile オブジェクトを作成/更新。既存参照 (PG/Queue) は再バインドされる。",
        "side_effects": "プロファイル変更はそれを参照するすべての PG/Queue に即座に影響。`xoff` 変更は PFC pause frame 送信タイミングに影響。",
        "stage1_note": "動的バッファ管理 (`buffermgrdyn`) では cable length や speed から自動計算して上書きする。",
    },
    "buffer-queue": {
        "consumer": "`buffermgrd` → `BufferOrch` (APPL_DB 経由)",
        "appl": "`APP_BUFFER_QUEUE_TABLE` に書き込み",
        "sai": "`sai_buffer_api` — キューのバッファプロファイルをバインド",
        "timing": "CONFIG_DB 変化を `buffermgrd` が検知後 APPL_DB に書き込み。`BufferOrch` が SAI queue buffer attribute を更新。",
        "side_effects": "対象キューの egress バッファ割り当てが変更される。キューの動作中変更は一時的な traffic 影響を伴う可能性がある。",
        "stage1_note": "`BUFFER_QUEUE` の key は `<port>|<queue_range>` (例: `Ethernet0|0-2`)。",
    },
    "community-set": {
        "consumer": "`bgpcfgd`",
        "appl": "なし (FRR vtysh 経由で community-list を設定)",
        "sai": "なし (FRR BGP policy のみ)",
        "timing": "変化検知後 FRR に `ip community-list` コマンドを発行。次回 BGP route-map 評価から適用。",
        "side_effects": "community-list 変更は route-map を通じて BGP 経路のフィルタリング/属性に影響。soft-clear により即時反映が可能。",
        "stage1_note": "`COMMUNITY_SET` は SONiC の route policy 管理用 (OpenConfig 準拠)。",
    },
    "console-port": {
        "consumer": "`hostcfgd` (console port 管理) / `conserver` (コンソールサーバ)",
        "appl": "なし (APPL_DB 中継なし)",
        "sai": "なし (SAI 非経由 — Linux tty / conserver の設定を更新)",
        "timing": "CONFIG_DB 変化を検知後、`conserver.cf` 等の設定ファイルを書き換え。`conserver` デーモンの再起動または HUP シグナルで反映。",
        "side_effects": "コンソールポートの baud rate / flow control 変更は進行中のコンソール接続を切断する可能性がある。",
        "stage1_note": "`CONSOLE_PORT` の key は `<port_num>` (例: `1`)。",
    },
    "copp-group": {
        "consumer": "`coppmgrd` → `CoppOrch` (APPL_DB 経由)",
        "appl": "`APP_COPP_TABLE` に書き込み (`COPP_TABLE`)",
        "sai": "`sai_hostif_api` — `sai_create_hostif_trap_group` でトラップグループ (policer 込み) を作成/更新",
        "timing": "CONFIG_DB 変化を `coppmgrd` が検知後 `APP_COPP_TABLE` に書き込み。`CoppOrch` が SAI trap group を更新。既存トラップのグループ再割り当ては即時反映。",
        "side_effects": "policer (rate/burst) 変更は CPU 宛て control plane traffic の制限に即座に影響。誤設定により制御プレーンへの過剰 traffic が発生する可能性。",
        "stage1_note": "`COPP_GROUP` の key はグループ名 (例: `default`, `queue4_group1`)。policer の `cir`/`cbs` を含む。",
    },
    "copp-trap": {
        "consumer": "`coppmgrd` → `CoppOrch` (APPL_DB 経由)",
        "appl": "`APP_COPP_TABLE` に書き込み",
        "sai": "`sai_hostif_api` — `sai_create_hostif_trap` でトラップ (BGP/ARP/OSPF 等) を作成/更新",
        "timing": "CONFIG_DB 変化を `coppmgrd` が検知後 APPL_DB に書き込み。`CoppOrch` が SAI hostif trap を更新。`FEATURE` テーブルの state により一部トラップが有効化される。",
        "side_effects": "トラップの `trap_action` 変更 (`drop`/`trap`/`copy`) は直ちに該当プロトコルの CPU 転送動作に影響。`OSPF` トラップ無効化で routing protocol が停止する可能性。",
        "stage1_note": "`COPP_TRAP` の key はトラップ名 (例: `bgp`, `arp_req`, `lldp`)。`COPP_GROUP` を `trap_group` フィールドで参照。",
    },
    "crm": {
        "consumer": "`CrmOrch` (orchagent 直接 CFG 購読)",
        "appl": "なし (orchagent が直接 CONFIG_DB を購読)",
        "sai": "`sai_switch_api` — SAI resource counter の polling interval / threshold を設定",
        "timing": "orchagent 起動時と CONFIG_DB 変化時に即時反映。SAI リソースカウンタの polling は設定した interval で定期実行される。",
        "side_effects": "`polling_interval` 変更は次回 polling から有効。`threshold_type`/`threshold` 変更はリソース枯渇警告の発火条件を変更する。",
        "stage1_note": "`CRM` の key は `Config` (単一エントリ)。各リソース (`ipv4_route`, `nexthop` 等) の threshold を個別設定。",
    },
    "debug-counter": {
        "consumer": "`DebugCounterOrch` (orchagent 直接 CFG 購読)",
        "appl": "なし (orchagent が直接 CONFIG_DB を購読)",
        "sai": "`sai_debug_counter_api` — デバッグカウンタ (drop reason 集計) を SAI に作成/削除",
        "timing": "orchagent が CONFIG_DB 変化を検知後即座に SAI debug counter を作成/削除。カウンタは作成後即座に集計開始。",
        "side_effects": "デバッグカウンタはハードウェアリソースを消費。作成後は `COUNTERS_DB` に counter OID がマッピングされ `show dropcounters` で確認可能。",
        "stage1_note": "`DEBUG_COUNTER` と `DEBUG_COUNTER_DROP_REASON` は対で使用。drop reason リストで集計対象を指定。",
    },
    "default-lossless-buffer-parameter": {
        "consumer": "`buffermgrdyn` (動的バッファ管理デーモン)",
        "appl": "なし (内部計算パラメータとして使用)",
        "sai": "なし (直接 SAI 呼び出しなし — 計算結果が `BUFFER_PROFILE` に反映されて SAI に到達)",
        "timing": "CONFIG_DB 変化を `buffermgrdyn` が検知後、すべての lossless バッファプロファイルを再計算。再計算された値が `APPL_DB` の `BUFFER_PROFILE_TABLE` に書き込まれ `BufferOrch` が SAI を更新。",
        "side_effects": "パラメータ変更はすべての lossless ポートのバッファプロファイルを再生成する。一時的な traffic 影響が発生する可能性。",
        "stage1_note": "`DEFAULT_LOSSLESS_BUFFER_PARAMETER` は静的バッファモード (`buffermgrd`) では使用されない。",
    },
    "device-neighbor-metadata": {
        "consumer": "`lldpmgrd` / `intfmgrd` / neighbor discovery",
        "appl": "なし (APPL_DB 中継なし)",
        "sai": "なし (SAI 非経由 — LLDP / neighbor テーブルのメタデータとして参照)",
        "timing": "CONFIG_DB に書き込まれると即時に参照可能。lldpmgrd が LLDP neighbor との照合に使用。",
        "side_effects": "neighbor metadata の変更は LLDP 情報の表示 / 解釈に影響。ネットワーク動作への直接影響なし。",
        "stage1_note": "`DEVICE_NEIGHBOR_METADATA` は `<device_name>` の key で hwsku / type 情報を保持。",
    },
    "device-neighbor": {
        "consumer": "`lldpmgrd` / neighbor 情報参照",
        "appl": "なし (APPL_DB 中継なし)",
        "sai": "なし (SAI 非経由 — neighbor topology 情報)",
        "timing": "CONFIG_DB に書き込まれると即時に参照可能。lldpmgrd が neighbor 情報との照合に使用。",
        "side_effects": "topology 情報の更新のみ。ネットワーク動作への直接影響なし。",
        "stage1_note": "`DEVICE_NEIGHBOR` の key は `<port>` (例: `Ethernet0`)。接続先 device / port 情報を保持。",
    },
    "device-runtime-metadata": {
        "consumer": "`sonic-cfggen` / 各種設定生成スクリプト",
        "appl": "なし (APPL_DB 中継なし)",
        "sai": "なし (SAI 非経由 — ランタイムメタデータ)",
        "timing": "デバイス起動時に `sonic-cfggen` が生成して CONFIG_DB に書き込む。実行時に参照されるが基本的に読み取り専用。",
        "side_effects": "直接的なネットワーク動作への影響なし。`DEVICE_METADATA` と組み合わせてシステム設定生成に使用。",
        "stage1_note": "`DEVICE_RUNTIME_METADATA` は動的に生成されるデバイス情報 (mac address 等) を保持。",
    },
    "dhcp-relay": {
        "consumer": "`dhcrelay` Docker コンテナ / `dhcp_relay` サービス",
        "appl": "なし (APPL_DB 中継なし)",
        "sai": "なし (SAI 非経由 — Linux カーネルの L4 DHCP relay)",
        "timing": "`dhcrelay` サービスが CONFIG_DB の `DHCP_RELAY` を読み込んで起動パラメータを決定。設定変更はサービス再起動が必要。",
        "side_effects": "DHCP server アドレスの変更は relay 転送先を変更。サービス再起動中 DHCP relay が一時停止する。",
        "stage1_note": "`DHCP_RELAY` の key は `<vlan_intf>` (例: `Vlan1000`)。複数 server を `dhcp_servers` フィールドでリスト。",
    },
    "dhcp-server-ipv4": {
        "consumer": "`dhcpservd` (`sonic-dhcp-server`)",
        "appl": "なし (APPL_DB 中継なし)",
        "sai": "なし (SAI 非経由 — Linux カーネルの DHCP サーバ機能)",
        "timing": "`dhcpservd` が CONFIG_DB の `DHCP_SERVER_IPV4` を購読。変化検知後 DHCP server 設定を更新。新規設定は次回 DHCP discover から有効。",
        "side_effects": "subnet / pool 変更は新規 DHCP リクエストから適用。既存 lease には影響しない (lease 期限まで)。",
        "stage1_note": "`DHCP_SERVER_IPV4` は SONiC 独自の DHCP server 機能 (sonic-dhcp-server)。",
    },
    "dhcpv4-relay": {
        "consumer": "`dhcrelay` / `dhcp_relay` サービス (DHCPv4 relay 専用)",
        "appl": "なし (APPL_DB 中継なし)",
        "sai": "なし (SAI 非経由 — Linux カーネルの DHCPv4 relay)",
        "timing": "`dhcrelay` が CONFIG_DB を読み込んで設定。`DHCP_RELAY` と同様にサービス再起動で反映。",
        "side_effects": "`DHCP_RELAY` テーブルと機能的に重複する部分がある。設定変更時はサービス再起動が必要。",
        "stage1_note": "`DHCPV4_RELAY` は一部の SONiC バージョンで `DHCP_RELAY` と統合/分離されている。",
    },
    "dot1p-to-tc-map": {
        "consumer": "`QosOrch` (orchagent 直接 CFG 購読)",
        "appl": "なし (orchagent が直接 CONFIG_DB を購読)",
        "sai": "`sai_qos_map_api` — `sai_create_qos_map` で DOT1P→TC マッピングテーブルを作成",
        "timing": "orchagent が CONFIG_DB 変化を検知後即座に SAI QoS map を作成/更新。ポートへのマップ割り当ては `PORT_QOS_MAP` テーブルで行う。",
        "side_effects": "マップ内容の変更は即座にマップを参照するすべてのポートの QoS 分類に影響。traffic の優先度処理が変化する。",
        "stage1_note": "`DOT1P_TO_TC_MAP` の key はマップ名 (例: `AZURE`)。`<dot1p_value>` → `<tc_value>` のマッピング。",
    },
    "dscp-to-tc-map": {
        "consumer": "`QosOrch` (orchagent 直接 CFG 購読)",
        "appl": "なし (orchagent が直接 CONFIG_DB を購読)",
        "sai": "`sai_qos_map_api` — `sai_create_qos_map` で DSCP→TC マッピングテーブルを作成",
        "timing": "orchagent が CONFIG_DB 変化を検知後即座に SAI QoS map を作成/更新。ポートへの割り当ては `PORT_QOS_MAP` で行う。",
        "side_effects": "DSCP→TC マップ変更はそのマップを使用するすべてのポートの QoS 分類に即座に影響。L3 traffic の優先度処理が変化する。",
        "stage1_note": "`DSCP_TO_TC_MAP` の key はマップ名 (例: `AZURE`)。DSCP 値 (0-63) → TC (0-7) のマッピング。",
    },
    "fabric-monitor": {
        "consumer": "`fabricmgrd` → `FabricPortsOrch` (APPL_DB 経由)",
        "appl": "`APP_FABRIC_MONITOR_DATA_TABLE` に書き込み",
        "sai": "fabric 固有 SAI (fabric link monitor threshold)",
        "timing": "CONFIG_DB 変化を `fabricmgrd` が検知後 APPL_DB に書き込み。`FabricPortsOrch` が SAI attribute を更新。Chassis/VoQ 構成でのみ有効。",
        "side_effects": "fabric link error threshold の変更は fabric isolate/recover の trigger 条件に影響。",
        "stage1_note": "`FABRIC_MONITOR` は Chassis (VoQ) 構成の supervisorモジュールで使用。通常の ToR では意味なし。",
    },
    "fabric-port": {
        "consumer": "`fabricmgrd` → `FabricPortsOrch` (APPL_DB 経由)",
        "appl": "`APP_FABRIC_MONITOR_PORT_TABLE` に書き込み",
        "sai": "fabric 固有 SAI (fabric port enable/isolate)",
        "timing": "CONFIG_DB 変化を `fabricmgrd` が検知後 APPL_DB に書き込み。`FabricPortsOrch` が SAI fabric port attribute を更新。",
        "side_effects": "`admin_status` 変更は fabric link の up/down に直結。isolate 設定は traffic の再ルーティングを引き起こす。",
        "stage1_note": "`FABRIC_PORT` は Chassis の fabric ASIC ポートを管理。通常の ToR では使用しない。",
    },
    "feature": {
        "consumer": "`hostcfgd` の `FeatureHandler` + `containercfgd` + `coppmgrd` + `dhcprelayd`",
        "appl": "なし (APPL_DB 中継なし)",
        "sai": "なし (SAI 非経由 — Docker コンテナの起動/停止制御)",
        "timing": "CONFIG_DB の `FEATURE` エントリ変化を `hostcfgd` が検知後、`systemctl start/stop <feature>` を呼び出す。コンテナ起動/停止は非同期で時間がかかる。",
        "side_effects": "`state: disabled` でコンテナ停止 → そのコンテナが管理するすべての機能が停止。`auto_restart: disabled` でクラッシュ時に自動復旧しない。`set_owner: kube` に変更で Kubernetes 管理に移行。",
        "stage1_note": "`FEATURE` の key はフィーチャー名 (例: `bgp`, `swss`, `lldp`)。`always_enabled` フィーチャーは disable 不可。",
    },
    "fg-nhg": {
        "consumer": "`FgNhgOrch` (orchagent 直接 CFG 購読)",
        "appl": "なし (orchagent が直接 CONFIG_DB を購読)",
        "sai": "`sai_next_hop_group_api` — Fine Grained ECMP next hop group を作成/更新",
        "timing": "orchagent が CONFIG_DB 変化を検知後即座に SAI next hop group を作成/更新。`FG_NHG_PREFIX` で対象プレフィクスを、`FG_NHG_MEMBER` でメンバーを指定。",
        "side_effects": "Fine Grained ECMP の hash 制御に影響。traffic の分散方法が変化。メンバー変更は既存フローのリハッシュを引き起こす可能性。",
        "stage1_note": "`FG_NHG` / `FG_NHG_PREFIX` / `FG_NHG_MEMBER` の 3 テーブルがセット。通常の ECMP とは別のコードパスを使用。",
    },
    "fips": {
        "consumer": "`hostcfgd` の `FIPSHandler`",
        "appl": "なし (APPL_DB 中継なし)",
        "sai": "なし (SAI 非経由 — OpenSSL FIPS モードの有効化/無効化)",
        "timing": "CONFIG_DB 変化を検知後、OpenSSL FIPS 設定を更新。FIPS モードの有効化はシステム再起動後に完全に反映される場合がある。",
        "side_effects": "FIPS 有効化は FIPS 非準拠の暗号アルゴリズムを使用するすべてのアプリケーションに影響。SSH / TLS の設定も変更される可能性がある。",
        "stage1_note": "`FIPS` の key は `global` (単一エントリ)。`enable` フラグのみ。",
    },
    "flex-counter-table": {
        "consumer": "`FlexCounterOrch` (orchagent 直接 CFG 購読)",
        "appl": "なし (orchagent が直接 CONFIG_DB を購読)",
        "sai": "`sai_counter_api` — SAI flexible counter グループの polling interval / enable を設定",
        "timing": "orchagent が CONFIG_DB 変化を検知後即座に SAI counter group を更新。`POLL_INTERVAL` 変更は次回 polling から有効。",
        "side_effects": "counter polling の有効/無効化は `COUNTERS_DB` の更新頻度に影響。`FLEX_COUNTER_STATUS` を `enable` にすると対応する SAI カウンタが増分し始める。",
        "stage1_note": "`FLEX_COUNTER_TABLE` の key はグループ名 (例: `PORT`, `QUEUE`, `TUNNEL`)。各グループの polling interval と状態を管理。",
    },
    "heartbeat": {
        "consumer": "`heartbeat` daemon / `system_health_monitor`",
        "appl": "なし (APPL_DB 中継なし)",
        "sai": "なし (SAI 非経由 — システムヘルスチェック設定)",
        "timing": "CONFIG_DB の `HEARTBEAT` エントリ変化を検知後、heartbeat チェック間隔/閾値を更新。次回チェックサイクルから有効。",
        "side_effects": "heartbeat interval 変更は障害検知の速度に影響。閾値変更は誤検知/検知遅延に影響する可能性がある。",
        "stage1_note": "`HEARTBEAT` はシステムヘルスモニタリング機能の設定。`system_health_monitor` と連携。",
    },
    "interface": {
        "consumer": "`intfmgrd` → `IntfsOrch` (APPL_DB 経由)",
        "appl": "`APP_INTF_TABLE` に書き込み (IP address 付き router interface)",
        "sai": "`sai_router_intf_api` — router interface を作成/更新 + `sai_neighbor_api` で ネイバー設定",
        "timing": "CONFIG_DB 変化を `intfmgrd` が検知後 `APP_INTF_TABLE` に書き込み。`IntfsOrch` が APPL_DB を購読して SAI router interface を作成/更新。IP address 追加は即時反映。",
        "side_effects": "IP address 追加は ARP/NDP 送信を開始。IP address 削除は関連する ARP エントリと neighbor を削除。MTU 変更は PMTUD に影響。",
        "stage1_note": "`INTERFACE` の key は `<intf_name>|<ip_prefix>` または `<intf_name>` (intf 属性のみ)。physical port の L3 設定。",
    },
    "kdump": {
        "consumer": "`hostcfgd` の `KdumpHandler`",
        "appl": "なし (APPL_DB 中継なし)",
        "sai": "なし (SAI 非経由 — `kdump-tools` の設定ファイルを更新)",
        "timing": "CONFIG_DB 変化を検知後、`/etc/default/kdump-tools` を書き換え。`kdump-tools` の設定は次回サービス再起動またはシステム再起動で反映。",
        "side_effects": "`enabled: true` にしてもシステム再起動なしでは kdump カーネルがロードされない。`num_dumps` 変更は次回 coredump 発生時から適用。",
        "stage1_note": "`KDUMP` の key は `config` (単一エントリ)。`enabled` / `memory` / `num_dumps` フィールドを持つ。",
    },
    "kubernetes-master": {
        "consumer": "`kube_scheduler` / `hostcfgd`",
        "appl": "なし (APPL_DB 中継なし)",
        "sai": "なし (SAI 非経由 — Kubernetes master 接続設定)",
        "timing": "CONFIG_DB の `KUBERNETES_MASTER` 変化を検知後、Kubernetes クライアント設定を更新。接続は非同期で再確立。",
        "side_effects": "Kubernetes master アドレス変更は `set_owner: kube` のフィーチャーの管理移行に影響。TLS 証明書の再取得が必要な場合がある。",
        "stage1_note": "`KUBERNETES_MASTER` の key は `SERVER` (単一エントリ)。`ip` / `port` / `insecure` フィールド。",
    },
    "ldap-server": {
        "consumer": "`hostcfgd` の `LdapHandler`",
        "appl": "なし (APPL_DB 中継なし)",
        "sai": "なし (SAI 非経由 — `nslcd` / LDAP クライアント設定を更新)",
        "timing": "CONFIG_DB 変化を検知後、LDAP クライアント設定ファイルを更新して `nslcd` を再起動。次回 LDAP 認証から新設定が有効。",
        "side_effects": "`nslcd` 再起動中は LDAP 認証が一時中断。既存 SSH session は影響なし (PAM session は認証完了済み)。",
        "stage1_note": "`LDAP_SERVER` の key は LDAP server の IP アドレス。複数サーバをリストで指定可能。`AAA` テーブルで `login` に `ldap` を含む場合に有効。",
    },
    "lldp-port": {
        "consumer": "`lldpmgrd`",
        "appl": "なし (APPL_DB 中継なし)",
        "sai": "なし (SAI 非経由 — `lldpd` デーモンの設定を更新)",
        "timing": "CONFIG_DB 変化を `lldpmgrd` が検知後、`lldpcli` コマンドで `lldpd` に設定を注入。即時反映。",
        "side_effects": "LLDP port 設定変更は次回 LLDP PDU 送受信から反映。`lldp_enable` 変更でポート毎に LLDP を有効/無効化可能。",
        "stage1_note": "`LLDP_PORT` の key は `<port>` (例: `Ethernet0`)。ポート毎の LLDP 動作 (rx/tx/rxtx/disabled) を設定。",
    },
    "lldp": {
        "consumer": "`lldpmgrd`",
        "appl": "なし (APPL_DB 中継なし)",
        "sai": "なし (SAI 非経由 — `lldpd` デーモンのグローバル設定)",
        "timing": "CONFIG_DB 変化を `lldpmgrd` が検知後、`lldpcli` でグローバル設定を注入。即時反映。",
        "side_effects": "global LLDP 設定変更 (system description / chassis ID 等) は次回 LLDP PDU 送信から反映。隣接機器の LLDP テーブルが更新されるまで時間がかかる。",
        "stage1_note": "`LLDP` の key は `GLOBAL` (単一エントリ)。system description / hello timer 等のグローバルパラメータ。",
    },
    "loopback-interface": {
        "consumer": "`intfmgrd` → `IntfsOrch` (APPL_DB 経由)",
        "appl": "`APP_INTF_TABLE` に書き込み (loopback interface の IP address)",
        "sai": "`sai_router_intf_api` — loopback router interface を作成/更新",
        "timing": "CONFIG_DB 変化を `intfmgrd` が検知後 `APP_INTF_TABLE` に書き込み。`IntfsOrch` が SAI loopback router interface を更新。即時反映。",
        "side_effects": "Loopback IP address は BGP の Router ID / peering source として使用される。削除すると BGP session に影響する可能性がある。",
        "stage1_note": "`LOOPBACK_INTERFACE` の key は `<lo_name>|<ip_prefix>` または `<lo_name>`。`Loopback0` が BGP router-id として使用される。",
    },
    "lossless-traffic-pattern": {
        "consumer": "`buffermgrdyn` (動的バッファ管理)",
        "appl": "なし (内部計算パラメータ)",
        "sai": "なし (直接 SAI 呼び出しなし — 計算結果が BUFFER_PROFILE 経由で SAI に到達)",
        "timing": "CONFIG_DB 変化を `buffermgrdyn` が検知後、lossless バッファプロファイルを再計算。再計算結果が APPL_DB の BUFFER_PROFILE_TABLE に書き込まれる。",
        "side_effects": "PFC lossless traffic パターン変更は lossless バッファ量の再計算を引き起こす。すべての lossless ポートのバッファプロファイルが再生成される。",
        "stage1_note": "`LOSSLESS_TRAFFIC_PATTERN` の key は `AZURE` 等のパターン名。`mtu` / `small_packet_percentage` 等のパラメータを保持。",
    },
    "macsec-profile": {
        "consumer": "`macsecmgrd` → `MACsecOrch` (APPL_DB 経由)",
        "appl": "`APP_MACSEC_TABLE` / `APP_MACSEC_PORT_TABLE` 等に書き込み",
        "sai": "`sai_macsec_api` — MACsec セキュリティアソシエーション (SC/SA) を作成/更新",
        "timing": "CONFIG_DB 変化を `macsecmgrd` が検知後 APPL_DB に書き込み。`MACsecOrch` が SAI MACsec オブジェクトを作成/更新。キーロールオーバーは非同期。",
        "side_effects": "MACsec プロファイル変更は該当ポートの MACsec セキュリティアソシエーションを再生成。切り替え中に brief traffic interrupt が発生する可能性がある。",
        "stage1_note": "`MACSEC_PROFILE` の key はプロファイル名。`primary_cak` / `fallback_cak` / `cipher_suite` 等のキー情報を保持。",
    },
    "map-pfc-priority-to-queue": {
        "consumer": "`QosOrch` (orchagent 直接 CFG 購読)",
        "appl": "なし (orchagent が直接 CONFIG_DB を購読)",
        "sai": "`sai_qos_map_api` — PFC priority → Queue マッピングテーブルを作成",
        "timing": "orchagent が CONFIG_DB 変化を検知後即座に SAI QoS map を作成/更新。ポートへの割り当ては `PORT_QOS_MAP` で行う。",
        "side_effects": "PFC priority → Queue マッピング変更は PFC フロー制御の動作に直接影響。誤設定で lossless traffic が loss になる可能性がある。",
        "stage1_note": "`MAP_PFC_PRIORITY_TO_QUEUE` の key はマップ名。PFC priority (0-7) → Queue (0-7) のマッピング。",
    },
    "mclag-domain": {
        "consumer": "`MlagOrch` (orchagent 直接 CFG 購読) + `mclagsyncd`",
        "appl": "なし (orchagent が直接 CONFIG_DB を購読)",
        "sai": "`sai_fdb_api` (FDB 同期) + `mclagsyncd` が MCLAG ピアとの制御接続を管理",
        "timing": "orchagent が CONFIG_DB 変化を検知後、MCLAG セッションのネゴシエーションを開始。`mclagsyncd` が ICCP (Inter-Chassis Control Protocol) 接続を確立。非同期で完了。",
        "side_effects": "MCLAG domain の peer IP/source IP 変更は ICCP session reset を引き起こす。ICCP session reset 中は MCLAG で同期していた FDB/ARP が失われる可能性がある。",
        "stage1_note": "`MCLAG_DOMAIN` の key は domain ID (例: `1`)。`peer_link` / `peer_ip` / `source_ip` / `session_timeout` 等を保持。",
    },
    "mgmt-interface": {
        "consumer": "`mgmt-framework` / `interfaces-config` スクリプト",
        "appl": "なし (APPL_DB 中継なし)",
        "sai": "なし (SAI 非経由 — Linux kernel netlink で管理インターフェースを設定)",
        "timing": "CONFIG_DB 変化を検知後、`interfaces-config` スクリプトが `ip addr add/del` 等の netlink コマンドを発行。即時反映。",
        "side_effects": "管理インターフェースの IP 変更は SSH セッションの切断を引き起こす。デフォルトルートの変更は管理トラフィックの経路に影響。",
        "stage1_note": "`MGMT_INTERFACE` の key は `<eth0>|<ip_prefix>` の形式。管理 VRF (`mgmt`) に関連付けられることが多い。",
    },
}

def gen_runtime_trace_block(slug, data):
    """Generate <!-- runtime-trace --> block for a given slug."""
    return f"""
<!-- runtime-trace -->
## 実コンテナ動作トレース

### 段階 1 — Consumer 登録

{data['consumer']} が CONFIG_DB の `{slug.upper().replace('-', '_')}` テーブルを購読する。

{data.get('stage1_note', '')}

### 段階 2 — CFG→APPL 翻訳

{data['appl']}

### 段階 3 — APPL→SAI

{data['sai']}

### 段階 4 — タイミングと副作用

**適用タイミング**: {data['timing']}

**副作用**: {data['side_effects']}
<!-- /runtime-trace -->
"""

def gen_intermediate_file(slug, data, block):
    """Generate intermediate markdown file."""
    table_name = slug.upper().replace('-', '_')
    return f"""# {table_name} — 実コンテナ動作トレース (Direction B)

> 自動生成: `meta/scripts/gen_runtime_trace.py`
> 対象ページ: `docs/reference/config-db/{slug}.md`

## 4 段階トレース

| 段階 | 内容 |
|------|------|
| 1. Consumer 登録 | {data['consumer']} |
| 2. CFG→APPL 翻訳 | {data['appl']} |
| 3. APPL→SAI | {data['sai']} |
| 4. タイミング+副作用 | {data['timing'][:80]}... |

## 生成ブロック

```markdown
{block.strip()}
```
"""

def main():

    # Load tier_low[:60] slugs
    cardinality_path = os.path.join(WT, "meta/cdb-enum-cardinality.json")
    with open(cardinality_path) as f:
        data = json.load(f)
    slugs = [p["slug"] for p in data["tier_low"][:60]]

    intermediate_dir = os.path.join(WT, "meta/_intermediate/cdb-flow")
    os.makedirs(intermediate_dir, exist_ok=True)

    modified_pages = []
    skipped_pages = []
    missing_pages = []

    for slug in slugs:
        page_path = os.path.join(WT, f"docs/reference/config-db/{slug}.md")

        if not os.path.exists(page_path):
            missing_pages.append(slug)
            continue

        with open(page_path) as f:
            content = f.read()

        if "<!-- runtime-trace -->" in content:
            skipped_pages.append(slug)
            continue

        if slug not in TRACE_DATA:
            print(f"WARNING: No trace data for {slug}, skipping")
            skipped_pages.append(slug)
            continue

        trace_data = TRACE_DATA[slug]
        block = gen_runtime_trace_block(slug, trace_data)

        # Write intermediate file
        intermediate_path = os.path.join(intermediate_dir, f"{slug}-runtime-trace.md")
        intermediate_content = gen_intermediate_file(slug, trace_data, block)
        with open(intermediate_path, "w") as f:
            f.write(intermediate_content)

        # Append block to page before last footnote or at end
        # Find insertion point: before <!-- glossary-links-injected --> or at end
        if "<!-- glossary-links-injected" in content:
            insert_before = content.rindex("<!-- glossary-links-injected")
            new_content = content[:insert_before] + block + "\n" + content[insert_before:]
        elif "[^1]:" in content:
            # Before footnotes section
            idx = content.index("\n[^1]:")
            new_content = content[:idx] + "\n" + block + content[idx:]
        else:
            new_content = content + "\n" + block

        with open(page_path, "w") as f:
            f.write(new_content)

        modified_pages.append(slug)
        print(f"OK: {slug}")

    print("\nSummary:")
    print(f"  Modified: {len(modified_pages)}")
    print(f"  Skipped (already has block): {len(skipped_pages)}")
    print(f"  Missing pages: {len(missing_pages)}")
    if missing_pages:
        print(f"  Missing: {missing_pages}")

if __name__ == "__main__":
    main()
