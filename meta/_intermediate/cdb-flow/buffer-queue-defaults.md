# BUFFER_QUEUE フィールド暗黙デフォルト調査メモ

調査日: 2026-05-15
対象テーブル: CONFIG_DB `BUFFER_QUEUE`

## 調査対象ファイル

- `sonic-swss/orchagent/bufferorch.cpp` (BufferOrch::processQueue / SAI buffer profile attach)
- `sonic-buildimage/files/build_templates/buffers_config.j2` (ビルド時の BUFFER_QUEUE 既定エントリ生成)
- `sonic-buildimage/files/build_templates/qos_config.j2` (関連 QoS マッピング — BUFFER_QUEUE 自体は記述なし、SCHEDULER/QUEUE 経由)

YANG (`sonic-buffer-queue.yang`) は `profile` leafref に明示 default を持たない。実体の「未指定時挙動」はテンプレートおよび orchagent コードに分散している。

---

## フィールド別 暗黙デフォルト

### `profile` (BUFFER_QUEUE_LIST)

**YANG default**: なし (leafref で `BUFFER_PROFILE.name` を参照、`mandatory false`)

**コード由来デフォルト (ビルド時テンプレート — 非 VOQ)**:

`buffers_config.j2` L307–324 は `PORT_ACTIVE` 各ポートに対し以下 3 レンジを生成する:

| queue range | 既定 profile |
|---|---|
| `<port>\|3-4` | `egress_lossless_profile` |
| `<port>\|0-2` | `egress_lossy_profile` |
| `<port>\|5-6` | `egress_lossy_profile` |

```jinja
"BUFFER_QUEUE": {
{% for port in PORT_ACTIVE %}
    "{{ port }}|3-4": { "profile" : "egress_lossless_profile" },
{% endfor %}
{% for port in PORT_ACTIVE %}
    "{{ port }}|0-2": { "profile" : "egress_lossy_profile" },
{% endfor %}
{% for port in PORT_ACTIVE %}
    "{{ port }}|5-6": { "profile" : "egress_lossy_profile" }
{% endfor %}
}
```
(`buffers_config.j2:307–324`)

ただしプラットフォーム側 `buffers_defaults_*.j2` で `defs.generate_queue_buffers` 等のマクロが定義されている場合、上記 fallback ブロックは使用されず `defs.*` のマクロ展開が優先される (L298–305 の `{% elif %}` チェーン)。

**コード由来デフォルト (ビルド時テンプレート — VOQ シャーシ)**:

`buffers_config.j2` L279–295 は `SYSTEM_PORT_ALL` 各 system_port に対し同一の 3 レンジ (`3-4` egress_lossless、`0-2` / `5-6` egress_lossy) を生成する。

### orchagent ランタイム fallback

`BufferOrch::processQueue` (bufferorch.cpp L961–975) において:

- `profile` フィールドが解決不能 (`ref_resolve_status::not_resolved`) → `task_need_retry` を返し、何も SAI に書かない (= 既存値を維持)。
- `profile` 自体がエントリに欠落して `doesObjectExist` で取得できない場合は SAI `SAI_NULL_OBJECT_ID` をセット (DEL_COMMAND と同等動作、L1005)。

→ **CONFIG_DB に `profile` キーが書かれていない `BUFFER_QUEUE` エントリは、SAI 側で queue buffer profile が NULL になる** (デフォルト profile を自動で適用するロジックは orchagent には存在しない)。

### zero profile 特殊扱い

プロファイル名に `_zero_` を含む場合 (例: `egress_lossless_zero_profile`):

- L995, L1017, L1421: flex counter の追加・削除をスキップ
- L378 (`isPortReady`): zero profile を持つ queue は ready 判定から除外

→ 「トラフィックなし」を示す予約名前として扱われる。設定そのものは正常に SAI に伝わる。

---

## scheduler 既定との関係

`BUFFER_QUEUE` 自体は scheduler を持たないが、同じ queue index に紐づく `QUEUE|<port>|<qindex>` 側で `scheduler` がデフォルト割当される (`qos_config.j2`)。ここでは BUFFER_QUEUE スコープ外のため省略。

---

## まとめ

| フィールド | YANG default | コード由来デフォルト | 源 |
|---|---|---|---|
| `profile` (qindex 3-4) | なし | `egress_lossless_profile` | `buffers_config.j2:309-311` (非 VOQ fallback), `:281-283` (VOQ) |
| `profile` (qindex 0-2) | なし | `egress_lossy_profile` | `buffers_config.j2:314-316` (非 VOQ), `:286-288` (VOQ) |
| `profile` (qindex 5-6) | なし | `egress_lossy_profile` | `buffers_config.j2:319-321` (非 VOQ), `:291-293` (VOQ) |
| `profile` (未設定エントリ) | なし | `SAI_NULL_OBJECT_ID` (= 解放) | `bufferorch.cpp:1005, 1057` |

プラットフォーム固有 `buffers_defaults_*.j2` (`defs.generate_queue_buffers` マクロ) がある SKU では上記 fallback は不使用。t1-lag.j2 / Mellanox dynamic buffer 系統では `defs.*` を経由した別マッピングが適用される点に注意。
