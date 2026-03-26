# Guardian — Competitive Positioning

## The Problem

Existing tax and compliance software assumes the user is a normal US person. For the ~13 million nonimmigrant visa holders in the US, this default assumption creates cascading compliance failures that can result in six- to seven-figure penalties.

## The Failure Pattern

### Step 1: Wrong Software, Wrong Form
TurboTax, H&R Block, and FreeTaxUSA cannot file Form 1040-NR (nonresident alien return). When an immigrant uses them, the software defaults to Form 1040 (resident return), which:
- Claims the standard deduction ($14,600) they're not entitled to
- Reports worldwide income when only US-source income may be taxable
- Misses tax treaty benefits that could reduce or eliminate withholding
- Creates a record of claiming US tax residency — contradicting nonimmigrant status

### Step 2: Missing Information Returns
Because the software treats them as a US person, it doesn't surface:
- **FBAR** (FinCEN 114) — required if foreign accounts > $10K aggregate. Penalty: up to 50% of account balance per year (willful), or $16,536/year (non-willful)
- **FATCA Form 8938** — required if foreign assets > $50K. Penalty: $10K + $50K continued failure
- **Form 5472** — required for foreign-owned single-member LLCs. Penalty: $25K/year, no statute of limitations
- **Form 3520** — required for foreign gifts > $100K. Penalty: 25% of unreported amount
- **Form 8843** — required for all F/J visa holders, even with zero income. Often completely unknown

### Step 3: Cascading Penalties
For a typical immigrant professional with:
- $500K in foreign bank accounts (family accounts, home country savings)
- A US LLC formed 3 years ago
- $200K in family gifts from abroad
- 5 years of filing 1040 instead of 1040-NR

**Potential penalty exposure:**
| Item | Calculation | Amount |
|---|---|---|
| FBAR (5 years, willful) | 50% × $500K × 5 | $1,250,000 |
| FATCA (5 years) | $10K × 5 + continued | $100,000 |
| Form 5472 (3 years) | $25K × 3 | $75,000 |
| Form 3520 (family gifts) | 25% × $200K | $50,000 |
| Amended returns + interest | Variable | $50,000+ |
| **Total exposure** | | **$1.5M+** |

This is a conservative estimate. With larger foreign accounts or willful non-filing, exposure can reach $5-15M.

## Existing Software Limitations

| Software | Can file 1040-NR? | Cross-domain? | Document analysis? | Risk surfacing? | Memory? |
|---|---|---|---|---|---|
| TurboTax | No | No | No | No | Annual reset |
| H&R Block | No | No | No | No | Annual reset |
| Sprintax | Yes (tax only) | No | No | No | Annual reset |
| Immigration lawyers | N/A | Immigration only | Manual | Partial | Case files |
| CPAs | Sometimes | Tax only | Manual | Depends | Annual |
| **Guardian** | **Checks, not files** | **Tax + Immigration + Entity + Employment** | **Mistral OCR + Claude** | **Rule engine + proactive chat** | **Persistent data room** |

## Guardian's Differentiation

1. **Doesn't assume you're American** — the entire product is built for immigrants
2. **Crosses every domain** — tax, immigration, entity, employment in one view
3. **Reads your actual documents** — OCR + AI extraction, not manual data entry
4. **Surfaces risks you don't know about** — deterministic rules + proactive questions
5. **Remembers everything** — persistent timeline, deadlines, document vault
6. **Explains in plain English** — no jargon, no form numbers without context

## Target Customer Segments

1. **F-1 students on CPT/OPT/STEM** — highest urgency, most confused, most at risk from unauthorized employment
2. **H-1B professionals** — employer change compliance, status maintenance, H-1B to green card transition
3. **Immigrant entrepreneurs** — foreign-owned LLC/C-Corp compliance, Form 5472, entity structure risks
4. **Anyone who used TurboTax when they shouldn't have** — amendment needed, cascading fixes

## Key Insight

The user's real problem is not "I need to file a tax return." It's "I don't know what I don't know, and the penalty for not knowing is catastrophic."

Guardian's value is not in filing — it's in **finding what's wrong before it becomes a penalty.**
