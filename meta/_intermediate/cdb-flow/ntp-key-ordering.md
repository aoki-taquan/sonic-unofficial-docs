# NTP_KEY テーブル — Phase B 書込み順依存調査メモ

対象テーブル: `NTP_KEY`
調査日: 2026-05-18

## 調査対象ファイル

| ファイル | 役割 |
|---------|------|
| `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-ntp.yang` | YANG スキーマ — `NTP_SERVER.key` → `NTP_KEY.id` leafref 制約定義 |
| `sonic-host-services/scripts/hostcfgd` | `NtpCfg.ntp_srv_key_update()` — `NTP_SERVER` / `NTP_KEY` を合算して一括処理 |
| `sonic-buildimage/files/image_config/chrony/chrony.keys.j2` | chrony.keys 生成テンプレート — `NTP_KEY` 全件を展開 |

---

## 1. NTP_KEY は被参照側（削除順序制約）

`sonic-ntp.yang` L201-203:

```yang
leaf key {
    type leafref {
        path /ntp:sonic-ntp/ntp:NTP_KEY/ntp:NTP_KEY_LIST/ntp:id;
    }
}
```

`NTP_SERVER.<server>.key` が `NTP_KEY_LIST/id` へ leafref している。`NTP_KEY` 側は自身のテーブルに leafref を持たないが、`NTP_SERVER` から参照されているため DEL 順序に制約が生まれる。

**DEL 順序依存**:
- `NTP_SERVER` エントリが `key=<id>` フィールドを持ったまま `NTP_KEY|<id>` を DEL すると、YANG leafref 整合性チェックで拒否される。
- 正しい順序: `NTP_SERVER|<server>.key` をクリア（または `NTP_SERVER|<server>` を DEL）→ `NTP_KEY|<id>` を DEL。

**SET 順序依存**:
- `NTP_KEY|<id>` の SET そのものには他テーブルへの依存なし（自律的に書き込み可能）。ただし `NTP_SERVER|<server>.key=<id>` の SET は `NTP_KEY|<id>` の先行存在を必須とする（YANG leafref）。

---

## 2. hostcfgd: NTP_KEY 変更で NTP_SERVER も合算再読み込み

`hostcfgd` L2511-2517:

```python
self.config_db.subscribe(swsscommon.CFG_NTP_SERVER_TABLE_NAME,
                         make_callback(self.ntp_srv_key_handler))
self.config_db.subscribe(swsscommon.CFG_NTP_KEY_TABLE_NAME,
                         make_callback(self.ntp_srv_key_handler))
```

`NTP_KEY` の変更イベントは `NTP_SERVER` 変更と同一ハンドラ `ntp_srv_key_handler` を起動する。ハンドラは両テーブルを同時に全件読み取って `chrony.conf` / `chrony.keys` を再生成し `systemctl restart chrony` を実行する。

**順序依存**:
- `NTP_KEY` を SET した直後に `NTP_SERVER.key` を SET した場合、各々の DB イベントが独立して `ntp_srv_key_handler` を起動し、chrony が 2 回再起動される。1 回目は `NTP_KEY` のみ変更済みの状態（`NTP_SERVER.key` 未設定のまま）で chrony を再起動するが、機能的には問題なく 2 回目で最終設定に収束する。
- leafref バリデーション（YANG 層）が `NTP_KEY` 先行を強制するため、`NTP_SERVER.key` の SET は必ず `NTP_KEY` 存在後となり実際にはレースが防がれる。

---

## 3. NTP|global.authentication と NTP_KEY の順序推奨

`NTP.global.authentication = enabled` に設定する前に `NTP_KEY` が登録されていない場合、`chrony.keys.j2` テンプレートが空の keyfile を生成した状態で chrony が再起動され、認証付きサーバとの同期が失敗する。

推奨順序: `NTP_KEY|<id>` SET → `NTP|global.authentication=enabled` SET。

---

## 4. 書込み順序依存サマリ

| # | 依存関係 | 強制度 | 違反時の挙動 |
|---|----------|--------|------------|
| 1 | `NTP_SERVER\|<server>.key` クリア 先行 → `NTP_KEY\|<id>` DEL | **必須** | YANG leafref 整合性チェックで拒否 |
| 2 | `NTP_KEY\|<id>` SET 先行 → `NTP_SERVER\|<server>.key=<id>` SET | **必須（NTP_SERVERが要求）** | NTP_SERVER 側の YANG leafref 拒否 |
| 3 | `NTP_KEY` 登録 先行 → `NTP\|global.authentication=enabled` | 推奨 | chrony が空 keyfile で再起動し認証失敗 |
