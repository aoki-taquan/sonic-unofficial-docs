---
title: thermalctld の speed_tolerance API 廃止と移行
area: platform
tags: [thermalctld, platform-daemons, fan, thermal, api-change]
description: thermalctld が speed_tolerance を Redis DB に書き込まなくなった変更と、is_under_speed / is_over_speed API への移行方法。
source_issues:
  - https://github.com/sonic-net/sonic-platform-daemons/issues/395
verification: issue-confirmed
last_verified: 2026-05-20
---

# thermalctld の speed_tolerance API 廃止と移行

## 概要

`thermalctld`（温度・ファン制御デーモン）において、`speed_tolerance` フィールドが [Redis](../reference/glossary.md#term-redis) データベースへの書き込み対象から除外された。これはプラットフォーム API の変更を反映したものであり、既存のカスタムプラットフォームプラグインや `health_checker.py` に影響する。

## 変更内容

### 旧 API（廃止）

```python
# プラットフォームプラグインに speed_tolerance プロパティが必要だった
class FanDrawer:
    def get_speed_tolerance(self):
        return 10  # 許容速度誤差 (%)
```

`thermalctld` はこの値を Redis の `FAN_INFO` テーブルに `speed_tolerance` フィールドとして書き込んでいた。

### 新 API（現行）

`speed_tolerance` プロパティは廃止され、2 つのメソッドで置き換えられた。

```python
class FanDrawer:
    def is_under_speed(self):
        """ファン速度が許容下限を下回っているか判定する"""
        return False  # 正常時は False

    def is_over_speed(self):
        """ファン速度が許容上限を超えているか判定する"""
        return False  # 正常時は False
```

## health_checker.py への影響

`health_checker.py`（および類似のカスタムヘルスチェック実装）で `speed_tolerance` フィールドを Redis から読み取っている場合、値が存在しなくなるため更新が必要である。

### 移行例

```python
# 旧: speed_tolerance を使った判定
speed_tolerance = fan_info.get("speed_tolerance", 0)
actual_speed = int(fan_info.get("speed", 0))
target_speed = int(fan_info.get("target_speed", 0))
if abs(actual_speed - target_speed) > speed_tolerance:
    raise_alarm()

# 新: is_under_speed / is_over_speed を使った判定
# これらはプラットフォームプラグインが直接判定を行い、
# health_checker は FAN_INFO テーブルの is_under_speed / is_over_speed
# フィールドを参照する
if fan_info.get("is_under_speed") == "True" or fan_info.get("is_over_speed") == "True":
    raise_alarm()
```

## プラットフォームプラグイン実装者への対応

カスタムプラットフォームプラグインを実装している場合、`Fan` クラスに `is_under_speed()` と `is_over_speed()` を実装する必要がある。

```python
class MyFan(Fan):
    def is_under_speed(self):
        target = self.get_target_speed()
        actual = self.get_speed()
        tolerance = self._get_speed_tolerance()  # 内部メソッド
        return actual < (target - tolerance)

    def is_over_speed(self):
        target = self.get_target_speed()
        actual = self.get_speed()
        tolerance = self._get_speed_tolerance()
        return actual > (target + tolerance)
```

`is_under_speed()` / `is_over_speed()` を実装しない場合、デフォルト実装（常に `False` を返す）が使われ、ファン速度異常が検出されなくなる。

## Redis DB への影響

変更後の `FAN_INFO` テーブル構造（`STATE_DB`）：

| フィールド | 説明 |
|------------|------|
| `speed` | 現在の回転速度 (%) |
| `target_speed` | 目標回転速度 (%) |
| `is_under_speed` | 速度不足フラグ (`True` / `False`) |
| `is_over_speed` | 速度過剰フラグ (`True` / `False`) |
| ~~`speed_tolerance`~~ | **廃止** |

## 関連

- GitHub Issue: [sonic-net/sonic-platform-daemons#395](https://github.com/sonic-net/sonic-platform-daemons/issues/395)

<!-- glossary-links-injected: 0f594312e2b7 -->
