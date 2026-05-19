# STP / STP_VLAN / STP_PORT — Phase H プラットフォーム差調査

## 結論

`stpmgrd` は SAI / ASIC SDK を一切経由しない純粋なソフトウェア STP 実装。プラットフォーム依存の挙動は以下の 2 点に集約される:

1. **`max_stp_instances`** — ASIC 能力に依存する最大 PVST インスタンス数（STATE_DB 経由で取得）
2. **multi-asic / VoQ chassis 非対応** — `stpmgrd` はシングル namespace 専用。マルチ ASIC / VoQ シャーシ環境での分散 STP 制御機構は存在しない

## 根拠

### 1. max_stp_instances — ASIC 能力依存

`stpmgrd.cpp:77-78` は起動時に `getStpMaxInstances()` を呼んで stpd へ `STP_INIT_READY` メッセージを送信する:

```cpp
msg.max_stp_instances = stpmgr.getStpMaxInstances();
stpmgr.sendMsgStpd(STP_INIT_READY, sizeof(msg), (void *)&msg);
```

`getStpMaxInstances()` (`stpmgr.cpp:1381-1413`) は `STATE_STP_TABLE|GLOBAL.max_stp_inst` を最大 60 秒間ポーリングし、ASIC / プラットフォームドライバが書き込んだ値を読み取る:

- Broadcom プラットフォーム: SAI から `sai_switch_attr_max_stp_instance` 取得後、StpOrch (`stporch.cpp:612`) が `STATE_STP_TABLE|GLOBAL.max_stp_inst` に書き込む
- VS（仮想スイッチ）: STATE_STP_TABLE が書き込まれない場合が多く、フォールバック値 `255` が使われる
- フォールバック: タイムアウト（60 秒）または取得値が `0` の場合 `STP_DEFAULT_MAX_INSTANCES = 255`

`allocL2Instance()` は `IS_INST_ID_AVAILABLE()` マクロ (`stpmgr.h:47`) で `max_stp_instances` 上限チェックを行い、超過時は `SWSS_LOG_ERROR` + 恒久スキップとなる。つまり PVST の実際の最大 VLAN 数は CLI の `PVST_MAX_INSTANCES = 255` ではなく、ASIC 能力が小さい場合はそちらが実効上限になる。

### 2. multi-asic / VoQ chassis 非対応

`stpmgrd.cpp:35-37` は `DBConnector` をすべて `DEFAULT_UNIXSOCKET`（ホスト namespace）で生成:

```cpp
DBConnector conf_db(CONFIG_DB, DBConnector::DEFAULT_UNIXSOCKET, 0);
DBConnector app_db(APPL_DB, DBConnector::DEFAULT_UNIXSOCKET, 0);
DBConnector state_db(STATE_DB, DBConnector::DEFAULT_UNIXSOCKET, 0);
```

- `is_multi_npu()` / `gMySwitchType` / `isChassisDbInUse()` の参照なし
- CHASSIS_APP_DB / asicN namespace 指定なし
- VOQ シャーシの line card 上で `stpmgrd` が動作する場合、そのカードのホスト CONFIG_DB のみを処理し、他カードとの PVST 状態同期機構は存在しない

### 3. PVST BPDU ebtables — カーネル依存のみ（ベンダー非依存）

PVST 有効化時に stpmgrd がハードコードする ebtables ルール:

```
ebtables -A FORWARD -d 01:00:0c:cc:cc:cd -j DROP
```

カーネルの ebtables モジュールが利用可能であれば動作する。ASIC ベンダー固有の処理はなく、全プラットフォームで同一コードパスを通る (`stpmgr.cpp:113`)。

### 4. PortInitDone 待機 — ASIC 初期化タイミング依存

`stpmgrd.cpp:72` の `stpmgr.isPortInitDone(&app_db)` は APPL_DB `APP_PORT_TABLE|PortInitDone` を無限ループで待機する。プラットフォームによってポート SAI 初期化の所要時間は異なるが、stpmgrd 自体の動作ロジックに差分はない（待機するだけ）。

### 5. warm-reboot — 宣言のみ（全プラットフォーム共通スタブ）

`stpmgrd.cpp:39-40`:

```cpp
WarmStart::initialize("stpmgrd", "stpd");
WarmStart::checkWarmStart("stpmgrd", "stpd");
```

`stpmgr.cpp` 内には `WarmStart::setWarmStartState()` 呼び出しや reconciliation ロジックが存在しない。warm reboot / cold reboot の区別なく全 CONFIG_DB エントリを再処理するため、プラットフォーム差は生じない。

## まとめ

stpmgrd は SAI 非依存・ASIC SDK 非依存のソフトウェア STP 実装。プラットフォーム差として意味があるのは `max_stp_instances` の上限値（STATE_DB 経由でプラットフォームドライバが書き込む）のみ。multi-asic / VoQ chassis 構成では stpmgrd がホスト単体スコープで動作し、分散シャーシ全体での PVST 制御は行わない。

## ソース参照

- `stpmgr.cpp:1381-1413` — `getStpMaxInstances()`
- `stpmgrd.cpp:35-40, 72, 77-78` — DBConnector 初期化・PortInitDone 待機・STP_INIT_READY 送信
- `stpmgr.cpp:113, 161` — ebtables ルール挿入・削除
- `stpmgr.h:38, 47` — `STP_DEFAULT_MAX_INSTANCES`, `IS_INST_ID_AVAILABLE()`
- `stporch.cpp:612` — `STATE_STP_TABLE|GLOBAL.max_stp_inst` 書き込み（orchagent 側）
