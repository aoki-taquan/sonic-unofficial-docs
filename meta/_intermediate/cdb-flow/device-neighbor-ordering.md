# DEVICE_NEIGHBOR — 書込み順依存分析 (Phase B)

## 調査対象

- テーブル: `DEVICE_NEIGHBOR`
- フェーズ: Phase B (ordering)
- 調査日: 2026-05-18

## consumer 一覧とその順序依存

| consumer | 順序依存 | evidence |
|---------|---------|---------|
| minigraph.py (`parse_xml`) | PORT (port_config.ini) が先行必須。port_config.ini に存在しないキーは自動削除 | `minigraph.py:2064,2631-2636` |
| minigraph.py (`parse_xml`) | DEVICE_NEIGHBOR 確定後に DEVICE_NEIGHBOR_METADATA を派生 | `minigraph.py:2638-2641` |
| pfcwd (`start_default`) | DEVICE_NEIGHBOR が書き込まれた後に実行。空だと外部ポート 0 件で PFC WD 有効化されない | `pfcwd/main.py:413-416` |
| ecnconfig | DEVICE_NEIGHBOR が書き込まれた後に実行。空だと Exception raise | `scripts/ecnconfig:282-287` |
| bgpcfgd (`managers_bgp.py`) | 間接依存: `name` フィールド → DEVICE_NEIGHBOR_METADATA → BGP peer 確立 | `managers_bgp.py:219-224` |

## minigraph 生成シーケンス

```
get_port_config() → ports dict (port_config.ini 由来)
  ↓
minigraph.xml 解析 → neighbors dict
  ↓
port_config.ini に存在しない key を neighbors から削除 (Warning)
  ↓
results['DEVICE_NEIGHBOR'] = neighbors   # L2637
  ↓
results['DEVICE_NEIGHBOR_METADATA'] = ...  # L2638-2641 (neighbors.values() から派生)
```

## orchestrator / SAI 依存

- **なし**: DEVICE_NEIGHBOR は orchagent / SAI 経由の処理がない純粋 topology テーブル。

## 推奨書込み順序

```
1. PORT テーブル確定 (port_config.ini 由来)
2. DEVICE_NEIGHBOR 書込み (sonic-cfggen -m)
3. DEVICE_NEIGHBOR_METADATA 書込み (同上 parse_xml() 内で自動)
4. pfcwd start_default / ecnconfig 実行
```
