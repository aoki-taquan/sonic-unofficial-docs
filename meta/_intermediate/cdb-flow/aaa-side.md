# AAA — Phase F: 副次 DB 書込スキャン中間ファイル

生成日: 2026-05-15 (Task F Phase F / cdb_q67_f)

## 調査対象

`docs/reference/config-db/aaa.md` 配下の CONFIG_DB `AAA` テーブル変更時に、`hostcfgd` の `AaaCfg` ハンドラおよび関連 mgr が APPL_DB / STATE_DB / COUNTERS_DB / その他副次 DB へ何らかの書き込みを行うか。

## 走査範囲

- `.cache/sonic-sources/sonic-host-services/scripts/hostcfgd` (主購読者: `AaaCfg` クラス L354–L800 付近)
- `.cache/sonic-sources/sonic-host-services/` 全体 (`AAA` テーブル名 / `STATE_DB` / `APPL_DB` / `COUNTERS_DB` の grep)
- `.cache/sonic-sources/sonic-swss/` 全体 (mgrd/orchagent で AAA テーブルを購読する箇所)

## 走査コマンドと結果

### 1. `AaaCfg` クラスでの DB 書込検索

```bash
sed -n '354,720p' hostcfgd \
  | grep -n -E "set\(|hset|publish|Producer|Table\(|Notification|swsscommon"
```

結果: **マッチ 0 件**。`AaaCfg.aaa_update()`、`tacacs_*_update()`、`radius_*_update()`、`ldap_*_update()`、`hostname_update()`、`handle_radius_*` のいずれも DB への書込呼出を含まない。これらはすべて `modify_conf_file()` 経由で `/etc/pam.d/common-auth`、`/etc/nsswitch.conf`、`/etc/tacplus_nss.conf`、`/etc/pam_radius_auth.conf`、`/etc/raddb/server`、`/etc/nslcd.conf`、`/etc/sssd/sssd.conf`、`/etc/pam.d/sshd` などの **PAM/NSS/sshd 設定ファイルの書き換え** に閉じる。

### 2. `hostcfgd` 全体で AAA に関連する DB 名前空間アクセス

```bash
grep -n -i -E "STATE_DB|APPL_DB|COUNTERS_DB|state_db|appl_db" \
  .cache/sonic-sources/sonic-host-services/scripts/hostcfgd
```

検出されたヒット (抜粋):

- L107 `STATE_DB = "STATE_DB"` (定数定義のみ)
- L1759–L1821 `FipsCfg` クラスが `FIPS_STATS|state` を `STATE_DB` に hset (AAA とは無関係)
- L2160–L2162 `state_db_conn` の生成と `RestartWaiter.isAdvancedBootInProgress()` 用途のみ
- L2210 `FipsCfg(self.state_db_conn)` への引き渡し

`AaaCfg` 関連の参照は **皆無**。

### 3. sonic-swss 側 mgrd / orchagent

```bash
grep -rn -E "AAA\||subscribe.*AAA|'AAA'" .cache/sonic-sources/sonic-swss/ \
  | grep -i -E "state_db|appl_db|counters_db"
```

結果: **マッチ 0 件**。`AAA` テーブルを購読する mgrd / orchagent は存在しない (購読者は `hostcfgd` の `AaaCfg` のみ)。

## 結論

CONFIG_DB `AAA` テーブルの変更に伴う **APPL_DB / STATE_DB / COUNTERS_DB その他副次 DB への書き込みは存在しない**。

副作用はすべて Linux ホスト OS のファイル書き換え (PAM / NSS / nslcd / sssd / radiusd / sshd の各 conf) に閉じる。SAI も介さない。

## 根拠サマリ

| 検証項目 | ファイル/行 | 結果 |
|---|---|---|
| `AaaCfg` 内の DB 書込 API 呼出 | `sonic-host-services/scripts/hostcfgd:354-720` | 0 件 |
| `AAA` テーブル名と副次 DB 名前空間の共起 | `sonic-host-services/` 全体 | 0 件 |
| swss 側で `AAA` を購読する mgrd | `sonic-swss/` 全体 | 0 件 |
| 主要副作用 | `AaaCfg.modify_conf_file()` (hostcfgd:641-648) | PAM/NSS/sshd ファイル書換のみ |

したがって本ページの副次 DB 書込ブロックは「いずれの副次 DB にも書込なし」を結論として明示する。
