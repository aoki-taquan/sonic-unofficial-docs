# BGP_ALLOWED_PREFIXES — Phase F: 副次 DB 書込スキャン中間ファイル

生成日: 2026-05-16 (Task F Phase F / cdb_q67_f)

## 調査対象

`docs/reference/config-db/bgp-allowed-prefixes.md` 配下の CONFIG_DB `BGP_ALLOWED_PREFIXES` テーブル変更時に、`bgpcfgd` の `BGPAllowListMgr` ハンドラおよび関連テンプレート (`policies.conf.j2`) が APPL_DB / STATE_DB / COUNTERS_DB / その他副次 DB へ何らかの書き込みを行うか。

## 走査範囲

- `.cache/sonic-sources/sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_allow_list.py` (主購読者: `BGPAllowListMgr`)
- `.cache/sonic-sources/sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/templates/general/policies.conf.j2` (起動時 ALLOW_LIST テンプレ)
- `.cache/sonic-sources/sonic-swss/` 全体 (BGP_ALLOWED_PREFIXES を購読する mgrd/orchagent の有無)

## 走査コマンドと結果

### 1. `managers_allow_list.py` 内の DB 書込 API 呼出

```bash
grep -nE "STATE_DB|APPL_DB|COUNTERS_DB|state_db|appl_db|counters_db|hset|publish|Producer|Notification|Table\(" \
  .cache/sonic-sources/sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_allow_list.py
```

結果: **マッチ 0 件**。`BGPAllowListMgr.set_handler()` / `del_handler()` / `__update_policy()` / `__remove_policy()` のいずれも DB 書込呼出を含まない。

### 2. `BGPAllowListMgr` の出力経路

```bash
grep -nE "swsscommon|SonicV2Connector|cfg_mgr|directory|self\.db" \
  .cache/sonic-sources/sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_allow_list.py
```

検出されたヒットはすべて `self.cfg_mgr.update()` / `self.cfg_mgr.push_list(cmds)` / `self.cfg_mgr.restart_peer_groups(peer_groups)` / `self.cfg_mgr.get_text()` (`managers_allow_list.py:166-178, 199-211, 336, 402, 467, 540, 603, 619, 636, 692`)。**出力経路は FRR vtysh への push のみ** で、Redis (CONFIG_DB / APPL_DB / STATE_DB / COUNTERS_DB) を経由しない。

### 3. `policies.conf.j2` の DB 書込

```bash
grep -nE "STATE_DB|APPL_DB|COUNTERS_DB|hset|Producer|Notification" \
  .cache/sonic-sources/sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/templates/general/policies.conf.j2
```

結果: **マッチ 0 件**。テンプレ出力は FRR `vtysh` 設定 (route-map / prefix-list / community-list) のみ。

### 4. sonic-swss 側 mgrd / orchagent

```bash
grep -rnE "BGP_ALLOWED_PREFIXES" .cache/sonic-sources/sonic-swss/
```

結果: **マッチ 0 件**。`BGP_ALLOWED_PREFIXES` テーブルを購読する mgrd / orchagent は存在しない (購読者は `bgpcfgd` の `BGPAllowListMgr` のみ)。

## 結論

CONFIG_DB `BGP_ALLOWED_PREFIXES` テーブルの変更に伴う **APPL_DB / STATE_DB / COUNTERS_DB その他副次 DB への書き込みは存在しない**。

副作用はすべて **FRR vtysh への設定 push** (`ip prefix-list`, `ipv6 prefix-list`, `bgp community-list standard`, `route-map`) と、必要に応じた **peer-group の `soft clear`** (`__find_peer_group()` → `restart_peer_groups()`) に閉じる。SAI も介さない (BGP UPDATE フィルタは FRR ユーザ空間で完結)。

## 根拠サマリ

| 検証項目 | ファイル/行 | 結果 |
|---|---|---|
| `BGPAllowListMgr` 内の DB 書込 API 呼出 | `managers_allow_list.py` 全体 | 0 件 |
| 出力経路 | `managers_allow_list.py:166-178, 199-211` | `cfg_mgr.push_list()` / `cfg_mgr.restart_peer_groups()` のみ (FRR vtysh) |
| `policies.conf.j2` 内の DB 書込 | `general/policies.conf.j2` | 0 件 (vtysh テンプレのみ) |
| swss 側で `BGP_ALLOWED_PREFIXES` を購読する mgrd | `sonic-swss/` 全体 | 0 件 |

したがって本ページの副次 DB 書込ブロックは「いずれの副次 DB にも書込なし、副作用は FRR vtysh push のみ」を結論として明示する。
