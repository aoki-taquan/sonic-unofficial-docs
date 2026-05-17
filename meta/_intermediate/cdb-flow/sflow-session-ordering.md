# sflow-session — Phase B: 書込み順依存 (ordering)

調査対象: `sonic-swss/cfgmgr/sflowmgr.cpp`, `sonic-swss/orchagent/sfloworch.cpp`
調査日: 2026-05-17

## O1: PORT → SFLOW_SESSION (必須)

`sflowmgr.cpp:522-528` (doTask の per-port SESSION SET 処理):

```cpp
auto sflowPortConf = m_sflowPortConfMap.find(key);
if (sflowPortConf == m_sflowPortConfMap.end())
{
    it++;
    continue;
}
```

ポートが `m_sflowPortConfMap` に未登録の場合、`it++; continue` で永続スキップされる（リトライなし）。
`m_sflowPortConfMap` は `CFG_PORT_TABLE_NAME` の SET イベントで初期化される。したがって `PORT|<port>` SET が先行必須。

## O2: SFLOW|global admin=up → SFLOW_SESSION の APP_DB 反映 (実質必須)

`sflowmgr.cpp:531-534`:

```cpp
if (m_gEnable)
{
    m_appSflowSessionTable.set(key, fvs);
}
```

`m_gEnable == false` の場合、per-port SESSION の SET を受信しても APP_DB には何も書かれない。
グローバルを後から up にすると `sflowHandleSessionAll()` / `sflowHandleSessionLocal()` が再適用する。

## O3: SFLOW_SESSION|all → SFLOW_SESSION|<port> (推奨)

`sflowmgr.cpp:374-382` (`sflowCheckAndFillValues()`):

```cpp
if (!dir_present)
{
    if (m_sflowPortConfMap[alias].dir == "")
    {
        m_sflowPortConfMap[alias].dir = m_gDirection;
    }
    ...
}
```

per-port に `sample_direction` 未指定の場合、`m_gDirection` (グローバル方向) がフォールバックとして採用される。
`SFLOW_SESSION|all` が先行すると `m_intfAllDir` に正しい方向が設定され、その後の per-port
設定がその値を継承する。順序が逆だと per-port の初期 direction が `m_gDirection` 固定 (`"rx"`) になる。

## O4: APP_SFLOW_TABLE → APP_SFLOW_SESSION_TABLE (SflowOrch 段・必須)

`sfloworch.cpp:365-392` (doTask):

```cpp
if (table_name == APP_SFLOW_TABLE_NAME)
{
    sflowStatusSet(consumer);
    return;
}
...
if (!m_sflowStatus)
{
    return;
}
```

`m_sflowStatus = false` の間は SFLOW_SESSION_TABLE の全 SET を `return` でスキップする。
APP_SFLOW_TABLE の SET (sflowStatusSet) が先に到着して `m_sflowStatus = true` になるまで
SESSION は永続無視される。

## O5: oper_speed 確定 → SFLOW_SESSION 書込み (推奨)

`sflowmgr.cpp:385-401` (findSamplingRate):

```cpp
string oper_speed = m_sflowPortConfMap[alias].oper_speed;
string cfg_speed  = m_sflowPortConfMap[alias].speed;
if (!oper_speed.empty() && oper_speed != NA_SPEED)
{
    return oper_speed;
}
return cfg_speed;
```

`sample_rate` 未指定時は `oper_speed` (STATE_DB) 優先、なければ cfg_speed を使う。
ポートが UP する前に SFLOW_SESSION を書くと cfg_speed ベースの暫定レートが入る。
`local_rate_cfg = false` のポートは `sflowProcessOperSpeed()` が oper_speed 確定時に自動更新するため、
実運用上は問題が出にくいが、起動直後の一時的な不整合に注意。

## 推奨書込み順序（SFLOW_SESSION 観点）

```
1. PORT|<port>                SET  — ポート登録 (m_sflowPortConfMap 初期化)
2. SFLOW|global               SET (admin_state=up)  — グローバル有効化
3. SFLOW_SESSION|all          SET  — 全ポートデフォルト方向・admin 設定
4. SFLOW_SESSION|<port>       SET  — per-port 個別設定
```

ステップ 1 より先にステップ 4 を書くとエントリが永続スキップされる (O1 違反)。
ステップ 2 より先にステップ 4 を書くと APP_DB への反映が遅延する (O2 違反)。
