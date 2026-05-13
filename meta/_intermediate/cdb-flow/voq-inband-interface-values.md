# VOQ_INBAND_INTERFACE — 値依存挙動メモ

## inband_type: port / Port
- YANG: pattern "port|Port" — どちらも有効
- YANG default: "port"
- 実装上 "port" と "Port" の両方が許可されており挙動は同一

## name: Ethernet-IB[0-9]+
- YANG pattern 必須
- 違反は YANG バリデーションで reject

## ip-prefix
- IPv4 / IPv6 どちらも可 (sonic-ip-prefix)
- BGP internal neighbor のソース IP に使われる

## フィールド数・enum 数
- enum フィールドなし（name は string パターン、inband_type は pattern）
- 実質的な enum 挙動は inband_type の "port|Port" のみ

Sources:
- sonic-buildimage/src/sonic-yang-models/yang-models/sonic-voq-inband-interface.yang
- sonic-swss/cfgmgr/intfmgr.cpp
