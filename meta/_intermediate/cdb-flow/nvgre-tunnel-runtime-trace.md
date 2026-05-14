# nvgre-tunnel — CDB → 実コンテナ動作 ランタイムトレース

## 対象テーブル
`NVGRE_TUNNEL`

## 段階 1: Consumer 登録

- **orchagent / TunnelDecapOrch**: `NVGRE_TUNNEL` テーブルを `SubscriberStateTable` で購読。

## 段階 2: CFG → APPL 翻訳

- TunnelDecapOrch がエントリを解析し APP_DB `TUNNEL_DECAP_TABLE` に書き込む (一部実装)。
- 実装は VS/仮想 ASIC 向けが主体で、物理 ASIC サポートはベンダー依存。

## 段階 3: APPL → SAI

- orchagent から SAI `sai_tunnel_api->create_tunnel()` を呼び出して NVGRE デカプセルトンネルを作成。
- SAI_TUNNEL_TYPE_NVGRE を使用。

## 段階 4: タイミング + 副作用

- トンネル作成は orchagent が処理を受け取った数 ms 以内。
- 副作用: 対応する SAI サポートが必要。非サポート ASIC では task_failed となる。
