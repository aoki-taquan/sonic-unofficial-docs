# LDAP_SERVER — Phase F: 副次 DB 書込スキャン中間ファイル

生成日: 2026-05-17 (Task F Phase F / cdb_q67_f)

## 調査対象

`docs/reference/config-db/ldap-server.md` 対象の CONFIG_DB `LDAP_SERVER` / `LDAP|global` テーブル変更時に、`hostcfgd` の `AaaCfg` ハンドラが APPL_DB / STATE_DB / COUNTERS_DB / その他副次 DB へ何らかの書き込みを行うか。

## 走査範囲

- `.cache/sonic-sources/sonic-host-services/scripts/hostcfgd` (主購読者: `AaaCfg` クラス L354–L800 付近、`ldap_server_update` / `ldap_global_update` / `ldap_server_handler` / `ldap_global_handler`)
- `.cache/sonic-sources/sonic-host-services/scripts/ldap.py` (`LdapCfg` クラス)
- `.cache/sonic-sources/sonic-host-services/` 全体 (`LDAP_SERVER` テーブル名 / `STATE_DB` / `APPL_DB` / `COUNTERS_DB` の共起 grep)
- `.cache/sonic-sources/sonic-swss/` 全体 (mgrd/orchagent で LDAP テーブルを購読する箇所)

## 走査コマンドと結果

### 1. `AaaCfg` クラスでの DB 書込検索

```bash
grep -n "set(\|hset\|produce\|publish\|Notification\|ProducerState" \
  sonic-host-services/scripts/hostcfgd
```

結果: `AaaCfg` の LDAP 関連ハンドラ (`ldap_server_update` L555–L564, `ldap_global_update` L547–L553, `ldap_server_handler` L2338–L2343, `ldap_global_handler` L2331–L2337) のいずれも DB への書込呼出を含まない。これらはすべて `handle_nslcd_service()` → `modify_conf_file()` 経由で `/etc/nslcd.conf` / `/etc/nsswitch.conf` / `/etc/pam.d/common-auth-sonic` / `/etc/pam.d/common-session` などの **ホスト OS 設定ファイルの書き換えと nslcd サービス再起動** に閉じる。

### 2. `hostcfgd` 全体で LDAP 関連の副次 DB 名前空間アクセス

```bash
grep -n -i -E "STATE_DB|APPL_DB|COUNTERS_DB" \
  .cache/sonic-sources/sonic-host-services/scripts/hostcfgd \
  | grep -i "ldap"
```

結果: **マッチ 0 件**。

全体 STATE_DB アクセス確認:
- L107 `STATE_DB = "STATE_DB"` (定数定義のみ)
- L1792 `self.state_db_conn.hset('FIPS_STATS|state', ...)` — `FipsCfg` クラスのみ (LDAP とは無関係)
- L2160–L2163 `state_db_conn` の生成は `RestartWaiter.isAdvancedBootInProgress()` 用途のみ

`AaaCfg` / `LdapCfg` 関連の STATE_DB / APPL_DB / COUNTERS_DB 参照は **皆無**。

### 3. sonic-swss 側 mgrd / orchagent

```bash
grep -rn -E "LDAP_SERVER|'LDAP'" .cache/sonic-sources/sonic-swss/ \
  | grep -i -E "state_db|appl_db|counters_db"
```

結果: **マッチ 0 件**。`LDAP_SERVER` / `LDAP` テーブルを購読する mgrd / orchagent は存在しない。購読者は `hostcfgd` の `AaaCfg` (CONFIG_DB 経由) のみ。

## 具体的な副作用（ファイル書換）

LDAP 設定変更時に `modify_conf_file()` が書き換えるファイル (DB 書込ではなく OS ファイル):

| 副作用ファイル | パス | 条件 | 根拠 |
|---|---|---|---|
| `nslcd.conf` | `/etc/nslcd.conf` | LDAP_SERVER / LDAP\|global 変更時常時 | `hostcfgd` L43, `handle_nslcd_service()` L241–251 |
| `common-auth-sonic` (PAM) | `/etc/pam.d/common-auth-sonic` | `AAA.authentication.login` に `ldap` 含む場合 | `hostcfgd` L28, L720–731 |
| `common-session` (PAM) | `/etc/pam.d/common-session` | `ldap` 有効時: `pam_mkhomedir.so` 行を挿入, 無効時: 削除 | `hostcfgd` L44, L733–741 |
| `common-session-noninteractive` | `/etc/pam.d/common-session-noninteractive` | 同上 | `hostcfgd` L45, L737–742 |
| `nsswitch.conf` | `/etc/nsswitch.conf` | `ldap` 優先時: `passwd/group/shadow` 行に `ldap` 追加 | `hostcfgd` L39, L770–776 |
| `sshd` (PAM インクルード) | `/etc/pam.d/sshd` | `common-auth-sonic` 存在時に `@include` を書換 | `hostcfgd` L50, L747–751 |
| `login` (PAM インクルード) | `/etc/pam.d/login` | 同上 | `hostcfgd` L51, L748–751 |

## 結論

CONFIG_DB `LDAP_SERVER` / `LDAP|global` テーブルの変更に伴う **APPL_DB / STATE_DB / COUNTERS_DB その他副次 DB への書き込みは存在しない**。

副作用はすべて Linux ホスト OS の設定ファイル書き換え (`/etc/nslcd.conf`, `/etc/nsswitch.conf`, 各 PAM conf) および `nslcd` サービスの再起動 (`systemctl restart nslcd`) に閉じる。SAI も介さない。

## 根拠サマリ

| 検証項目 | ファイル/行 | 結果 |
|---|---|---|
| `ldap_server_update` / `ldap_global_update` 内の DB 書込 API 呼出 | `hostcfgd:547-564` | 0 件 |
| `LDAP_SERVER` テーブル名と副次 DB 名前空間の共起 | `sonic-host-services/` 全体 | 0 件 |
| swss 側で `LDAP_SERVER` を購読する mgrd | `sonic-swss/` 全体 | 0 件 |
| 主要副作用 | `handle_nslcd_service()` + `modify_conf_file()` | PAM/NSS/nslcd ファイル書換 + nslcd 再起動のみ |
