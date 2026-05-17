# PASS_THROUGH_ROUTE_TABLE (ChassisOrch) — Phase D: 失敗挙動調査

調査日: 2026-05-17
対象テーブル: CONFIG_DB `PASS_THROUGH_ROUTE_TABLE`
ソース: `sonic-net/sonic-swss/orchagent/chassisorch.cpp`、`orchagent/vnetorch.cpp`、`orchagent/orchdaemon.cpp`

---

## 1. ChassisOrch::doTask() — 入力バリデーションなし

`doTask()` は CONFIG_DB のエントリを処理する際、key の妥当性チェックを行わない。`IpPrefix` クラスによる正規化は `addRouteToPassThroughRouteTable()` 内で行われるが、`doTask()` 自体は key が無効な IP プレフィックスでも `attach()/detach()` を呼び出す。

```cpp
// chassisorch.cpp:50-72
void ChassisOrch::doTask(Consumer &consumer)
{
    auto it = consumer.m_toSync.begin();
    while (it != consumer.m_toSync.end())
    {
        auto t = it->second;
        const std::string & op = kfvOp(t);
        const std::string & ip = kfvKey(t);  // バリデーションなし

        if (op == SET_COMMAND)
            m_vNetRouteOrch->attach(this, ip);   // IpAddress() コンストラクタが例外を投げる可能性
        else
            m_vNetRouteOrch->detach(this, ip);
        it = consumer.m_toSync.erase(it);  // 例外発生時はここに到達しない
    }
}
```

不正な IP 文字列が key として書き込まれた場合、`IpAddress` コンストラクタが例外を投げ、`doTask()` は未処理エントリを `m_toSync` に残したまま上位に例外が伝播する。

---

## 2. VNetRouteOrch::detach() — assert(false) で強制終了

CONFIG_DB から `DEL` 操作が到達した場合、`doTask()` は `m_vNetRouteOrch->detach(this, ip)` を呼び出す。`detach()` は以下の 2 条件でエラーログ + `assert(false)` を実行する（デバッグビルド時はクラッシュ、リリースビルドでは UB として継続）:

```cpp
// vnetorch.cpp:1910-1950
void VNetRouteOrch::detach(Observer* observer, const IpAddress& dstAddr)
{
    auto observerEntry = next_hop_observers_.find(dstAddr);
    if (observerEntry == next_hop_observers_.end())
    {
        SWSS_LOG_ERROR("Failed to detach observer for %s. Entry not found.",
                       dstAddr.to_string().c_str());
        assert(false);  // デバッグビルド: プロセスクラッシュ
        return;
    }
    auto iter = std::find(...);
    if (iter == observerEntry->second.observers.end())
    {
        SWSS_LOG_ERROR("Failed to detach observer for %s. Observer not found.",
                       dstAddr.to_string().c_str());
        assert(false);  // デバッグビルド: プロセスクラッシュ
        return;
    }
    // ...
}
```

| 失敗条件 | 発生経路 | 挙動 |
|---------|---------|------|
| `DEL` を受けたが対応 observer エントリが `next_hop_observers_` に存在しない | CONFIG_DB への直接書込 / warm-reboot 後の再同期ズレ | `SWSS_LOG_ERROR` + `assert(false)` |
| `DEL` を受けたが observer リストに自身が含まれない | observer が二重 detach された場合 | `SWSS_LOG_ERROR` + `assert(false)` |

---

## 3. VNetRouteOrch が初期化されていない場合

`ChassisOrch` の constructor は `VNetRouteOrch*` をそのままポインタで保持する:

```cpp
// chassisorch.h
VNetRouteOrch* m_vNetRouteOrch;
```

`orchdaemon.cpp` では `VNetRouteOrch` が先に生成されてから `ChassisOrch` に渡される。ただし `vnet_rt_orch` が null ポインタの場合は `doTask()` 内で null 参照によるクラッシュが発生する。現実的には orchdaemon が VoQ 環境以外で `ChassisOrch` を生成しない制御を持っているが、コード上は null チェックなし。

---

## 4. APP_DB 書き込み失敗

`addRouteToPassThroughRouteTable()` は `ProducerStateTable::set()` を使って APP_DB に書き込む。swsscommon の `ProducerStateTable::set()` は Redis 接続エラーを例外としてスローせず、内部的に再接続を試みる実装になっている。したがって APP_DB への書き込みが silent に失敗することはなく、Redis が完全に到達不能な場合は `orchagent` プロセス全体が異常終了する。

---

## 5. VoQ 非環境での起動

`ChassisOrch` は `orchdaemon.cpp` で `m_switchOrch->isVoqEnabled()` チェック後に生成される:

```cpp
// orchdaemon.cpp:285-293 (概略)
if (isVoq)
{
    // VNetRouteOrch, ChassisOrch を生成
}
```

VoQ が無効な環境では `ChassisOrch` 自体が生成されないため、CONFIG_DB の `PASS_THROUGH_ROUTE_TABLE` に書き込みがあっても購読者が存在せず、APP_DB への転送は一切行われない（silent drop）。

---

## 証拠リンク

- `sonic-swss/orchagent/chassisorch.cpp:50-72` — `doTask()` の入力処理
- `sonic-swss/orchagent/vnetorch.cpp:1861-1960` — `attach()` / `detach()` 実装
- `sonic-swss/orchagent/orchdaemon.cpp:281-293` — `ChassisOrch` 生成条件
