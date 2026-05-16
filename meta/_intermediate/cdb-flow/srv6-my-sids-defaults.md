# SRV6_MY_SIDS — Phase A コード由来の暗黙デフォルト (grep 証跡)

## 探索対象 field 一覧

SRV6_MY_SIDS のフィールド: `ip_prefix` (key), `locator` (key), `action`, `decap_vrf`, `decap_dscp_mode`

grep entry コマンド:
```
grep -rn "SRV6_MY_SIDS" .cache/sonic-sources/ --include="*.py" --include="*.cpp" --include="*.yang" -l
```

ヒット: sonic-utilities/show/srv6.py, sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_srv6.py,
sonic-swss/orchagent/srv6orch.cpp, sonic-buildimage/src/sonic-yang-models/yang-models/sonic-srv6.yang

---

## field: ip_prefix (key)

**探索コマンド**:
```
grep -n "ip_prefix\|mandatory" sonic-srv6.yang
```

**結果**: `sonic-srv6.yang:101-103` — `ip_prefix` は `inet:ipv6-prefix` 型、`mandatory` 宣言なし (optional)。
ただし composite key `key "locator ip_prefix"` の一部のためキー省略不可。

**code fallback**: キー要素のため省略不可。デフォルト概念なし。0-hit。

---

## field: locator (key)

**探索コマンド**:
```
grep -n "leafref.*SRV6_MY_LOCATORS\|locator.*key" sonic-srv6.yang
```

**結果**: `sonic-srv6.yang:106-110` — `locator` は `SRV6_MY_LOCATORS_LIST/locator_name` への leafref。
composite key の一部のためキー省略不可。

`managers_srv6.py:57-59`: `key.split("|")[0]` でキー先頭要素を locator_name として使用。

**code fallback**: キー要素のため省略不可。デフォルト概念なし。0-hit。

---

## field: action

**探索コマンド**:
```
grep -n "'action'\|data\['action'\]\|action.*mandatory" managers_srv6.py sonic-srv6.yang
```

**結果**:
- `sonic-srv6.yang:113-119` — `action` は enum `{uN, uDT46}`、`mandatory` 宣言なし。
- `managers_srv6.py:78-83`:
  ```python
  if 'action' not in data:
      log_err("Found a SRv6 SID config entry that does not specify action: ...")
      return False
  if data['action'] not in supported_SRv6_behaviors:
      log_err("Found a SRv6 SID config entry associated with unsupported action: ...")
      return False
  ```
  action 未指定はエラー扱いで処理中断。

- `srv6orch.cpp:2215-2217`: `if (fvField(i) == "action") { end_action = fvValue(i); }` — 未指定時は空文字列。
- `srv6orch.cpp:1473-1475`: `sidEntryEndpointBehavior(end_action, ...)` で不正値はエラー return。

**code fallback**: なし — 実質 mandatory (YANG は mandatory 宣言なしだが bgpcfgd が未指定をエラーとして拒否)。
YANG との乖離: YANG は mandatory 未定義、コードは `action` 省略を拒否する。

---

## field: decap_vrf

**探索コマンド**:
```
grep -n "decap_vrf\|DEFAULT_VRF\|default.*vrf" managers_srv6.py sonic-srv6.yang
```

**結果**:
- `sonic-srv6.yang:121-133` — `decap_vrf` は VRF leafref | `"default"` pattern の union、
  `default "default"` 明示宣言あり。
- `managers_srv6.py:11`: `DEFAULT_VRF = "default"`
- `managers_srv6.py:150`: `self.decap_vrf = data['decap_vrf'] if 'decap_vrf' in data else DEFAULT_VRF`
  — 未指定時に `"default"` を使用。
- `srv6orch.cpp:1484`: `if (dt_vrf == "default") { dt_vrf_id = gVirtualRouterId; }`
  — `"default"` を global VRF の VirtualRouter ID に解決。

**code fallback**: **YANG default `"default"` + bgpcfgd の Python fallback `DEFAULT_VRF = "default"` — 一致**。
省略時は global routing table (default VRF) でデカプセル化を実行。

---

## field: decap_dscp_mode

**探索コマンド**:
```
grep -n "decap_dscp_mode\|dscp_mode\|boost::none" srv6orch.cpp sonic-srv6.yang
```

**結果**:
- `sonic-srv6.yang:135-141` — `decap_dscp_mode` は enum `{uniform, pipe}`、`mandatory` 宣言なし、
  `default` 宣言なし。
- `srv6orch.cpp:383-396` (`addMySidCfgCacheEntry`):
  ```cpp
  boost::optional<sai_tunnel_dscp_mode_t> dscp_mode = boost::none;
  auto cfg = fvsGetValue(fvs, "decap_dscp_mode", false);
  if (cfg) {
      // parse and set dscp_mode
  }
  // dscp_mode remains boost::none if not specified
  ```
  未指定時は `boost::none` のまま — SAI に DSCP mode 属性を送らない。

- `srv6orch.cpp` SWSS_LOG: `"DSCP mode %s"` — `cfg ? cfg->c_str() : "none"` と記録。

**code fallback**: なし — 未指定時は `boost::none`。DSCP mode は SAI デフォルト (プラットフォーム依存) に委ねる。
一般的な SAI デフォルトは `uniform` (外側パケットの DSCP を内側に継承) だが、これは SAI 実装依存であり
SONiC コード自体にはハードコードされたデフォルトなし。

---

## 0-hit フィールド (fallback なし)

| フィールド | 探索 | 0-hit 理由 |
|---|---|---|
| `action` | grep `action.*default\|default.*action` | 実質 mandatory — bgpcfgd が省略をエラー扱い |
| `decap_dscp_mode` | grep `dscp_mode.*default\|boost::none` | 未指定時 boost::none — SAI デフォルト依存 |

---

## YANG-コード 乖離サマリ

| フィールド | YANG default | コード fallback | 乖離 |
|---|---|---|---|
| `ip_prefix` | - (key) | - (key) | なし |
| `locator` | - (key) | - (key) | なし |
| `action` | なし (mandatory 未定義) | 省略をエラー拒否 | あり — YANG は mandatory 未定義だがコードは必須扱い |
| `decap_vrf` | `"default"` (YANG 明示) | `"default"` (bgpcfgd) | なし — 一致 |
| `decap_dscp_mode` | なし | boost::none (SAI 依存) | なし (YANG もコードも default なし) |

---

## 参照ファイル

- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-srv6.yang`
  (SHA: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd)
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_srv6.py`
  (SHA: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd)
- `sonic-swss/orchagent/srv6orch.cpp`
  (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)
