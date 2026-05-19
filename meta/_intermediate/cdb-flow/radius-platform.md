# Phase H 中間ファイル: RADIUS プラットフォーム差

ソース: `sonic-host-services/scripts/hostcfgd`、`sonic-buildimage/src/sonic-yang-models/yang-models/sonic-system-radius.yang`

## 調査方針

RADIUS は SSH / コンソール認証のコントロールプレーン処理。SAI 経由の ASIC 操作はなく、
`hostcfgd` が PAM / NSS 設定ファイルを Linux ホスト上で直接書き換えるのみ。

## ASIC 種別への影響

`hostcfgd` の `radius_global_update()` / `modify_conf_file()` (hostcfgd:527-545, 641-851) は
SAI API を一切呼び出さない。ASIC 種別 (Broadcom BRCM / Mellanox / Marvell / Innovium 等) に
依存するコードパスなし。

## multi-asic への影響

`hostcfgd` は `ConfigDBConnector()` (引数なし) で起動し、host 単体の CONFIG_DB を購読する。
`asicN` namespace 向けの `ConfigDBConnector(namespace=...)` 呼び出しなし。

```python
# hostcfgd:2166-2185 — main() の DBConnector 初期化
config_db = ConfigDBConnector()
```

RADIUS 認証は管理プレーン経由の per-host 処理のため、asic namespace への分散適用は設計上不要。

## VOQ chassis への影響

RADIUS テーブルは host scope。`CHASSIS_APP_DB` や `CHASSIS_STATE_DB` への書き込みなし。
各 line card host で `hostcfgd` が独立に PAM 設定を生成する。

## SmartSwitch (NPU + DPU) への影響

DPU テーブル (`DPU|<name>`) に RADIUS 関連フィールドなし。DPU 側の orchagent は RADIUS を参照しない。
管理プレーン認証は NPU (host) 側のみで処理される。

## Jinja2 テンプレート確認

`sonic-buildimage/files/image_config/radius/` にある設定テンプレートを確認:
- `pam_radius_auth.conf.j2`
- `radius_nss.conf.j2`

これらのテンプレート内で `platform`、`asic`、`chassis`、`namespace`、`vendor` による条件分岐なし。
分岐は `auth_type`、`src_ip`、`vrf_name`、`statistics` フィールド値のみ。

## 結論

RADIUS / RADIUS_SERVER テーブルはプラットフォーム差なし。
