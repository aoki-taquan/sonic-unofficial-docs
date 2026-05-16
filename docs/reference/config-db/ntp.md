---
title: NTP テーブル群 (Phase A defaults + Phase D failure + Phase G pubsub)
description: "NTP / NTP_SERVER / NTP_KEY の各フィールドに対するコード由来の暗黙デフォルト・乖離・dead field・silent drop・hostcfgd / chrony テンプレート・chronyd-starter.sh の失敗挙動、および CONFIG_DB Subscribe / chrony 制御 / SIGHUP 通信メカニズムを網羅した調査ページ。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-15
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-ntp.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-buildimage
    path: files/image_config/chrony/chrony.conf.j2
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-buildimage
    path: files/build_templates/init_cfg.json.j2
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-buildimage
    path: files/image_config/chrony/chrony.keys.j2
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-buildimage
    path: files/image_config/chrony/chronyd-starter.sh
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-host-services
    path: scripts/hostcfgd
    ref: master
related:
  config_db:
    - NTP
    - NTP_SERVER
    - NTP_KEY
    - MGMT_VRF_CONFIG
  cli:
    - config ntp
  yang:
    - sonic-ntp
---

# NTP テーブル群 — コード由来デフォルト (Phase A) + 失敗挙動 (Phase D) + 通信メカニズム (Phase G)

> このページは `NTP` / `NTP_SERVER` / `NTP_KEY` 3 テーブルを横断して、YANG 定義・`init_cfg.json.j2`・`chrony.conf.j2` テンプレート・`hostcfgd` ハンドラの全行精読から得た**暗黙デフォルト**・**乖離**・**dead field**・**silent drop** を記録する。各テーブルの詳細は [`NTP (global)`](./ntp-global.md)・[`NTP_SERVER`](./ntp-server.md)・[`NTP_KEY`](./ntp-key.md) を参照。

<!-- defaults -->
## コード由来デフォルト分析

<!-- evidence:
  sonic-ntp.yang:143,149,155,161,189,195,213,219,231,255,268
  init_cfg.json.j2:210-219
  chrony.conf.j2:20-53,57-64,87-116,124-128
  chrony.keys.j2:7-18
  chronyd-starter.sh:3-16
  minigraph.py:2646
  hostcfgd:1272-1406,2512-2517
-->

### NTP|global フィールド

| フィールド | YANG default | init_cfg.json.j2 | 有効デフォルト | 分類 |
|-----------|-------------|-------------------|--------------|------|
| `authentication` | `disabled` | `"disabled"` | `disabled` | 一致 |
| `dhcp` | `enabled` | `"enabled"` | `enabled` | 一致 |
| `server_role` | `enabled` | **`"disabled"`** | **`disabled`** | **YANG-実装乖離** |
| `src_intf` | なし (任意) | `"eth0"` | `"eth0"` | build-time ハードコード |
| `vrf` | なし (任意) | `"default"` | `"default"` | build-time ハードコード |
| `admin_state` | `enabled` | `"enabled"` | `enabled` | 一致 |

#### `server_role` — YANG default=`enabled` vs init_cfg.json.j2=`"disabled"`

`sonic-ntp.yang` L155 は `default enabled` を宣言するが、`init_cfg.json.j2` L214 は `"server_role": "disabled"` を明示的に書き込む[^1]。

さらに `chrony.conf.j2` L57-63 は SmartSwitch (`DEVICE_METADATA.localhost.subtype == 'SmartSwitch'` かつ `type != 'SmartSwitchDPU'`) のときのみ `server_role` の値を参照する:

```jinja2
{% if device_metadata.subtype == 'SmartSwitch' and device_metadata.type != 'SmartSwitchDPU' -%}
{% if global.server_role == 'enabled' or global.dhcp == 'enabled' -%}
allow
binddevice bridge-midplane
{% endif -%}
{% endif -%}
```

**非 SmartSwitch では `server_role` は dead field** — フィールド値にかかわらず `chrony.conf` への影響はない。SmartSwitch では `dhcp == 'enabled'` (default) でも `allow` が追加されるため、`server_role=disabled` でも SmartSwitch は NTP server として動作する。

#### `src_intf` — YANG は任意、init_cfg が `"eth0"` を注入

YANG 上は任意の leaf-list だが、`init_cfg.json.j2` が `"eth0"` を常に設定する。`chrony.conf.j2` L87-107 は `global.src_intf` が存在する場合に `bindacqaddress <ip>` を生成し、インタフェース名の prefix でテーブルを振り分ける:

- `eth0` → `MGMT_INTERFACE`
- `Ethernet*` → `INTERFACE`
- `Loopback*` → `LOOPBACK_INTERFACE`
- `PortChannel*` → `PORTCHANNEL_INTERFACE`
- `Vlan*` → `VLAN_INTERFACE`

`src_intf` が leaf-list (複数値) でも `global.src_intf` が文字列として取り出される点に注意。hostcfgd `handle_ntp_source_intf_chg` は `src_intf` を `;` 区切りで split して比較する[^2]。

#### `vrf` — YANG は任意、init_cfg が `"default"` を注入

`init_cfg.json.j2` が `"vrf": "default"` を設定。`chronyd-starter.sh` はランタイムに:

1. `MGMT_VRF_CONFIG|vrf_global.mgmtVrfEnabled` が `"true"` かを確認
2. true なら `NTP|global.vrf` を読み、`"default"` なら default VRF で起動、それ以外 (mgmt) なら `ip vrf exec mgmt chronyd`
3. false なら常に default VRF で起動

YANG `must` 制約は DB 書き込み時のみ評価されるが、`chronyd-starter.sh` はランタイムに MGMT_VRF_CONFIG を再確認する。MGMT VRF を無効化したまま `vrf=mgmt` が DB に残ると chronyd は mgmt VRF で起動しようとして失敗する可能性がある(**経路依存乖離**)。

---

### NTP_SERVER フィールド

| フィールド | YANG default | template fallback | minigraph | 有効デフォルト | 分類 |
|-----------|-------------|-------------------|-----------|--------------|------|
| `association_type` | `server` | `\| d('server')` | - | `server` | 一致 (二重保護) |
| `iburst` | `on` | 条件付き | `"on"` 固定 | `on` | 一致。ただし潜在バグあり |
| `resolve_as` | なし (任意) | `\| d(server)` | - | server_address キー | template fallback |
| `admin_state` | `enabled` | filter による | - | `enabled` | 一致 |
| `trusted` | `no` | - | - | `no` | 一致。resolve_as 要件あり |
| `version` | `4` | - | - | `4` | 一致 |
| `key` | なし (任意) | - | - | - | authentication=disabled 時 silent drop |

#### `iburst` の潜在バグ

`chrony.conf.j2` L37 は `{% if config.iburst %}` で判定する。Jinja2/Python では文字列 `'off'` は truthy であるため、`iburst = 'off'` が DB に入っていても `iburst` オプションが `chrony.conf` に追加されてしまう[^3]。

正しくは `config.iburst == 'on'` と比較すべきところを truthy 判定しているため、**明示的に iburst=off を設定しても効かない可能性**がある。YANG が on/off enum を強制するので on/off 以外の値は入らないが、`iburst = 'off'` の場合の動作が意図と異なる。

#### `NTP_SERVER.key` — authentication=disabled 時 silent drop

`chrony.conf.j2` L30-34:

```jinja2
{% if global.authentication == 'enabled' -%}
    {% if config.key -%}
        {% set soptions = soptions ~ ' key ' ~ config.key -%}
    {% endif -%}
{% endif -%}
```

`NTP.authentication = 'disabled'` (デフォルト) のとき、`NTP_SERVER.key` に値が設定されていても `chrony.conf` の `key` オプションは生成されない。YANG バリデーションで leafref は通るが、認証なしでは鍵が使われない。

#### `NTP_SERVER.trusted` — resolve_as が必須条件

`chrony.keys.j2` L8-10:

```jinja2
{% for server in NTP_SERVER if NTP_SERVER[server].trusted == 'yes' and
                               NTP_SERVER[server].resolve_as -%}
    {% set _ = trusted_arr.append(NTP_SERVER[server].resolve_as) -%}
```

`trusted = 'yes'` でも `resolve_as` が空の場合は `trusted_str` に追加されない。YANG で `resolve_as` は任意 leaf のため、CLI や minigraph.py が `resolve_as` を設定しない場合は trusted 指定が silent drop される。

---

### NTP_KEY フィールド

| フィールド | YANG default | template参照 | 有効デフォルト | 分類 |
|-----------|-------------|-------------|--------------|------|
| `type` | `md5` | `NTP_KEY[keyid].type` (必須チェック) | `md5` | 一致。RFC 8573 非推奨 |
| `trusted` | `no` | **未参照** | `no` | **dead field** |
| `value` | なし (任意) | b64decode 必須 | - | Base64 エンコード前提 |

#### `NTP_KEY.trusted` — dead field

`chrony.keys.j2` は `NTP_KEY[keyid].trusted` を一切参照しない。trustedkey の制御は `NTP_SERVER[server].trusted` フィールドで行う。`NTP_KEY.trusted = 'yes'` を設定しても `chrony.keys` ファイルへの影響はない。

#### `NTP_KEY.value` — Base64 エンコード必須

`chrony.keys.j2` L16 は `NTP_KEY[keyid].value | b64decode` でデコードする。DB に平文を格納すると Base64 として誤ってデコードされ、chrony が誤った鍵値を使用する。CLI `config ntp authentication-key add` が Base64 エンコードを行う前提。

---

## 乖離・特殊挙動サマリ

<!-- evidence: 上記全証跡 -->

| 分類 | フィールド | 詳細 |
|------|----------|------|
| **YANG-実装乖離** | `NTP.server_role` | YANG default=`enabled`、init_cfg=`"disabled"` — 有効デフォルトは `disabled` |
| **build-time ハードコード** | `NTP.src_intf` | YANG 任意だが init_cfg が `"eth0"` を常時注入 |
| **build-time ハードコード** | `NTP.vrf` | YANG 任意だが init_cfg が `"default"` を常時注入 |
| **dead field (非SmartSwitch)** | `NTP.server_role` | 非 SmartSwitch では chrony.conf.j2 が参照しない |
| **dead field** | `NTP_KEY.trusted` | chrony.keys.j2 は NTP_KEY.trusted を未参照 |
| **silent drop** | `NTP_SERVER.key` | authentication=disabled 時は key が chrony.conf に反映されない |
| **silent drop** | `NTP_SERVER.trusted=yes` | resolve_as 未設定なら trustedkey に含まれない |
| **潜在バグ** | `NTP_SERVER.iburst` | `if config.iburst` が truthy 判定 → iburst='off' でも有効になる可能性 |
| **経路依存乖離** | `NTP.vrf` | YANG must はDB書込時のみ評価。chronyd-starter.sh はランタイムに MGMT_VRF_CONFIG を再確認 |
| **platform依存** | `NTP.server_role` / `NTP.dhcp` | SmartSwitch のみ `allow`+`binddevice` を追加 |
| **書き込み順依存** | `NTP_SERVER.key` / `NTP_KEY` | NTP_KEY 未登録時に NTP_SERVER.key を設定すると YANG leafref 拒否 |
| **Base64前提** | `NTP_KEY.value` | b64decode 必須。平文格納は誤動作 |
| **template fallback** | `NTP_SERVER.association_type` | `\| d('server')` で YANG と一致するフォールバックあり |
| **template fallback** | `NTP_SERVER.resolve_as` | `\| d(server)` でアドレスキーにフォールバック |

<!-- /defaults -->

<!-- failure -->
## 失敗挙動 (Phase D)

> 詳細証跡は `meta/_intermediate/cdb-flow/ntp-failure.md` を参照。

### hostcfgd NtpCfg ハンドラの失敗経路

| 失敗条件 | 検出箇所 | 結果 | evidence |
|---|---|---|---|
| `systemctl restart chrony` 失敗 (`handle_ntp_source_intf_chg`) | `hostcfgd:1324-1328` | `LOG_ERR` → `return`（キャッシュ更新なし・再試行なし） | `hostcfgd:1326-1329` |
| `systemctl restart chrony` 失敗 (`ntp_global_update`) | `hostcfgd:1356-1361` | `LOG_ERR` → `return`（キャッシュ更新なし — CONFIG_DB 変更は適用済みだがキャッシュが旧値のまま残存） | `hostcfgd:1358-1361` |
| `systemctl restart chrony` 失敗 (`ntp_srv_key_update`) | `hostcfgd:1397-1402` | `LOG_ERR` → `return`（キャッシュ更新なし → 次イベントで再処理保証） | `hostcfgd:1399-1402` |
| `src_intf` に対応するサーバが未設定 | `hostcfgd:1315-1316` | `return`（no-op、サーバ登録後に反映） | `hostcfgd:1315-1316` |
| `systemctl stop/start chrony` 失敗（MGMT_VRF_CONFIG 変更時） | `hostcfgd:1659-1665` | `CalledProcessError` → `LOG_ERR` → `return`（mgmt_vrf_enabled キャッシュ未更新） | `hostcfgd:1663-1666` |

#### キャッシュ不整合リスク（ntp_global_update）

`ntp_global_update` は `systemctl restart chrony` 失敗時にキャッシュを更新しない（L1364 の `self.cache[key] = data` は `return` で到達しない）。CONFIG_DB の値は既に変更済みのため、次回同フィールドに同一値が書かれた場合にキャッシュ差分なしと誤判定し no-op になる可能性がある（**経路依存不整合**）。

### テンプレート失敗経路（サイレント動作）

| 失敗条件 | 結果 | evidence |
|---|---|---|
| `NTP_SERVER.admin_state == 'disabled'` | そのサーバを `chrony.conf` から除外（サイレント除去） | `chrony.conf.j2:20` |
| `NTP_KEY.type` または `NTP_KEY.value` が空 | そのキーをキーファイルからスキップ（サイレントスキップ） | `chrony.keys.j2:15` |
| `NTP_KEY.value` が不正 Base64 | `b64decode` が誤ってデコード → 誤った鍵値を書き込む（サイレント誤動作） | `chrony.keys.j2:16` |
| `NTP_SERVER.trusted == 'yes'` かつ `resolve_as` 未設定 | `trusted_str` に追加されない（サイレントドロップ） | `chrony.keys.j2:8-10` |
| `NTP.authentication != 'enabled'` かつ `NTP_SERVER.key` 設定済み | `key` オプションが生成されない（サイレントドロップ） | `chrony.conf.j2:30-34` |
| `NTP.authentication == 'enabled'` かつ `NTP_KEY` が空 | `keyfile` ディレクティブ追加されるが chrony.keys が空 → 認証エラーで chrony が起動失敗する可能性 | `chrony.conf.j2:124-128` |
| `config.iburst == 'off'`（Jinja2 truthy 判定） | `iburst` オプションが生成される（意図に反する） | `chrony.conf.j2:37` |

### chronyd-starter.sh の失敗経路

| 失敗条件 | 結果 | evidence |
|---|---|---|
| `sonic-db-cli` が `MGMT_VRF_CONFIG|vrf_global.mgmtVrfEnabled` 読み取り失敗 | `VRF_ENABLED` が空 → default VRF で起動（安全フォールバック） | `chronyd-starter.sh:3-16` |
| `sonic-db-cli` が `NTP|global.vrf` 読み取り失敗（`mgmtVrfEnabled=true` のとき） | `VRF_CONFIGURED` が空 → mgmt VRF で起動（意図しないフォールバック） | `chronyd-starter.sh:5-11` |
| `ip vrf exec mgmt chronyd` 失敗（mgmt VRF 未設定） | `exec` 失敗 → chrony サービス起動不可（サービス障害） | `chronyd-starter.sh:11` |

### 失敗の可観測性

NTP 処理系は **STATE_DB への NTP ステータス書き込みを持たない**。失敗検知は以下のみで行う:

- `journalctl -u chrony` — chrony サービスの起動失敗
- `grep 'NtpCfg.*Failed' /var/log/syslog` — hostcfgd の `LOG_ERR` 出力
- `chronyc tracking` / `chronyc sources` — 実際の同期状態確認

<!-- /failure -->

<!-- ordering -->
## 書込み順依存 (Phase B)

### NTP_KEY 先行必須 — NTP_SERVER.key leafref

`sonic-ntp.yang` L199-203 は `NTP_SERVER.<server>.key` を `NTP_KEY.id` への leafref として定義する。YANG バリデーション層は SET 時に参照先の存在を検証するため、`NTP_KEY|<id>` が未登録の状態で `NTP_SERVER|<server>.key=<id>` を書き込むと SET が拒否される。<!-- evidence: sonic-ntp.yang:199-203 -->

正しい順序: `NTP_KEY|<id>` SET → `NTP_SERVER|<server>.key=<id>` SET。

DEL の逆順序: `NTP_SERVER` の `key` フィールドをクリアまたは `NTP_SERVER` エントリを DEL → `NTP_KEY|<id>` DEL。参照を残したまま `NTP_KEY` を先に DEL すると leafref が dangling になり DEL が失敗する。<!-- evidence: sonic-ntp.yang:199-203 -->

### NTP_KEY 先行推奨 — authentication=enabled 設定時

`chrony.conf.j2` L125-131 は `NTP.authentication == 'enabled'` のときのみ `NTP_SERVER.key` フィールドを `chrony.conf` に出力する。`NTP|global.authentication` を `enabled` に切り替えるタイミングで `NTP_KEY` が未登録だと、chrony.keys ファイルが空のまま chrony が再起動し認証が機能しない。<!-- evidence: chrony.conf.j2:125-131; hostcfgd:1331-1364 -->

正しい順序: `NTP_KEY|<id>` SET → `NTP|global.authentication=enabled` SET。

### MGMT_VRF_CONFIG 先行必須 — vrf=mgmt 設定時

`sonic-ntp.yang` L127-129 の `must` 制約により、`NTP|global.vrf = 'mgmt'` を書き込む際に `MGMT_VRF_CONFIG|vrf_global.mgmtVrfEnabled = 'true'` が未設定だと YANG `must` 違反として SET が拒否される。<!-- evidence: sonic-ntp.yang:127-129 -->

逆方向の依存: `MGMT_VRF_CONFIG.mgmtVrfEnabled` を `false` に戻す前に `NTP|global.vrf` を `default` に戻さないと、`chronyd-starter.sh` がランタイムに `ip vrf exec mgmt chronyd` で起動しようとして失敗する（YANG `must` はブート時以降の整合性を保証しない経路依存乖離）。<!-- evidence: hostcfgd:1331-1364 -->

### 参照インタフェース先行必須 — src_intf（eth0 以外）

`src_intf` に `eth0` 以外のインタフェース名（`EthernetX`、`LoopbackX`、`PortChannelX` 等）を設定する場合、対応するインタフェーステーブル（`PORT|EthernetX`、`LOOPBACK_INTERFACE|LoopbackX` 等）が先行して存在しなければ leafref バリデーションが失敗する。`eth0` は `pattern 'eth0'` の string 型で leafref を迂回しており常に書き込み可能。<!-- evidence: sonic-ntp.yang:95-124 -->

### hostcfgd: NTP_SERVER / NTP_KEY の合算処理タイミング

`ntp_srv_key_handler` は `NTP_SERVER` または `NTP_KEY` のいずれかが変更されると、**両テーブルを同時に全件読み取って** chrony を再起動する。`NTP_KEY` SET イベントと `NTP_SERVER.key` SET イベントが別々に届く場合、1 回目の再起動では `NTP_SERVER.key` がまだ未設定の状態で chrony が起動するが、2 回目のイベントで正しく反映される。YANG leafref バリデーションが `NTP_KEY` 未存在時の `NTP_SERVER.key` SET を拒否するため、実運用上この race は防がれる。<!-- evidence: hostcfgd:2387-2391 -->

### ブート時の書込みシーケンス

`sonic-cfggen` が `init_cfg.json.j2` を展開して CONFIG_DB に `NTP|global` を書き込んだ後、`hostcfgd` が `load()` でスナップショットを一括取得する。`hostcfgd` の `load()` は chrony を再起動しない（ブート時の NTP 設定は chrony の起動設定ファイルから直接読み込まれる）。ブート後の最初の CONFIG_DB 変更イベントで初めて `chrony restart` が発火する。<!-- evidence: hostcfgd:1285-1310 -->

### 順序依存サマリ

| # | 依存関係 | 違反時の挙動 |
|---|----------|------------|
| 1 | `NTP_KEY\|<id>` 先行 → `NTP_SERVER\|<server>.key=<id>` SET | YANG leafref 拒否（SET 失敗） |
| 2 | `NTP_SERVER.key` クリア 先行 → `NTP_KEY\|<id>` DEL | YANG leafref dangling（DEL 失敗） |
| 3 | `NTP_KEY` 登録 先行 → `NTP\|global.authentication=enabled` | chrony 認証失敗（鍵なし起動） |
| 4 | `MGMT_VRF_CONFIG.mgmtVrfEnabled=true` 先行 → `NTP\|global.vrf=mgmt` | YANG must 違反（SET 失敗） |
| 5 | `NTP\|global.vrf=default` 先行 → `MGMT_VRF_CONFIG.mgmtVrfEnabled=false` | chronyd 起動失敗（mgmt VRF 不存在） |
| 6 | 対応インタフェーステーブル 先行 → `NTP\|global.src_intf=<intf>` (eth0 以外) | YANG leafref 拒否（SET 失敗） |

> 中間調査詳細: `meta/_intermediate/cdb-flow/ntp-ordering.md`
<!-- /ordering -->

<!-- pubsub -->
## 通信メカニズム (Phase G) — CONFIG_DB Subscribe / chrony 制御 / SIGHUP

> 詳細証跡は `meta/_intermediate/cdb-flow/ntp-pubsub.md` を参照。

### CONFIG_DB Subscribe 登録

hostcfgd は `config_db.subscribe()` で 3 テーブルを監視する。<!-- evidence: hostcfgd:2511-2517 -->

| テーブル | swsscommon 定数 | コールバック |
|---------|---------------|------------|
| `NTP` | `CFG_NTP_GLOBAL_TABLE_NAME` | `ntp_global_handler` → `NtpCfg.ntp_global_update()` |
| `NTP_SERVER` | `CFG_NTP_SERVER_TABLE_NAME` | `ntp_srv_key_handler` → `NtpCfg.ntp_srv_key_update()` |
| `NTP_KEY` | `CFG_NTP_KEY_TABLE_NAME` | `ntp_srv_key_handler` → `NtpCfg.ntp_srv_key_update()` |

`NTP_SERVER` と `NTP_KEY` は**共通ハンドラ** (`ntp_srv_key_handler`) に集約されており、
いずれかの変更でその時点の両テーブル全件を再取得して chrony を再起動する。<!-- evidence: hostcfgd:2387-2391 -->

### 間接 Subscribe — src_intf 連動

`LOOPBACK_INTERFACE` テーブルも監視しており (`hostcfgd:2483`)、変更時に
`NtpCfg.handle_ntp_source_intf_chg(lpbk_name)` を呼び出す。<!-- evidence: hostcfgd:2355-2364 -->

条件: `NTP_SERVER` 未設定なら即 return。`src_intf` に含まれるインタフェース名が変化した場合のみ chrony 再起動。
他インタフェース種別 (`INTERFACE` / `VLAN_INTERFACE` / `PORTCHANNEL_INTERFACE`) には NTP 連動コールなし。<!-- evidence: hostcfgd:2367-2381 -->

### chrony 制御方式

すべての NTP イベントは `systemctl restart chrony` によるフルリスタートで対応する。<!-- evidence: hostcfgd:1280,1324-1329,1355-1361,1396-1402 -->

```python
CHRONY_RESTART = ['systemctl', 'restart', 'chrony']  # hostcfgd:1280
```

| ハンドラ | トリガー | キャッシュ差分チェック | キャッシュ更新タイミング |
|---------|---------|-------------------|-------------------|
| `ntp_global_update` | `NTP` 変更 | `cache['global'] == data` → no-op | `systemctl restart` 成功後 |
| `ntp_srv_key_update` | `NTP_SERVER` / `NTP_KEY` 変更 | `cache['servers'] == ntp_servers and cache['keys'] == ntp_keys` → no-op | `systemctl restart` 成功後 |
| `handle_ntp_source_intf_chg` | `LOOPBACK_INTERFACE` 変更 | インタフェース名照合のみ（差分チェックなし） | キャッシュ更新なし |

### SIGHUP の扱い

hostcfgd 自体は `signal.SIGHUP` を登録するが**何もしない**（無視）。<!-- evidence: hostcfgd:111-112 -->

```python
def signal_handler(sig, frame):
    if sig == signal.SIGHUP:
        syslog.syslog(syslog.LOG_INFO, "HostCfgd: signal 'SIGHUP' is caught and ignoring..")
```

chrony へ SIGHUP を送る経路は存在しない。NTP 設定変更は必ずフルリスタートであり、
設定のホットリロード (SIGHUP) は採用されていない。
（比較: TACACS+ の `audisp-tacplus` へは SIGHUP を送信している — `hostcfgd:489-491`）

### pub/sub ループ起動

```python
def start(self):
    self.config_db.listen(init_data_handler=self.load)  # hostcfgd:2527-2528
```

`config_db.listen()` は swsscommon の SubscriberStateTable を介した Redis Keyspace 通知ポーリングループ。
`init_data_handler=self.load` によりループ開始前に `NtpCfg.load()` でスナップショット一括取得し
ブート時のキャッシュを初期化する。<!-- evidence: hostcfgd:1285-1310,2255-2272 -->

<!-- /pubsub -->

## 関連ページ

- [CONFIG_DB: NTP (global)](./ntp-global.md)
- [CONFIG_DB: NTP_SERVER](./ntp-server.md)
- [CONFIG_DB: NTP_KEY](./ntp-key.md)
- [YANG: sonic-ntp](../yang/sonic-ntp.md)
- [CLI: config ntp](../cli/config-ntp.md)

## 引用元

[^1]: `init_cfg.json.j2` L210-219: `"NTP": {"global": {"authentication": "disabled", "dhcp": "enabled", "server_role": "disabled", "src_intf": "eth0", "admin_state": "enabled", "vrf": "default"}}`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/files/build_templates/init_cfg.json.j2#L210-L219>

[^2]: `hostcfgd` L1319: `ifs = self.cache.get('global', {}).get('src_intf', '').split(';')` — leaf-list が `;` 区切り文字列として格納される CONFIG_DB の実装依存。<https://github.com/sonic-net/sonic-host-services/blob/master/scripts/hostcfgd>

[^3]: `chrony.conf.j2` L37: `{% if config.iburst %}` — Jinja2 で文字列 `'off'` は truthy。`iburst = 'off'` のサーバも `iburst` オプションが生成される潜在的挙動。<https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/files/image_config/chrony/chrony.conf.j2#L37>
