# cdb_batch_0 値依存挙動分析

## 集計

- 対象ページ: 12
- enum 型フィールド合計: 12
  - AAA.type (3値), AAA.login (11パターン)
  - ACL_RULE.PACKET_ACTION (6値), ACL_RULE.IP_TYPE (9値)
  - ACL_TABLE.type (14値), ACL_TABLE.stage (2値)
  - AS_PATH_SET.action (2値)
  - AUTO_TECHSUPPORT_FEATURE.state (2値)
  - AUTO_TECHSUPPORT.state×2 (GLOBAL/FEATURE, 各2値)
  - BANNER_MESSAGE.state (2値)
  - BGP_ALLOWED_PREFIXES.default_action (2値)
  - BGP_DEVICE_GLOBAL.idf_isolation_state (3値)
- 値別分岐合計: 約58分岐

## cross-cutting 事象 (代表3つ)

### 1. `failthrough` が AAA 全メソッドに横断適用
`sonic-host-services/data/templates/common-auth-sonic.j2` では `failthrough` が PAM の `auth_err=die` フラグとして TACACS+/RADIUS/LDAP すべての stanza に同一フラグとして適用される。メソッドごとに個別設定できない。

### 2. BGP_DEVICE_GLOBAL 3フィールドはすべて FRR route-map を直接書き換える
`tsa_enabled`, `wcmp_enabled`, `idf_isolation_state` は独立した Jinja2 テンプレートを持ち、それぞれ `TO_BGP_PEER_V4/V6` や `CHECK_IDF_ISOLATION` という共通 route-map に書き込む。chassis_tsa が true のとき tsa_enabled による local TSA 操作をスキップするという chassis-level cross-cutting がある。

### 3. BGP_ALLOWED_PREFIXES.default_action と no-export community の間接マッピング
`default_action=deny` が直接 FRR deny ルールを生成するのではなく、`no-export` community を付与することで AS 外流出を抑制するという間接実装。同一 community を NEIGHBOR_TYPE 単位のサブポリシーと GLOBAL ポリシーで共用することで、AND 条件による複合フィルタリングを実現している。

## ページ別 enum フィールド一覧

| ページ | enum フィールド | 値数 |
|---|---|---|
| AAA | `type`, `login` (複合) | 3+11 |
| ACL_RULE | `PACKET_ACTION`, `IP_TYPE` | 6+9 |
| ACL_TABLE | `type`, `stage` | 14+2 |
| AS_PATH_SET | `action` | 2 |
| AUTO_TECHSUPPORT_FEATURE | `state` | 2 |
| AUTO_TECHSUPPORT | `state` (GLOBAL+FEATURE) | 2+2 |
| BANNER_MESSAGE | `state` | 2 |
| BGP_AGGREGATE_ADDRESS | なし (boolean のみ) | 0 |
| BGP_ALLOWED_PREFIXES | `default_action` | 2 |
| BGP_DEVICE_GLOBAL | `idf_isolation_state` | 3 |
| BGP_GLOBALS_AF_AGGREGATE_ADDR | なし (boolean のみ) | 0 |
| BGP_GLOBALS_AF_NETWORK | なし (boolean のみ) | 0 |
