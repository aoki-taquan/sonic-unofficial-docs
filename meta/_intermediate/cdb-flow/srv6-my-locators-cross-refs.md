# SRV6_MY_LOCATORS — Phase C クロスリファレンス・スキャンノート

対象テーブル: `SRV6_MY_LOCATORS`
Consumer: `bgpcfgd` (`SRv6Mgr`)、`frrcfgd`、`srv6orch` (sonic-swss)
スキャン範囲: `managers_srv6.py` 全行、`sonic-srv6.yang` 全行、`frrcfgd.py` L121/L2335/L2732、`srv6orch.cpp` L107/L331-350

---

## 検出したクロスリファレンス

### 1. SRV6_MY_LOCATORS → SRV6_MY_SIDS (同一 YANG モデル内 leafref)

`sonic-srv6.yang:108-109`:
```yang
type leafref {
    path "/srv6:sonic-srv6/srv6:SRV6_MY_LOCATORS/srv6:SRV6_MY_LOCATORS_LIST/srv6:locator_name";
}
```

`SRV6_MY_SIDS` の `locator_name` フィールドは `SRV6_MY_LOCATORS` の `locator_name` への leafref。
`SRV6_MY_LOCATORS` エントリが存在しない状態で `SRV6_MY_SIDS` を書くと YANG バリデーション違反になる。

evidence: `sonic-srv6.yang:108-109`

### 2. SRV6_MY_LOCATORS.vrf → VRF テーブル (YANG leafref)

`sonic-srv6.yang:81-82`:
```yang
type leafref {
    path "/vrf:sonic-vrf/vrf:VRF/vrf:VRF_LIST/vrf:name";
}
```

`vrf` フィールドを非 `"default"` 値で指定する場合、`VRF` テーブルにその名前が存在している必要がある。
bgpcfgd は `vrf` を FRR コマンドに反映しないが、YANG バリデーション層は leafref 参照を検証する。

evidence: `sonic-srv6.yang:81-82`

### 3. srv6orch → CONFIG_DB SRV6_MY_LOCATORS (直接読み取り)

`srv6orch.cpp:107`:
```cpp
m_locatorCfgTable(cfgDb, CFG_SRV6_MY_LOCATOR_TABLE_NAME),
```

`Srv6Orch` は `m_locatorCfgTable` を通じて CONFIG_DB の `SRV6_MY_LOCATORS` を直接参照する。
`getLocatorCfgFromDb()` (srv6orch.cpp:331-350) が MySID エントリ処理時にロケータのビット長設定を取得する。

evidence: `srv6orch.cpp:107, 331-350`

### 4. frrcfgd → SRV6_MY_LOCATORS (zebra へ転送)

`frrcfgd.py:121`:
```python
'SRV6_MY_LOCATORS': ['zebra'],
```

`frrcfgd` も `SRV6_MY_LOCATORS` を購読し、zebra デーモンへ転送する経路がある。
bgpcfgd の `SRv6Mgr` と並立してロケータ設定を FRR に通知する。

evidence: `frrcfgd.py:121, 2335, 2732`

---

## クロスリファレンスサマリ

| 参照元 | 参照先 | 種別 | 備考 |
|--------|--------|------|------|
| `SRV6_MY_SIDS.locator_name` | `SRV6_MY_LOCATORS.locator_name` | YANG leafref (必須) | SID のロケータ名がロケータテーブルに存在必須 |
| `SRV6_MY_LOCATORS.vrf` | `VRF.name` | YANG leafref (条件付き) | 非 default VRF を指定時のみ |
| `srv6orch` (swss) | `CONFIG_DB SRV6_MY_LOCATORS` | 直接 DB 読み取り | MySID 処理時のビット長取得 |
| `frrcfgd` | `CONFIG_DB SRV6_MY_LOCATORS` | 購読 + zebra 転送 | bgpcfgd と並立した FRR 通知経路 |
