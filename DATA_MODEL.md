# Data model: `pessimism.duckdb`

**What it's for.** When we ideate, a new idea meets resistance. This answers:
*has something like this been resisted before, by whom, for what reason, and was the
resistance right?* So it holds both directions: fears about new things that proved
wrong (the Pessimists Archive's beat) and warnings that proved right (the half the
Archive leaves out). A case is scored on the same axes either way, so the two can be
compared instead of cherry-picked.

```
source ──< case_source >── case ──< quote
                             │
                             └── (verdict, claim_type, warner, incumbent_stake, modern_analog …)
```

## `case` — one new thing meeting one prediction about it
| field | question it answers |
|---|---|
| `case_id` | slug, e.g. `walkman-isolation-1980s` |
| `thing` | What was new? (the Walkman, leaded petrol, the novel) |
| `domain` | media · computing · transport · energy · medicine · food · finance · work · consumer · science · culture |
| `year` | When did the fear/prediction peak? (int; first strong statement if unclear) |
| `claim` | The prediction in one line, in plain words |
| `claim_type` | health · youth_morals · jobs · safety · wont_work (impossible / no market) · isolation · decline (culture, attention, intellect) · environment · financial · privacy · security · legal |
| `warner` | Who said it: press · physicians · scientists · clergy · incumbents · unions · government · intellectuals · public · investors · insiders |
| `incumbent_stake` | Did the warner lose money or status if the thing won? (bool) — the strongest single tell in the Archive |
| `verdict` | **fear_wrong** · **fear_right** · **mixed** (both true: the fear was real but overstated, or right about harm and wrong about adoption) |
| `what_happened` | One line: how it actually turned out |
| `years_to_verdict` | Roughly how long until it was clear? |
| `cost_of_error` | What did getting it wrong cost? (one line: delayed adoption, deaths, money) |
| `modern_analog` | What today rhymes with it? (AI, social media, crypto, GLP-1, EVs, self-driving, gene editing, nuclear …) |
| `lesson` | The one transferable sentence for someone deciding today |
| `confidence` | high (primary source quoted) · medium (secondary) · low |

## `quote` — verbatim words, the evidence
| `case_id` | `text` (verbatim) | `speaker` | `year` | `publication` | `url` |

## `source` / `case_source`
| `source_id` | `kind` (substack · bigthink · freethink · research) | `title` | `date` | `url` | `text` |

## Rules
- **A verdict is never inferred from the Archive's framing alone.** The Archive only publishes fears it thinks were wrong; record `mixed` where the fear was partly borne out (e.g. TV and attention, social media and teen girls).
- **`fear_right` cases need a primary or authoritative source** (a regulator, a court record, a peer-reviewed retrospective), cited in `quote` or `case_source`.
- **Every quote is verbatim** from the source page, never paraphrased into quote marks.
