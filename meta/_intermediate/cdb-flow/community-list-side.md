# SNMP_COMMUNITY — Phase F 副次 DB 書込・外部副作用 証跡

生成日: 2026-05-18
対象ページ: `docs/reference/config-db/community-list.md`
調査ソース:
- `sonic-buildimage/dockers/docker-snmp/snmpd.conf.j2`
- `sonic-buildimage/dockers/docker-snmp/snmp_yml_to_configdb.py`
- `sonic-utilities/config/main.py` L4370-4462

---

## 1. 調査方針

`SNMP_COMMUNITY` テーブルへの書き込みが発生したとき、CONFIG_DB 以外のどのリソース（STATE_DB / APPL_DB / kernel / 外部ファイル / サービス再起動）に変化が生じるかを調査した。

## 2. 副次副作用の詳細

### 2-1. `/etc/snmp/snmpd.conf` の再生成（コンテナ起動時）

`snmpd.conf.j2` テンプレートが `docker-snmp` コンテナ起動時に `SNMP_COMMUNITY` テーブルを一括読み取りして `/etc/snmp/snmpd.conf` を生成する。CONFIG_DB への書き込みは即時に `snmpd.conf` を変更しない（バッチ生成）。

- evidence: `snmpd.conf.j2 L48-64`（SNMP_COMMUNITY ループ）

### 2-2. `systemctl restart snmp.service` の自動発行（CLI 経由のみ）

CLI（`config snmp community add/del/replace`）は DB 書き込み完了直後に `systemctl reset-failed snmp.service` + `systemctl restart snmp.service` を発行する。これによりコンテナが再起動し、`snmpd.conf` が新しい `SNMP_COMMUNITY` を反映した状態で再生成される。

direct DB 書き込み（`sonic-db-cli` / JSON load）では自動再起動は発生しない。

- evidence: `config/main.py L4397-4402`（add_community の restart 処理）
- evidence: `config/main.py L4425-4430`（del_community の restart 処理）
- evidence: `config/main.py L4456-4461`（replace_community の restart 処理）

### 2-3. snmpd プロセスのセッション影響（再起動後）

`snmp.service` 再起動後、既存の SNMPv1/v2c セッションは切断される。削除した community を使用していた NMS（ネットワーク管理システム）は以降のポーリングが失敗する。追加した community は再起動後から有効になる。

### 2-4. STATE_DB / APPL_DB への書き込み: なし

`snmpd.conf.j2` はファイル生成のみ行い STATE_DB / APPL_DB への書き込みは行わない。`snmp_yml_to_configdb.py` も CONFIG_DB 書き込みのみ。

### 2-5. SAI / カーネル FIB への影響: なし

SNMP は MIB ツリー経由でスイッチ統計を読み取るのみ。SNMP_COMMUNITY 変更は SAI または kernel routing table に影響しない。

## 3. 副次書込みサマリ

| 副次先 | 操作 | 内容 | evidence |
|--------|------|------|----------|
| `/etc/snmp/snmpd.conf` | 再生成（コンテナ起動時） | `rocommunity` / `rwcommunity` / `rocommunity6` / `rwcommunity6` 行更新 | `snmpd.conf.j2 L48-64` |
| `snmp.service` | 再起動（CLI 経由のみ） | 古い community 無効化・新規 community 有効化 | `config/main.py L4397-4401` |
| STATE_DB | なし | — | スキャン 0 件 |
| APPL_DB | なし | — | スキャン 0 件 |
| SAI / kernel FIB | なし | — | SNMP は統計読み取りのみ |
