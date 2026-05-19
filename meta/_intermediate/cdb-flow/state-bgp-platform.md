# state-bgp Phase H — プラットフォーム差異調査メモ

調査対象:
- sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/main.py
- sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py
- sonic-swss/fpmsyncd/fpmsyncd.cpp
- sonic-swss/fpmsyncd/bgp_eoiu_marker.py
- sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_chassis_app_db.py

調査日: 2026-05-19

## BGP_STATE_TABLE

bgp_eoiu_marker.py 内に switch_type / chassis / platform 分岐なし。
`checkWarmStart("bgp", "bgp", False)` が false を返す（Warm Restart 無効）場合は
スクリプト全体がスキップされ BGP_STATE_TABLE への書き込みは発生しない。
この条件は Warm Restart 設定のみに依存し、ASIC 種別やプラットフォームには非依存。

fpmsyncd.cpp も switch_type 等の参照は一切なし。BGP_STATE_TABLE の読み取り判定は
`warmStartEnabled` フラグのみ（fpmsyncd.cpp:153）。

→ **BGP_STATE_TABLE はプラットフォーム非依存**

## BGP_PEER_CONFIGURED_TABLE

main.py:87-92 で 6 種の BGPPeerMgrBase インスタンスを登録。
- BGP_NEIGHBOR (general)
- BGP_INTERNAL_NEIGHBOR (internal)
- BGP_MONITORS (monitors)
- BGP_PEER_RANGE (dynamic)
- BGP_VOQ_CHASSIS_NEIGHBOR (voq_chassis)  ← chassis/VOQ 固有
- BGP_SENTINELS (sentinels)

BGPPeerMgrBase.update_state_db() は peer_type に関わらず同一コードパスで
BGP_PEER_CONFIGURED_TABLE に書き込む (managers_bgp.py:271-298)。

ただし BGP_VOQ_CHASSIS_NEIGHBOR テーブルに設定が存在するのは VOQ chassis 構成
（supervisor で DEVICE_METADATA.localhost.switch_type == "voq"）のときのみ。
通常スイッチではこのテーブルは空なので、BGP_PEER_CONFIGURED_TABLE に
voq_chassis ピアのエントリが現れることはない。

ChassisAppDbMgr は is_chassis() が true の場合のみ登録 (main.py:112-113)。
これは TSA 状態の chassis 間同期に使われ BGP_PEER_CONFIGURED_TABLE には影響しない。

→ **VOQ chassis 構成ではのみ chassis-internal iBGP ピアが BGP_PEER_CONFIGURED_TABLE に現れる**

## BMP_STATE_DB テーブル群

openbmpd は RFC 7854 の BMP プロトコル実装であり、FRR bgpd が稼働する任意の
プラットフォームで動作する。ASIC 種別や switch_type には非依存。
テーブルの生成有無は CONFIG_DB BMP テーブルの各フィールド設定のみで制御される。

→ **BMP テーブルはプラットフォーム非依存**

## 結論

プラットフォーム差異は 1 点のみ:
- VOQ chassis (switch_type == "voq") 構成では BGP_PEER_CONFIGURED_TABLE に
  BGP_VOQ_CHASSIS_NEIGHBOR 由来の chassis-internal iBGP エントリが追加される。
- 通常スイッチ (switch_type == "switch") では BGP_VOQ_CHASSIS_NEIGHBOR テーブルが
  空のため、こうしたエントリは生成されない。
- BGP_STATE_TABLE と BMP_STATE_DB テーブルにはプラットフォーム差異なし。
