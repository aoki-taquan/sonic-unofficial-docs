# BGP_GLOBALS_AF_NETWORK — Phase H: プラットフォーム差分

生成日: 2026-05-16 (Task F Phase H)

<!-- platform -->
## Phase H: プラットフォーム / ASIC 依存分岐

### 調査スコープ

- `sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py` — BGP_GLOBALS_AF_NETWORK ハンドラ全体
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-bgp-global.yang`

### 結論: プラットフォーム / ASIC 分岐なし

`frrcfgd.py` 全体に `platform`・`hwsku`・`asic` キーワードは**一切存在しない**（grep 結果 0 件）。

BGP_GLOBALS_AF_NETWORK テーブルのハンドラ (`bgp_table_handler_common`) および
テーブル登録コード (L99, L2119, L2139, L2318) にも、プラットフォーム・ASIC・
チップ型番による条件分岐は含まれない。

### 根拠

| チェック項目 | 結果 |
|-------------|------|
| `frrcfgd.py` 内 `platform` 参照 | 0 件 |
| `frrcfgd.py` 内 `hwsku` 参照 | 0 件 |
| `frrcfgd.py` 内 `asic` 参照 | 0 件 |
| `DEVICE_METADATA` 参照 | L80, L2162 のみ — `frr_mgmt_framework_config` フラグ読み取りに限定。プラットフォーム選択ではなく frr-mgmt-framework 有効/無効の切り替えのみ |

### frr-mgmt-framework 有効フラグについて

```python
# frrcfgd.py:2162
db_entry = self.config_db.get_entry('DEVICE_METADATA', 'localhost')
```

`DEVICE_METADATA` は `frr_mgmt_framework_config` フラグの取得にのみ使用される。
これはプラットフォーム依存ではなく、**管理者設定**（`true`/`false`）により frrcfgd 全体の
動作モードを切り替えるものであり、BGP_GLOBALS_AF_NETWORK ハンドラの
内部ロジックには影響しない。

### SAI / ハードウェア非経由

BGP_GLOBALS_AF_NETWORK は FRR (`bgpd`) へ直接 vtysh コマンドを発行する経路のみを持ち、
orchagent / syncd / SAI を経由しない。したがって ASIC ケイパビリティ差による
コードパスの分岐が発生する設計上の余地がない。

<!-- /platform -->
