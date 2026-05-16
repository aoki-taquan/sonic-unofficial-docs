# IPv6 Link-local (INTERFACE / PORTCHANNEL_INTERFACE / VLAN_INTERFACE) — Phase A: フィールド暗黙デフォルト調査メモ

調査日: 2026-05-14  
調査対象:
- `sonic-swss/cfgmgr/intfmgr.cpp`
- `sonic-swss/neighsyncd/neighsync.cpp`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-interface.yang`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-portchannel.yang`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-vlan.yang`
- `sonic-utilities/config/main.py`
- `sonic-utilities/show/main.py`

---

## `ipv6_use_link_local_only` フィールド — 完全解析

本フィールドは INTERFACE / PORTCHANNEL_INTERFACE / VLAN_INTERFACE の属性ロウに共通して存在する。

### YANG デフォルト

| テーブル | YANG leaf | YANG default |
|---------|-----------|-------------|
| `INTERFACE` | `ipv6_use_link_local_only` (type `mode-status`) | `disable` |
| `PORTCHANNEL_INTERFACE` | `ipv6_use_link_local_only` (type `mode-status`) | `disable` |
| `VLAN_INTERFACE` | `ipv6_use_link_local_only` (type `mode-status`) | `disable` |

`mode-status` 型: `enum enable | enum disable`。ソース: `sonic-types.yang.j2:210-218`。

### intfmgr.cpp の処理分岐 (L781-928)

1. `ipv6_link_local_mode = ""` (C++ string) で初期化 (L781)
2. フィールドキー `"ipv6_use_link_local_only"` が存在しない場合: `ipv6_link_local_mode` は空文字列のまま
3. `if (!ipv6_link_local_mode.empty())` (L913) — 空の場合: **APP_DB に書き込まない (silent skip)**
4. `enable` の場合: `m_ipv6LinkLocalModeList.insert(alias)` → in-memory set に追加 (L917)
5. `disable` の場合: `m_ipv6LinkLocalModeList.erase(alias)` + `delIpv6LinkLocalNeigh(alias)` (L920-924)
6. どちらの場合も `FieldValueTuple("ipv6_use_link_local_only", mode)` を APP_DB に書く (L926)

**暗黙デフォルト**: CONFIG_DB にフィールドが存在しない場合は APP_DB に `ipv6_use_link_local_only` が書かれない。
→ APP_DB の `INTF_TABLE` に本フィールドが存在しない = `disable` と同等だが、明示的な "disable" エントリとは異なる。

### CONFIG_DB → APP_DB 乖離

- HLD (doc/ipv6/ipv6_link_local.md) では APP_DB `INTF_TABLE` にも `ipv6_use_link_local_only` が書かれると記述されている
- 実装 (intfmgr.cpp L913): `ipv6_link_local_mode.empty()` の場合は完全スキップ → CONFIG_DB 未設定時は APP_DB にエントリが存在しない
- `disable` を明示設定した場合のみ APP_DB に `"disable"` が書かれる
- **HLD との乖離**: HLD は「デフォルト disable が APP_DB に書かれる」と示唆するが、実装は「空の場合はスキップ」

### neighsync.cpp — dead consumer / silent drop

`NeighSync::isLinkLocalEnabled()` (L193-239):
1. ポート名プレフィクスで VLAN (`Vlan`), PortChannel (`PortChannel`), Ethernet (`Ethernet`) を判定
2. それ以外のインターフェース名 → `return false` (silent drop) → IPv6 link-local neigh を APP_DB に登録しない
3. `"Ethernet"` で始まらないポート (例: `eth0`, `docker0`, Loopback) → **暗黙 disable**: link-local neigh 学習不可
4. CONFIG_DB のエントリが存在しない場合 → `m_cfgInterfaceTable.get()` が false → `return false`
   → フィールドの有無に関わらず、属性ロウ自体がなければ link-local neigh を無視
5. `ipv6_use_link_local_only` が存在するが `"enable"` でない場合 → `return false` (例: `"disable"` でも false)

### 書き込み順依存 (ordering dependency)

1. **属性ロウ先行必須**: `ipv6_use_link_local_only` を有効にするには、まず INTERFACE 属性ロウを SET する必要がある  
   `isIntfCreated(alias)` が true である前提で `doIntfGeneralTask` が動く (L833, L1115)
2. **PORT ready 前提**: `isIntfStateOk()` が false → `return false` してキューに戻す → state_db ready 待ち
3. **VRF ready 前提** (VRF binding 同時の場合): `isIntfStateOk(vrf_name)` も確認
4. **削除時の自動クリア**: DEL_COMMAND 処理 (L1081-1086) で `m_ipv6LinkLocalModeList.erase()` + `delIpv6LinkLocalNeigh()` が実行される → 属性ロウ削除時に link-local neigh も自動削除される

### warm boot 後の挙動 (implicit reset)

- `m_ipv6LinkLocalModeList` (std::set) はプロセスメモリ上のみ。warm restart で intfmgrd が再起動すると空になる
- CONFIG_DB の `ipv6_use_link_local_only=enable` が再 replay されて再度 `insert()` される (normalな warm boot フロー)
- ただし warm boot 中の `m_AppRestartAssist` により neigh エントリは cache map 経由で温存される (`neighsync.cpp:177-179`)

### CLI の暗黙制約 (silent reject)

`config interface ipv6 enable use-link-local-only` (`config/main.py:6733-6772`):
1. インターフェース名が `Ethernet` / `PortChannel` / `Vlan` で始まらない → `ctx.fail()` (明示エラー)
2. インターフェース名が存在しない (invalid) → `ctx.fail()` (明示エラー)
3. VLAN member のインターフェース → `ctx.fail()` (明示エラー: L2 port は不可)
4. PortChannel member のインターフェース → `ctx.fail()` (明示エラー: L2 mode 不可)

`set_ipv6_link_local_only_on_interface()` (L9451-9484):
- `curr_mode == mode` の場合: **no-op** (重複設定を silent skip)
- `mode == "disable"` かつ `curr_mode is None`: **no-op** (未設定に対して disable を設定してもスキップ)
- `mode == "disable"` かつ他の属性 (VRF / IP prefix) が存在する場合: `mod_entry` で `"disable"` を書く
- `mode == "disable"` かつ他の属性が存在しない場合: **エントリごと削除** (`set_entry(None)`) → CONFIG_DB からキーを消す

### `show ipv6 link-local-mode` の読み取りロジック (show/main.py:1603-1627)

- PORT / PORTCHANNEL / VLAN テーブルを基準にループ (INTERFACE 系テーブルではなく)
- 対応する INTERFACE エントリが存在しない → `Disabled` と表示 (フィールドなし = disabled 扱い)
- INTERFACE エントリが存在するが `ipv6_use_link_local_only` フィールドなし → `Disabled`
- `ipv6_use_link_local_only == "enable"` → `Enabled`
- それ以外 (`"disable"` 含む) → `Disabled`
- **Loopback, eth0 は対象外**: PORT / PORTCHANNEL / VLAN テーブルしか見ないため、Loopback は表示されない

### プラットフォーム依存

- SAI に対応する RIF 属性なし: `ipv6_use_link_local_only` は Linux カーネルの `/proc/sys/net/ipv6` を制御する (intfmgr が直接 sysctl)
- IntfsOrch は APP_DB の `ipv6_use_link_local_only` を読んでも SAI には転送しない → **dead consumer (orchagent 側)**
- 実際の link-local アドレス自動生成はカーネルの IPv6 EUI-64 機能 + RA が担う (ASIC 非依存)
- 各 ASIC の L3 RIF 作成可否 (最大数超過等) はプラットフォーム依存で、超過時は link-local ルーティング失敗するが CONFIG_DB には記録されない

### YANG-実装 discrepancy 一覧

| 項目 | YANG/HLD の記述 | 実装の実際 | 分類 |
|-----|----------------|-----------|------|
| APP_DB デフォルト値 | HLD: `"disable"` が APP_DB に書かれる | CONFIG_DB 未設定時は APP_DB に書かれない (skip) | YANG-実装乖離 |
| IntfsOrch の consumer | HLD: IntfsOrch が L3 RIF 作成 | `ipv6_use_link_local_only` 自体を orchagent は SAI に転送しない (dead consumer) | HLD vs 実装乖離 |
| Loopback サポート | HLD 要件1.1.1: "Loopback interfaces do not require link-local" | INTERFACE テーブルにも YANG default `disable` あり。intfmgr ではプレフィクス判定で `is_lo=true` の場合も `ipv6_use_link_local_only` を処理する (L781-928) ただし neighsync は Loopback に対し `isLinkLocalEnabled()` が呼ばれない | 部分的不整合 |
| disable 時の CONFIG_DB エントリ削除 | HLD: 言及なし | 他の属性がなければ `set_entry(None)` でキーごと削除される | 未文書化挙動 |
