# Claims ledger

Generated 2026-11-04. This repo already builds its own claims discipline in — `claims.py` tiers every material claim
Demonstrated/Inferred/Assumed/Unsupported with a source and gates the thesis on it, and `recommendation.py` issues
"NO CALL" rather than a rating when a gate fails. This ledger checks the README's framing against that, not re-deriving it.

| Claim | Tag | Evidence |
|---|---|---|
| J&J initiation report built on Trellis + ValuationLab; 181 tests, every module mutation-tested | Demonstrated | README, `claims.py` module |
| ValuationLab's verdict that no method is structurally fit to anchor a conclusion on J&J (DCF 82% terminal value, precedents disagree 2.6x, comps span 3.0x) | Demonstrated — reported as the honest output, not papered over | REPORT.md |
| Three items disclosed as sitting outside the numbers on every run ($5.5bn talc cash, acquisition spend/buyback mismatch, equity-comp issuance) | Demonstrated — correctly disclosed as exclusions, not hidden | README |
| Diluted weighted-average share count from XBRL (not available upstream in Trellis/ValuationLab) | Demonstrated | `shares.py` |
| Rating/target price issued unconditionally | Unsupported as a general claim — the repo's own design issues NO CALL when gates fail; README correctly reflects this | `recommendation.py` |

## Action
No overclaim found. This repo is the one in the portfolio already enforcing the exact discipline P0-15 exists to retrofit elsewhere — worth pointing to as the model for the others' claims.md, not just auditing it the same way.
