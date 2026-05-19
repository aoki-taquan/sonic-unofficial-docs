# CONFIG_DB 暗黙参照分析: MCLAG_UNIQUE_IP (Phase C)

## 調査対象

`CONFIG_DB:MCLAG_UNIQUE_IP|<if_name>` の暗黙参照テーブル。

## 参照元: MCLAG_UNIQUE_IP → 参照先

### 1. MCLAG_DOMAIN（YANG must 制約）

- YANG `must "count(../../MCLAG_DOMAIN/MCLAG_DOMAIN_LIST/domain_id) != 0"` により、MCLAG_DOMAIN に 1 件以上エントリがない状態で MCLAG_UNIQUE_IP を書くと YANG バリデーション拒否
- CLI `config/mclag.py:328-330` も `db.get_table('MCLAG_DOMAIN').keys()` で件数チェックし、0 件なら `ctx.fail("MCLAG not configured.")`
- evidence: `sonic-mclag.yang:132-134`, `config/mclag.py:328-330`

### 2. VLAN テーブル（コメントアウトの leafref）

- YANG `leaf if_name` に本来 `type leafref { path "/vlan:sonic-vlan/vlan:VLAN/vlan:VLAN_LIST/vlan:name"; }` を意図していたが libyang back-links の制約でコメントアウト。現在は string パターン制約のみ。
- 実運用上 Vlan<id> が存在しない VLAN ID を指定しても YANG レベルでは拒否されない。
- evidence: `sonic-mclag.yang:146-152`

### 3. VLAN_INTERFACE テーブル（CLI 事前チェック）

- CLI `config mclag unique-ip add/del` は `db.get_table('VLAN_INTERFACE')` を全スキャンして `if_name` 一致エントリを探し、IP アドレスが設定済みならば `ctx.fail()` で中断。
- `get_intf_vrf_bind_unique_ip(db, interface_name, "VLAN_INTERFACE")` により非デフォルト VRF バインドも事前チェック。
- 直接 `sonic-db-cli` で書く場合はこのチェックは実行されない（YANG コメントアウト部分のバリデーションも無効なため回避可能）。
- evidence: `config/mclag.py:338-347`, `config/mclag.py:365-373`

## 参照先 → MCLAG_UNIQUE_IP（逆方向）

- MCLAG_UNIQUE_IP を参照するテーブルは YANG モデル上存在しない。
- `mclagsyncd` が SubscriberStateTable として購読するが、これはプログラム内部の接続であり CONFIG_DB テーブル間のスキーマ制約ではない。

## 暗黙 STATE_DB 関連

- `addDomainCfgDependentSelectables()` により、MCLAG_DOMAIN 初回 SET 後に `STATE_VLAN_MEMBER_TABLE`（STATE_DB）の購読も同時に開始される
- mclagsyncd が FDB ルーティングのために STATE_DB VLAN メンバーシップ情報を間接的に参照する
- evidence: `mclaglink.cpp:910-935`
