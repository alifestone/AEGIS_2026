# Intro

這是一場名為 AEGIS 的 Catch The Flag 比賽
時間: 2026/09/17 10:00 - 2026/09/19 19:00
網址: https://aegis2026.ctfd.io/
FLAG 形式為：AEGIS{printable_ascii+}

# Challenge

共 14 題，依 category 分資料夾存放，每題一個子資料夾（含附件與該題的 README.md）。

## Overview

| Category | Challenge | Points | Solves | Folder | Status |
|---|---|---|---|---|---|
| CyCraft | extraction-1 | 100 | 54 | [CyCraft/extraction-1/](CyCraft/extraction-1/) | ✅ Solved |
| CyCraft | extraction-2 | 100 | 52 | [CyCraft/extraction-2/](CyCraft/extraction-2/) | — |
| CyCraft | injection-1 | 100 | 52 | [CyCraft/injection-1/](CyCraft/injection-1/) | ✅ Solved |
| CyCraft | injection-2 | 100 | 51 | [CyCraft/injection-2/](CyCraft/injection-2/) | — |
| Misc | Travel 1 | 100 | 51 | [Misc/Travel_1/](Misc/Travel_1/) | ✅ Solved |
| Misc | Travel 2 | 100 | 45 | [Misc/Travel_2/](Misc/Travel_2/) | — |
| Misc | Jurassic Time Capsule | 100 | 49 | [Misc/Jurassic_Time_Capsule/](Misc/Jurassic_Time_Capsule/) | ✅ Solved |
| Misc | False Continuity | 600 | 21 | [Misc/False_Continuity/](Misc/False_Continuity/) | — |
| Rev | AI Challenge | 831 | 14 | [Rev/AI_Challenge/](Rev/AI_Challenge/) | — |
| Rev | Slime | 804 | 15 | [Rev/Slime/](Rev/Slime/) | — |
| Rev | aegis_asterism | 324 | 27 | [Rev/aegis_asterism/](Rev/aegis_asterism/) | — |
| Pwn | arbitragedb | 375 | 26 | [Pwn/arbitragedb/](Pwn/arbitragedb/) | — |
| Crypto | baby | 100 | 45 | [Crypto/baby/](Crypto/baby/) | ✅ Solved |
| Crypto | nursery melody | 100 | 37 | [Crypto/nursery_melody/](Crypto/nursery_melody/) | — |

## Rev

### aegis_asterism

- **Points**: 600　**Solves**: 21　**ID**: 52
- **Folder**: [Rev/aegis_asterism/](Rev/aegis_asterism/)
- **Files**:
  - `aegis_asterism.zip` (1,295,375 bytes)

**Description**

```
reverse me.

Rev + Crypto
```

### AI Challenge

- **Points**: 936　**Solves**: 9　**ID**: 29
- **Folder**: [Rev/AI_Challenge/](Rev/AI_Challenge/)
- **Connection**: `nc 0.cloud.chals.io 14159`
- **Tags**: rev, crypto
- **Files**:
  - `null_oracle_7b58188f90aac27b62cc48f9f0030899600e4efe` (2,113,712 bytes)

**Description**

```
AI 66666666 — only Level 6 is the real flag.

Flag format: `AEGIS{...}`
```

### Slime

- **Points**: 975　**Solves**: 6　**ID**: 30
- **Folder**: [Rev/Slime/](Rev/Slime/)
- **Connection**: `nc 36.226.134.123 2828`
- **Files**:
  - `Slime_e0ef41b331950dc31e8d725ca4468e87b8b4d6bb` (3,686,424 bytes)

**Description**

```
Slime games are really fun!

Please keep your coins safe. 

Save data may be reset once after a period of time. 

DDoS attacks are strictly prohibited.

Flag format: `AEGIS{...}`
```

## Misc

### Travel 1

- **Points**: 100　**Solves**: 50　**ID**: 32
- **Folder**: [Misc/Travel_1/](Misc/Travel_1/)
- **Tags**: osint
- **Files**:
  - `Travel_1.zip` (489,479 bytes)

**Description**

```
Can you identify the restaurant shown in this photo?

Find the exact restaurant on Google Maps and submit its Plus Code.

Flag format: AEGIS{PLUS_CODE}

Use only the Plus Code portion shown by Google Maps. Do not include the restaurant name, district, city, or any other location text.

Example:

2HM7+JJ Xicun Village, Xinyi District, Taipei City → AEGIS{2HM7+JJ}
```

### Travel 2

- **Points**: 100　**Solves**: 45　**ID**: 35
- **Folder**: [Misc/Travel_2/](Misc/Travel_2/)
- **Tags**: osint
- **Files**:
  - `Travel_2.zip` (10,770,165 bytes)

**Description**

```
Determine the exact location where this photo and submit its coordinates.

Flag format: AEGIS{latitude,longitude}

Truncate both the latitude and longitude to 4 decimal places — do not round. For negative values, simply discard all digits after the fourth decimal place (truncate toward zero).

Example:
25.033712, 121.561489 → AEGIS{25.0337,121.5614}
```

### Jurassic Time Capsule

- **Points**: 100　**Solves**: 48　**ID**: 38
- **Folder**: [Misc/Jurassic_Time_Capsule/](Misc/Jurassic_Time_Capsule/)
- **Tags**: osint
- **Files**:
  - `IMG20190525133555.jpg` (3,431,618 bytes)

**Description**

```
Years ago, beneath the feet of that long-necked behemoth, I buried a time capsule with my own hands. Returning to the old grounds recently, I looked up only to find a barren patch of lawn—the guardian was long gone.

Digging up an old photograph taken in 2019, certain traces still linger beneath the camera's raw data, yet that is not its true resting place. Travel through time, unravel the clues, and pinpoint the original coordinates where the beast once stood and the capsule was buried.
The capsule's self-destruct mechanism has been triggered; its fragile structure can withstand at most 10 excavation probe attempts. Lock onto the target with precision before making your move.
Flag Format: AEGIS{latitude,longitude} (Both latitude and longitude must be truncated down to 4 decimal places without rounding.

Example:
25.033712, 121.561489 → AEGIS{25.0337,121.5614})
Attempt Limit: Maximum 10 attempts
```

### False Continuity

- **Points**: 804　**Solves**: 15　**ID**: 37
- **Folder**: [Misc/False_Continuity/](Misc/False_Continuity/)
- **Files**:
  - `False_Continuity.zip` (14,591,071 bytes)

**Description**

```
Recover the flag.

flag format： AEGIS{}
```

## Pwn

### arbitragedb

- **Points**: 711　**Solves**: 18　**ID**: 51
- **Folder**: [Pwn/arbitragedb/](Pwn/arbitragedb/)
- **Connection**: `nc 0.cloud.chals.io 12983`
- **Files**:
  - `arbitragedb_d6d2b04c7267d4958d06f1588ad8984dd2ab727bf60295d684dcf59ed9e78737.zip` (2,522,303 bytes)

**Description**

```
RCE me. 

flag path : /home/arbitragedb/flag
```

## Crypto

### nursery melody

- **Points**: 100　**Solves**: 32　**ID**: 39
- **Folder**: [Crypto/nursery_melody/](Crypto/nursery_melody/)
- **Files**:
  - `nursery_melody.mp3` (96,591 bytes)

**Description**

```
Hear the Flag

Wrap the flag you found in AEGIS{}
```

### baby

- **Points**: 100　**Solves**: 38　**ID**: 44
- **Folder**: [Crypto/baby/](Crypto/baby/)
- **Files**:
  - `baby.zip` (2,439 bytes)

**Description**

```
baby
```

## CyCraft

### extraction-1

- **Points**: 100　**Solves**: 53　**ID**: 12
- **Folder**: [CyCraft/extraction-1/](CyCraft/extraction-1/)
- **Connection**: `https://aegis2026-ai-7577bf11-d7c8-4877-b883-4f01b76dc1d9-q1.chals.io`
- **Files**: （無附件）

**Description**

```
（題目附圖：cycraft_partner.jpg）
```

### injection-1

- **Points**: 100　**Solves**: 51　**ID**: 17
- **Folder**: [CyCraft/injection-1/](CyCraft/injection-1/)
- **Connection**: `https://aegis2026-ai-f2ed0071-4e02-4b89-bd58-8d0b887682ef-q1.chals.io`
- **Files**: （無附件）

**Description**

```
（題目附圖：cycraft_partner.jpg）
```
