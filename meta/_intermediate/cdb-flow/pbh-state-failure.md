# pbh-state Phase D — 失敗挙動調査メモ

## 調査対象

`sonic-swss/orchagent/pbh/pbhcap.cpp` — `PbhCapabilities` コンストラクタおよび
`writePbhVendorCapabilitiesToDb()` の失敗経路。

## 書き込みフロー概要

1. `parsePbhAsicVendor()` — `ASIC_VENDOR` env var 読み取り
2. `initPbhVendorCapabilities()` — ベンダー別能力オブジェクト構築
3. `writePbhVendorCapabilitiesToDb()` — 4 サブキー一括書き込み

## 検出された失敗経路

### 1. `ASIC_VENDOR` 環境変数が未設定

- `std::getenv(PBH_PLATFORM_ENV_VAR)` が `nullptr` を返す (`pbhcap.cpp:314-317`)
- `parsePbhAsicVendor()` が `false` を返す
- コンストラクタで `SWSS_LOG_WARN("Failed to parse ASIC vendor: fallback to %s platform", ...)` を出力し `asicVendor = GENERIC` に fallback (`pbhcap.cpp:295-298`)
- **影響**: Generic 向け値が STATE_DB に書かれる（失敗ではなく silent fallback）

### 2. unknown ASIC vendor

- `parsePbhAsicVendor()` は `"mellanox"` のみを分岐しており、他はすべて `GENERIC` 扱い (`pbhcap.cpp:323-329`)
- 将来的なベンダー名が追加されても `fieldCap` がない場合は `initPbhVendorCapabilities()` 内で `SWSS_LOG_ERROR("Failed to initialize PBH capabilities: unknown ASIC vendor")` 出力して即座に return (`pbhcap.cpp:356-359`)
- **影響**: `this->table` 等のメンバが `nullptr` のまま → 後続の `writePbhVendorCapabilitiesToDb()` で `nullptr` の `shared_ptr` deref になり、STATE_DB への書き込みがスキップされる（実質 PBH_CAPABILITIES が欠如）

### 3. STATE_DB 接続失敗

- `PbhCapabilities::stateDb` は static メンバ (`DBConnector`, timeout=0) — Redis 接続失敗時は `swsscommon` 内で例外が発生し orchagent プロセス自体が crash する
- **影響**: orchagent 全体が起動失敗（PBH 固有の影響ではなく systemd restart で自動復旧）

### 4. `Table::set()` 失敗

- `capTable.set()` は Redis `HSET` コマンドを発行するが、戻り値は void であり失敗の検出はない (`pbhcap.cpp:381,405,420,437`)
- Redis 側で `HSET` が拒否された場合（ACL 等）は silent drop になるが、通常の SONiC 環境では発生しない

### 5. 消費側 (`config pbh`) の失敗

- orchagent 未起動 / PBH_CAPABILITIES キー欠如時、`pbh_capabilities_query()` が空 dict を返す
- 各 `config pbh` サブコマンドは空 dict を「capability 不明 = 操作拒否」と解釈し `"PBH capabilities are not valid"` 等のエラーを出力する (`sonic-utilities/config/plugins/pbh.py:670-679, 781, 1090, 1351`)

## evidence line numbers

- `pbhcap.cpp:291-302` — コンストラクタ本体
- `pbhcap.cpp:295-298` — ASIC_VENDOR 未設定時 fallback
- `pbhcap.cpp:310-334` — parsePbhAsicVendor() 実装
- `pbhcap.cpp:337-368` — initPbhVendorCapabilities() 実装
- `pbhcap.cpp:356-359` — unknown vendor の SWSS_LOG_ERROR + return
- `pbhcap.cpp:370-439` — writePbhEntityCapabilitiesToDb() テンプレート特殊化 (4 種)
- `pbhcap.cpp:442-452` — writePbhVendorCapabilitiesToDb() 本体
- `sonic-utilities/config/plugins/pbh.py:670-679` — hash-field capability query
