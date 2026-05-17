# sflow-collector — Phase F (side-effects) intermediate

## 調査日時
2026-05-17

## 調査対象ソース
- `sonic-swss/cfgmgr/sflowmgr.cpp` (全行精読)
- `sonic-swss/cfgmgr/sflowmgrd.cpp` (全行精読)
- `sonic-utilities/config/main.py` (sflow collector add/del 周辺)
- `sonic-utilities/show/sflow.py` (全行精読)
- `sonic-mgmt-common/translib/transformer/xfmr_sflow.go` (全行精読)

## 主要発見事項

### SET 時の副作用

#### 直接副作用: CONFIG_DB 書き込みのみ
- `config sflow collector add` → `config_db.mod_entry('SFLOW_COLLECTOR', name, {...})` で CONFIG_DB に書き込むのみ
- sflowmgrd は SFLOW_COLLECTOR を購読していないため (`sflowmgrd.cpp:36-41`)、即時の downstream 副作用なし

#### 間接副作用: hsflowd 設定ファイル + プロセス再起動
- SFLOW_COLLECTOR の変更が実際に hsflowd に届くには:
  1. `/etc/hsflowd.conf` が再生成される（hsflowd 起動スクリプト側で CONFIG_DB から生成）
  2. `service hsflowd restart` が実行される
- このトリガーは `SFLOW|global.admin_state` の変化のみ (`sflowmgr.cpp:456-459`):
  - `sflowHandleService(true)` → `service hsflowd restart`
  - `sflowHandleService(false)` → `service hsflowd stop`
- つまり SFLOW_COLLECTOR を追加/変更しても、SFLOW global admin_state を一度 down→up しない限り hsflowd には反映されない

#### gNMI/REST SET の副作用
- `YangToDb_sflow_collector_xfmr` (`xfmr_sflow.go:272`) が OpenConfig YANG から SFLOW_COLLECTOR テーブルにマッピング
- キー形式: `<ip>_<port>_<vrf>` (例: `1.1.1.1_6343_default`)
- CLI のキー形式 (name 任意文字列) とは異なる — gNMI では ip+port+vrf の複合キーが自動生成される

### DEL 時の副作用

#### 直接副作用: CONFIG_DB エントリ削除のみ
- `config sflow collector del` → `config_db.set_entry('SFLOW_COLLECTOR', name, None)` でエントリを削除
- sflowmgrd 非購読のため即時の downstream 副作用なし

#### gNMI/REST DEL の制約
- `SAMPLING_SFLOW_COLS_COL_CONFIG` パス (`/collectors/collector/config`) への DELETE は拒否 (`xfmr_sflow.go:283-284`):
  ```
  return res_map, errors.New("Delete operation not supported for this xpath")
  ```
- `/collectors/collector` レベルでの DELETE は許容される

### APPL_DB への副作用 (SFLOW_COLLECTOR 経由ではなく SFLOW|global 経由)

SFLOW_COLLECTOR テーブル自体は APPL_DB に直接書き込まれない。
APPL_DB への sFlow 関連書き込みは以下で発生:
- `m_appSflowTable.set(key, values)` — SFLOW|global の admin_state 変化時 (`sflowmgr.cpp:468`)
- `m_appSflowSessionTable.set(key, fvs)` — SFLOW_SESSION/ポート設定変化時

SFLOW_COLLECTOR のエントリは APPL_DB には複製されない。hsflowd が直接 `/etc/hsflowd.conf` を参照する。

### show コマンドへの副作用
- `show sflow` コマンド (`sonic-utilities/show/sflow.py`) は CONFIG_DB から `SFLOW_COLLECTOR` テーブルを直接読み、コレクタ情報を表示する
- APPL_DB への依存なし（コレクタ情報表示は CONFIG_DB 直接参照）

## 副作用マトリクス

| 操作 | 直接副作用 | 間接副作用 | 遅延 |
|------|-----------|-----------|------|
| SET (CLI) | CONFIG_DB SFLOW_COLLECTOR エントリ追加/更新 | なし (sflowmgrd 非購読) | hsflowd 再起動まで反映なし |
| SET (gNMI) | CONFIG_DB SFLOW_COLLECTOR エントリ追加/更新 | なし | 同上 |
| DEL (CLI) | CONFIG_DB SFLOW_COLLECTOR エントリ削除 | なし | hsflowd 再起動まで反映なし |
| DEL (gNMI /collector) | CONFIG_DB SFLOW_COLLECTOR エントリ削除 | なし | 同上 |
| DEL (gNMI /collector/config) | エラー返却 (削除不可) | なし | N/A |
| SFLOW|global admin_state up | hsflowd restart トリガー | /etc/hsflowd.conf 再生成 + hsflowd プロセス再起動 | 即時 |

## 結論
SFLOW_COLLECTOR テーブルへの書き込みは CONFIG_DB のみに副作用を持ち、sflowmgrd/APPL_DB への即時副作用はない。
唯一の downstream 副作用は hsflowd 起動時の設定ファイル読み込みであり、これは SFLOW|global.admin_state 変化時にトリガーされる。
