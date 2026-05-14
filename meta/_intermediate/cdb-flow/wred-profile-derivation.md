# WRED_PROFILE — Phase 6/7 derivation grep 証跡

## Phase 6: 自動派生 (assignment scan)

### 1. qos_config.j2 での WRED_PROFILE 静的生成

**ソース**: `sonic-buildimage/files/build_templates/qos_config.j2:486-506`

```jinja2
{% if generate_wred_profiles is defined %}
    {{- generate_wred_profiles() }}
{% else %}
    "WRED_PROFILE": {
        "AZURE_LOSSLESS" : {
            "wred_green_enable"      : "true",
            "wred_yellow_enable"     : "true",
            "wred_red_enable"        : "true",
            "ecn"                    : "ecn_all",
            "green_max_threshold"    : "2097152",
            "green_min_threshold"    : "1048576",
            ...
        }
    },
```

- `generate_wred_profiles` が未定義 (標準ビルド) の場合、`AZURE_LOSSLESS` プロファイルが `ecn=ecn_all` で自動生成される。
- ベンダー固有プラットフォームは `generate_wred_profiles()` 関数を上書きして独自プロファイルを生成可能。

### 2. QUEUE テーブルからの `wred_profile` 参照

**ソース**: `sonic-swss/orchagent/qosorch.cpp:1886,1936`

```
QUEUE|<port>|<queue_index>.wred_profile = "AZURE_LOSSLESS"
→ QosOrch::applyWredProfileToQueue() が SAI_QUEUE_ATTR_WRED_PROFILE_ID を設定
```

- `qos_config.j2:514-660` の QUEUE セクションで `wred_profile: "AZURE_LOSSLESS"` が自動で設定される（RoCE キュー 3, 4 等）。
- WRED_PROFILE エントリが未解決なら `task_need_retry` で待機（qosorch.cpp:1864-1870）。

### 3. db_migrator.py での wred_profile 参照フォーマット変換

**ソース**: `sonic-utilities/scripts/db_migrator.py:574-585`

```python
qos_table_list = [
    ('QUEUE', ['scheduler', 'wred_profile']),
    ...
]
# ABNF 形式の | 区切り参照を除去するマイグレーション
```

- 旧バージョンの CONFIG_DB では `wred_profile` フィールドが `|AZURE_LOSSLESS|` のような ABNF 参照形式で格納されていた。マイグレーションステップでプレーン名前形式 `AZURE_LOSSLESS` に変換。

---

## Phase 7: 条件付き登録

### QosOrch の無条件登録

**ソース**: `sonic-swss/orchagent/orchdaemon.cpp:375-384`

```cpp
gQosOrch = new QosOrch(m_configDb, qos_tables);
// CFG_WRED_PROFILE_TABLE_NAME を含む全 QoS テーブルを購読
```

- `QosOrch` は platform / capability 無関係で常時起動。
- WRED_PROFILE テーブルの購読は `qos_tables` ベクタに `CFG_WRED_PROFILE_TABLE_NAME` が固定で含まれるため無条件 (orchdaemon.cpp:375)。

### VoQ (Virtual Output Queue) 条件

**ソース**: `sonic-swss/orchagent/qosorch.cpp:1709-1730`

```cpp
if (gMySwitchType == "voq") {
    // VoQ ポートの queue_id を getPortVoQIds() から取得
} else {
    // 通常の port.m_queue_ids を使用
}
```

- `gMySwitchType == "voq"` の場合、`applyWredProfileToQueue()` は物理キューではなく VoQ ID を使用。条件分岐はあるが WRED_PROFILE の適用可否には影響しない。
