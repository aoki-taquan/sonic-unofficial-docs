# MCLAG_INTERFACE — Phase D 失敗挙動スキャンノート

生成日: 2026-05-19 (Task F Phase D / q67-f-batch856)

## 調査対象

`MCLAG_INTERFACE` テーブルを処理する 2 つの主要 Consumer:

1. `MlagOrch::doMlagInterfaceTask()` (`sonic-swss/orchagent/mlagorch.cpp`)
2. `MclagLink::mclagsyncdSendMclagIfaceCfg()` (`sonic-swss/mclagsyncd/mclaglink.cpp`)

## 走査範囲

- `sonic-swss/orchagent/mlagorch.cpp` L45-250 全行
- `sonic-swss/mclagsyncd/mclaglink.cpp` L989-1085 (`mclagsyncdSendMclagIfaceCfg`), L918-960 (`addDomainCfgDependentSelectables`)

## 検出した失敗経路

### MlagOrch 側

#### 1. allPortsReady() 未完了時の処理遅延

- `mlagorch.cpp:49-52`: `gPortsOrch->allPortsReady()` が false の間は即 `return`。
- MCLAG_INTERFACE エントリはキューに保留され、PortsOrch 起動完了後に一括処理される。
- **失敗ではなく「遅延」**: エントリは失われない。PortsOrch 起動後に自動処理される。

#### 2. unknown op (SET でも DEL でもない操作)

- `mlagorch.cpp:148-151`: `else` 分岐で `SWSS_LOG_ERROR("MLAG receives unknown operation type %s", op.c_str())` のみ。
- エントリは `erase` されてドロップ。retry なし。

#### 3. addMlagInterface での重複 SET

- `mlagorch.cpp:198-203`: `m_mlagIntfs.find(if_name) != m_mlagIntfs.end()` 時は `SWSS_LOG_ERROR("MLAG adds duplicate MLAG interface %s")` のみ。
- それ以上の処理は行われない（`m_mlagIntfs` への重複 insert は起きない）が、`addMlagInterface` は `true` を返してエントリは erase される（retry なし）。

#### 4. delMlagInterface での未知インターフェース DEL

- `mlagorch.cpp:220-225`: `m_mlagIntfs.find(if_name) == m_mlagIntfs.end()` 時は `SWSS_LOG_ERROR("MLAG deletes unknown MLAG interface %s")` のみ。
- `delMlagInterface` は `true` を返してエントリは erase される（retry なし）。

### mclagsyncd 側

#### 5. KEY 形式不正（if_name が空）

- `mclaglink.cpp:1022-1025`: `key` のデリミタ後の `mclag_ifaces` が空の場合は `SWSS_LOG_ERROR("Invalid Key %s Format. No mclag iface specified")` → `continue`。
- 当該エントリのみスキップ。後続エントリの処理は継続。

#### 6. write() 失敗（iccpd 向け IPC 送信失敗）

- `mclaglink.cpp:1055-1059`: バッチ中間バッファの `::write(getConnSocket(), ...)` 失敗時は `SWSS_LOG_ERROR` のみ。
- `mclaglink.cpp:1080-1083`: 最終バッチ書込み失敗も `SWSS_LOG_ERROR` のみ。
- **retry なし**: write 失敗でもデーモンは継続。iccpd への通知が欠落するが、iccpd 側は次の ICCP セッション再確立時に再 fetch される。

#### 7. MCLAG_INTERFACE SET/DEL の subscribe 未完（MCLAG_DOMAIN 未 SET）

- `mclaglink.cpp:918`: `p_mclag_intf_cfg_tbl` は MCLAG_DOMAIN 初回 SET 後の `addDomainCfgDependentSelectables()` 内でのみ生成される。
- それ以前に MCLAG_INTERFACE を書いても `mclagsyncd` は購読しておらず、**完全に無視**される（エラーログもなし）。

## 結論

| # | 失敗条件 | 発生箇所 | 結果 | retry |
|---|---------|---------|------|-------|
| 1 | allPortsReady() 未完了 | `mlagorch.cpp:49-52` | エントリ保留（自動処理） | あり（PortsOrch 起動待ち） |
| 2 | 不明 op | `mlagorch.cpp:148-151` | SWSS_LOG_ERROR + erase | なし |
| 3 | 重複 addMlagInterface | `mlagorch.cpp:198-203` | SWSS_LOG_ERROR、erase、通知スキップ | なし |
| 4 | 未知 if_name の DEL | `mlagorch.cpp:220-225` | SWSS_LOG_ERROR + erase | なし |
| 5 | KEY に if_name なし | `mclaglink.cpp:1022-1025` | SWSS_LOG_ERROR + continue | なし |
| 6 | iccpd write() 失敗 | `mclaglink.cpp:1055-1059, 1080-1083` | SWSS_LOG_ERROR、通知欠落 | なし（ICCP 再接続時に iccpd 側再 fetch） |
| 7 | MCLAG_DOMAIN 未 SET 時の MCLAG_INTERFACE | `mclaglink.cpp:918` | 完全無視（エラーログなし） | なし |
