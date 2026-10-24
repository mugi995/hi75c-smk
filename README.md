# Leobog Hi75C — SMK firmware

Leobog Hi75C（ANSI / US、81キー＋ノブ）向けの
[SMK](https://github.com/karstx/smk) ファームウェアビルドです。
VIA（usevia.app）と Vial（vial.rocks / WebHID）からキーとノブを編集できます。

- 対象: Leobog Hi75C
- MCU: SinoWealth **SH68F90A**
- マトリクス: 6行 × 15列（[docs/matrix.md](docs/matrix.md)）
- USB: `258A:010C`

## 状態

| 項目 | 状態 |
| --- | --- |
| 81キーの入力 | ✅ |
| Fn レイヤー（`MO(1)`） | ✅ |
| ISP 再投入（`0603:1020`） | ✅ |
| 書き込み・検証・復旧 | ✅ |
| ノブ（回転・押し込み） | ✅ 既定は音量 Up/Down・Mute、Vial から変更可能 |
| RGB / LED | ✅ 全キー同一色（Vial/VIA の Solid Color、`Fn+Up/Down` 明るさ。ちらつきは既知の制限） |
| VIA（usevia.app） | ✅ 5層 |
| Vial（vial.rocks / WebHID） | ✅ 82キー＋ノブ2方向＋単一色RGB＋5層 |

## ファームウェア

| ファイル | 内容 |
| --- | --- |
| `firmware/leobog-hi75c_default_smk.hex` | v0.3.0（復旧用。VIA/Vial なし） |
| `firmware/leobog-hi75c_default-via_smk.hex` | VIA ビルド |
| `firmware/leobog-hi75c_default-vial_smk.hex` | Vial ビルド（VIA 9 + Vial 6） |

- ソース: https://github.com/mugi995/smk （`master`、`src/keyboards/leobog-hi75c`）
- ビルド: GitHub Actions（Nix + SDCC）
- ライセンス: リポジトリ全体は **GPL-2.0**（[`LICENSE`](LICENSE)）。`firmware/*.hex` は
  GPL-2.0（全文は [`firmware/LICENSE`](firmware/LICENSE)、対応ソースは
  [`firmware/SOURCE`](firmware/SOURCE)）。`tools/`・`docs/`・`README.md` は **MIT**
  （[`tools/LICENSE`](tools/LICENSE)、[`docs/LICENSE`](docs/LICENSE)）。範囲の詳細は
  [`NOTICE`](NOTICE)。

## 書き込み

```sh
# 1. ISP ブートローダへ移行
python tools/hi75c_isp.py --seq

# 2. 書き込み（--reboot false の場合、書き込み後に USB を挿し直す）
sinowisp write --platform sh68f90 --vendor_id 0x0603 --product_id 0x1020 \
  --reboot false -f firmware/leobog-hi75c_default-vial_smk.hex
```

- 書き込み後は USB を挿し直してください。
- 書き込みでキーマップ・設定はリセットされます。
- 現在のファームが ISP feature レポートを持たない場合は、`tools/recovery/` の
  WinUSB 経由の手順を使ってください。

## VIA / Vial

### VIA（usevia.app）

1. [usevia.app](https://usevia.app) を Chrome / Edge で開く
2. Settings → **Show Design tab**
3. Design → **Load** で `firmware/leobog-hi75c_via.json` を読み込む
4. Configure → **Authorize device** → 「SMK Keyboard」

### Vial（vial.rocks）

1. [vial.rocks](https://vial.rocks) を Chrome / Edge で開く
2. **Start Vial** → 「SMK Keyboard」を選ぶ
3. キー・ノブ（2方向）・RGB（Solid Color）・レイヤー（5層）を編集する

**WebHID は1タブだけで使ってください。** usevia.app や別タブを同時に開くと、
入力レポートの取り合いで応答がずれます（VIA app の既知問題
[#228](https://github.com/the-via/app/issues/228) と同じ症状）。

- ノブ: 押し込みは通常キー、回転はエンコーダの2方向。既定は回転=音量 Up/Down、
  押し込み=Mute。
- RGB: Vial の RGB 画面（**Solid Color**）または VIA の Lighting タブで、全キー同一色の
  色と明るさを変更できます。`Fn+Up/Down` でも明るさを調整できます。
  **ちらつき**は既知の制限です（キー走査との干渉）。
- レイヤー: **5層**。Vial/VIA のレイヤーボタンで切替・編集できます。
  層2〜4は既定で透過（`KC_TRNS`）です。
- 制限: 回転に `MO()` や `KB_BRI_UP/DN` を割り当てても送信されません。
  RGB は単一色のみ（per-key・効果・VialRGB のアニメーションは非対応）。

## 復旧

- ISP ブートローダは書き込みでは消えません。
- ベンダー提供のファームウェアはこのリポジトリに含みません。必要なら各自で
  保管し、同じ ISP 手順で書き戻してください。

## クレジット

- [SMK](https://github.com/karstx/smk) — ファームウェア本体
- [F65-CustomFirmware](https://github.com/goyamamoto/F65-CustomFirmware) —
  VIA / Vial 実装の参照

本プロジェクトは LEOBOG とは無関係です。実機への書き込みは自己責任で行ってください。
