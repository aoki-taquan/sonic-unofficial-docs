# pbh-state — Phase B: オブジェクト生成順序・依存関係

調査日: 2026-05-16
調査対象: sonic-swss/orchagent/pbhorch.cpp, pbhcap.cpp, orchdaemon.cpp

## PbhCapabilities の初期化位置

`PBH_CAPABILITIES` テーブルを STATE_DB に書き込む `PbhCapabilities` クラスは `PbhOrch` の非 static メンバとして宣言されている (`pbhorch.h:88`)。

```
PbhOrch::pbhCap  (型: PbhCapabilities)
```

`PbhOrch` が `new PbhOrch(...)` でインスタンス化される時点で `PbhCapabilities()` コンストラクタが呼ばれ、STATE_DB への書き込みが一度だけ実行される。

## orchdaemon.cpp における生成順序

```text
orchdaemon.cpp:232  gPortsOrch = new PortsOrch(...)
orchdaemon.cpp:533  gAclOrch   = new AclOrch(...)   ← PbhOrch の引数に必要
orchdaemon.cpp:565  gPbhOrch   = new PbhOrch(connectorList, gAclOrch, gPortsOrch)
                                  ↳ PbhCapabilities() コンストラクタが即座に実行
                                     1. parsePbhAsicVendor()  — ASIC_VENDOR env var 読み取り
                                     2. initPbhVendorCapabilities() — ベンダー別能力を構築
                                     3. writePbhVendorCapabilitiesToDb() — STATE_DB に書き込み
```

## PbhCapabilities 自体の依存関係

| 依存対象 | 種別 | 必須か |
|---------|------|--------|
| `STATE_DB` | Redis データベース接続 | 必須 (static メンバ `stateDb`) |
| `ASIC_VENDOR` 環境変数 | OS 環境変数 | 任意 (未設定時 GENERIC へ fallback) |
| `gAclOrch` / `gPortsOrch` | 引数 (PbhOrch へ) | PbhOrch の動作に必要; PbhCapabilities 自体は参照しない |

`PbhCapabilities` の静的メンバ:

```cpp
// pbhcap.cpp:288-289
DBConnector PbhCapabilities::stateDb(PBH_STATE_DB_NAME, PBH_STATE_DB_TIMEOUT);
Table       PbhCapabilities::capTable(&stateDb, STATE_PBH_CAPABILITIES_TABLE_NAME);
```

`stateDb` は静的変数なので orchdaemon 初期化の最初期に生成される。他の Orch オブジェクトや CONFIG_DB エントリを必要としない。

## CONFIG_DB 側との関係

`PBH_CAPABILITIES` は STATE_DB の read-only テーブルであり、CONFIG_DB の PBH_TABLE / PBH_RULE / PBH_HASH / PBH_HASH_FIELD とは書き込みタイミングが独立している。起動後に CONFIG_DB のエントリが追加されても `PBH_CAPABILITIES` は更新されない（one-shot write）。

## 消費者の依存関係

`config pbh` コマンド (`sonic-utilities/config/plugins/pbh.py`) は `pbh_capabilities_query()` を呼ぶ前に STATE_DB へ接続する。orchagent が起動して `PBH_CAPABILITIES` を書き込んだ後でないと `config pbh` の validation が失敗する。
ただし CLI は orchagent の起動完了を明示的に wait しない（`sonic_py_common.multi_asic` 等の準備はない）。

## まとめ

```
STATE_DB 接続 (static) ─┐
ASIC_VENDOR env var ────┤→ PbhCapabilities() → PBH_CAPABILITIES 書き込み (起動時1回)
gPortsOrch / gAclOrch  ─┘  (PbhOrch コンストラクタ引数として必要だが
                              PbhCapabilities 内部では参照しない)
```
