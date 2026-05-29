---
title: thermalctld の speed_tolerance API 廃止と移行
area: platform
description: thermalctld が speed_tolerance を STATE_DB に書き込まなくなった変更と、Fan クラスの is_under_speed / is_over_speed API への移行方法。
verification: code-verified
last_verified: 2026-05-28
sources:
- repo: sonic-net/sonic-platform-common
  path: sonic_platform_base/fan_base.py
  ref: 64beade8cddecdbc154531bc84bed2fa86581ea8
- repo: sonic-net/sonic-platform-daemons
  path: sonic-thermalctld/scripts/thermalctld
  ref: 4ba9612cb7756651062d37f977e3df17d57f740d
related:
  config_db: []
  cli:
  - show platform fan
  - show environment
  yang: []
  _no_related_yang: true
  _no_related_config_db: true
---

# thermalctld の speed_tolerance API 廃止と移行

## 概要

`thermalctld`（温度・ファン制御デーモン）において、`speed_tolerance` フィールドが [Redis](../reference/glossary.md#term-redis) の `STATE_DB`（`FAN_INFO` テーブル）への書き込み対象から除外された。代わりに `Fan` クラスの `is_under_speed()` / `is_over_speed()` メソッドの戻り値が `is_under_speed` / `is_over_speed` フィールドとして書き込まれるようになった。この変更は既存のカスタムプラットフォームプラグインや、`FAN_INFO` を参照するヘルスチェック実装に影響する。

## 変更内容

### 旧来の挙動（廃止）

かつて `thermalctld` はプラットフォームプラグインの `get_speed_tolerance()` の戻り値を `FAN_INFO` テーブルに `speed_tolerance` フィールドとして書き込んでおり、`FAN_INFO` を読む側がこの許容誤差と実速度・目標速度を突き合わせて速度異常を判定していた。

### 新しい挙動（現行）

速度異常の判定は `Fan` クラス側に移り、`thermalctld` は判定結果のみを `FAN_INFO` に書き込む。`Fan` クラスには判定用の 2 メソッドが用意されている[^1]。

```python
# sonic_platform_base/fan_base.py の FanBase
class FanBase(DeviceBase):
    def is_under_speed(self):
        """ファン速度が許容下限を下回っているか判定する。
        既定実装は get_speed() / get_target_speed() / get_speed_tolerance() を使い、
        speed * 100 < target_speed * (100 - tolerance) を返す。"""
        ...

    def is_over_speed(self):
        """ファン速度が許容上限を超えているか判定する。
        既定実装は speed * 100 > target_speed * (100 + tolerance) を返す。"""
        ...
```

`get_speed_tolerance()` 自体は廃止されていない。既定の `is_under_speed()` / `is_over_speed()` が内部で利用する。廃止されたのは、許容誤差を `FAN_INFO` テーブルに `speed_tolerance` フィールドとして公開する挙動である。

`thermalctld` 本体は `fan.is_under_speed` / `fan.is_over_speed` を呼び、その結果を `FAN_INFO` の `is_under_speed` / `is_over_speed` フィールドとして書き込む[^2]。

## FAN_INFO を参照する実装への影響

`FAN_INFO` テーブルから `speed_tolerance` フィールドを読んで独自に速度異常を計算しているヘルスチェック実装やスクリプトは、値が存在しなくなるため更新が必要である。

### 移行例

```python
# 旧: speed_tolerance を読んで独自に判定
speed_tolerance = int(fan_info.get("speed_tolerance", 0))
actual_speed = int(fan_info.get("speed", 0))
target_speed = int(fan_info.get("speed_target", 0))
if abs(actual_speed - target_speed) > speed_tolerance:
    raise_alarm()

# 新: thermalctld が書き込む判定済みフラグを参照
if fan_info.get("is_under_speed") == "True" or fan_info.get("is_over_speed") == "True":
    raise_alarm()
```

## プラットフォームプラグイン実装者への対応

カスタムプラットフォームプラグインを実装している場合、`Fan` クラスで `get_speed_tolerance()`（既定実装が利用）か、あるいは `is_under_speed()` / `is_over_speed()` 自体をオーバーライドする。

```python
class MyFan(FanBase):
    def is_under_speed(self):
        target = self.get_target_speed()
        actual = self.get_speed()
        tolerance = self.get_speed_tolerance()
        return actual * 100 < target * (100 - tolerance)

    def is_over_speed(self):
        target = self.get_target_speed()
        actual = self.get_speed()
        tolerance = self.get_speed_tolerance()
        return actual * 100 > target * (100 + tolerance)
```

既定実装は `get_speed_tolerance()` の実装を前提とする。これらを実装せず `get_speed_tolerance()` も `NotImplementedError` のままだと、`thermalctld` は `try_get` により値を取得できず判定が `False` 相当として扱われ、ファン速度異常が検出されなくなる。

## STATE_DB への影響

変更後の `FAN_INFO` テーブル構造（`STATE_DB`）の主なフィールド[^2]：

| フィールド | 説明 |
|------------|------|
| `speed` | 現在の回転速度 (%) |
| `speed_target` | 目標回転速度 (%) |
| `is_under_speed` | 速度不足フラグ (`True` / `False`) |
| `is_over_speed` | 速度過剰フラグ (`True` / `False`) |
| ~~`speed_tolerance`~~ | **廃止**（書き込まれなくなった） |

なお `Fan` クラスのメソッドは `FanDrawer`（ファンドロワー）ではなく、個々のファンを表す `Fan`（`FanBase`）に定義されている点に注意。

## 引用元

- `is_under_speed` / `is_over_speed` / `get_speed_tolerance` の定義: [`sonic_platform_base/fan_base.py`](https://github.com/sonic-net/sonic-platform-common/blob/64beade8cddecdbc154531bc84bed2fa86581ea8/sonic_platform_base/fan_base.py)
- `FAN_INFO` への書き込み: [`sonic-thermalctld/scripts/thermalctld`](https://github.com/sonic-net/sonic-platform-daemons/blob/4ba9612cb7756651062d37f977e3df17d57f740d/sonic-thermalctld/scripts/thermalctld)
- 関連 Issue: [sonic-net/sonic-platform-daemons#395](https://github.com/sonic-net/sonic-platform-daemons/issues/395)

[^1]: [`sonic_platform_base/fan_base.py` L69-L113](https://github.com/sonic-net/sonic-platform-common/blob/64beade8cddecdbc154531bc84bed2fa86581ea8/sonic_platform_base/fan_base.py#L69-L113)
[^2]: [`sonic-thermalctld/scripts/thermalctld` L399-L463](https://github.com/sonic-net/sonic-platform-daemons/blob/4ba9612cb7756651062d37f977e3df17d57f740d/sonic-thermalctld/scripts/thermalctld#L399-L463)

<!-- evidence:
source: sonic-platform-common/sonic_platform_base/fan_base.py#L69-L113 (sha: 64beade8cddecdbc154531bc84bed2fa86581ea8)
excerpt: |
  def is_under_speed(self):
      speed = self.get_speed()
      target_speed = self.get_target_speed()
      tolerance = self.get_speed_tolerance()
      return speed * 100 < target_speed * (100 - tolerance)
  def is_over_speed(self):
      ...
      return speed * 100 > target_speed * (100 + tolerance)
reasoning: is_under_speed / is_over_speed は Fan(FanBase) のメソッド。FanDrawer ではない。get_speed_tolerance は既定実装が内部利用するため残存。
-->

<!-- evidence-rendered:start -->
??? note "📋 検証エビデンス: sonic-platform-common/sonic_platform_base/fan_base.py#L69-L113 (sha: 64beade8cddecdbc154531bc84bed2fa86581ea8)"

    **出典**:

    `sonic-platform-common/sonic_platform_base/fan_base.py#L69-L113 (sha: 64beade8cddecdbc154531bc84bed2fa86581ea8)`

    **抜粋**:

    ```text
    def is_under_speed(self):
        speed = self.get_speed()
        target_speed = self.get_target_speed()
        tolerance = self.get_speed_tolerance()
        return speed * 100 < target_speed * (100 - tolerance)
    def is_over_speed(self):
        ...
        return speed * 100 > target_speed * (100 + tolerance)
    ```

    **判断根拠**: is_under_speed / is_over_speed は Fan(FanBase) のメソッド。FanDrawer ではない。get_speed_tolerance は既定実装が内部利用するため残存。

<!-- evidence-rendered:end -->

<!-- evidence:
source: sonic-platform-daemons/sonic-thermalctld/scripts/thermalctld#L399-L463 (sha: 4ba9612cb7756651062d37f977e3df17d57f740d)
excerpt: |
  is_under_speed = try_get(fan.is_under_speed)
  is_over_speed = try_get(fan.is_over_speed)
  ...
  fvs = swsscommon.FieldValuePairs(
      [('speed', str(speed)),
       ('speed_target', str(speed_target)),
       ('is_under_speed', str(is_under_speed)),
       ('is_over_speed', str(is_over_speed)), ...])
reasoning: thermalctld は fan.is_under_speed/is_over_speed を呼び FAN_INFO に書き込む。DB のフィールド名は speed_target (target_speed ではない)。speed_tolerance は書き込み対象外。
-->

<!-- evidence-rendered:start -->
??? note "📋 検証エビデンス: sonic-platform-daemons/sonic-thermalctld/scripts/thermalctld#L399-L463 (sha: 4ba9612cb7756651062d37f977e3df17d57f740d)"

    **出典**:

    `sonic-platform-daemons/sonic-thermalctld/scripts/thermalctld#L399-L463 (sha: 4ba9612cb7756651062d37f977e3df17d57f740d)`

    **抜粋**:

    ```text
    is_under_speed = try_get(fan.is_under_speed)
    is_over_speed = try_get(fan.is_over_speed)
    ...
    fvs = swsscommon.FieldValuePairs(
        [('speed', str(speed)),
         ('speed_target', str(speed_target)),
         ('is_under_speed', str(is_under_speed)),
         ('is_over_speed', str(is_over_speed)), ...])
    ```

    **判断根拠**: thermalctld は fan.is_under_speed/is_over_speed を呼び FAN_INFO に書き込む。DB のフィールド名は speed_target (target_speed ではない)。speed_tolerance は書き込み対象外。

<!-- evidence-rendered:end -->

<!-- glossary-links-injected: 0f594312e2b7 -->
