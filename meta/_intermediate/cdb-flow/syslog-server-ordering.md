# SYSLOG_SERVER — Phase B 書込み順依存 証跡

生成日: 2026-05-16
対象ページ: `docs/reference/config-db/syslog-server.md`
調査コミット: sonic-buildimage (rsyslog-config.service, rsyslog.conf.j2), sonic-host-services/scripts/hostcfgd

---

## 1. 書込み経路（入り口）

| 経路 | 呼び出し | キー |
|------|---------|------|
| CLI `config syslog add` | `set_entry('SYSLOG_SERVER', <ip>, {...})` | サーバー IP / ホスト名 |
| CLI `config syslog del` | `del_entry('SYSLOG_SERVER', <ip>)` | サーバー IP / ホスト名 |
| minigraph / sonic-cfggen | `<SyslogServer>` タグから自動生成 | サーバー IP |
| REST / gNMI | 未実装（YANG 定義済みのため将来対応可能） | — |
| db_migrator | マイグレーションなし | — |

---

## 2. systemd 起動順序

```
config-setup.service
  └─ rsyslog-config.service
       ├─ Requires=config-setup.service
       ├─ After=config-setup.service
       ├─ After=sonic.target
       └─ After=interfaces-config.service
            └─ ExecStart=/usr/bin/rsyslog-config.sh
                 └─ sonic-cfggen -d -t rsyslog.conf.j2 → /etc/rsyslog.conf
                      └─ systemctl restart rsyslog
```

evidence: `sonic-buildimage/files/image_config/rsyslog/rsyslog-config.service`

---

## 3. hostcfgd ロード時の順序

```
HostConfigDaemon.load(init_data)
  │
  ├─ load_independent_config()   # AAA/TACACS/RADIUS/LDAP（systemd 待機前）
  │
  ├─ wait_till_system_init_done()  # systemctl is-system-running --wait
  │
  ├─ rsyslogcfg.load(syslog_cfg, syslog_srv)   # L2269
  │   └─ キャッシュに SYSLOG_CONFIG + SYSLOG_SERVER を格納（サービス再起動なし）
  │
  └─ register_callbacks()
      ├─ subscribe(SYSLOG_CONFIG, rsyslog_config_handler)   # L2500-2501
      └─ subscribe(SYSLOG_SERVER, rsyslog_server_handler)   # L2502-2503
```

evidence: `sonic-host-services/scripts/hostcfgd` L2232-2274, L2499-2503

---

## 4. 書込み順依存の要点

### 4-1. SYSLOG_CONFIG と SYSLOG_SERVER の結合再生成

`rsyslog_server_handler()` は SYSLOG_SERVER への変更で `rsyslog_handler()` を呼び、内部で `get_table(SYSLOG_CONFIG)` + `get_table(SYSLOG_SERVER)` の両方を再取得する。
これは `severity` 3 段階カスケード（per-server → GLOBAL → デフォルト）の計算に両テーブルが必要なため。

evidence: `hostcfgd` L2410-2415, L2417-2419

### 4-2. VRF 先行必須

`vrf=mgmt` を使用する場合: YANG `must` 制約により `MGMT_VRF_CONFIG|mgmtVrfEnabled=true` が先行必須。
`vrf=<leafref>` を使用する場合: YANG leafref 制約により `VRF.<name>` エントリ作成が先行必須。
いずれも違反時は CLI/REST 書き込み時点で reject される（hostcfgd 層での追加チェックなし）。

evidence: `sonic-syslog.yang` must/leafref 定義

### 4-3. 再起動中の中間状態

`rsyslog-config.service` 再起動（テンプレート展開 + `systemctl restart rsyslog`）中の数秒間はリモート転送が停止する。
`RemainAfterExit=yes` により完了状態は保持されるが、再起動中は transient 停止が発生する。

evidence: `hostcfgd` L1730-1738, `rsyslog-config.service` RemainAfterExit

### 4-4. キャッシュ比較による不要再起動抑制

`update_rsyslog_config()` は `self.cache` と現在設定を比較し、変化がない場合は `rsyslog-config.service` を再起動しない（cache 更新のみ）。
これにより `config reload` 時の不必要な rsyslog 再起動を抑制している。

evidence: `hostcfgd` L1725-1726

---

## 5. フィールドごとの書込み先と依存関係

| フィールド | 書込み先 | 依存関係 |
|-----------|---------|---------|
| `server_address` (key) | `/etc/rsyslog.conf` (omfwd Target) | なし（YANG inet:host 型で構文チェック） |
| `port` | `/etc/rsyslog.conf` (omfwd Port) | なし（未設定時デフォルト 514） |
| `protocol` | `/etc/rsyslog.conf` (omfwd Protocol) | なし（未設定時デフォルト udp） |
| `vrf` | `/etc/rsyslog.conf` (omfwd Device) | `VRF` テーブルまたは `MGMT_VRF_CONFIG` 先行必須 |
| `source` | `/etc/rsyslog.conf` (omfwd Address) | インターフェース設定が先行必須（rsyslog-config.service は interfaces-config.service 後） |
| `severity` | `/etc/rsyslog.conf` (severity filter) | `SYSLOG_CONFIG|GLOBAL.severity` とのカスケード |
| `filter` / `filter_regex` | `/etc/rsyslog.conf` (ereregex フィルタ行) | 両フィールドが揃っている必要あり |

---

## 6. evidence

- `sonic-buildimage/files/image_config/rsyslog/rsyslog-config.service` (systemd 起動順)
- `sonic-buildimage/files/image_config/rsyslog/rsyslog-config.sh` (設定生成スクリプト)
- `sonic-buildimage/files/image_config/rsyslog/rsyslog.conf.j2` L84-125 (Jinja2 テンプレート)
- `sonic-host-services/scripts/hostcfgd` L1695-1743 (`RSyslogCfg` クラス)
- `sonic-host-services/scripts/hostcfgd` L2203-2204 (`RSyslogCfg` 初期化)
- `sonic-host-services/scripts/hostcfgd` L2251, L2269 (load フェーズでの syslog 読込)
- `sonic-host-services/scripts/hostcfgd` L2410-2415, L2417-2419 (`rsyslog_handler`, `rsyslog_server_handler`)
- `sonic-host-services/scripts/hostcfgd` L2499-2503 (subscribe 登録)
- `sonic-yang-models/yang-models/sonic-syslog.yang` (must/leafref 制約)
