# APPL_DB STP Orchagent テーブル — Phase H プラットフォーム差調査

## 結論

`StpOrch` 自体はプラットフォーム分岐コードを一切持たない。ASIC 固有の差異はすべて SAI レイヤーに隠蔽されており、orchagent から見たプラットフォーム差は以下 3 点に集約される:

1. **`SAI_SWITCH_ATTR_MAX_STP_INSTANCE`** — ASIC が返す最大 STP インスタンス数がハードウェア依存
2. **multi-asic / VoQ chassis 非対応** — `StpOrch` は host namespace 単体で動作。per-namespace 分割なし
3. **VS (virtual switch) 環境** — SAI STP スタブ実装が動作するが BPDU 処理はカーネル転送非依存

## 根拠

### 1. SAI_SWITCH_ATTR_MAX_STP_INSTANCE — ASIC 能力依存

`StpOrch::StpOrch()` コンストラクタ (`stporch.cpp:29-43`) は SAI スイッチ属性から最大インスタンス数を取得し `updateMaxStpInstance()` で STATE_DB に公開する:

```cpp
attr.id = SAI_SWITCH_ATTR_MAX_STP_INSTANCE;
if (sai_switch_api->get_switch_attribute(gSwitchId, 2, attrs) == SAI_STATUS_SUCCESS)
{
    updateMaxStpInstance(attrs[1].value.u32);
}
```

`updateMaxStpInstance()` (`stporch.cpp:603-616`) は `max_stp_instances - 1` を `STATE_DB STP_TABLE|GLOBAL.max_stp_inst` に書き込む。この値は ASIC ベンダー実装から返されるため、ハードウェア依存:

| プラットフォーム | 典型値 | 備考 |
|---|---|---|
| Broadcom 系 (BRCM SAI) | 実測 64 が一般的 | ASIC SKU による |
| VS (virtual switch) | SAI スタブが返す実装依存値 | 実際の転送制約なし |
| その他 ASIC | 未定義 (ASIC ベンダー実装に依存) | — |

SAI クエリ失敗時は `m_maxStpInstance` が未初期化のままで STATE_DB への書き込みが行われない。この場合、`stpmgrd` は 60 秒のタイムアウト後に `STP_DEFAULT_MAX_INSTANCES = 255` (`stpmgr.h:38`) にフォールバックする。

HLD (`SONiC_PVST_HLD.md:88`) も明示的に「スケーリング限界はプラットフォームと CPU に依存し、テストで決定する必要がある」と記載している。

### 2. StpOrch 自体はプラットフォーム分岐なし

`stporch.cpp` には `getenv("platform")` / `#ifdef` / ASIC ベンダー文字列判定が存在しない。`addVlanToStpInstance()` / `addStpPort()` / `updateStpPortState()` はすべてのプラットフォームで同一の SAI API 呼び出しシーケンスを実行する。

### 3. multi-asic / VoQ chassis 非対応

`orchdaemon.cpp:262` での `StpOrch` 初期化は `m_applDb` (host APPL_DB) のみを使用し、namespace 指定がない:

```cpp
gStpOrch = new StpOrch(m_applDb, m_stateDb, stp_tables);
```

`stpmgrd` も `DBConnector::DEFAULT_UNIXSOCKET` (host namespace) のみを使用し (`stpmgrd.cpp:35-37`)、`is_multi_npu()` / `CHASSIS_APP_DB` の参照がない。

VOQ シャーシ / multi-ASIC 環境での動作は:
- `orchagent` per-namespace インスタンスが複数起動する構成では各 namespace の `StpOrch` が独立して動作する
- ただし `stpd` / `stpmgrd` は host 単一インスタンスのみ想定のため、namespace 間での STP 状態同期機構は存在しない
- HLD はシングル ASIC プラットフォームを想定スコープとして記述している

### 4. VS (virtual switch) 環境

VS SAI (`sonic-sairedis` の vs ドライバ) は `sai_stp_api_t` の各操作を実装するが、実際のデータプレーン転送制御は行わない。`StpOrch` からの視点では VS も通常の SAI 呼び出しとして処理される。

STP の BPDU 受送信は CoPP トラップ (`SAI_HOSTIF_TRAP_TYPE_STP` / `SAI_HOSTIF_TRAP_TYPE_PVRST`, `copporch.cpp:56,60`) を通じて行われるが、VS ではパケット転送がソフトウェアシミュレーションであるため BPDU のハードウェアトラップは実動作しない。結果として VS 環境での STP 動作確認は限定的となる。

### 5. SAI STP API の必須サポート

`SAI_OBJECT_TYPE_STP` は SAI 仕様上の mandatory object ではなく、プラットフォームによってはサポートしない場合がある。`sai_switch_api->get_switch_attribute` で `SAI_SWITCH_ATTR_MAX_STP_INSTANCE` 取得が失敗した場合 (`stporch.cpp:33-36`) は WARN ログのみで動作継続するが、STP インスタンスの作成 (`create_stp`) が後続で失敗するとエントリは `it++` 残置となる。

## まとめ

StpOrch はプラットフォーム非依存の SAI 抽象化レイヤーの上に構築されており、ベンダー固有の分岐を含まない。プラットフォーム差として実運用上意味があるのは `SAI_SWITCH_ATTR_MAX_STP_INSTANCE` の返値（ASIC ハードウェアの STP インスタンス上限）のみ。multi-ASIC / VoQ chassis 構成では stpd/stpmgrd がシングル namespace 専用設計のため STP の有効スコープはシングル ASIC に限定される。

## ソース参照

- `orchagent/stporch.cpp:29-43` — コンストラクタでの SAI 属性取得
- `orchagent/stporch.cpp:603-616` — `updateMaxStpInstance()`
- `orchagent/orchdaemon.cpp:256-263` — `StpOrch` 初期化 (namespace 指定なし)
- `cfgmgr/stpmgrd.cpp:35-37` — host namespace 専用 DBConnector
- `cfgmgr/stpmgr.h:38` — `STP_DEFAULT_MAX_INSTANCES = 255`
- `orchagent/copporch.cpp:56,60` — `SAI_HOSTIF_TRAP_TYPE_STP` / `SAI_HOSTIF_TRAP_TYPE_PVRST`
- `SONiC/doc/stp/SONiC_PVST_HLD.md:88` — スケーリング限界はプラットフォーム依存
