# PORTCHANNEL_MEMBER フィールド値分析

## enum フィールド

なし — key のみのテーブル。name は PORTCHANNEL.name leafref、port は PORT.name leafref。

## 制約・挙動

### `name` (key: PORTCHANNEL.name leafref)
- 存在する PORTCHANNEL: 正常、SAI LAG member 追加
- 存在しない PORTCHANNEL: YANG leafref 違反 → reject

### `port` (key: PORT.name leafref)
- 存在する物理ポート: 正常
- 存在しない PORT: YANG leafref 違反 → reject
- PHY / SYSTEM 型以外: `LAG member port has to be of type PHY or SYSTEM` → SWSS_LOG_ERROR
- chassis 環境で switch_id ミスマッチ: `System lag switch id mismatch` → SWSS_LOG_ERROR

## ソース
- sonic-portchannel.yang (sonic-buildimage sha 9ea932ec)
- orchagent/portsorch.cpp, teammgrd (sonic-swss)
