# AUTO_TECHSUPPORT_FEATURE — Phase H プラットフォーム差分析

調査対象: `AUTO_TECHSUPPORT_FEATURE` テーブルの consumer がプラットフォーム
(ASIC ベンダー / multi-asic / VOQ chassis / namespace) に応じて挙動を変えるか。

## 結論

**プラットフォーム差なし**。AUTO_TECHSUPPORT_FEATURE の挙動は ASIC 種別・
multi-asic / VOQ chassis 構成・ベンダーに依らず、host 単位で一様に適用される。

## 根拠 grep

### `coredump_gen_handler.py` (82 行)

```
$ grep -nE "multi.asic|chassis|namespace|platform|vendor|asic_id|host_namespace|NAMESPACE|is_supervisor|chassis_db|asic[0-9]" \
    .cache/sonic-sources/sonic-utilities/scripts/coredump_gen_handler.py
(0 hits)
```

- `SonicV2Connector(use_unix_socket_path=True)` で接続。namespace 引数なし →
  host CONFIG_DB のみ参照。
- `db.connect(cfg_db)` / `db.connect(state_db)` も namespace 指定なし。
- multi-asic 環境でも asic0/asic1 namespace の CONFIG_DB を iterate しない。
  各 docker (asic-scoped) で core dump が発生しても、host CONFIG_DB の
  `AUTO_TECHSUPPORT_FEATURE|<container_name>` を見るだけ。
  (container 名は `swss0` / `syncd0` のように asic suffix 付きで来るため、
  feature 名と `startswith` で前方一致して評価される)

### `techsupport_cleanup.py` (59 行)

```
$ grep -nE "multi.asic|chassis|namespace|platform|vendor|asic_id|host_namespace|NAMESPACE" \
    .cache/sonic-sources/sonic-utilities/scripts/techsupport_cleanup.py
(0 hits)
```

- `SonicV2Connector(use_unix_socket_path=True)` で host CONFIG_DB のみ参照。
- AUTO_TECHSUPPORT_FEATURE は読まず、GLOBAL の `state` / `max_techsupport_limit`
  のみで cleanup 判定。

### `utilities_common/auto_techsupport_helper.py`

```
$ grep -nE "multi.asic|chassis|namespace|platform|vendor|asic_id|host_namespace|NAMESPACE" \
    .cache/sonic-sources/sonic-utilities/utilities_common/auto_techsupport_helper.py
(0 hits)
```

helper も namespace 概念を持たない。`/var/dump/` / `/var/core/` の Linux
path はすべて host 上の絶対パスで、per-asic 分離なし。

## ASIC ベンダー観点

- AUTO_TECHSUPPORT_FEATURE は SAI 非経由 (Phase F runtime-trace 段階 3 参照)。
  ASIC SDK / syncd-vendor 固有処理は介在しない。
- 出力先 techsupport tarball には `show platform summary` / `bcmcmd` /
  `mlxreg` 等のベンダー固有コマンド結果が含まれるが、これは `generate_dump`
  シェルスクリプト側の挙動であり、AUTO_TECHSUPPORT_FEATURE テーブル schema
  /handler ロジックには影響しない。

## VOQ chassis 観点

- supervisor / line card いずれの host でも同一 `coredump_gen_handler.py`
  バイナリが動作。chassis 全体に渡る集中 techsupport 機構は AUTO_TECHSUPPORT
  ファミリには存在しない (各 line card host で独立にローカル CONFIG_DB を
  見て、ローカル `/var/dump/` に techsupport を生成する)。
- `chassisdb` (REDIS_CHASSIS_SERVER) を AUTO_TECHSUPPORT は参照しない。

## namespace 観点

- multi-asic platform (Broadcom DNX、Cisco 8000、特定 Spectrum 構成等) で
  asic0..asicN namespace が作られても、`coredump_gen_handler.py` は host
  namespace の `unix:///var/run/redis/redis.sock` (`use_unix_socket_path=True`)
  にのみ接続。
- core dump 発生時の `container_name` 引数 (`swss0` / `syncd1` 等) は asic
  suffix 付きで渡されるが、CONFIG_DB key は host の
  `AUTO_TECHSUPPORT_FEATURE|<feature>` を見る (`startswith` で前方一致)。

## テンプレート / init_cfg

```
$ grep -lE "platform|asic|chassis|namespace|vendor" \
    .cache/sonic-sources/sonic-buildimage/files/build_templates/init_cfg.json.j2 \
    | grep -i auto_techsupport
(no AUTO_TECHSUPPORT_FEATURE-specific platform branch)
```

init_cfg.json.j2 の AUTO_TECHSUPPORT_FEATURE ブロックは `{% for feature in
FEATURE %}` で feature リストを iterate するのみ。platform 分岐なし。

## まとめ表

| 観点 | 結果 | 根拠 |
|------|------|------|
| ASIC 種別 (Broadcom / Mellanox / Marvell / Innovium / Cisco / DASH) | 影響なし | SAI 非経由、`coredump_gen_handler.py` / `techsupport_cleanup.py` に vendor 分岐 0 |
| multi-asic (`is_multi_npu() == True`) | 影響なし | `SonicV2Connector(use_unix_socket_path=True)` で host CONFIG_DB のみ参照、namespace iterate なし |
| VOQ chassis (supervisor + line card) | 各 host で独立 | chassisdb 非参照、各 host で local CONFIG_DB / `/var/dump/` を独立に扱う |
| namespace (asic0..asicN) | 影響なし | container 名の asic suffix は `startswith` 前方一致で吸収。feature key 自体は asic suffix を持たない |
| init_cfg / build template | 分岐なし | AUTO_TECHSUPPORT_FEATURE 部に platform 条件式なし |

## 注記

`generate_dump` シェルスクリプト本体は本 phase の対象外 (AUTO_TECHSUPPORT
**_FEATURE** テーブルの consumer ではなく、AUTO_TECHSUPPORT (GLOBAL) を
起点に呼ばれる別 entity)。そちらでは `show platform summary` 等の vendor
依存コマンド呼び出しがあるが、`AUTO_TECHSUPPORT_FEATURE` テーブル
field の解釈・handler 分岐には影響しない。
