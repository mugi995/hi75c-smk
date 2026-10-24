# Matrix

6 rows × 15 columns. The matrix index is `col * 6 + row`.
The table below is the default base layer (ANSI / US); VIA and Vial can
remap it.

## Pins

Rows are inputs with pull-ups; columns are outputs driven low one at a time.

| Row | Pin |
| --- | --- |
| R0 | `P7.0` |
| R1 | `P7.1` |
| R2 | `P7.2` |
| R3 | `P7.3` |
| R4 | `P5.3` |
| R5 | `P5.4` |

| Column | Pin |
| --- | --- |
| C0 | `P6.0` |
| C1 | `P6.1` |
| C2 | `P6.2` |
| C3 | `P6.3` |
| C4 | `P6.4` |
| C5 | `P6.5` |
| C6 | `P6.6` |
| C7 | `P6.7` |
| C8 | `P5.0` |
| C9 | `P5.1` |
| C10 | `P5.2` |
| C11 | `P5.7` |
| C12 | `P4.0` |
| C13 | `P4.2` |
| C14 | `P4.3` |

## Keys (base layer)

`—` is `KC_NO` (no key at that position).

| Row \ Col | C0 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 | C9 | C10 | C11 | C12 | C13 | C14 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R0 | Esc | — | F1 | F2 | F3 | F4 | F5 | F6 | F7 | F8 | F9 | F10 | F11 | F12 | Mute |
| R1 | Backtick | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 0 | - | = | Backspace | Del |
| R2 | Tab | Q | W | E | R | T | Y | U | I | O | P | [ | ] | \ | End |
| R3 | Caps | A | S | D | F | G | H | J | K | L | ; | ' | — | Enter | PgUp |
| R4 | LShift | Z | X | C | V | B | N | M | , | . | / | RShift | — | ↑ | PgDn |
| R5 | LCtrl | LGui | LAlt | — | — | Space | — | — | RAlt | Fn (`MO(1)`) | RCtrl | — | ← | ↓ | → |

## Encoder

The knob push is matrix `(0,14)` = Mute. The rotation is a separate
quadrature encoder on `P0.5` / `P0.6` and is not part of the matrix; its two
directions are assigned from Vial.
