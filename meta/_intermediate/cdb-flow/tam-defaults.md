# TAM / IFA フィールド暗黙デフォルト調査メモ

調査日: 2026-05-14  
対象テーブル: CONFIG_DB `TAM_DEVICE_TABLE`, `TAM_COLLECTOR_TABLE`, `TAM_INT_IFA_FEATURE_TABLE`, `TAM_INT_IFA_FLOW_TABLE`

## 調査対象ファイル

- `sonic-mgmt-common/cvl/testdata/schema/sonic-tam.yang` (TAM_DEVICE_TABLE / TAM_COLLECTOR_TABLE)
- `sonic-mgmt-common/cvl/testdata/schema/sonic-ifa.yang` (TAM_INT_IFA_FEATURE_TABLE / TAM_INT_IFA_FLOW_TABLE)
- `sonic-swss/orchagent/portsorch.cpp` (SAI_TAM_INT 属性参照)
- `sonic-swss/orchagent/high_frequency_telemetry/hftelorch.cpp` (TAM_COLLECTOR SAI 属性参照)

---

## フィールド別 暗黙デフォルト

### TAM_DEVICE_TABLE|device

#### `deviceid`

**コード由来デフォルト**: `0` (uint16)

```yang
# sonic-tam.yang:36-38
leaf deviceid {
    type uint16;
    default 0;
}
```

YANG `default` 文で明示。`TAM_DEVICE_TABLE|device` エントリに `deviceid` フィールドが存在しない場合、CVL (Config Validation Library) は `0` をデフォルトとして扱う。

---

### TAM_COLLECTOR_TABLE|<name>

#### `ipaddress-type`

**コード由来デフォルト**: なし（YANG に default 文なし）  
**必須扱い**: `must` 制約 (`ipaddress` の内容と type が一致しなければならない) があるため、実質的に `ipaddress` と同時設定が必要。  
指定可能値: `ipv4` / `ipv6`

```yang
# sonic-tam.yang:54-65
leaf ipaddress-type {
    type enumeration {
        enum ipv4;
        enum ipv6;
    }
    must "(contains(../ipaddress, ':') and current()='ipv6') or " +
         "(contains(../ipaddress, '.') and current()='ipv4')" { ... }
}
```

#### `ipaddress`

**コード由来デフォルト**: なし（mandatory ではないが、`must` 制約により `ipaddress-type` と対になる必要がある）  
型: `inet:ip-address`（IPv4/IPv6 両対応）

#### `port`

**コード由来デフォルト**: なし（YANG に default 文なし）  
型: `inet:port-number`（0..65535）

---

### TAM_INT_IFA_FEATURE_TABLE|feature

#### `enable`

**コード由来デフォルト**: なし（YANG に default 文なし。boolean 型）

```yang
# sonic-ifa.yang:38-40
leaf enable {
    type boolean;
}
```

DB にエントリが存在しない場合、IFA は無効状態として扱われる（enable=false 相当）。

---

### TAM_INT_IFA_FLOW_TABLE|<name>

#### `acl-table-name`

**コード由来デフォルト**: なし  
**mandatory**: `true`（YANG mandatory 文）  
型: leafref → `ACL_TABLE.aclname`

#### `acl-rule-name`

**コード由来デフォルト**: なし  
**mandatory**: `true`（YANG mandatory 文）  
型: leafref → `ACL_RULE[aclname=../acl-table-name].rulename`

#### `sampling-rate`

**コード由来デフォルト**: なし（YANG に default 文なし）  
型: `uint16` 範囲 `1..10000`

```yang
# sonic-ifa.yang:70-76
leaf sampling-rate {
    type uint16 {
        range "1..10000" {
            error-app-tag "Invalid IFA flow sampling rate.";
        }
    }
}
```

#### `collector-name`

**コード由来デフォルト**: なし  
型: string（`[a-zA-Z0-9]{1}([-a-zA-Z0-9_]{0,32})`、長さ 1..32）  
`TAM_COLLECTOR_TABLE` の name を参照する想定（leafref ではなく string だが CVL test でリンクされている）。

---

## 要約表

| テーブル | フィールド | コード由来デフォルト | 備考 |
|---------|-----------|-------------------|------|
| `TAM_DEVICE_TABLE\|device` | `deviceid` | `0` (uint16) | YANG `default 0` |
| `TAM_COLLECTOR_TABLE\|<name>` | `ipaddress-type` | なし | `must` 制約あり、ipaddress と対 |
| `TAM_COLLECTOR_TABLE\|<name>` | `ipaddress` | なし | inet:ip-address |
| `TAM_COLLECTOR_TABLE\|<name>` | `port` | なし | inet:port-number |
| `TAM_INT_IFA_FEATURE_TABLE\|feature` | `enable` | なし（false 相当） | boolean |
| `TAM_INT_IFA_FLOW_TABLE\|<name>` | `acl-table-name` | なし | mandatory |
| `TAM_INT_IFA_FLOW_TABLE\|<name>` | `acl-rule-name` | なし | mandatory |
| `TAM_INT_IFA_FLOW_TABLE\|<name>` | `sampling-rate` | なし | uint16 1..10000 |
| `TAM_INT_IFA_FLOW_TABLE\|<name>` | `collector-name` | なし | string ref to TAM_COLLECTOR |

---

## 証拠リンク

- `sonic-tam.yang:36-38` — `deviceid` default 0
- `sonic-tam.yang:54-65` — `ipaddress-type` must 制約
- `sonic-ifa.yang:38-40` — `enable` boolean (no default)
- `sonic-ifa.yang:55-61` — `acl-table-name` mandatory leafref
- `sonic-ifa.yang:63-68` — `acl-rule-name` mandatory leafref
- `sonic-ifa.yang:70-76` — `sampling-rate` range 1..10000
- `sonic-ifa.yang:78-83` — `collector-name` string pattern
- `sonic-swss/orchagent/portsorch.cpp:11593-11609` — SAI_TAM_INT 属性（PATH_TRACING）
- `sonic-swss/orchagent/high_frequency_telemetry/hftelorch.cpp:183-188` — SAI_TAM_COLLECTOR 属性
