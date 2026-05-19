# lossless-traffic-pattern — Phase F side-effects 調査メモ

## 調査日
2026-05-19

## 調査対象ソース
- `sonic-net/sonic-swss/cfgmgr/buffermgrdyn.cpp` (HEAD)
- `sonic-net/sonic-swss/cfgmgr/buffer_headroom_mellanox.lua`
- `sonic-net/sonic-swss/cfgmgr/buffer_headroom_barefoot.lua`

## 概要

`LOSSLESS_TRAFFIC_PATTERN` は `buffermgrdyn` の Lua ヘッドルーム計算プラグインが CONFIG_DB から直接参照する。
このテーブルのフィールド変更は即時に再計算を誘発しないが、他のバッファ関連テーブル変更や
ポート速度変更をトリガーとして Lua が再実行される際に最新値が読み取られ、
APP_DB と STATE_DB の BUFFER_PROFILE_TABLE が更新される。

## 主要な副次書込み

### APP_DB APP_BUFFER_PROFILE_TABLE

- evidence: `buffermgrdyn.cpp:919`
- キー: `pg_lossless_<speed>_<cable>[_mtu<mtu>]_profile`
- フィールド: `xon`, `xoff`, `size`, `xon_offset`, `dynamic_th`
- 書込み値: Lua 計算結果の数値文字列
- 書込み関数: `m_applBufferProfileTable.set(name, fvVector)`

### STATE_DB BUFFER_PROFILE_TABLE

- evidence: `buffermgrdyn.cpp:920`
- キー: 同上
- フィールド: 同上
- 書込み関数: `m_stateBufferProfileTable.set(name, fvVector)`

## 注意

`LOSSLESS_TRAFFIC_PATTERN` テーブルは `buffermgrdyn` が直接 Subscribe していない。
Lua プラグインが実行時に `KEYS 'LOSSLESS_TRAFFIC_PATTERN*'` + `HGETALL` で CONFIG_DB を
直接読み取る設計（`buffer_headroom_mellanox.lua:91-96`, `buffer_headroom_barefoot.lua:80-85`）。

## ASIC_DB への波及

APP_DB BUFFER_PROFILE_TABLE の変更を orchagent BufferOrch が購読し、
SAI `sai_buffer_api` 経由で ASIC_DB に書き込む（二次波及）。
`LOSSLESS_TRAFFIC_PATTERN` の変更は間接的に ASIC バッファプロファイル設定にも影響する。
