# sonic-platform-common Issue Decisions

## #489: xcvrd crashes when MediaInterfaceIDApp is not defined [OPEN]
**判定: DOC → docs/platform/xcvrd-cmis-mediainterface-crash.md**
CMIS アプリケーション広告リストに MediaInterfaceIDApp が未定義の場合に xcvrd がクラッシュする問題。PR #457 の変更で発生。回避策と修正 PR #457 を記録。

## #449: SFF-8472 Rx power conversion function incorrect [OPEN]
**判定: DOC → docs/platform/sfp-sff8472-rx-power-calibration.md**
外部キャリブレーション方式の SFP で Rx パワー変換が誤っている不具合。PR #479 で修正。光モジュール診断の精度に関わる重要な技術情報。

## #255: xcvrd crashes in SFP refactored code. [CLOSED]
**判定: SKIP** — クローズ済み、内容なし。

## #179: SfpUtilBase: not all EEPROM data are parsed [OPEN]
**判定: DOC → docs/platform/sfp-eeprom-parsing-gaps.md**
SfpUtilBase クラスに EEPROM 解析ハンドラはあるが実装されていない get/set 関数が残存する問題。xcvrd 経由でのアクセスが推奨される設計議論も含む。

## #170: [sonic_eeprom] Class methods shouldn't take the EEPROM data as a parameter [OPEN]
**判定: SKIP** — API リファクタリング要求。コース課題として割り当て済み。ドキュメント化する設計上の確定情報がない。
