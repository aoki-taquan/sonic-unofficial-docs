# STATIC_ROUTE — プラットフォーム差分 (Phase H)

ソース: `sonic-buildimage/src/sonic-bgpcfgd/`

## 調査対象ファイル

- `bgpcfgd/main.py`
- `bgpcfgd/managers_static_rt.py`
- `bgpcfgd/managers_chassis_app_db.py`
- `bfdmon/bfdmon.py`
- `staticroutebfd/main.py`
- `bgpcfgd/static_rt_timer.py`

## 発見されたプラットフォーム差分

### 1. VOQ Chassis

**ソース**: `bgpcfgd/main.py:112-113`

```python
if device_info.is_chassis():
    managers.append(ChassisAppDbMgr(common_objs, "CHASSIS_APP_DB", "BGP_DEVICE_GLOBAL"))
```

- `is_chassis()` が True の場合（VOQ 分散シャーシ構成）、`ChassisAppDbMgr` が追加登録される。
- `ChassisAppDbMgr` は Supervisor の TSA (Traffic Shift Away) 状態変化を `CHASSIS_APP_DB` の `BGP_DEVICE_GLOBAL` から購読し、Line Card の BGP を isolate/unisolate する。
- **STATIC_ROUTE テーブル自体の処理には差分なし**。`StaticRouteMgr` は VOQ 構成でも同一ロジックで動作する。
- VOQ Chassis 固有の BGP peer は `BGP_VOQ_CHASSIS_NEIGHBOR` テーブルで別途管理される（`main.py:91`）。これは静的経路の nexthop 到達性に間接的に影響する可能性がある。

### 2. SmartSwitch DPU

**ソース**: `bfdmon/bfdmon.py:25-30`

```python
switch_type = device_info.get_localhost_info("switch_type")
if switch_type and switch_type == "dpu":
    self.remote_db_connector = swsscommon.DBConnector("DPU_STATE_DB", 0, True)
    self.remote_table = swsscommon.Table(self.remote_db_connector, self.remote_status_table)
```

- `switch_type == "dpu"` の場合、BFD プローブ状態テーブルを `STATE_DB` ではなく `DPU_STATE_DB` から読む。
- テーブル名: 通常は `DPU_BFD_PROBE_STATE`（STATE_DB）、DPU では `DASH_BFD_PROBE_STATE`（DPU_STATE_DB）。
- `bfd=true` を設定した STATIC_ROUTE の BFD 監視は、DPU 環境では上記の異なる DB / テーブルから BFD セッション状態を取得する。
- **STATIC_ROUTE の CONFIG_DB 書き込み・FRR 反映ロジックは DPU 固有差分なし**。差分は BFD 監視経路のみ。

### 3. FRR バージョン差

- `bgpcfgd` のコードベースに FRR バージョン分岐コードは**存在しない**。
- `vtysh` コマンド文字列は固定（`ip route ...` / `ipv6 route ...` 形式）。
- `frr.py` は FRR デーモン起動待ちのみを行い、バージョン検出は行わない。
- FRR バージョン差による STATIC_ROUTE 挙動への影響は bgpcfgd レイヤでは吸収されており、コード上の分岐は確認されない。

## 結論

| 項目 | 差分有無 | 詳細 |
|------|----------|------|
| VOQ Chassis | △ 間接的 | `ChassisAppDbMgr` が追加。STATIC_ROUTE 処理自体は共通。TSA 状態が BGP to FRR nexthop 到達性に影響しうる |
| SmartSwitch DPU | △ BFD のみ | `bfd=true` 経路の BFD プローブ監視が `DPU_STATE_DB` 経由になる |
| FRR バージョン差 | なし | bgpcfgd レイヤでバージョン分岐なし |
