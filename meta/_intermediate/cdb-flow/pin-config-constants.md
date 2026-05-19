# pin-config: ハードコード定数調査 (Phase E)

source: sonic-net/sonic-buildimage/dockers/docker-sonic-p4rt/p4rt.sh (ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd)
source: sonic-net/sonic-buildimage/dockers/docker-sonic-p4rt/p4rt_vars.j2 (ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd)

## 発見した定数

### EXIT_P4RT_VARS_FILE_NOT_FOUND = 1
- 場所: p4rt.sh:L3
- 用途: テンプレートファイル不在時の exit code。配備スクリプト / supervisord がこの終了コードで p4rt コンテナの起動失敗を検知できる。

### P4RT_VARS_FILE = "/usr/share/sonic/templates/p4rt_vars.j2"
- 場所: p4rt.sh:L4
- 用途: CONFIG_DB → 起動引数変換テンプレートのハードコードパス。ファイルが存在しない場合は exit 1。

### --use_insecure_server_credentials (フォールバック文字列リテラル)
- 場所: p4rt.sh:L25, L42, L56
- 用途: 証明書設定が不完全（server_crt/server_key いずれか欠如）または証明書設定が全くない場合のデフォルトフォールバック引数。設定不備時でもエラーにならず平文 gRPC で起動する。

### KEY テーブル名リテラル (p4rt_vars.j2)
- "certs" — P4RT テーブルのサブキー識別子 (p4rt_vars.j2:L2)
- "p4rt_app" — P4RT テーブルのサブキー識別子 (p4rt_vars.j2:L3)
- "x509" — DEVICE_METADATA テーブルのサブキー識別子 (p4rt_vars.j2:L4)
これらは文字列リテラルとして固定されており、YANG モデルに定義されていない。

## YANG 定義との乖離
- 専用 YANG モデルなし。すべてのキー名・フォールバック動作が p4rt.sh / p4rt_vars.j2 のリテラルのみで実装される。
- デフォルト gRPC ポート 9559 は p4rt バイナリ内部のデフォルトであり、p4rt.sh には記述なし（CONFIG_DB に port フィールドがなければ引数自体を渡さない）。
