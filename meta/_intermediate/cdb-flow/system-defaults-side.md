# SYSTEM_DEFAULTS — Phase F 副次 DB 書込スキャンノート

対象テーブル: `SYSTEM_DEFAULTS`
Consumer: `orchagent`(orchagent.sh + swss_vars.j2)、`muxorch`(MuxAclHandler)、`bgpcfgd`(main.py)
スキャン範囲: orchagent.sh, swss_vars.j2, muxorch.cpp, bgpcfgd/main.py 全行精読 + APPL_DB/STATE_DB/ASIC_DB 書込呼出 grep

---

## 副次 DB 書込の有無

### muxorch (MuxAclHandler) — ASIC_DB への間接書込

`MuxAclHandler::MuxAclHandler()` (muxorch.cpp:1388-1402) が `SYSTEM_DEFAULTS|mux_tunnel_egress_acl` を読み取り、
`is_ingress_acl_` フラグを決定したうえで `createMuxAclTable()` / `createMuxAclRule()` を呼び出す。
これらは `aclorch` を経由して ASIC_DB (SAI オブジェクト) を生成するが、
CONFIG_DB / APPL_DB / STATE_DB への直接書込は行わない（SAI API 経由の ASIC_DB 操作）。

- **直接 DB 書込**: なし（APPL_DB / STATE_DB / CONFIG_DB いずれも書込なし）
- **間接的 ASIC_DB 変更**: `createMuxAclTable()` が SAI API 経由で ACL テーブル/ルールオブジェクトを生成
- evidence: `sonic-swss/orchagent/muxorch.cpp:1388-1416`

### bgpcfgd — BfdMgr の STATE_DB 書込（条件付き）

`bgpcfgd/main.py` が `SYSTEM_DEFAULTS.software_bfd.status == "enabled"` のとき `BfdMgr` を managers に追加する。
`BfdMgr` は STATE_DB の `STATE_BFD_SOFTWARE_SESSION_TABLE_NAME` を購読・更新するが、
これは `SYSTEM_DEFAULTS` 変更への反応ではなく BFD セッション状態の追跡に閉じる。

- **直接 DB 書込**: なし（SYSTEM_DEFAULTS 変更に反応する DB 書込なし）
- **条件付き有効化**: `software_bfd=enabled` のとき BfdMgr が STATE_DB `BFD_SESSION_TABLE` を管理
- evidence: `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/main.py:117-121`

### orchagent.sh / swss_vars.j2 — DB 書込なし

`orchagent.sh` は `sonic-cfggen -d -t swss_vars.j2` で `SYSTEM_DEFAULTS` を読み取り、
orchagent 引数 (`-s` フラグ等) を決定するが、任意の DB への書込は行わない。

- **直接 DB 書込**: なし
- evidence: `sonic-buildimage/dockers/docker-orchagent/orchagent.sh:8-42`

## 結論

| 副次 DB | 書込有無 | 根拠 |
|---|---|---|
| APPL_DB | なし | muxorch/bgpcfgd/orchagent.sh いずれも SYSTEM_DEFAULTS 変更に対して APPL_DB 書込なし |
| STATE_DB | なし（間接的あり） | BfdMgr は STATE_DB を使うが SYSTEM_DEFAULTS 変更への直接反応ではない。起動時に software_bfd=enabled のときのみ有効化 |
| ASIC_DB | 間接的あり | MuxAclHandler が SAI API 経由で ACL オブジェクトを生成（CONFIG_DB 書込ではない） |
| COUNTERS_DB / FLEX_COUNTER_DB | なし | SYSTEM_DEFAULTS を参照するコードに COUNTERS_DB 書込なし |
| CONFIG_DB（自己書込） | なし | SYSTEM_DEFAULTS は書込専用（自己更新なし） |

主な副作用は DB ではなく起動引数・テンプレートレンダリング結果（`swss_vars.j2` の `dscp_remapping`）への反映と、
muxorch MuxPort 初期化時の SAI ACL オブジェクト生成に閉じる。
