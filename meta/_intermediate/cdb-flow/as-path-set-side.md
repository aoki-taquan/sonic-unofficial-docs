# AS_PATH_SET — Phase F: 副次 DB 書込スキャン中間ファイル

生成日: 2026-05-15 (Task F Phase F / cdb_q67_f)

## 調査対象

`docs/reference/config-db/as-path-set.md` 配下の CONFIG_DB `AS_PATH_SET` テーブル変更時に、主購読者 `frrcfgd` (`sonic-frr-mgmt-framework`) および補助購読経路 `AsPathMgr` (`sonic-bgpcfgd`) が APPL_DB / STATE_DB / COUNTERS_DB / その他副次 DB へ何らかの書き込みを行うか。

## 走査範囲

- `.cache/sonic-sources/sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py` — `hdl_aspath_set` (L1009-L1020)、`aspath_set_key_map` (L1977)、startup スキャン (L2248-L2253)、AS_PATH_SET handler 分岐 (L2998-L3011)
- `.cache/sonic-sources/sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_as_path.py` — `AsPathMgr` 全 67 行
- `.cache/sonic-sources/sonic-buildimage/dockers/docker-fpm-frr/frrcfgd/` (Jinja2 テンプレート / 起動スクリプト)
- 同リポ内で `AS_PATH_SET` テーブル名を参照する mgrd / orchagent

## 走査コマンドと結果

### 1. `frrcfgd.py` での副次 DB 書込 API 検索

```bash
grep -nE "STATE_DB|APPL_DB|COUNTERS_DB|set_entry|hset|publish|SonicV2Connector|ProducerStateTable|Notification" \
  src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py
```

結果: **マッチ 0 件**。`frrcfgd.py` は `from swsscommon.swsscommon import ConfigDBConnector` のみで CONFIG_DB の購読リスナーとして動作し、他 DB に書込む API オブジェクトをいっさい生成しない。AS_PATH_SET handler (`hdl_aspath_set`、L1009-L1020) は FRR `vtysh -c "bgp as-path access-list <name> permit <regex>"` 形式のコマンドリストを返すだけで、コマンドは `cmd_str.format(...)` で文字列組み立て → 上位 dispatcher が FRR デーモンへ vtysh 経由で送出する。

### 2. `AsPathMgr` 内の副次 DB 書込

```bash
grep -nE "STATE_DB|APPL_DB|COUNTERS_DB|set_entry|hset|publish|ProducerStateTable" \
  src/sonic-bgpcfgd/bgpcfgd/managers_as_path.py
```

結果: **マッチ 0 件**。`AsPathMgr` は `swsscommon` を import するが、メソッド `set_handler` / `del_handler` (L30-L66) で行うのは:

1. `self.cfg_mgr.update()` で FRR running-config を読み戻し (read-only)
2. `self.cfg_mgr.push("...")` で `bgp as-path access-list T2_GROUP_ASNS permit _<asn>_` / `no bgp as-path access-list T2_GROUP_ASNS ...` を FRR に送出

のみ。DB エントリへの書込なし。

### 3. AS_PATH_SET を購読する mgrd/orchagent

```bash
grep -rn "AS_PATH_SET" .cache/sonic-sources/sonic-swss/ 2>/dev/null
```

結果: **マッチ 0 件**。swss 側に `AS_PATH_SET` を購読する mgrd / orchagent は存在しない (購読者は `frrcfgd` と `AsPathMgr` の 2 経路のみ、いずれも CONFIG_DB → FRR 直送)。

### 4. Jinja2 テンプレート経路 (`bgpd.conf.db.j2`)

`bgpd.conf.db.j2:11-20` の AS_PATH_SET レンダリングは `bgp as-path access-list {{key}} permit {{path}}` を生成して FRR `bgpd` の **起動時 config として書き出すのみ**。DB 書込は伴わない (出力先は `/etc/frr/bgpd.conf` 系ファイル)。

## 結論

CONFIG_DB `AS_PATH_SET` テーブル変更に伴う **APPL_DB / STATE_DB / COUNTERS_DB / ASIC_DB / FLEX_COUNTER_DB / LOGLEVEL_DB その他副次 DB への書き込みは存在しない**。

副作用はすべて FRR `bgpd` プロセスへの vtysh コマンド送出 (および起動時の Jinja2 によるテキスト config 生成) に閉じ、SAI 非経由・swss DB 名前空間にも触れない。

## 根拠サマリ

| 検証項目 | ファイル/行 | 結果 |
|---|---|---|
| `frrcfgd` 内の副次 DB 書込 API 呼出 | `sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py` 全体 | 0 件 (`swsscommon` import は `ConfigDBConnector` のみ) |
| `AsPathMgr` 内の副次 DB 書込 | `sonic-bgpcfgd/bgpcfgd/managers_as_path.py:1-67` | 0 件 (`cfg_mgr.push()` で FRR vtysh 送出のみ) |
| swss 側で AS_PATH_SET を購読する mgrd/orchagent | `sonic-swss/` 全体 | 0 件 |
| 主購読者の主作用 | `frrcfgd.py:1009-1020` / `managers_as_path.py:30-66` | FRR `bgp as-path access-list` コマンド送出のみ |

したがって本ページの副次 DB 書込ブロックは「いずれの副次 DB にも書込なし。副作用は FRR デーモンへの vtysh コマンド送出のみ」を結論として明示する。
