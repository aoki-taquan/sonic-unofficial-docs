# DEVICE_NEIGHBOR (deviceop-state) — Phase D 失敗挙動スキャンノート

対象ページ: `docs/reference/config-db/deviceop-state.md`
対象テーブル: `CONFIG_DB DEVICE_NEIGHBOR` (consumer 側視点)
Consumer: `pfcwd` (`sonic-utilities/pfcwd/main.py`), `ecnconfig` (`sonic-utilities/scripts/ecnconfig`), `bgpcfgd` (`sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py`), `show interfaces` (`sonic-utilities/show/interfaces/__init__.py`)
スキャン範囲: `pfcwd/main.py:97-108,405-430`; `scripts/ecnconfig:265-295`; `managers_bgp.py:118-155,160-235`; `show/interfaces/__init__.py:310-370`

---

## 検出した失敗パターン

### 1. ecnconfig — DEVICE_NEIGHBOR 空時の Exception

- `scripts/ecnconfig:282-287` の `EcnConfig.__init__()` では非 multi-ASIC 時に `port_table = self.config_db.get_table(DEVICE_NEIGHBOR_TABLE_NAME)` を呼び、`len(self.ports_key) == 0` の場合に `raise Exception("No active ports detected in table 'DEVICE_NEIGHBOR'")` を投げる。
- コマンド全体が異常終了する。retry 機構なし。
- multi-ASIC 環境では `SYSTEM_PORT_TABLE` を使用するため影響なし（`ecnconfig:265-280`）。

### 2. pfcwd start_default — DEVICE_NEIGHBOR 空時のサイレント縮退

- `pfcwd/main.py:412` で `external_ports = list(self.config_db.get_table('DEVICE_NEIGHBOR').keys())` を実行。
- 空テーブルでも Exception なし。`active_ports = natsorted(set([] + bp_ports))` としてバックプレーンポートのみが PFC WD 対象になる。
- pfcwd の起動後に DEVICE_NEIGHBOR が追加されても反映されない（スナップショット方式）。

### 3. pfcwd get_server_facing_ports — name フィールド欠落時の KeyError

- `pfcwd/main.py:102` の `candidates[port]['name']` で DEVICE_NEIGHBOR エントリに `name` フィールドがない場合に `KeyError` が発生。
- pfcwd 起動シーケンスが中断する。

### 4. pfcwd get_server_facing_ports — DEVICE_NEIGHBOR_METADATA 未登録時のフォールバック

- `pfcwd/main.py:106-107` でサーバー向けポートが 0 件の場合、`VLAN_MEMBER` テーブルをフォールバックとして使用。
- DEVICE_NEIGHBOR_METADATA の `type='server'` エントリが存在しない場合、VLAN_MEMBER が pfcwd のポートスコープを決定するという非自明な挙動が生じる。

### 5. bgpcfgd — check_neig_meta 有効時の自動延期

- `managers_bgp.py:220-223` の `add_peer()` で `data['name']` が DEVICE_NEIGHBOR_METADATA に不在の場合、`log_info("DEVICE_NEIGHBOR_METADATA is not ready...")` を出力して `return False`。
- DEVICE_NEIGHBOR_METADATA 書込み後に directory 機構が自動再処理するため、正しい書込み順序を守れば自動回復する。

---

## 失敗パターンサマリ

| # | consumer | 失敗ケース | 挙動 | 自動回復 |
|---|---------|-----------|------|---------|
| 1 | ecnconfig | DEVICE_NEIGHBOR 空 | Exception → コマンド異常終了 | なし |
| 2 | pfcwd start_default | DEVICE_NEIGHBOR 空 | サイレント縮退（外部ポートなし） | なし |
| 3 | pfcwd get_server_facing_ports | name フィールド欠落 | KeyError → 起動中断 | なし |
| 4 | pfcwd get_server_facing_ports | type='server' 未登録 | VLAN_MEMBER フォールバック（非自明） | なし |
| 5 | bgpcfgd | DEVICE_NEIGHBOR_METADATA 不在 | return False（延期） | DEVICE_NEIGHBOR_METADATA 書込み後に自動回復 |

---

## ページ反映方針

- `<!-- failure -->` ブロックを `<!-- /cross-refs -->` の直後に挿入する。
- consumer 別失敗パターン表 + ecnconfig（最も影響大）と bgpcfgd（自動回復あり）の詳細を散文で記述。
- `<!-- value-behavior -->` / `<!-- defaults -->` / 既存ブロックは触らない。
