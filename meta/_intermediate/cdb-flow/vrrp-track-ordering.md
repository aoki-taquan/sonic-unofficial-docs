# VRRP_TRACK — Phase B 書込み順依存スキャンノート

対象テーブル: `VRRP_TRACK`
Consumer: FRR `vrrpd` (zebra 経由インタフェース状態通知受信) + `sonic-utilities/config/main.py` (CLI バリデーション)
スキャン範囲: `sonic-utilities/config/main.py` `add_track_interface()` / `remove_track_interface()` 全行、`sonic-utilities/tests/vrrp_test.py` 全行、`SONiC/doc/vrrp/VRRP_Adaptation_HLD.md` DB Changes / Modules Design セクション精読

---

## 検出した順序依存・タイミング依存

### 1. VRRP インスタンス先行必須（VRRP エントリが存在しなければ VRRP_TRACK を書けない）

- `add_track_interface()` (`config/main.py:7017-7019`) は `config_db.get_entry("VRRP", (interface_name, str(vrrp_id)))` で親 VRRP インスタンスの存在を確認し、エントリが空 (`{}`) の場合は `ctx.fail("vrrp instance {} not found on interface {}")` でコマンドを中断する。
- **順序依存**: `VRRP_TRACK|<intf>|<vrid>|<track_intf>` を書く前に必ず `VRRP|<intf>|<vrid>` エントリが CONFIG_DB に存在しなければならない。直接 `redis-cli` / プログラム的書き込みをする場合も、FRR vrrpd は CONFIG_DB を経由しないため CLI 同様の前提がある（vrrpd が VRRP インスタンスを認識していない状態では track 設定が無効）。
- evidence: `sonic-utilities/config/main.py:7017-7019`

### 2. 追跡インタフェース (track_interface) のルータインタフェース先行必須

- `add_track_interface()` は `track_interface` が `get_interface_table_name()` で有効なテーブル名（`INTERFACE`, `PORTCHANNEL_INTERFACE`, `VLAN_INTERFACE`）に解決されるかを確認し、さらに `config_db.get_table(table_name_t)` の存在チェックを行う (`config/main.py:7007-7014`)。
- **順序依存**: `track_interface` 名に対応するルータインタフェースエントリ (`INTERFACE`, `PORTCHANNEL_INTERFACE`, `VLAN_INTERFACE`) が CONFIG_DB に存在しなければ `ctx.fail("Router Interface '{}' not found")` でコマンドを拒絶する。物理ポート (`Ethernet*`) のみが対象で Loopback は無効 (`table_name == "" or table_name == "LOOPBACK_INTERFACE"` の場合はエラー)。
- evidence: `sonic-utilities/config/main.py:7004-7014`

### 3. ベースインタフェース (interface_name) のルータインタフェース先行必須

- `add_track_interface()` は `interface_name` についても同様のルータインタフェース存在チェックを行う (`config/main.py:7000-7006`)。
- **順序依存**: `VRRP_TRACK` を書く前に `interface_name` のルータインタフェースエントリが CONFIG_DB に存在しなければならない。VRRP インスタンス自体の存在チェック（依存 #1）より前に実行されるため、インタフェース → VRRP → VRRP_TRACK の順序で投入する必要がある。
- evidence: `sonic-utilities/config/main.py:7000-7006`

### 4. 1 VRRP インスタンスあたりの track インタフェース上限（最大 8）

- `add_track_interface()` は `config_db.get_keys("VRRP_TRACK")` で全トラックキーを列挙し、同一 `(interface_name, vrid)` のエントリ数が 8 以上であれば `ctx.fail("The Vrrpv instance {} has already configured 8 track interfaces")` で拒絶する (`config/main.py:7028-7038`)。
- **順序依存なし**（上限チェックは各 SET 操作で独立して実行される）。ただし同時並列で 8 本目と 9 本目を書く場合は TOCTOU により上限超過が起きる可能性があるが、運用上は CLI 逐次実行が前提。
- evidence: `sonic-utilities/config/main.py:7028-7038`

### 5. DEL 操作 — VRRP インスタンス削除と VRRP_TRACK の残留リスク

- `remove_track_interface()` (`config/main.py:7074-7077`) は VRRP インスタンスの存在確認後に `config_db.set_entry('VRRP_TRACK', ..., None)` でエントリを削除する。
- HLD によると VRRP インスタンス削除時に関連する VRRP_TRACK エントリが自動削除されるかどうかは実装依存。CLI では `vrrp ip remove` で仮想 IP を削除しても `VRRP_TRACK` は明示削除が必要。
- **推奨順序**: VRRP インスタンス削除 (`config interface vrrp ip remove`) の前に `config interface vrrp track_interface remove` で全 track エントリを明示削除する。VRRP インスタンスを先に消すと `remove_track_interface()` の存在チェック (`7070-7072`) が `ctx.fail` するため、逆順 (track_interface 先削除) が必要。
- evidence: `sonic-utilities/config/main.py:7045-7077`

### 6. FRR vrrpd による priority 再計算タイミング

- HLD の「Uplink interface tracking」セクションによると、track インタフェースの Up/Down を zebra がカーネルイベントから検知し、vrrpd に通知する。vrrpd はその通知を受けて VRRP_TRACK の `priority_increment` を参照し priority を加減算する。
- CONFIG_DB への `VRRP_TRACK` 書き込みが FRR に反映されるタイミングは FRR の設定読み込み周期に依存する（即時ではない可能性がある）。
- **順序依存**: VRRP インスタンス起動後に track インタフェースを追加した場合、FRR が新しい track 設定を読む前にそのインタフェースが Down すると priority 計算が欠落する。確実なトラッキングが必要な場合は VRRP インスタンス起動前にすべての VRRP_TRACK エントリを投入することが推奨される。
- evidence: `SONiC/doc/vrrp/VRRP_Adaptation_HLD.md` — "Uplink interface tracking" セクション (L481-492)

---

## まとめ（順序推奨）

推奨投入順序:
1. ルータインタフェース確立 (`INTERFACE` / `PORTCHANNEL_INTERFACE` / `VLAN_INTERFACE`)
2. VRRP インスタンス作成 (`VRRP|<intf>|<vrid>`)
3. VRRP_TRACK エントリ投入 (`VRRP_TRACK|<intf>|<vrid>|<track_intf>`)

削除時の逆順:
1. VRRP_TRACK エントリ削除
2. VRRP インスタンス削除
3. ルータインタフェース削除（任意）
