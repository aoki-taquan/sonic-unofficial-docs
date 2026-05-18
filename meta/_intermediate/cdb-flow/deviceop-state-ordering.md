# DEVICE_NEIGHBOR — Phase B: 書込み順依存（deviceop-state）

## 調査方法

1. consumer 特定: pfcwd/main.py, scripts/ecnconfig, show/interfaces/__init__.py, lldpmgrd, managers_bgp.py
2. 各 consumer の起動時テーブル読み出しタイミングを確認（`get_table` 呼び出し箇所）
3. bgpcfgd deps リスト (`managers_bgp.py:118-150`) から依存テーブルと延期条件を確認

対象ファイル:
- `sonic-utilities/pfcwd/main.py:97-108,405-416`
- `sonic-utilities/scripts/ecnconfig:282-287`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py:118-150,219-224`

## 検出された順序依存

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | DEVICE_NEIGHBOR 書込み → pfcwd start_default 実行 | 強制先行（起動時スナップショット） | 後から追加エントリは pfcwd スコープに反映されない |
| 2 | DEVICE_NEIGHBOR 書込み → ecnconfig 起動 | 強制先行（起動時スナップショット） | 空テーブル時は Exception で動作停止 |
| 3 | DEVICE_NEIGHBOR + DEVICE_NEIGHBOR_METADATA 書込み → bgpcfgd BGP peer 処理 | 2 段前提（check_neig_meta 有効時） | return False で延期、DEVICE_NEIGHBOR_METADATA 到着後に自動再処理 |
| 4 | DEVICE_NEIGHBOR_METADATA type='server' → pfcwd get_server_facing_ports | 強制先行 | 未存在時は VLAN_MEMBER フォールバック |
| 5 | DEVICE_NEIGHBOR → show interfaces neighbor expected | 任意（表示のみ、runtime 影響なし） | None 時は "not present" 表示して即 return |

## 結論

DEVICE_NEIGHBOR は subscribe ではなく起動時 get_table スナップショットで参照されるため、
書込み順依存は「consumer 起動タイミング vs. テーブル書込みタイミング」として現れる。
bgpcfgd のみ directory メカニズムによる遅延処理で自動緩和される。
pfcwd と ecnconfig は DEVICE_NEIGHBOR が書込まれた後に実行することが運用上の前提となる。
