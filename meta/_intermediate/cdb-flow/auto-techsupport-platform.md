# AUTO_TECHSUPPORT (GLOBAL) — Phase H プラットフォーム差分析

調査対象: `AUTO_TECHSUPPORT|GLOBAL` テーブルの consumer (auto-techsupport
パイプライン本体) が ASIC ベンダー / multi-asic / VOQ chassis / namespace に
応じて挙動を変えるか。

## 結論

**プラットフォーム差はほぼなし**。AUTO_TECHSUPPORT (GLOBAL) の評価は
ASIC 種別・VOQ chassis 構成・ベンダーに依らず host 単位で一様。multi-asic
環境のみ「container 名 (`swss0` / `syncd1` 等) の asic suffix を吸収する
ため `startswith` 前方一致で feature key を引く」という 1 箇所の配慮が
あるが、CONFIG_DB key 構造自体は host 共通 (per-asic namespace の
AUTO_TECHSUPPORT は持たない)。

## 根拠 grep

`sonic-host-services/scripts/` 配下には auto-techsupport を直接 consume
するハンドラは存在しない (タスク指定の探索範囲だが該当 0)。実コンシューマ
は `sonic-utilities/scripts/` 配下:

```
$ ls .cache/sonic-sources/sonic-host-services/scripts/ | grep -i techsupport
(0 hits)

$ grep -rli "AUTO_TECHSUPPORT" .cache/sonic-sources/sonic-host-services/
(0 hits)
```

### 主要 consumer 4 ファイル一括 grep

```
$ grep -nE "multi.asic|chassis|namespace|platform|vendor|asic_id|\
host_namespace|NAMESPACE|is_supervisor|chassis_db|is_multi_npu" \
  .cache/sonic-sources/sonic-utilities/scripts/coredump_gen_handler.py \
  .cache/sonic-sources/sonic-utilities/scripts/techsupport_cleanup.py \
  .cache/sonic-sources/sonic-utilities/scripts/memory_threshold_check.py \
  .cache/sonic-sources/sonic-utilities/scripts/memory_threshold_check_handler.py \
  .cache/sonic-sources/sonic-utilities/utilities_common/auto_techsupport_helper.py
memory_threshold_check.py:204:    # startswith to handle multi asic instances
```

唯一の hit が `memory_threshold_check.py:204` の **コメント** であり、ロジック
分岐ではなく「container 名と feature 名の前方一致比較」を行う 1 行の補足。

### multi-asic 1 箇所の中身

```python
# memory_threshold_check.py:201-206
for feature, memory_available_threshold in self.config.feature_config.items():
    for container, memory_usage in container_memory_usage.items():
        # startswith to handle multi asic instances
        if not container.startswith(feature):
            continue
```

container 名は multi-asic では `swss0` / `swss1` / `syncd0` / `syncd1` の
ように asic suffix が付くが、CONFIG_DB の
`AUTO_TECHSUPPORT_FEATURE|<feature>` key は asic suffix なしの feature 名
(`swss` / `syncd`) で保存される。これを吸収するため `startswith` で前方一致
させているだけで、namespace 別 DB 接続や per-asic 別ロジックは存在しない。

### DB 接続パターン

```
$ grep -n "SonicV2Connector\|use_unix_socket_path\|connect(" \
  .cache/sonic-sources/sonic-utilities/scripts/coredump_gen_handler.py \
  .cache/sonic-sources/sonic-utilities/scripts/techsupport_cleanup.py
```

いずれも `SonicV2Connector(use_unix_socket_path=True)` で host CONFIG_DB
(`/var/run/redis/redis.sock`) に接続。`namespace=` 引数なし。asic
namespace の CONFIG_DB は読まない。

## ASIC ベンダー観点

- AUTO_TECHSUPPORT (GLOBAL) は SAI 非経由 (本ページの Phase F
  runtime-trace 段階 3 参照)。ASIC SDK / syncd-vendor 固有処理は介在しない。
- AUTO_TECHSUPPORT が起動する `show techsupport` (= `generate_dump`
  シェルスクリプト) は内部で `bcmcmd` / `sx_api_dbg` / `mlxreg` 等の
  vendor 依存コマンドを呼ぶが、それは generate_dump 側の責務であり、
  AUTO_TECHSUPPORT テーブル schema・handler 分岐には反映されない。

## VOQ chassis 観点

- supervisor / line card いずれの host でも同一 `coredump_gen_handler.py`
  / `techsupport_cleanup.py` バイナリが動作。chassis 全体に渡る集中
  techsupport 機構は AUTO_TECHSUPPORT ファミリには存在しない (各 host で
  独立にローカル CONFIG_DB を見て、ローカル `/var/dump/` に techsupport
  を生成する)。
- `chassisdb` (`REDIS_CHASSIS_SERVER`) を AUTO_TECHSUPPORT は参照しない
  (上記 grep に hit 0)。

## namespace 観点

- multi-asic platform (Broadcom DNX、Cisco 8000、特定 Spectrum 構成等) で
  asic0..asicN namespace が作られても、auto-techsupport 系スクリプトは host
  namespace の `unix:///var/run/redis/redis.sock` (`use_unix_socket_path=True`)
  にのみ接続する。
- core dump 発生時に渡される `container_name` 引数 (`swss0` / `syncd1` 等)
  は asic suffix 付きだが、CONFIG_DB key は host の
  `AUTO_TECHSUPPORT_FEATURE|<feature>` を見る (`startswith` で前方一致吸収)。
- AUTO_TECHSUPPORT (GLOBAL) は key が `GLOBAL` 固定単一行で、asic suffix を
  そもそも持たない。

## init_cfg / build template

```
$ grep -nE "platform|asic|chassis|namespace|vendor" \
  .cache/sonic-sources/sonic-buildimage/files/build_templates/init_cfg.json.j2 \
  | grep -A1 -i AUTO_TECHSUPPORT
(no AUTO_TECHSUPPORT-specific platform branch)
```

init_cfg.json.j2 の AUTO_TECHSUPPORT (GLOBAL) ブロックは
`enable_auto_tech_support` ビルド変数で `state` を `enabled`/`disabled` に
切り替えるのみで、ASIC / chassis / vendor 分岐は持たない。

## まとめ表

| 観点 | 結果 | 根拠 |
|------|------|------|
| ASIC 種別 (Broadcom / Mellanox / Marvell / Innovium / Cisco / DASH) | 影響なし | SAI 非経由、4 consumer ファイルに vendor 分岐 0 |
| multi-asic (`is_multi_npu() == True`) | key 構造は影響なし、container 名のみ `startswith` で前方一致 | `memory_threshold_check.py:204` のコメント / 1 行ロジック |
| VOQ chassis (supervisor + line card) | 各 host で独立 | `chassisdb` 非参照、各 host で local CONFIG_DB / `/var/dump/` を独立に扱う |
| namespace (asic0..asicN) | 影響なし | 全 consumer が `use_unix_socket_path=True` で host CONFIG_DB のみ参照 |
| init_cfg / build template | 分岐なし | AUTO_TECHSUPPORT (GLOBAL) 部に platform 条件式なし (`enable_auto_tech_support` ビルド変数のみ) |

## ソース確認範囲

タスク指定の `sonic-host-services/scripts/` には auto-techsupport
consumer が存在しないため (`grep -rli AUTO_TECHSUPPORT` で 0 hit)、実体
である `sonic-utilities/scripts/` の以下 4 ファイル + 1 helper を確認:

- `sonic-utilities/scripts/coredump_gen_handler.py`
- `sonic-utilities/scripts/techsupport_cleanup.py`
- `sonic-utilities/scripts/memory_threshold_check.py`
- `sonic-utilities/scripts/memory_threshold_check_handler.py`
- `sonic-utilities/utilities_common/auto_techsupport_helper.py`

## 注記

`generate_dump` シェルスクリプト本体は本 phase の対象外 (AUTO_TECHSUPPORT
テーブルの **handler** ではなく、起動された techsupport 収集側のスクリプト)。
そちらでは `show platform summary` 等の vendor 依存コマンド呼び出しが
あるが、AUTO_TECHSUPPORT テーブル field の解釈・handler 分岐には影響しない。
