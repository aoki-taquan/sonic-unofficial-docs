# sflow-ordering — Phase B: SFLOW 書込み順依存

対象ページ: `docs/reference/config-db/sflow.md`
調査ソース: `sonic-swss/cfgmgr/sflowmgr.cpp`, `sonic-swss/orchagent/sfloworch.cpp`

---

## 依存関係一覧

### O1: PORT テーブル → SFLOW_SESSION (必須先行)

**根拠**: `sflowmgr.cpp:522-528`

```cpp
auto sflowPortConf = m_sflowPortConfMap.find(key);
if (sflowPortConf == m_sflowPortConfMap.end())
{
    it++;
    continue;  // ← ポートが未登録なら SFLOW_SESSION を無視して next へ
}
```

`CFG_PORT_TABLE_NAME` の SET イベント受信時に `sflowUpdatePortInfo()` が `m_sflowPortConfMap` にポート情報を登録する。このマップへの登録が済む前に `SFLOW_SESSION|<port>` の SET が届くと、エントリはスキップ（消費）され **リトライも再通知もなく永続的に無視される**。

**必須書込み順**: `PORT|<port>` SET → `SFLOW_SESSION|<port>` SET

---

### O2: SFLOW|global admin_state=up → SFLOW_SESSION|<port> の APP_DB 反映 (必須先行)

**根拠**: `sflowmgr.cpp:531-534`

```cpp
if (m_gEnable)
{
    m_appSflowSessionTable.set(key, fvs);
}
```

per-port SESSION は `m_gEnable == true` (= `SFLOW.global.admin_state == "up"`) のときのみ APP_DB へ書き込まれる。グローバルが `down` のまま per-port SESSION を書き込んでも APP_DB には何も届かず、後からグローバルを `up` にすると `sflowHandleSessionAll()` / `sflowHandleSessionLocal()` 経由で全ポートに再適用される（ただしその時点の設定で上書きされる）。

**実害**: per-port SESSION のみ先に書き込んでも APP_DB には反映されない。グローバルを後から `up` にすれば再適用されるが、タイミング依存。

**推奨書込み順**: `SFLOW|global admin_state=up` → `SFLOW_SESSION|<port>`

---

### O3: SFLOW|global → APP_SFLOW_TABLE → APP_SFLOW_SESSION_TABLE (SflowOrch 段)

**根拠**: `sfloworch.cpp:365-392`

```cpp
if (table_name == APP_SFLOW_TABLE_NAME)
{
    sflowStatusSet(consumer);
    return;
}
// ...
if (!m_sflowStatus)
{
    return;  // ← APP_SFLOW_TABLE が来るまで SESSION を全無視
}
```

SflowOrch は `APP_SFLOW_TABLE` の SET を受けて `m_sflowStatus = true` になるまで、`APP_SFLOW_SESSION_TABLE` の全 SET/DEL を **スキップ（return）** する。O2 と合わせて CONFIG_DB → APP_DB → SAI の全経路で「グローバル有効化が先行必須」という制約が二重に存在する。

**必須書込み順**: `APP_SFLOW_TABLE` SET → `APP_SFLOW_SESSION_TABLE` SET

---

### O4: SFLOW_SESSION|all → SFLOW_SESSION|<port> (direction 継承の前提)

**根拠**: `sflowmgr.cpp:374-382`（`sflowCheckAndFillValues`）

```cpp
if (m_sflowPortConfMap[alias].dir == "")
{
    /* By default direction is set to global, if not set explicitly */
    m_sflowPortConfMap[alias].dir = m_gDirection;
}
```

per-port SESSION に `sample_direction` が未指定の場合、`m_gDirection`（グローバル方向）が採用される。`SFLOW_SESSION|all` が先に書かれ `m_intfAllDir` が確定している場合、`sflowHandleSessionAll()` は `m_intfAllDir` で全ポートを設定する。後から per-port SESSION が来ると `m_gDirection` をフォールバックとして使う。

- `SFLOW_SESSION|all` を先に書く → `m_intfAllDir` が設定され `sflowHandleSessionAll()` が全ポートに適用
- `SFLOW_SESSION|<port>` が先に来ると `dir=""` → `m_gDirection` をデフォルト採用（`"rx"`）

DEL 時も順序依存: `SFLOW_SESSION|all` を DEL すると `m_intfAllConf=true` に戻り、`sflowHandleSessionAll(true, m_gDirection)` が全ポートに再適用される。

**推奨書込み順**: `SFLOW_SESSION|all` → `SFLOW_SESSION|<port>`（方向を正確に伝搬させる場合）

---

### O5: PORT 速度確定 → SFLOW_SESSION 書込み (sample_rate デフォルト精度)

**根拠**: `sflowmgr.cpp:385-401`（`findSamplingRate`）

```cpp
string oper_speed = m_sflowPortConfMap[alias].oper_speed;
string cfg_speed = m_sflowPortConfMap[alias].speed;
if (!oper_speed.empty() && oper_speed != NA_SPEED)
{
    return oper_speed;
}
return cfg_speed;
```

`sample_rate` を未指定の場合、ポートの `oper_speed`（STATE_DB 経由）優先、なければ `cfg_speed`（PORT テーブル）を使う。ポート up 前・auto-neg 完了前に SFLOW_SESSION が設定されると cfg_speed ベースのレートが APP_DB に入り、後で `oper_speed` が確定すると `sflowProcessOperSpeed()` が自動更新する（`local_rate_cfg=false` の場合のみ）。`local_rate_cfg=true`（明示指定）の場合は自動更新されない。

**書込み推奨**: oper_speed 確定後に sample_rate を省略した SFLOW_SESSION を書くと正確なレートが設定される。ただし実運用では後自動補正あり。

---

## サマリ表

| ID | 先行テーブル/エントリ | 後続テーブル/エントリ | 違反時の実害 | 自動回復 |
|----|---------------------|---------------------|------------|---------|
| O1 | `PORT\|<port>` SET | `SFLOW_SESSION\|<port>` SET | エントリ永続スキップ | なし |
| O2 | `SFLOW\|global` admin=up | `SFLOW_SESSION\|<port>` SET | APP_DB 未書込み | グローバル up 時に再適用 |
| O3 | `APP_SFLOW_TABLE` SET | `APP_SFLOW_SESSION_TABLE` SET | SESSION 全スキップ | なし（再通知なし） |
| O4 | `SFLOW_SESSION\|all` SET | `SFLOW_SESSION\|<port>` SET | direction が m_gDirection 固定 | なし |
| O5 | `STATE_PORT` oper_speed | `SFLOW_SESSION\|<port>` 未rate | cfg_speed ベースの暫定レート | oper_speed 確定時に自動更新 |
