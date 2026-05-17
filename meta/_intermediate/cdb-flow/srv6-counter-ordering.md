# srv6-counter (FLEX_COUNTER_TABLE|SRV6) — Phase B 順序依存調査メモ

## 調査対象ファイル

- `sonic-swss/orchagent/srv6orch.cpp` (ref: master)
- `sonic-swss/orchagent/flexcounterorch.cpp` (ref: master)
- `sonic-swss/orchagent/srv6orch.h` (ref: master)

---

## 1. `FLEX_COUNTER_STATUS = enable` の前提条件

### SRV6_MY_SIDS の存在

`Srv6Orch::setCountersState(true)` (srv6orch.cpp:251–283) は
`srv6_my_sid_table_` を全走査し、既存の MySID エントリ各々に対して
`addMySidCounter()` + `setMySidEntryCounter()` を呼び出す。

**MySID エントリが存在しない状態で `enable` を書いても、
`COUNTERS_SRV6_NAME_MAP` へのエントリ追加は発生しない**（走査するリストが空）。
`SRV6_MY_SIDS` を先に投入し、orchagent が SAI に MY_SID_ENTRY を作成してから
`FLEX_COUNTER_TABLE|SRV6|FLEX_COUNTER_STATUS = enable` を書くことで
全エントリのカウンタが一括登録される。

逆順（先に enable → 後から SID 追加）でも動作するが、各 SID 追加時に
`addMySidCounter()` が個別に呼ばれるため、カウンタ有効化タイミングが SID ごとに
最大 1 秒ずつずれる（SRV6_FLEX_COUNTER_UPDATE_TIMER による遅延）。

### プラットフォーム能力チェック（起動時 1 回）

`initializeCounters()` → `queryMySidCountersCapability()` が起動時に 1 度だけ
`sai_query_attribute_capability()` を実行する (srv6orch.cpp:122)。
`m_mysid_counters_supported = false` になると `enable` を書き込んでも
`setCountersState` が無視される（silent drop）。
再起動なしに `supported` を `true` に変更する手段はない。

---

## 2. `gSrv6Orch` の初期化タイミング

`flexcounterorch.cpp:337`:
```cpp
if (gSrv6Orch && (key == SRV6_KEY))
{
    gSrv6Orch->setCountersState((value == "enable"));
}
```

`gSrv6Orch` が null の場合（`Srv6Orch` 初期化前に `FLEX_COUNTER_TABLE|SRV6` が
CONFIG_DB に存在した場合など）、`setCountersState` は呼ばれない（silent drop）。
orchagent 再起動後に `FlexCounterOrch` の `load()` が再度テーブルを読み込む際には
`gSrv6Orch` は初期化済みのため問題は発生しない。
ただし **orchagent 起動中に外部から `FLEX_COUNTER_TABLE|SRV6` を書き込む場合は
`gSrv6Orch` の初期化完了を待つ必要がある**。

---

## 3. `FLEX_COUNTER_TABLE|SRV6` と counterpoll の設定順序

`counterpoll srv6 interval <ms>` は `POLL_INTERVAL` を CONFIG_DB に書き込む。
`FlexCounterOrch` が `POLL_INTERVAL` を受け取り `FlexCounterManager::update_timer()` を
呼び出して syncd に伝える。

**推奨順序**: `interval` を先に設定してから `enable` を書くことで、
最初のポーリングから目的の間隔が使われる。
`enable` 後に `interval` を変更しても次回ポーリングから反映されるため
機能上は問題ないが、初回だけデフォルト 10000 ms が使われる。

---

## 4. 削除 (DEL / disable) 時の順序

`setCountersState(false)` は `srv6_my_sid_table_` を走査し
全 MySID エントリのカウンタを削除する。
MySID エントリを先に削除すると `removeMySidCounter()` が個別に呼ばれるため、
`setCountersState(false)` 時点では既に削除済みのエントリは走査対象外になる。
順序は問わないが、**`SRV6_MY_SID_TABLE` の DEL と `disable` は同時並走しない**こと
（`m_pending_counters` への同時アクセスが発生する可能性）。

---

## 5. 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | `SRV6_MY_SID_TABLE` の SAI 登録完了 → `FLEX_COUNTER_STATUS = enable` | 推奨先行 | 逆順可だが SID ごとに最大 1 秒遅延 |
| 2 | `queryMySidCountersCapability()` 成功（起動時） → enable 有効 | 起動時一回、変更不可 | プラットフォーム非対応なら silent drop |
| 3 | `gSrv6Orch` 初期化完了 → `FLEX_COUNTER_TABLE|SRV6` 書き込み | orchagent 起動後に書き込むなら保証済み | 起動前の CONFIG_DB 書き込みは init 時に再読み込み |
| 4 | `counterpoll srv6 interval` → `counterpoll srv6 enable` | 推奨先行 | 逆順でも次ポーリングから反映 |
