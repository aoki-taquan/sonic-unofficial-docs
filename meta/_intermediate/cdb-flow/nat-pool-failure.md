# nat-pool Phase D — 失敗挙動調査メモ

調査対象: `sonic-swss/cfgmgr/natmgr.cpp` `NatMgr::doNatPoolTask()` L6482–6866

## 主要知見

- すべてのバリデーション失敗は `consumer.m_toSync.erase(it)` で即破棄（保留/retry なし）
- iptables / APPL_DB 設定スキップ（NAT 無効・インタフェース未準備）の場合のみ erase せずに自然再処理
- STATE_DB / ERROR_TABLE への書き込みなし

## 失敗フラグ変数

```cpp
bool ipFound = false, portFound = false, nonValueFound = false, isOverlap = false;
```

## 主要バリデーション行番号

| チェック | 行番号 |
|---------|--------|
| key size != 1 | L6504-6508 |
| nat_ip 欠落・複数 | L6539-6543 |
| nat_port 複数 | L6547-6551 |
| 未知フィールド | L6555-6559 |
| pool 名 > 32 文字 | L6563-6567 |
| nat_ip が空/"NULL" | L6571-6575 |
| nat_ip range token > 2 | L6588-6592 |
| IP 形式不正 | L6599-6604, L6617-6622, L6645-6649 |
| 特殊 IP アドレス | L6608-6613, L6626-6631, L6656-6661 |
| IP low >= high | L6635-6639 |
| port range token > 2 | L6673-6677 |
| port 整数変換失敗 | L6682-6690, L6701-6709, L6731-6739 |
| port 範囲外 (0, >65535) | L6694-6698, L6714-6718, L6743-6747 |
| port low >= high | L6721-6725 |
| STATIC_NAT 重複 | L6771-6775 |
| 重複 SET | L6786-6788 |

## DEL パス

- キャッシュあり: binding 確認 → removeDynamicNatRule → m_natPoolInfo.erase → 正常完了
- キャッシュなし: SWSS_LOG_ERROR + erase (no-op)
