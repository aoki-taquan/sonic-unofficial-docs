# FEC_STATE フィールド暗黙デフォルト調査メモ

調査日: 2026-05-14
対象: STATE_DB `PORT_TABLE` の FEC 関連フィールド（`fec`, `supported_fecs`）

## 調査対象ファイル

- `sonic-swss/orchagent/portsorch.cpp` — 書き込み主体 (`updateDbPortOperFec`, `initPortSupportedFecModes`)
- `sonic-swss/orchagent/port/porthlpr.cpp` — `fecToStr` / `portFecRevMap` / `portFecOverrideMap`
- `sonic-swss/orchagent/port/portschema.h` — 定数定義 (`PORT_FEC_NONE`, `PORT_FEC_RS`, `PORT_FEC_FC`, `PORT_FEC_AUTO`)
- `sonic-utilities/scripts/intfutil` — consumer (`show interfaces fec status`)

---

## フィールド別 暗黙デフォルト・挙動

### `fec` (STATE_DB PORT_TABLE|<port> → field "fec")

**書き込み関数**: `updateDbPortOperFec(port, fec_str)` (portsorch.cpp:9864)

```cpp
// portsorch.cpp:9868-9870
vector<FieldValueTuple> tuples;
tuples.emplace_back(std::make_pair("fec", fec_str));
m_portStateTable.set(port.m_alias, tuples);
```

**書き込みトリガー**:
1. ポート oper_status が UP に変化したとき (portsorch.cpp:9682-9694)
2. `refreshPortStatus()` 起動時 (portsorch.cpp:9920-9929)

**値の決定ロジック**:

```
if (oper_fec_sup && getPortOperFec(port, fec_mode)) {
    // SAI_PORT_ATTR_OPER_PORT_FEC_MODE で取得成功
    fecToStr(fec_str, fec_mode)  // portFecRevMap で変換
    // 変換失敗時: fec_str = "N/A"
} else {
    fec_str = "N/A"
}
updateDbPortOperFec(port, fec_str)
```

**暗黙デフォルト**: `"N/A"`

- `oper_fec_sup` が false (vendor が `SAI_PORT_ATTR_OPER_PORT_FEC_MODE` の get を未実装) の場合は常に `"N/A"`
- `getPortOperFec` が SAI_STATUS_SUCCESS 以外を返した場合も `"N/A"`
- ポートが PHY 型以外（LAG, VLAN ポートなど）: `getPortOperFec` は `return false` → `"N/A"`
- ポートが DOWN の場合: このフィールドは **更新されない** (oper_status=UP 時のみ書き込み)

**portFecRevMap** (porthlpr.cpp:85-90):

```cpp
{ SAI_PORT_FEC_MODE_NONE, "none" },
{ SAI_PORT_FEC_MODE_RS,   "rs"   },
{ SAI_PORT_FEC_MODE_FC,   "fc"   }
// "auto" は逆引き map に存在しない → "N/A" にフォールバック
```

#### 検出した挙動乖離

1. **"auto" の dead consumer**: `portFecRevMap` に `SAI_PORT_FEC_MODE_NONE → "none"` しかなく、
   `fec=auto` で設定されたポートでも SAI が実際に `SAI_PORT_FEC_MODE_NONE` を使用した場合、
   oper fec は `"none"` と表示される（`"auto"` とは表示されない）。
2. **DOWN 時は stale**: ポート DOWN 後も最後に書き込まれた `fec` 値が STATE_DB に残る。
   `intfutil` は `oper_status != "up"` のとき表示を `"N/A"` に上書きするが、STATE_DB 自体の値はそのまま。
3. **dpu switch_type は除外**: `gMySwitchType != "dpu"` の条件 (portsorch.cpp:987) により、
   dpu 環境では `oper_fec_sup` が常に false → `fec` フィールドは常に `"N/A"`。

---

### `supported_fecs` (STATE_DB PORT_TABLE|<port> → field "supported_fecs")

**書き込み関数**: `initPortSupportedFecModes(alias, port_id)` (portsorch.cpp:3265)

**書き込みトリガー**: `isFecModeSupported()` が初めて呼ばれたとき（lazy init, 1回のみ）

**値の決定ロジック**:

```
getPortSupportedFecModes → SAI_PORT_ATTR_SUPPORTED_FEC_MODE
  成功: supported_fecmodes (set<sai_port_fec_mode_t>)
    空集合: ["N/A"]
    非空: fecToStr で変換した文字列をカンマ区切り
          + fec_override_sup=true なら "auto" を末尾に追加
  失敗 (NOT_SUPPORTED/NOT_IMPLEMENTED): フィールド書き込み自体をスキップ
  失敗 (その他 error): SWSS_LOG_ERROR + フィールド書き込みスキップ
```

**暗黙デフォルト**:
- フィールド不在 (supported FEC モード取得が platform 未対応) → STATE_DB にキーなし
- 空集合 → `"N/A"`
- `fec_override_sup=false` → `"auto"` が supported_fecs に含まれない（末尾追加されない）

**検出した挙動乖離**:

1. **フィールド不在は "サポートしていない" の意味ではない**: SAI が NOT_IMPLEMENTED を返した場合と
   空集合を返した場合で挙動が異なる。NOT_IMPLEMENTED は「取得不可 → バリデーション省略」であり、
   実際には FEC が動作する可能性がある。
2. **lazy init = 再取得なし**: 一度 m_portSupportedFecModes に格納されたら SAI 再問い合わせをしない。
   プラグイン型トランシーバ換装後も値が更新されない（dead field 相当）。
3. **"auto" の追加条件**: `fec_override_sup` は `SAI_PORT_ATTR_AUTO_NEG_FEC_MODE_OVERRIDE` の
   capability (`set_implemented && create_implemented` 両方) で決まる。この属性が `dpu` では
   そもそもクエリされない。

---

## 経路依存乖離まとめ

| 条件 | `fec` oper の挙動 | `supported_fecs` の挙動 |
|------|-----------------|----------------------|
| vendor が OPER_PORT_FEC_MODE 未実装 | 常に `"N/A"` | フィールドが存在しないか取得できない |
| dpu switch_type | 常に `"N/A"` | クエリ自体スキップ |
| ポート DOWN | 前回 UP 時の値が残留 (表示は intfutil が "N/A" に変換) | 変化なし |
| FEC=auto 設定 | SAI が NONE を返せば "none" と表示 | "auto" は fec_override_sup が true 時のみ出現 |
| SAI supported FEC 空集合 | 関係なし | `"N/A"` 文字列 |

## consumer 一覧

| プロセス | 読み取り方 | 用途 |
|----------|----------|------|
| `intfutil` (show interfaces fec status) | `STATE_DB PORT_TABLE\|<port> → fec` | FEC Oper 表示; oper_status != "up" なら "N/A" に変換 |
| `intfutil` (show interfaces status) | `APPL_DB PORT_TABLE:<port> → fec` | FEC Admin 列（CONFIG_DB 由来ではなく APPL_DB から取得） |
