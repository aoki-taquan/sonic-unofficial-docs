# tunnel-decap-table — CDB → 実コンテナ動作 ランタイムトレース

## 対象テーブル
`TUNNEL_DECAP_TABLE`

## 段階 1: Consumer 登録

- **orchagent / TunnelDecapOrch** (`sonic-swss/orchagent/tunneldecaporch.cpp`): `TUNNEL_DECAP_TABLE` を `SubscriberStateTable` で購読。

## 段階 2: CFG → APPL 翻訳

- TunnelDecapOrch がトンネルタイプ (IPINIP) と内側/外側 IP 情報を解析。
- APP_DB への書き込みなし (orchagent → SAI 直接)。

## 段階 3: APPL → SAI

- TunnelDecapOrch が `sai_tunnel_api->create_tunnel()` / `create_tunnel_term_table_entry()` を呼び出し IP-in-IP デカプセルトンネルをハードウェアに設定。

## 段階 4: タイミング + 副作用

- トンネル作成は orchagent 処理後数 ms 以内。
- 副作用: 内側 IP アドレスの重複がある場合 SAI が resource エラーを返す。
