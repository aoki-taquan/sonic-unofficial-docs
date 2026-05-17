# PORT_STORM_CONTROL テーブル — Phase C 暗黙参照スキャンノート

対象テーブル: `CONFIG_DB PORT_STORM_CONTROL`
Consumer: `PolicerOrch::handlePortStormControlTable()` / `doTask()` (`sonic-swss/orchagent/policerorch.cpp`)
CLI 書込み経路: `config/main.py:storm_control_set_entry()` (`sonic-net/sonic-utilities`)
スキャン範囲: `policerorch.cpp` 全行 + `config/main.py:800-830` + `sonic-storm-control.yang`

---

## 検出した暗黙参照

### 1. PORT — キーポート名の OID 解決（必須依存）

- `handlePortStormControlTable()` L138: `gPortsOrch->getPort(interface_name, port)` でキーの `<interface_name>` を Port OID に解決する。
- 解決失敗 (PORT が CONFIG_DB に未登録) → `SWSS_LOG_ERROR` + `task_success` 返却 → `consumer.m_toSync` から erase（**リトライなし**）。
- PORT が PortsOrch に登録されていれば `port.m_port_id` を取得し、SAI_PORT_ATTR_*_STORM_CONTROL_POLICER_ID の対象として使用する（L206-214）。
- evidence: `policerorch.cpp:138-143`, `policerorch.cpp:206-214`

### 2. SAI POLICER テーブル — 内部キャッシュ `m_syncdPolicers`（Orch 内状態）

- `handlePortStormControlTable()` は Orch 外部の DB テーブルを直接 Subscribe しないが、内部 map `m_syncdPolicers` を参照して作成済み policer の OID を管理する（L151, L239, L245）。
- storm control 更新時（update = true）: `m_syncdPolicers[storm_policer_name]` から既存 policer OID を取得し、SAI `set_policer_attribute` で更新する（L245-263）。
- storm control 削除時: `m_syncdPolicers` から OID を取り出し `remove_policer` → `m_syncdPolicers.erase()` でキャッシュを消去する（L309, L368）。
- evidence: `policerorch.cpp:151, 239, 245, 309, 368`

### 3. STATE_DB BUM_STORM_CAPABILITY — CLI 側読み取り（orchagent は非参照）

- `config/main.py:is_storm_control_supported()` (L806-813): CLI が storm control を設定する前に `STATE_DB:BUM_STORM_CAPABILITY|<storm_type>` の `supported` フィールドを読み取る。
- orchagent (`policerorch.cpp`) は `BUM_STORM_CAPABILITY` を一切参照しない。SAI 呼び出しに失敗した場合のみ SAI エラーとして記録される。
- **非対称参照**: CLI → STATE_DB BUM_STORM_CAPABILITY（確認後スキップ可）、orchagent → 非参照（SAI fail-through）。
- evidence: `config/main.py:806-813`, `policerorch.cpp` (該当コード不在)

### 4. ASIC_DB / SAI — create/set/remove_policer + set_port_attribute

`handlePortStormControlTable()` は以下の SAI API を呼び出す:

| SAI API | 操作 | コード箇所 |
|---------|------|----------|
| `sai_policer_api->create_policer()` | policer オブジェクト作成 | L197-236 |
| `sai_policer_api->set_policer_attribute()` | CIR 値更新 (update 時) | L250-263 |
| `sai_port_api->set_port_attribute()` | ポートへ policer OID をアタッチ / デタッチ | L206-214, L283-286, L326-347 |
| `sai_policer_api->remove_policer()` | policer オブジェクト削除 | L293-304, L349-361 |

これらは ASIC_DB への syncd 経由書き込みを引き起こす（直接 DB 書き込みではなく SAI API 経由）。

### 5. PORT — YANG leafref による制約

`sonic-storm-control.yang`:

```yang
leaf ifname {
    type leafref {
        path "/prt:sonic-port/prt:PORT/prt:PORT_LIST/prt:name";
    }
}
```

YANG レベルでは `PORT_LIST` への leafref が定義されており、CONFIG_DB に存在する PORT 名のみを許可する制約がある。ただし orchagent 側は YANG のバリデーションに依存せず、getPort() で実行時に確認する。

evidence: `sonic-storm-control.yang` (leafref 定義), `policerorch.cpp:138` (実行時確認)

---

## 参照関係サマリ

```
PORT_STORM_CONTROL テーブル
  |- [必須]  PORT (ifname → port OID → SAI_PORT_ATTR_*_STORM_CONTROL_POLICER_ID)
  |- [内部]  m_syncdPolicers (Orch 内 policer OID キャッシュ)
  |- [CLI側] STATE_DB:BUM_STORM_CAPABILITY (orchagent は非参照)
  `- [出力]  ASIC_DB (SAI create/set/remove_policer, set_port_attribute)
```

YANG の leafref は PORT に対して定義されているが、orchagent は YANG バリデーションを経由しない直接 CONFIG_DB 読み取りを行うため、無効なポート名でも DB に書き込めてしまう（orchagent 側で task_success erase）。
