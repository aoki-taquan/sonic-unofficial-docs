# port — CDB → 実コンテナ動作 ランタイムトレース

## 対象テーブル
`PORT`

## 段階 1: Consumer 登録

- **orchagent / PortsOrch** (`sonic-swss/orchagent/portsorch.cpp`): `PORT` テーブルを `SubscriberStateTable` で購読。
- **portmgrd** (`sonic-swss/cfgmgr/portmgr.cpp`): `PORT` テーブルを購読して Linux netdev を設定。
- **xcvrd** (`sonic-platform-daemons`): トランシーバ関連フィールドを購読。

## 段階 2: CFG → APPL 翻訳

- portmgrd が `PORT` → `APP_PORT_TABLE` に admin_status / mtu / speed 等を書き込む。
- PortsOrch は CONFIG_DB と APP_DB 両方から PORT 情報を統合して処理。

## 段階 3: APPL → SAI

- PortsOrch が `sai_port_api->set_port_attribute()` で speed/FEC/autoneg/MTU/admin_status を SAI に反映。
- syncd が SAI 呼び出しをシリアライズして ASIC ドライバに転送。

## 段階 4: タイミング + 副作用

- admin_status 変更: SAI 反映後に Linux netdev も portmgrd が更新 (二重管理)。数百 ms 以内。
- speed/FEC 変更: リンクフラップが発生する。対向装置との調整が必要。
- 副作用: breakout 操作は他サブポートへの影響大。VLAN/LAG に所属している場合は先に削除が必要。
