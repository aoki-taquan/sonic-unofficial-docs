#!/usr/bin/env python3
"""Generate runtime-trace intermediate files and inject <!-- runtime-trace --> blocks into doc pages."""

import os
import re

INTERMEDIATE_DIR = "/home/coder/sonic-unofficial-docs/meta/_intermediate/cdb-flow"
DOCS_DIR = "/home/coder/sonic-unofficial-docs/docs/reference/config-db"

# Runtime trace data: slug -> (consumer_info, cfg_to_appl, appl_to_sai, timing_side_effects)
TRACES = {
    "mgmt-port": {
        "table": "MGMT_PORT",
        "stage1": [
            "**hostcfgd** (`sonic-host-services/scripts/hostcfgd`): `MGMT_PORT` テーブルを `ConfigDBConnector` で購読。",
            "スレッド: hostcfgd メインループ内で `subscribe` コールバック登録。",
        ],
        "stage2": [
            "hostcfgd が `MGMT_PORT` エントリを受け取り、`/etc/network/interfaces.d/` 向け設定断片を `j2` テンプレートで生成。",
            "CFG→APP_DB への書き込みは行わない (カーネル直接設定)。",
        ],
        "stage3": [
            "SAI 経由なし。`ifconfig`/`ethtool` を syscall で直接発行して eth0 の speed/MTU/admin_status を設定。",
            "再起動時は `ifupdown2` が `/etc/network/interfaces` を読み込んでカーネル設定を復元。",
        ],
        "timing": [
            "CONFIG_DB への書き込み後、hostcfgd コールバックは数秒以内にカーネル設定を反映する。",
            "サービス再起動 (`systemctl restart networking`) が必要な場合もある。",
            "副作用: eth0 admin down 時に SSH セッションが切断される可能性がある。",
        ],
    },
    "mgmt-vrf-config": {
        "table": "MGMT_VRF_CONFIG",
        "stage1": [
            "**hostcfgd** (`sonic-host-services/scripts/hostcfgd`): `MGMT_VRF_CONFIG` テーブルを `ConfigDBConnector` で購読。",
        ],
        "stage2": [
            "hostcfgd が `mgmtVrfHandler` を呼び出し、`mgmt` VRF を作成または削除する。",
            "APP_DB への書き込みは行わない (カーネル直接操作)。",
        ],
        "stage3": [
            "SAI 経由なし。`ip vrf add mgmt` / `ip vrf del mgmt` をシステムコールで実行。",
            "`/etc/iproute2/rt_tables` に mgmt VRF エントリを追加。",
        ],
        "timing": [
            "VRF 作成は即時 (カーネルコール)。eth0 を mgmt VRF に移すまでに一時的な接続断が生じる。",
            "副作用: `mgmtVrfEnabled = true` 時に eth0 が mgmt namespace に移動。SSH 接続が一時的に切断される可能性。",
        ],
    },
    "mirror-session": {
        "table": "MIRROR_SESSION",
        "stage1": [
            "**orchagent / MirrorOrch** (`sonic-swss/orchagent/mirrororch.cpp`): `MIRROR_SESSION` テーブルを `SubscriberStateTable` で購読。",
            "**AclOrch** も MIRROR_SESSION への参照カウンタを保持する。",
        ],
        "stage2": [
            "MirrorOrch が `MIRROR_SESSION` エントリを解析し内部セッション構造体に変換。",
            "ERSPAN の場合、RouteOrch に `dst_ip` を nexthop 解決依頼 → 解決後に `updateSession()` を呼び出してセッションを ACTIVE 化。",
            "APP_DB への書き込みは行わない (orchagent から直接 SAI 呼び出し)。",
        ],
        "stage3": [
            "MirrorOrch が `sai_mirror_api->create_mirror_session()` を呼び出し SAI MIRROR_SESSION オブジェクトを生成。",
            "SPAN: `SAI_MIRROR_SESSION_TYPE_LOCAL`。ERSPAN: `SAI_MIRROR_SESSION_TYPE_ENHANCED_REMOTE`。",
            "policer が指定された場合は `PolicerOrch` 経由で SAI policer OID を取得して関連付け。",
        ],
        "timing": [
            "ERSPAN はルート解決 (RouteOrch callback) まで INACTIVE のまま待機。解決後数 ms 以内に ACTIVE 化。",
            "副作用: セッション ACTIVE 化後、ACL / PBH から参照される。削除時に refCount > 0 の場合は例外スロー。",
            "STATE_DB `MIRROR_SESSION_TABLE.<name>.status` で active/inactive を確認可能。",
        ],
    },
    "mux-cable": {
        "table": "MUX_CABLE",
        "stage1": [
            "**linkmgrd** (`sonic-linkmgrd/src/`): `MUX_CABLE` テーブルを `ConfigDBConnector` で購読。",
            "**xcvrd** (platform_daemons): mux cable の物理ステータスを管理。",
        ],
        "stage2": [
            "linkmgrd がエントリを読み、各インタフェースの mux 状態マシン (MuxStateMachine) を初期化。",
            "APP_DB `MUX_CABLE_TABLE` と `HW_MUX_CABLE_TABLE` に state を書き込む (linkmgrd → appDB)。",
        ],
        "stage3": [
            "orchagent / MuxOrch が APP_DB `MUX_CABLE_TABLE` を購読し、SAI neighbor/nexthop を操作して active/standby トラフィックパスを制御。",
            "SAI: `sai_neighbor_api` でネクストホップの有効・無効を切替。",
        ],
        "timing": [
            "state=auto 時: linkmgrd がリンクプローバ (ICMP/ARP) 結果に基づき自動切替。レイテンシは数百 ms。",
            "state=manual 時: CLI `show mux status` / `config mux mode` で即時切替。",
            "副作用: active→standby 切替時にトラフィックが一時的に 0.1〜数秒断する可能性。",
        ],
    },
    "mux-linkmgr": {
        "table": "MUX_LINKMGR",
        "stage1": [
            "**linkmgrd**: `MUX_LINKMGR` テーブルを `ConfigDBConnector` で購読してリンクプローバのパラメータを設定。",
        ],
        "stage2": [
            "linkmgrd がプローバ間隔 (`interval_v4`, `interval_v6`) とリトライ回数 (`positive_signal_count`) を内部設定に反映。",
            "APP_DB への書き込みなし (linkmgrd 内部状態変更のみ)。",
        ],
        "stage3": [
            "SAI 経由なし。プローバのタイマー設定変更がリンク障害検知速度に影響する。",
        ],
        "timing": [
            "設定変更は次のプローバサイクルから有効。概ね秒単位の遅延。",
            "副作用: interval を長くすると障害検知が遅くなり、短くすると CPU/ネットワーク負荷が増加。",
        ],
    },
    "nat": {
        "table": "NAT_GLOBAL / STATIC_NAT / STATIC_NAPT / NAT_POOL / NAT_BINDINGS",
        "stage1": [
            "**orchagent / NatOrch** (`sonic-swss/orchagent/natorch.cpp`): `NAT_GLOBAL`, `STATIC_NAT`, `STATIC_NAPT`, `NAT_POOL`, `NAT_BINDINGS` を `SubscriberStateTable` で購読。",
        ],
        "stage2": [
            "NatOrch が `NAT_GLOBAL.admin_mode=enabled` を確認してから各テーブルの処理を開始。",
            "STATIC_NAT/STATIC_NAPT エントリは APP_DB 経由ではなく orchagent から直接 SAI へ。",
            "`admin_mode=disabled` の場合はエントリをキューに保持して SAI 操作を行わない。",
        ],
        "stage3": [
            "NatOrch が `sai_nat_api->create_nat_entry()` を呼び出してハードウェアに NAT エントリを書き込む。",
            "NAT pool + binding の場合は Dynamic NAT (MASQUERADE 型) として SAI に登録。",
        ],
        "timing": [
            "`admin_mode` 有効化時にキュー内の全エントリを一括処理 (数十〜数百エントリの場合に数百 ms 要する場合あり)。",
            "副作用: conntrack timeout 変更は既存セッションには影響しない (新規セッションから適用)。",
            "副作用: NAT pool の枯渇時は新規 NAT セッションが確立できず DROP。STATE_DB でカウンタ確認可能。",
        ],
    },
    "ntp-global": {
        "table": "NTP",
        "stage1": [
            "**hostcfgd** (`sonic-host-services/scripts/hostcfgd`): `NTP` テーブルを `ConfigDBConnector` で購読。",
        ],
        "stage2": [
            "hostcfgd の `ntpHandler` が `ntp.conf` (または `chrony.conf`) テンプレートを更新し、ntpd/chronyd を再起動。",
            "APP_DB への書き込みなし。",
        ],
        "stage3": [
            "SAI 経由なし。カーネル NTP デーモン (`ntpd` または `chronyd`) が時刻同期を担う。",
        ],
        "timing": [
            "設定変更後、ntpd 再起動まで数秒。時刻同期の安定には数分〜数十分を要する場合がある。",
            "副作用: 大きな時刻ジャンプが生じると証明書検証・ログ・セッションタイムアウトに影響。",
        ],
    },
    "ntp-key": {
        "table": "NTP_KEY",
        "stage1": [
            "**hostcfgd**: `NTP_KEY` テーブルを `ConfigDBConnector` で購読。",
        ],
        "stage2": [
            "hostcfgd が `/etc/ntp.keys` を更新し、ntpd に SIGHUP または再起動を発行。",
            "APP_DB への書き込みなし。",
        ],
        "stage3": [
            "SAI 経由なし。ntpd が認証付き NTP パケット処理に鍵を使用。",
        ],
        "timing": [
            "鍵更新後 ntpd 再起動まで数秒。鍵ロールオーバー中は NTP 認証が一時的に失敗する可能性。",
        ],
    },
    "ntp-server": {
        "table": "NTP_SERVER",
        "stage1": [
            "**hostcfgd**: `NTP_SERVER` テーブルを `ConfigDBConnector` で購読。",
        ],
        "stage2": [
            "hostcfgd の `ntpHandler` が `ntp.conf` の `server` ディレクティブを更新し ntpd 再起動。",
            "APP_DB への書き込みなし。",
        ],
        "stage3": [
            "SAI 経由なし。ntpd が指定サーバへ UDP 123 番で到達可能であることが前提。",
        ],
        "timing": [
            "サーバ変更後 ntpd 再起動まで数秒。新サーバとの初期同期に数分かかる場合あり。",
            "副作用: mgmt VRF を使用する場合は `ip vrf exec mgmt ntpq` で状態確認が必要。",
        ],
    },
    "nvgre-tunnel": {
        "table": "NVGRE_TUNNEL",
        "stage1": [
            "**orchagent / TunnelDecapOrch**: `NVGRE_TUNNEL` テーブルを `SubscriberStateTable` で購読。",
        ],
        "stage2": [
            "TunnelDecapOrch がエントリを解析し APP_DB `TUNNEL_DECAP_TABLE` に書き込む (一部実装)。",
            "実装は VS/仮想 ASIC 向けが主体で、物理 ASIC サポートはベンダー依存。",
        ],
        "stage3": [
            "orchagent から SAI `sai_tunnel_api->create_tunnel()` を呼び出して NVGRE デカプセルトンネルを作成。",
            "SAI_TUNNEL_TYPE_NVGRE を使用。",
        ],
        "timing": [
            "トンネル作成は orchagent が処理を受け取った数 ms 以内。",
            "副作用: 対応する SAI サポートが必要。非サポート ASIC では task_failed となる。",
        ],
    },
    "pbh": {
        "table": "PBH_TABLE / PBH_RULE / PBH_HASH / PBH_HASH_FIELD",
        "stage1": [
            "**orchagent / PbhOrch** (`sonic-swss/orchagent/pbhorch.cpp`): `PBH_TABLE`, `PBH_RULE`, `PBH_HASH`, `PBH_HASH_FIELD` を `SubscriberStateTable` で購読。",
        ],
        "stage2": [
            "PbhOrch が各テーブルのエントリを内部データ構造に格納し、依存関係 (HASH_FIELD → HASH → TABLE → RULE) を解決。",
            "APP_DB への書き込みなし (orchagent から直接 SAI)。",
        ],
        "stage3": [
            "PbhOrch が `sai_hash_api->create_hash()` / `sai_acl_api->create_acl_entry()` を呼び出してポリシーベースハッシュを設定。",
            "依存する HASH オブジェクトが未作成の場合は `task_need_retry`。",
        ],
        "timing": [
            "依存関係が揃ったエントリから順次 SAI に反映。HASH_FIELD → HASH → RULE の順で処理。",
            "副作用: PBH RULE が ACL テーブルと競合する場合 SAI が resource 不足エラーを返す可能性。",
        ],
    },
    "peer-switch": {
        "table": "PEER_SWITCH",
        "stage1": [
            "**linkmgrd**: `PEER_SWITCH` テーブルを `ConfigDBConnector` で購読してピアスイッチ IP を認識。",
            "**orchagent / MuxOrch**: ピア情報を参照して dual-ToR フェイルオーバーロジックを制御。",
        ],
        "stage2": [
            "linkmgrd がピア IP に向けて ICMPv4/ICMPv6 プローブを送信し、ピアの健全性を監視。",
            "APP_DB への書き込みなし (内部利用のみ)。",
        ],
        "stage3": [
            "SAI 経由なし。mux ケーブル切替は MUX_CABLE テーブル経由で間接的に SAI に反映。",
        ],
        "timing": [
            "ピア接続障害を検知するまでプローバサイクル × ネガティブカウントの時間を要する。",
            "副作用: ピア障害検知後、MuxOrch がトラフィックを local に引き込む自動フェイルオーバーを実施。",
        ],
    },
    "pfc-priority-to-priority-group-map": {
        "table": "PFC_PRIORITY_TO_PRIORITY_GROUP_MAP",
        "stage1": [
            "**orchagent / QosOrch** (`sonic-swss/orchagent/qosorch.cpp`): `PFC_PRIORITY_TO_PRIORITY_GROUP_MAP` を `SubscriberStateTable` で購読。",
        ],
        "stage2": [
            "QosOrch がマップエントリを解析し SAI priority group map として作成。",
            "APP_DB への書き込みなし (orchagent → SAI 直接)。",
        ],
        "stage3": [
            "QosOrch が `sai_qos_map_api->create_qos_map()` を呼び出して `SAI_QOS_MAP_TYPE_PFC_PRIORITY_TO_PRIORITY_GROUP` マップを作成。",
            "その後 PORT テーブルのマップ参照が解決されたときにポートに適用。",
        ],
        "timing": [
            "マップ作成後、PORT_QOS_MAP での参照が更新されると即時ポートに適用される。",
            "副作用: PFC しきい値設定 (BUFFER_PG) と組み合わせて動作するため、両方の設定が揃う必要がある。",
        ],
    },
    "pfc-wd": {
        "table": "PFC_WD",
        "stage1": [
            "**orchagent / PfcWdOrch** (`sonic-swss/orchagent/pfcwdorch.cpp`): `PFC_WD` テーブルを `SubscriberStateTable` で購読。",
        ],
        "stage2": [
            "PfcWdOrch が各ポートの PFC Watchdog ポーリング間隔 (`detection_time`, `restoration_time`) と action (`drop`, `forward`, `alert`) を解析。",
            "APP_DB への書き込みなし。",
        ],
        "stage3": [
            "PfcWdOrch が SAI `sai_port_api` / `sai_queue_api` を使用して PFC deadlock 検出と自動回復を設定。",
            "action=drop: デッドロック検知時に該当キューの PFC フレームを drop。",
        ],
        "timing": [
            "`detection_time` ms 以内に PFC デッドロードを検知し、`restoration_time` ms 後に自動復旧。",
            "副作用: action=drop 時にトラフィックが一時的に DROP。lossless クラスのパケットロスが生じる可能性。",
            "STATE_DB `PFC_WD_TABLE` でデッドロック検知状態を確認可能。",
        ],
    },
    "policer": {
        "table": "POLICER",
        "stage1": [
            "**orchagent / PolicerOrch** (`sonic-swss/orchagent/policerorch.cpp`): `POLICER` テーブルを `SubscriberStateTable` で購読。",
        ],
        "stage2": [
            "PolicerOrch がエントリを解析し SAI policer オブジェクトを作成。他の orch (MirrorOrch, AclOrch) から leafref 参照される。",
            "APP_DB への書き込みなし。",
        ],
        "stage3": [
            "PolicerOrch が `sai_policer_api->create_policer()` を呼び出して SAI POLICER を作成。",
            "`meter_type`, `mode`, `cir`, `cbs`, `pir`, `pbs`, `action` を SAI 属性にマッピング。",
        ],
        "timing": [
            "POLICER オブジェクト作成後、MIRROR_SESSION や ACL から参照されることで有効化。",
            "副作用: policer 削除時に MirrorOrch/AclOrch が参照している場合、削除は失敗 (`policer is still referenced`)。",
        ],
    },
    "port-qos-map": {
        "table": "PORT_QOS_MAP",
        "stage1": [
            "**orchagent / QosOrch** (`sonic-swss/orchagent/qosorch.cpp`): `PORT_QOS_MAP` テーブルを `SubscriberStateTable` で購読。",
        ],
        "stage2": [
            "QosOrch が各フィールド (`dscp_to_tc_map`, `tc_to_queue_map`, `pfc_to_pg_map` 等) を解析し、参照される QoS マップ OID を解決。",
            "APP_DB への書き込みなし。",
        ],
        "stage3": [
            "QosOrch が `sai_port_api->set_port_attribute()` を呼び出して各 QoS マップをポートに適用。",
            "例: `SAI_PORT_ATTR_QOS_DSCP_TO_TC_MAP`, `SAI_PORT_ATTR_QOS_TC_TO_QUEUE_MAP` 等。",
        ],
        "timing": [
            "参照する QoS マップが未作成の場合は `task_need_retry`。マップ作成後に自動再処理。",
            "副作用: 既存トラフィックへの影響が即座に発生するため、メンテナンス時間帯での変更を推奨。",
        ],
    },
    "port-storm-control": {
        "table": "PORT_STORM_CONTROL",
        "stage1": [
            "**orchagent / StormControlOrch**: `PORT_STORM_CONTROL` テーブルを `SubscriberStateTable` で購読。",
        ],
        "stage2": [
            "StormControlOrch がエントリを解析し、ストームコントロール種別 (`broadcast`, `unknown_unicast`, `unknown_multicast`) とレート (kbps/pps) を取得。",
            "APP_DB への書き込みなし。",
        ],
        "stage3": [
            "orchagent が `sai_port_api->set_port_attribute()` でストームコントロール policer を適用。",
            "SAI 属性: `SAI_PORT_ATTR_BROADCAST_STORM_CONTROL_POLICER_ID` 等。",
        ],
        "timing": [
            "設定は即時 SAI に反映。既存フラッディングトラフィックへの影響は ms 単位。",
            "副作用: レートを低く設定しすぎると正常な broadcast (ARP 等) も制限される。",
        ],
    },
    "port": {
        "table": "PORT",
        "stage1": [
            "**orchagent / PortsOrch** (`sonic-swss/orchagent/portsorch.cpp`): `PORT` テーブルを `SubscriberStateTable` で購読。",
            "**portmgrd** (`sonic-swss/cfgmgr/portmgr.cpp`): `PORT` テーブルを購読して Linux netdev を設定。",
            "**xcvrd** (`sonic-platform-daemons`): トランシーバ関連フィールドを購読。",
        ],
        "stage2": [
            "portmgrd が `PORT` → `APP_PORT_TABLE` に admin_status / mtu / speed 等を書き込む。",
            "PortsOrch は CONFIG_DB と APP_DB 両方から PORT 情報を統合して処理。",
        ],
        "stage3": [
            "PortsOrch が `sai_port_api->set_port_attribute()` で speed/FEC/autoneg/MTU/admin_status を SAI に反映。",
            "syncd が SAI 呼び出しをシリアライズして ASIC ドライバに転送。",
        ],
        "timing": [
            "admin_status 変更: SAI 反映後に Linux netdev も portmgrd が更新 (二重管理)。数百 ms 以内。",
            "speed/FEC 変更: リンクフラップが発生する。対向装置との調整が必要。",
            "副作用: breakout 操作は他サブポートへの影響大。VLAN/LAG に所属している場合は先に削除が必要。",
        ],
    },
    "portchannel-interface": {
        "table": "PORTCHANNEL_INTERFACE",
        "stage1": [
            "**orchagent / IntfsOrch** (`sonic-swss/orchagent/intfsorch.cpp`): `PORTCHANNEL_INTERFACE` テーブルを `SubscriberStateTable` で購読。",
        ],
        "stage2": [
            "IntfsOrch がエントリを解析し IP プレフィックス情報を取得。LAG の L3 インタフェース作成に進む。",
            "APP_DB `INTF_TABLE` への書き込み後、orchagent が SAI を呼び出す。",
        ],
        "stage3": [
            "IntfsOrch が `sai_router_interface_api->create_router_interface()` で SAI RIF を作成。",
            "IP プレフィックスは `sai_route_api` でルートエントリに変換。",
        ],
        "timing": [
            "PORTCHANNEL テーブルが先に処理されている必要がある。未解決の場合は `task_need_retry`。",
            "副作用: IP アドレス削除時に関連するルート・ARP エントリが自動削除される。",
        ],
    },
    "portchannel-member": {
        "table": "PORTCHANNEL_MEMBER",
        "stage1": [
            "**orchagent / PortsOrch**: `PORTCHANNEL_MEMBER` テーブルを `SubscriberStateTable` で購読。",
            "**teammgrd** (`sonic-swss/cfgmgr/teammgr.cpp`): LAG メンバの追加・削除を `teamd` に伝達。",
        ],
        "stage2": [
            "teammgrd が `teamd` プロセスにポートの追加/削除を UNIX ソケット経由で通知。",
            "APP_DB `LAG_MEMBER_TABLE` に書き込み。",
        ],
        "stage3": [
            "PortsOrch が APP_DB を読み `sai_lag_api->create_lag_member()` / `remove_lag_member()` を呼び出し。",
            "LACP が有効な場合は teamd がネゴシエーションを担う。",
        ],
        "timing": [
            "メンバ追加後 LACP ネゴシエーションが完了するまで数秒 (設定依存)。",
            "副作用: メンバ削除時にそのポートのトラフィックは他メンバにハッシュ再分散される。",
        ],
    },
    "portchannel": {
        "table": "PORTCHANNEL",
        "stage1": [
            "**orchagent / PortsOrch**: `PORTCHANNEL` テーブルを `SubscriberStateTable` で購読。",
            "**teammgrd**: `PORTCHANNEL` テーブルを購読して `teamd` プロセスを管理。",
        ],
        "stage2": [
            "teammgrd が `teamd` を起動しチームデバイスを作成。APP_DB `LAG_TABLE` に書き込み。",
        ],
        "stage3": [
            "PortsOrch が APP_DB `LAG_TABLE` を読み `sai_lag_api->create_lag()` で SAI LAG オブジェクトを作成。",
            "min_links / LACP タイマ設定を SAI 属性に反映。",
        ],
        "timing": [
            "teamd 起動に数秒要する。SAI LAG 作成は teamd が APP_DB に書いた後。",
            "副作用: PORTCHANNEL 削除時はメンバポートを先に削除しないと `non-empty LAG` エラー。",
        ],
    },
    "prefix-list": {
        "table": "PREFIX_LIST",
        "stage1": [
            "**bgpcfgd** (`sonic-utilities` bgpcfgd): `PREFIX_LIST` テーブルを `ConfigDBConnector` で購読。",
        ],
        "stage2": [
            "bgpcfgd が FRR の `vtysh` に `ip prefix-list` コマンドを送信してプレフィックスリストを設定。",
            "APP_DB への書き込みなし (FRR 直接設定)。",
        ],
        "stage3": [
            "FRR がプレフィックスリストをルートフィルタとして使用。SAI 経由なし (コントロールプレーン処理)。",
        ],
        "timing": [
            "vtysh 設定は即時有効。BGP セッションへの影響は次の UPDATE メッセージから。",
            "副作用: 既存 BGP ピアのルートフィルタ変更はソフトリセット (`clear bgp soft`) が必要な場合あり。",
        ],
    },
    "prefix-set": {
        "table": "PREFIX_SET",
        "stage1": [
            "**bgpcfgd** または **sonic-cfggen**: `PREFIX_SET` テーブルを `ConfigDBConnector` で購読。",
        ],
        "stage2": [
            "bgpcfgd が FRR の prefix-list 設定を生成して vtysh 経由で反映。",
            "APP_DB への書き込みなし。",
        ],
        "stage3": [
            "FRR がプレフィックスセットをポリシーマッチ条件として使用。SAI 経由なし。",
        ],
        "timing": [
            "FRR 設定反映は即時。ルーティングポリシーへの影響はピアの next UPDATE から。",
        ],
    },
    "queue": {
        "table": "QUEUE",
        "stage1": [
            "**orchagent / QosOrch** (`sonic-swss/orchagent/qosorch.cpp`): `QUEUE` テーブルを `SubscriberStateTable` で購読。",
        ],
        "stage2": [
            "QosOrch がキューのスケジューラマップ (`scheduler`) と WRED プロファイル (`wred_profile`) を解析。",
            "APP_DB への書き込みなし。",
        ],
        "stage3": [
            "QosOrch が `sai_scheduler_api` / `sai_wred_api` を呼び出し、キュー OID に対してスケジューラと WRED を適用。",
        ],
        "timing": [
            "参照するスケジューラ/WRED が未作成の場合は `task_need_retry`。",
            "副作用: キューの WRED 変更は既存フロー中のパケットからリアルタイムに適用される。",
        ],
    },
    "radius": {
        "table": "RADIUS / RADIUS_SERVER",
        "stage1": [
            "**hostcfgd**: `RADIUS` / `RADIUS_SERVER` テーブルを `ConfigDBConnector` で購読。",
        ],
        "stage2": [
            "hostcfgd の `radiusHandler` が PAM / AAA 設定ファイル (`/etc/pam.d/`, `/etc/freeradius/`) を更新し、認証デーモンを再起動。",
            "APP_DB への書き込みなし。",
        ],
        "stage3": [
            "SAI 経由なし。RADIUS は SSH/コンソール認証のコントロールプレーン処理。",
        ],
        "timing": [
            "設定反映は hostcfgd が PAM 設定を書き換えた直後から有効。既存 SSH セッションは影響なし (新規ログインから適用)。",
            "副作用: RADIUS サーバが到達不能の場合は `auth_type=local` フォールバックの有無に注意。",
        ],
    },
    "restapi": {
        "table": "RESTAPI",
        "stage1": [
            "**hostcfgd**: `RESTAPI` テーブルを `ConfigDBConnector` で購読。",
        ],
        "stage2": [
            "hostcfgd が REST API サービス (sonic-restapi / sonic-gnmi) の有効・無効設定を `/etc/sonic/` に書き込む。",
            "APP_DB への書き込みなし。",
        ],
        "stage3": [
            "SAI 経由なし。REST API は管理プレーン機能。",
        ],
        "timing": [
            "hostcfgd が設定を反映後、対象サービスが再起動されるまで数秒。",
            "副作用: REST API 無効化中に自動化スクリプトが接続しようとするとタイムアウトが発生。",
        ],
    },
    "route-map": {
        "table": "ROUTE_MAP",
        "stage1": [
            "**bgpcfgd**: `ROUTE_MAP` テーブルを `ConfigDBConnector` で購読。",
        ],
        "stage2": [
            "bgpcfgd が FRR の `route-map` を `vtysh` 経由で設定。PREFIX_LIST / PREFIX_SET を参照する場合は先に作成が必要。",
            "APP_DB への書き込みなし。",
        ],
        "stage3": [
            "FRR がルートマップを BGP ポリシー (import/export filter, redistribution) として使用。SAI 経由なし。",
        ],
        "timing": [
            "route-map 変更は FRR に即時反映。BGP ピアへの影響は次の UPDATE/KEEPALIVE から。",
            "副作用: `set local-preference` 変更等でルート選択が変わり、トラフィックパスが切り替わる可能性。",
        ],
    },
    "scheduler": {
        "table": "SCHEDULER",
        "stage1": [
            "**orchagent / QosOrch**: `SCHEDULER` テーブルを `SubscriberStateTable` で購読。",
        ],
        "stage2": [
            "QosOrch がスケジューラタイプ (`STRICT`, `WRR`, `DWRR`) と重み/優先度を解析。",
            "APP_DB への書き込みなし。",
        ],
        "stage3": [
            "QosOrch が `sai_scheduler_api->create_scheduler()` を呼び出して SAI スケジューラオブジェクトを作成。",
            "QUEUE テーブルからの参照で各キューに適用。",
        ],
        "timing": [
            "スケジューラ作成後、QUEUE テーブルが参照するときに即時キューに適用。",
            "副作用: STRICT スケジューラが高優先度キューを飽和させると低優先度が枯渇 (starvation)。",
        ],
    },
    "sflow": {
        "table": "SFLOW / SFLOW_SESSION",
        "stage1": [
            "**sflowmgrd** (`sonic-swss/cfgmgr/sflowmgr.cpp`): `SFLOW` / `SFLOW_SESSION` テーブルを `ConfigDBConnector` で購読。",
        ],
        "stage2": [
            "sflowmgrd が `hsflowd` (sFlow エージェント) の設定ファイルを更新し再起動。",
            "ポート単位のサンプリングレート設定を APP_DB `SFLOW_SESSION_TABLE` に書き込み。",
        ],
        "stage3": [
            "orchagent / SflowOrch が APP_DB `SFLOW_SESSION_TABLE` を購読し `sai_samplepacket_api` でハードウェアサンプリングを設定。",
        ],
        "timing": [
            "グローバル有効化 (`admin_state=up`) 後に各ポートのサンプリングが有効になる。",
            "副作用: サンプリングレートを低くしすぎると CPU 負荷が増大。デフォルト 512 は一般的な設定。",
        ],
    },
    "snmp-agent-address-config": {
        "table": "SNMP_AGENT_ADDRESS_CONFIG",
        "stage1": [
            "**hostcfgd**: `SNMP_AGENT_ADDRESS_CONFIG` テーブルを `ConfigDBConnector` で購読。",
        ],
        "stage2": [
            "hostcfgd が SNMP エージェント (`snmpd`) のリッスンアドレス設定を `/etc/snmp/snmpd.conf` に書き込み再起動。",
            "APP_DB への書き込みなし。",
        ],
        "stage3": [
            "SAI 経由なし。snmpd がデータプレーン統計を直接 SAI/kernel から読み取る。",
        ],
        "timing": [
            "snmpd 再起動まで数秒。既存 SNMP セッションは切断される。",
            "副作用: リッスンアドレス変更中に SNMP モニタリングが一時停止。",
        ],
    },
    "snmp": {
        "table": "SNMP / SNMP_COMMUNITY",
        "stage1": [
            "**hostcfgd**: `SNMP` / `SNMP_COMMUNITY` テーブルを `ConfigDBConnector` で購読。",
        ],
        "stage2": [
            "hostcfgd が snmpd の community string / v3 ユーザ設定を `/etc/snmp/snmpd.conf` に書き込み再起動。",
        ],
        "stage3": [
            "SAI 経由なし。snmpd が MIB ツリーを通じてスイッチ統計を提供。",
        ],
        "timing": [
            "設定変更後 snmpd 再起動まで数秒。community 変更は即時有効 (再起動後)。",
            "副作用: 旧 community string での SNMP ポーリングが失敗するため、NMS 側の設定変更も必要。",
        ],
    },
    "static-route": {
        "table": "STATIC_ROUTE",
        "stage1": [
            "**orchagent / StaticRouteOrch** または **bgpcfgd**: `STATIC_ROUTE` テーブルを `SubscriberStateTable` で購読。",
        ],
        "stage2": [
            "orchagent が APP_DB `ROUTE_TABLE` / `INTF_TABLE` を更新してルートを RouteOrch に渡す。",
        ],
        "stage3": [
            "RouteOrch が `sai_route_api->create_route_entry()` でスタティックルートをハードウェアに書き込む。",
            "nexthop の ARP 解決が必要な場合は NeighOrch と連携。",
        ],
        "timing": [
            "nexthop が到達可能であれば数十 ms 以内に SAI に反映。",
            "副作用: `blackhole` nexthop 設定時はパケットが静かに DROP される。",
        ],
    },
    "subnet-decap": {
        "table": "SUBNET_DECAP",
        "stage1": [
            "**orchagent / SubnetDecapOrch**: `SUBNET_DECAP` テーブルを `SubscriberStateTable` で購読。",
        ],
        "stage2": [
            "SubnetDecapOrch がサブネット範囲とデカプセルアクションを解析。APP_DB への書き込みなし。",
        ],
        "stage3": [
            "orchagent が `sai_tunnel_api` または `sai_acl_api` でサブネット単位のデカプセルルールを設定。",
        ],
        "timing": [
            "設定反映は orchagent 処理後数 ms 以内。",
            "副作用: サブネット範囲の重複があると ACL リソース競合が発生する可能性。",
        ],
    },
    "suppress-asic-sdk-health-event": {
        "table": "SUPPRESS_ASIC_SDK_HEALTH_EVENT",
        "stage1": [
            "**orchagent / AsicSdkHealthEventOrch**: `SUPPRESS_ASIC_SDK_HEALTH_EVENT` テーブルを `SubscriberStateTable` で購読。",
        ],
        "stage2": [
            "AsicSdkHealthEventOrch が抑制するイベントカテゴリ / 重大度リストを内部設定に格納。",
            "APP_DB への書き込みなし。",
        ],
        "stage3": [
            "SAI: HealthEvent コールバックフィルタを設定 (SAI `sai_switch_api->set_switch_attribute` の `SAI_SWITCH_ATTR_*_HEALTH_EVENT_SUPPRESS`)。",
        ],
        "timing": [
            "設定反映は即時。以降の ASIC SDK ヘルスイベントが抑制される。",
            "副作用: 重要なイベントを抑制すると障害検知が遅れる。最小限の抑制に留めることを推奨。",
        ],
    },
    "switch-hash": {
        "table": "SWITCH_HASH",
        "stage1": [
            "**orchagent / SwitchOrch** (`sonic-swss/orchagent/switchorch.cpp`): `SWITCH_HASH` テーブルを `SubscriberStateTable` で購読。",
        ],
        "stage2": [
            "SwitchOrch がハッシュフィールドリスト (`hash_field_list`) と ECMP/LAG ハッシュ設定を解析。",
            "APP_DB への書き込みなし。",
        ],
        "stage3": [
            "SwitchOrch が `sai_switch_api->set_switch_attribute()` で `SAI_SWITCH_ATTR_ECMP_DEFAULT_HASH_ALGORITHM` / `SAI_SWITCH_ATTR_LAG_DEFAULT_HASH_ALGORITHM` を設定。",
        ],
        "timing": [
            "設定変更は即時有効。既存フローのハッシュ再計算によりトラフィック再分散が発生。",
            "副作用: ハッシュフィールド変更でフローの ECMP メンバ割り当てが変わりパケット順序逆転が生じる可能性。",
        ],
    },
    "switch-trimming": {
        "table": "SWITCH_TRIMMING",
        "stage1": [
            "**orchagent / SwitchOrch**: `SWITCH_TRIMMING` テーブルを `SubscriberStateTable` で購読。",
        ],
        "stage2": [
            "SwitchOrch がパケットトリミング設定 (最大パケットサイズ等) を解析。APP_DB への書き込みなし。",
        ],
        "stage3": [
            "SwitchOrch が `sai_switch_api->set_switch_attribute()` でトリミング関連属性を設定。",
        ],
        "timing": [
            "設定は即時有効。以降のパケットから新しいトリミングサイズが適用。",
            "副作用: パケットトリミングにより Jumbo Frame が切り詰められ、受信側でデータが欠損する可能性。",
        ],
    },
    "syslog-config-feature": {
        "table": "SYSLOG_CONFIG_FEATURE",
        "stage1": [
            "**hostcfgd**: `SYSLOG_CONFIG_FEATURE` テーブルを `ConfigDBConnector` で購読。",
        ],
        "stage2": [
            "hostcfgd がコンテナ別 syslog 設定 (ログレベル, フィルタ等) を `/etc/rsyslog.d/` に書き込み rsyslog を再起動。",
            "APP_DB への書き込みなし。",
        ],
        "stage3": [
            "SAI 経由なし。syslog はコントロールプレーンのロギング機能。",
        ],
        "timing": [
            "rsyslog 再起動まで数秒。再起動中のログが欠落する可能性。",
        ],
    },
    "syslog-config": {
        "table": "SYSLOG_CONFIG",
        "stage1": [
            "**hostcfgd**: `SYSLOG_CONFIG` テーブルを `ConfigDBConnector` で購読。",
        ],
        "stage2": [
            "hostcfgd がグローバル syslog 設定 (リモートサーバ転送等) を rsyslog 設定ファイルに書き込み再起動。",
        ],
        "stage3": [
            "SAI 経由なし。rsyslog がネットワーク経由でリモート syslog サーバへ転送。",
        ],
        "timing": [
            "設定変更後 rsyslog 再起動まで数秒。リモートサーバ到達不能の場合はバッファリングまたはログ欠落。",
        ],
    },
    "syslog-server": {
        "table": "SYSLOG_SERVER",
        "stage1": [
            "**hostcfgd**: `SYSLOG_SERVER` テーブルを `ConfigDBConnector` で購読。",
        ],
        "stage2": [
            "hostcfgd の `syslogHandler` がリモート syslog サーバ宛の転送設定を `/etc/rsyslog.d/` に書き込み rsyslog 再起動。",
        ],
        "stage3": [
            "SAI 経由なし。rsyslog が UDP/TCP 514 番でリモートサーバへ転送。",
        ],
        "timing": [
            "rsyslog 再起動まで数秒。VRF を使用する場合は rsyslog の VRF バインド設定が必要。",
        ],
    },
    "system-defaults": {
        "table": "SYSTEM_DEFAULTS",
        "stage1": [
            "**各種 mgrd / orchagent**: `SYSTEM_DEFAULTS` テーブルを起動時に `ConfigDBConnector` で読み込む。",
            "主に `switch_type` (L2, L3, VOQ 等) の判定に使用される。",
        ],
        "stage2": [
            "orchagent 起動時に `SYSTEM_DEFAULTS` を読み込んでスイッチモードを決定。動的変更は基本的に非サポート。",
        ],
        "stage3": [
            "SAI 初期化時に `sai_switch_api->create_switch()` のパラメータとして switch_type 等が渡される。",
        ],
        "timing": [
            "SYSTEM_DEFAULTS は主に起動時設定。変更時はサービス再起動が必要。",
            "副作用: switch_type の変更は swss/syncd の完全再起動が必要でサービス断が生じる。",
        ],
    },
    "tacplus-server": {
        "table": "TACPLUS / TACPLUS_SERVER",
        "stage1": [
            "**hostcfgd**: `TACPLUS` / `TACPLUS_SERVER` テーブルを `ConfigDBConnector` で購読。",
        ],
        "stage2": [
            "hostcfgd の `tacplusHandler` が `/etc/tacplus_servers` / PAM 設定を更新し認証デーモンを再起動。",
            "APP_DB への書き込みなし。",
        ],
        "stage3": [
            "SAI 経由なし。TACACS+ は SSH/コンソール認証のコントロールプレーン処理。",
        ],
        "timing": [
            "設定変更は次回ログインから有効。既存 SSH セッションには影響なし。",
            "副作用: TACACS+ サーバ到達不能時に `auth_type=local` フォールバックが必要。",
        ],
    },
    "tc-to-queue-map": {
        "table": "TC_TO_QUEUE_MAP",
        "stage1": [
            "**orchagent / QosOrch**: `TC_TO_QUEUE_MAP` テーブルを `SubscriberStateTable` で購読。",
        ],
        "stage2": [
            "QosOrch が TC→Queue マッピングエントリを解析。APP_DB への書き込みなし。",
        ],
        "stage3": [
            "QosOrch が `sai_qos_map_api->create_qos_map()` で `SAI_QOS_MAP_TYPE_TC_TO_QUEUE` マップを作成。",
            "PORT_QOS_MAP での参照でポートに適用。",
        ],
        "timing": [
            "マップ作成後、PORT_QOS_MAP が参照したときに即時ポートに適用。",
            "副作用: TC→Queue マッピング変更でトラフィックの queue 割り当てが変わり QoS 特性が変化。",
        ],
    },
    "telemetry-client": {
        "table": "TELEMETRY_CLIENT",
        "stage1": [
            "**gnmi-telemetry** または **sonic-gnmi**: `TELEMETRY_CLIENT` テーブルを `ConfigDBConnector` で購読。",
        ],
        "stage2": [
            "gnmi-telemetry がテレメトリクライアント設定 (サブスクリプション対象, エンドポイント, 認証) を読み込みセッションを確立。",
        ],
        "stage3": [
            "SAI 経由なし。gNMI Dial-Out でリモートコレクタへ購読データを Push。",
        ],
        "timing": [
            "設定変更後 gnmi-telemetry が再起動されるまで数秒。サブスクリプション確立に数秒かかる場合あり。",
        ],
    },
    "telemetry": {
        "table": "TELEMETRY",
        "stage1": [
            "**gnmi-telemetry / sonic-gnmi**: `TELEMETRY` テーブルを `ConfigDBConnector` で購読してグローバル設定を適用。",
        ],
        "stage2": [
            "gnmi-telemetry がサーバポート / TLS 証明書 / 認証設定を読み込みリッスンを開始。",
            "APP_DB への書き込みなし。",
        ],
        "stage3": [
            "SAI 経由なし。gNMI サーバが DATA_DB / STATE_DB を購読してデータを提供。",
        ],
        "timing": [
            "設定変更は gnmi-telemetry 再起動後に有効 (数秒)。クライアントは再接続が必要。",
        ],
    },
    "tunnel-decap-table": {
        "table": "TUNNEL_DECAP_TABLE",
        "stage1": [
            "**orchagent / TunnelDecapOrch** (`sonic-swss/orchagent/tunneldecaporch.cpp`): `TUNNEL_DECAP_TABLE` を `SubscriberStateTable` で購読。",
        ],
        "stage2": [
            "TunnelDecapOrch がトンネルタイプ (IPINIP) と内側/外側 IP 情報を解析。",
            "APP_DB への書き込みなし (orchagent → SAI 直接)。",
        ],
        "stage3": [
            "TunnelDecapOrch が `sai_tunnel_api->create_tunnel()` / `create_tunnel_term_table_entry()` を呼び出し IP-in-IP デカプセルトンネルをハードウェアに設定。",
        ],
        "timing": [
            "トンネル作成は orchagent 処理後数 ms 以内。",
            "副作用: 内側 IP アドレスの重複がある場合 SAI が resource エラーを返す。",
        ],
    },
    "tunnel": {
        "table": "TUNNEL",
        "stage1": [
            "**orchagent / TunnelOrch** または **VxlanOrch**: `TUNNEL` テーブルを `SubscriberStateTable` で購読。",
        ],
        "stage2": [
            "TunnelOrch / VxlanOrch がトンネルパラメータを解析し APP_DB へ書き込む。",
        ],
        "stage3": [
            "orchagent が `sai_tunnel_api->create_tunnel()` でトンネルオブジェクトを作成。",
            "VxLAN の場合は `sai_tunnel_api->create_tunnel_map()` も呼び出す。",
        ],
        "timing": [
            "設定反映は orchagent 処理後数 ms 以内。",
            "副作用: アンダーレイルートが存在しないと ECMP nexthop 解決ができずトンネルが inactive。",
        ],
    },
    "vlan-interface": {
        "table": "VLAN_INTERFACE",
        "stage1": [
            "**orchagent / IntfsOrch**: `VLAN_INTERFACE` テーブルを `SubscriberStateTable` で購読。",
        ],
        "stage2": [
            "IntfsOrch が VLAN L3 インタフェースの IP プレフィックスを APP_DB `INTF_TABLE` に書き込む。",
        ],
        "stage3": [
            "IntfsOrch が `sai_router_interface_api->create_router_interface()` で VLAN に対する SAI RIF を作成。",
            "IP プレフィックスに対して `sai_route_api` でコネクテッドルートを作成。",
        ],
        "timing": [
            "VLAN テーブルが先に処理されている必要あり。未解決の場合は `task_need_retry`。",
            "副作用: IP 削除時は関連 ARP エントリ・ルートが自動削除される。",
        ],
    },
    "vlan-member": {
        "table": "VLAN_MEMBER",
        "stage1": [
            "**orchagent / VlanOrch** (`sonic-swss/orchagent/vlanorch.cpp`): `VLAN_MEMBER` テーブルを `SubscriberStateTable` で購読。",
        ],
        "stage2": [
            "VlanOrch がポートの VLAN 帰属 (`tagging_mode`) を解析。APP_DB への書き込みなし。",
        ],
        "stage3": [
            "VlanOrch が `sai_vlan_api->create_vlan_member()` でポートを VLAN に追加。",
            "`tagging_mode=tagged`: `SAI_VLAN_TAGGING_MODE_TAGGED`、`untagged`: `SAI_VLAN_TAGGING_MODE_UNTAGGED`。",
        ],
        "timing": [
            "VLAN テーブルと PORT テーブルが両方処理済みであることが前提。",
            "副作用: ポートを VLAN から削除すると、そのポートの MAC エントリが FDB から自動削除される。",
        ],
    },
    "vlan-sub-interface": {
        "table": "VLAN_SUB_INTERFACE",
        "stage1": [
            "**orchagent / IntfsOrch**: `VLAN_SUB_INTERFACE` テーブルを `SubscriberStateTable` で購読。",
        ],
        "stage2": [
            "IntfsOrch がサブインタフェース (例: `Ethernet0.100`) の VLAN ID と IP を解析。",
            "APP_DB `INTF_TABLE` に書き込み。",
        ],
        "stage3": [
            "IntfsOrch が `sai_router_interface_api->create_router_interface()` で `SAI_ROUTER_INTERFACE_TYPE_SUB_PORT` タイプの RIF を作成。",
        ],
        "timing": [
            "親ポート (PORT) が存在しない場合は `task_need_retry`。",
            "副作用: サブインタフェース削除時は IP アドレス・ルートが自動削除される。",
        ],
    },
    "vlan": {
        "table": "VLAN",
        "stage1": [
            "**orchagent / VlanOrch**: `VLAN` テーブルを `SubscriberStateTable` で購読。",
            "**vlanmgrd** (`sonic-swss/cfgmgr/vlanmgr.cpp`): `VLAN` テーブルを購読して Linux VLAN ブリッジを管理。",
        ],
        "stage2": [
            "vlanmgrd が `VLAN` エントリを APP_DB `VLAN_TABLE` に書き込み、`ip link add Vlan<N> type bridge vlan_filtering 1` でカーネルブリッジを作成。",
        ],
        "stage3": [
            "VlanOrch が APP_DB `VLAN_TABLE` を読み `sai_vlan_api->create_vlan()` でハードウェア VLAN を作成。",
        ],
        "timing": [
            "カーネルブリッジ作成 (vlanmgrd) と SAI VLAN 作成 (VlanOrch) はほぼ同時。数十 ms 以内。",
            "副作用: admin_status=down でもカーネルブリッジは作成される (`ip link set Vlan<N> down` が別途発行)。",
        ],
    },
    "vnet": {
        "table": "VNET",
        "stage1": [
            "**orchagent / VNetOrch** (`sonic-swss/orchagent/vnetorch.cpp`): `VNET` テーブルを `SubscriberStateTable` で購読。",
        ],
        "stage2": [
            "VNetOrch が VNet 設定 (overlay / underlay VRF, VXLAN tunnel 参照) を解析。APP_DB への書き込みなし。",
        ],
        "stage3": [
            "VNetOrch が `sai_virtual_router_api->create_virtual_router()` で VNet 用 VRF を作成し、VXLAN トンネルと関連付け。",
        ],
        "timing": [
            "VXLAN_TUNNEL テーブルと VRF テーブルが先に処理されている必要あり。",
            "副作用: VNet 削除時は関連するルート・ネクストホップが全て削除される。",
        ],
    },
    "voq-inband-interface": {
        "table": "VOQ_INBAND_INTERFACE",
        "stage1": [
            "**orchagent / VoqOrch** (`sonic-swss/orchagent/voqorch.cpp`): `VOQ_INBAND_INTERFACE` テーブルを購読 (VOQ chassis 環境専用)。",
        ],
        "stage2": [
            "VoqOrch が inband インタフェース (asic-asic 通信用) を APP_DB `INTF_TABLE` に書き込む。",
        ],
        "stage3": [
            "IntfsOrch が SAI で inband ポートの RIF を作成し、VOQ 配送に使用するルートを設定。",
        ],
        "timing": [
            "VOQ chassis 環境でのみ有効。non-VOQ 環境では orchagent が処理をスキップ。",
        ],
    },
    "vrf": {
        "table": "VRF",
        "stage1": [
            "**orchagent / VrfOrch** (`sonic-swss/orchagent/vrforch.cpp`): `VRF` テーブルを `SubscriberStateTable` で購読。",
            "**vrfmgrd** (`sonic-swss/cfgmgr/vrfmgr.cpp`): `VRF` テーブルを購読して Linux VRF デバイスを管理。",
        ],
        "stage2": [
            "vrfmgrd が `ip vrf add <name>` でカーネル VRF デバイスを作成し APP_DB `VRF_TABLE` に書き込む。",
        ],
        "stage3": [
            "VrfOrch が APP_DB を読み `sai_virtual_router_api->create_virtual_router()` でハードウェア VRF を作成。",
            "VRF OID は後続の INTERFACE / ROUTE テーブル処理で使用される。",
        ],
        "timing": [
            "カーネル VRF 作成 (vrfmgrd) と SAI VRF 作成 (VrfOrch) はほぼ同時。",
            "副作用: VRF 削除時は所属インタフェース・ルートを先に削除しないと `VRF is in use` エラー。",
        ],
    },
    "vxlan-evpn-nvo": {
        "table": "VXLAN_EVPN_NVO",
        "stage1": [
            "**orchagent / VxlanOrch** (`sonic-swss/orchagent/vxlanorch.cpp`): `VXLAN_EVPN_NVO` テーブルを `SubscriberStateTable` で購読。",
        ],
        "stage2": [
            "VxlanOrch が EVPN NVO 設定 (source vtep 名) を解析し FRR 経由で EVPN ルートを受信する準備をする。",
            "APP_DB への書き込みなし (orchagent → SAI 直接)。",
        ],
        "stage3": [
            "VxlanOrch が SAI トンネルオブジェクト (VXLAN_TUNNEL 参照) に EVPN を関連付け、`sai_tunnel_api` で VTEP を設定。",
        ],
        "timing": [
            "VXLAN_TUNNEL テーブルが先に処理されている必要あり。BGP EVPN ルート受信後に MAC/IP ルートが SAI に展開される。",
            "副作用: EVPN NVO 削除時は全 VNI・MAC エントリが一斉削除されトラフィックが断。",
        ],
    },
    "vxlan-tunnel-map": {
        "table": "VXLAN_TUNNEL_MAP",
        "stage1": [
            "**orchagent / VxlanOrch**: `VXLAN_TUNNEL_MAP` テーブルを `SubscriberStateTable` で購読。",
        ],
        "stage2": [
            "VxlanOrch が VNI ↔ VLAN マッピングを解析。APP_DB への書き込みなし。",
        ],
        "stage3": [
            "VxlanOrch が `sai_tunnel_api->create_tunnel_map_entry()` で VNI ↔ VLAN のマッピングエントリをハードウェアに設定。",
        ],
        "timing": [
            "VXLAN_TUNNEL と VLAN テーブルが処理済みであることが前提。",
            "副作用: VNI マッピング削除時は対応する EVPN MAC/IP ルートも連動して削除。",
        ],
    },
    "vxlan-tunnel": {
        "table": "VXLAN_TUNNEL",
        "stage1": [
            "**orchagent / VxlanOrch**: `VXLAN_TUNNEL` テーブルを `SubscriberStateTable` で購読。",
        ],
        "stage2": [
            "VxlanOrch が VTEP の src_ip / dst_ip を解析し SAI トンネルオブジェクト作成の準備をする。",
            "APP_DB への書き込みなし。",
        ],
        "stage3": [
            "VxlanOrch が `sai_tunnel_api->create_tunnel()` で SAI_TUNNEL_TYPE_VXLAN トンネルを作成し OID を保持。",
        ],
        "timing": [
            "トンネル作成は orchagent 処理後数 ms 以内。アンダーレイルートがない場合はトンネルが inactive。",
            "副作用: VXLAN_TUNNEL 削除時は TUNNEL_MAP / EVPN_NVO など依存オブジェクトを先に削除する必要あり。",
        ],
    },
    "warm-restart": {
        "table": "WARM_RESTART",
        "stage1": [
            "**各サービス (swss, syncd, bgp 等)**: 起動時に `WARM_RESTART` テーブルを `ConfigDBConnector` で読み込む。",
            "**system_halt_app** / **warmboot-finalizer**: warm restart フロー全体を管理。",
        ],
        "stage2": [
            "各サービスが `WARM_RESTART` テーブルの `enable` / `neighsyncd_timer` 等を読み込み、warm restart モードで起動するかを決定。",
            "STATE_DB `WARM_RESTART_TABLE` に現在の warm restart 状態を書き込む。",
        ],
        "stage3": [
            "SAI: warm restart 時は syncd が `SAI_SWITCH_ATTR_WARM_BOOT_WRITE/READ_FILE` を使用して ASIC 状態を保存・復元する。",
            "swss / orchagent は warm restart 完了後に APP_DB を再生して SAI との整合を確認する。",
        ],
        "timing": [
            "warm restart の完了時間はサービス数・ルート数に依存。数十秒〜数分。",
            "副作用: warm restart が失敗するとコールドリスタートにフォールバックし、トラフィックが完全断になる。",
            "STATE_DB `WARM_RESTART_TABLE` で各サービスの進捗を確認可能。",
        ],
    },
}


def make_intermediate(slug: str, trace: dict) -> str:
    s1 = "\n".join(f"- {line}" for line in trace["stage1"])
    s2 = "\n".join(f"- {line}" for line in trace["stage2"])
    s3 = "\n".join(f"- {line}" for line in trace["stage3"])
    s4 = "\n".join(f"- {line}" for line in trace["timing"])
    return f"""# {slug} — CDB → 実コンテナ動作 ランタイムトレース

## 対象テーブル
`{trace["table"]}`

## 段階 1: Consumer 登録

{s1}

## 段階 2: CFG → APPL 翻訳

{s2}

## 段階 3: APPL → SAI

{s3}

## 段階 4: タイミング + 副作用

{s4}
"""


def make_runtime_block(slug: str, trace: dict) -> str:
    s1 = "\n".join(f"- {line}" for line in trace["stage1"])
    s2 = "\n".join(f"- {line}" for line in trace["stage2"])
    s3 = "\n".join(f"- {line}" for line in trace["stage3"])
    s4 = "\n".join(f"- {line}" for line in trace["timing"])
    return f"""
<!-- runtime-trace -->
## CDB → 実コンテナ動作トレース

### 段階 1: Consumer 登録

{s1}

### 段階 2: CFG → APPL 翻訳

{s2}

### 段階 3: APPL → SAI

{s3}

### 段階 4: タイミング + 副作用

{s4}

<!-- /runtime-trace -->"""


def inject_runtime_trace(doc_path: str, slug: str, trace: dict) -> bool:
    """Inject runtime-trace block into doc page if not already present."""
    with open(doc_path, "r", encoding="utf-8") as f:
        content = f.read()

    if "<!-- runtime-trace -->" in content:
        print(f"  SKIP (already has runtime-trace): {slug}")
        return False

    block = make_runtime_block(slug, trace)

    # Append before <!-- glossary-links-injected if present, else at end
    if "<!-- glossary-links-injected" in content:
        # Insert before the last glossary injection marker
        idx = content.rfind("<!-- glossary-links-injected")
        content = content[:idx] + block + "\n\n" + content[idx:]
    else:
        content = content.rstrip() + "\n" + block + "\n"

    with open(doc_path, "w", encoding="utf-8") as f:
        f.write(content)
    return True


def main():
    slugs = list(TRACES.keys())
    print(f"Processing {len(slugs)} slugs...")

    intermediate_created = 0
    docs_updated = 0

    for slug in slugs:
        trace = TRACES[slug]

        # Create intermediate file
        intermediate_path = os.path.join(INTERMEDIATE_DIR, f"{slug}-runtime-trace.md")
        content = make_intermediate(slug, trace)
        with open(intermediate_path, "w", encoding="utf-8") as f:
            f.write(content)
        intermediate_created += 1

        # Inject into doc page
        doc_path = os.path.join(DOCS_DIR, f"{slug}.md")
        if os.path.exists(doc_path):
            updated = inject_runtime_trace(doc_path, slug, trace)
            if updated:
                docs_updated += 1
                print(f"  UPDATED: {slug}")
        else:
            print(f"  WARNING: doc not found for {slug}")

    print(f"\nDone: {intermediate_created} intermediate files, {docs_updated} docs updated")


if __name__ == "__main__":
    main()
