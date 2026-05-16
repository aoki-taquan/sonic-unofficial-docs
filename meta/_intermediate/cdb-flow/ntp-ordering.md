# NTP テーブル群 — Phase B 書込み順依存調査メモ

対象テーブル: `NTP` / `NTP_SERVER` / `NTP_KEY`
調査日: 2026-05-15

## 調査対象ファイル

| ファイル | 役割 |
|---------|------|
| `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-ntp.yang` | YANG スキーマ — `NTP_SERVER.key` → `NTP_KEY.id` leafref 制約定義 |
| `sonic-buildimage/files/build_templates/init_cfg.json.j2` | ビルド時 CONFIG_DB 初期投入 — `NTP|global` を先行書込み |
| `sonic-buildimage/files/image_config/chrony/chrony.conf.j2` | chrony.conf 生成テンプレート — 書込み完了後に chrony を起動 |
| `sonic-host-services/scripts/hostcfgd` | `NtpCfg` クラス — `NTP_SERVER` / `NTP_KEY` を合算して `ntp_srv_key_handler` で一括処理 |

---

## 1. YANG leafref による書込み順制約

`sonic-ntp.yang` L199-203:

```yang
leaf key {
    description "NTP server key ID";
    type leafref {
        path /ntp:sonic-ntp/ntp:NTP_KEY/ntp:NTP_KEY_LIST/ntp:id;
    }
}
```

`NTP_SERVER.<server>.key` は `NTP_KEY` テーブルの `id` への leafref。YANG バリデーション層（`sonic-yang-mgmt`）は SET 時に参照先エントリの存在を検証する。

**順序依存**:
- `NTP_KEY|<id>` が CONFIG_DB に存在しない状態で `NTP_SERVER|<server>` に `key=<id>` を SET すると、YANG バリデーションが **leafref 解決失敗**として拒否する。
- 正しい順序: `NTP_KEY|<id>` を SET → その後 `NTP_SERVER|<server>.key=<id>` を SET。
- DEL 時の逆依存: `NTP_SERVER` が `key` フィールドで参照している `NTP_KEY|<id>` を先に DEL すると leafref が dangling になる。正しい順序: `NTP_SERVER` の `key` フィールドをクリア（または `NTP_SERVER` エントリを DEL）→ `NTP_KEY|<id>` を DEL。

---

## 2. hostcfgd: NTP_SERVER と NTP_KEY を合算処理

`hostcfgd` L2387-2391:

```python
def ntp_srv_key_handler(self, key, op, data):
    syslog.syslog(syslog.LOG_NOTICE, 'Handling NTP server/key config')
    self.ntpcfg.ntp_srv_key_update(
        self.config_db.get_table(swsscommon.CFG_NTP_SERVER_TABLE_NAME),
        self.config_db.get_table(swsscommon.CFG_NTP_KEY_TABLE_NAME))
```

`NTP_SERVER` または `NTP_KEY` のいずれかが変更されると、`ntp_srv_key_handler` が呼ばれ、**両テーブルを同時に全件読み取って** `chrony.conf` と `chrony.keys` を再生成し `chrony` を再起動する。

**順序依存**:
- `NTP_KEY` を SET した直後に `NTP_SERVER.key` を SET した場合、両変更が **別イベント** として順次 `ntp_srv_key_handler` を起動する可能性がある。1 回目のイベント（`NTP_KEY` SET）では `NTP_SERVER.key` がまだ未設定のまま `chrony` が再起動し、2 回目のイベント（`NTP_SERVER` SET）で再度再起動される。機能的には 2 回目で正しく反映されるが、**1 回目の再起動は中途半態の設定で chrony を短時間起動する**。
- `NTP_SERVER.key` の leafref チェックは YANG バリデーション層が担うため、実際には `NTP_KEY` SET 完了前に `NTP_SERVER.key` SET が行われると YANG レベルで拒否され、このレースは防がれる。

---

## 3. ntp_global_update: NTP|global 変更時の単独再起動

`hostcfgd` L1331-1364 の `ntp_global_update` は `NTP|global` の変更（`src_intf`, `vrf`, `authentication` 等）を受け取り、**単独で `systemctl restart chrony`** を実行する。

```python
def ntp_global_update(self, key: str, data: dict):
    ...
    if key != 'global' or self.cache.get('global', {}) == data:
        return  # early return: 変更なし
    ...
    run_cmd(self.CHRONY_RESTART, True, True)
    self.cache[key] = data
```

**順序依存**:
- `NTP|global` 変更（例: `authentication` を `enabled` に設定）と `NTP_KEY` 登録を並行して行う場合、`NTP|global` ハンドラと `ntp_srv_key_handler` が **独立して** chrony を再起動する。`authentication=enabled` になった時点で `NTP_KEY` がまだ未登録だと、chrony.conf.j2 の `{% if global.authentication == 'enabled' %}` ガードが通るが `chrony.keys` に鍵が存在しないため、chrony が認証鍵を見つけられず起動失敗する可能性がある。
- 正しい順序: `NTP_KEY|<id>` SET → `NTP|global.authentication=enabled` SET。

---

## 4. MGMT_VRF_CONFIG との順序依存

`sonic-ntp.yang` L127-129:

```yang
must "(current() != 'mgmt') or
     (/mvrf:sonic-mgmt_vrf/mvrf:MGMT_VRF_CONFIG/mvrf:vrf_global/mvrf:mgmtVrfEnabled = 'true')" {
    error-message "Must condition not satisfied. Try enable Management VRF.";
}
```

`NTP|global.vrf = 'mgmt'` を書き込む際、`MGMT_VRF_CONFIG|vrf_global.mgmtVrfEnabled = 'true'` が CONFIG_DB に先行して存在しなければ YANG `must` 違反でリジェクトされる。

**順序依存**: `MGMT_VRF_CONFIG|vrf_global|mgmtVrfEnabled=true` SET → `NTP|global.vrf=mgmt` SET。

さらに `chronyd-starter.sh` はランタイムに `MGMT_VRF_CONFIG` を再読み込みするため、`NTP|global.vrf=mgmt` を設定したまま `MGMT_VRF_CONFIG` を無効化すると chronyd が `ip vrf exec mgmt chronyd` で起動しようとして失敗する（**経路依存乖離**）。

---

## 5. src_intf 参照インタフェースとの順序依存

`sonic-ntp.yang` L95-124 の `src_intf` leaf-list は `PORT` / `PORTCHANNEL` / `LOOPBACK_INTERFACE` / `MGMT_PORT` への leafref union として定義される。

`NTP|global.src_intf` に設定するインタフェース名が対応テーブル（例: `MGMT_PORT|eth0`）に先行して存在しなければ leafref バリデーションが失敗する。ただし `eth0` は `pattern 'eth0'` の string 型として leafref を迂回しており、**`eth0` は常に書き込み可能**。

---

## 6. boot 時の書込みシーケンス（sonic-cfggen 経路）

`init_cfg.json.j2` L210-219 が `NTP|global` のデフォルト値を生成し、`sonic-cfggen` が CONFIG_DB に書き込む。この書込みは `hostcfgd` 起動前に行われるため、`hostcfgd` の `load()` メソッドがブート時スナップショットとして `NTP|global` / `NTP_SERVER` / `NTP_KEY` を一括取得する（`hostcfgd` L1285-1310）。

**順序依存**:
- ブート時: `sonic-cfggen` が CONFIG_DB を構築 → `hostcfgd` が `load()` で初期キャッシュを取得 → chrony はブート時の設定をそのまま引き継ぐ（hostcfgd は `load()` 時に chrony を再起動しない）。
- ブート後の最初の設定変更時に初めて `chrony restart` が行われる。

---

## 7. 書込み順序依存サマリ

| # | 依存関係 | 方向 | 違反時の挙動 |
|---|----------|------|------------|
| 1 | `NTP_KEY\|<id>` 先行 → `NTP_SERVER\|<server>.key=<id>` SET | **必須先行** | YANG leafref 拒否（SET 失敗） |
| 2 | `NTP_SERVER\|<server>` DEL または `key` クリア 先行 → `NTP_KEY\|<id>` DEL | **必須先行** | YANG leafref dangling（DEL 失敗） |
| 3 | `NTP_KEY\|<id>` SET 先行 → `NTP\|global.authentication=enabled` SET | **推奨先行** | chrony が鍵ファイルなしで起動し認証失敗 |
| 4 | `MGMT_VRF_CONFIG\|vrf_global\|mgmtVrfEnabled=true` 先行 → `NTP\|global.vrf=mgmt` SET | **必須先行** | YANG must 違反（SET 失敗） |
| 5 | `NTP\|global.vrf` クリアまたは `=default` 先行 → `MGMT_VRF_CONFIG.mgmtVrfEnabled=false` SET | **推奨先行** | chronyd が mgmt VRF で起動失敗（経路依存乖離） |
| 6 | 対応インタフェーステーブル 先行 → `NTP\|global.src_intf=<intf>` SET（eth0 以外） | **必須先行** | YANG leafref 拒否（SET 失敗） |
| 7 | CONFIG_DB 構築 (`sonic-cfggen`) 先行 → `hostcfgd` 起動 | **ブート順序保証** | hostcfgd の `load()` スナップショットが空になる |
