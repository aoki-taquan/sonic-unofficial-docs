# RADIUS — Phase 6/7/8 中間ファイル

生成日: 2026-05-14 (batch cdb_batch_4)

<!-- derivation -->
## Phase 6: 自動派生代入スキャン

### 全ソース — 該当なし

minigraph.py / config_samples.py / db_migrator.py / init_cfg.json.j2 に RADIUS への代入なし（TACACS_SERVER はあるが RADIUS は minigraph 管轄外）。CLI (`config radius`) で明示設定。

**結論**: Phase 6 派生なし。

<!-- /derivation -->

<!-- derivation -->
## Phase 7: 条件付き manager/orch 登録

### hostcfgd — AaaCfg クラス

```python
# hostcfgd:354  class AaaCfg(object)
# RADIUS, RADIUS_SERVER, AAA テーブルを購読
```

AaaCfg は **常時** 登録。条件付き登録なし。

<!-- /derivation -->

<!-- handler-branching -->
## Phase 8: manager メソッド内 early return / dispatch

### AaaCfg — RADIUS ハンドラ分岐

```
# hostcfgd:36-37
NSS_RADIUS_CONF = "/etc/radius_nss.conf"
NSS_RADIUS_CONF_TEMPLATE = "/usr/share/sonic/templates/radius_nss.conf.j2"
```

| 変更フィールド | 処理 |
|----------------|------|
| `passkey` / `auth_type` | `/etc/pam_radius_auth.d/` 設定ファイル再生成 |
| `timeout` / `retransmit` | RADIUS クライアント設定ファイル更新 |
| `nas_ip` | NAS IP 設定更新 |

early return: AAA で `radius` が有効でない (`authentication order` に含まれない) → PAM 設定を更新しない。

<!-- /handler-branching -->
