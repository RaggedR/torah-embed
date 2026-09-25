# LESSONS

Rules for myself, derived from mistakes made on this project.

## Storage

- **Write anything expensive to the repository the moment it exists.** Never
  leave generated data in the session scratchpad. If recreating it costs more
  than a minute, it does not belong in `/tmp`. (Cost: 15 agent-runs of
  generated training questions, 2026-09-24.)
- Checkpoint by *cost to recreate*, not by size. A 239 MB embedding array that
  takes 25 minutes matters less than a 2 MB question set that takes fifteen
  agents.

## Resources

- **Do not run agent fan-out and GPU training at the same time on a 16 GB
  machine.** They are mutually exclusive, not merely competing. Generate,
  drain, verify, then train.
- Cap concurrent sub-agents at 5 on this hardware.
- When a resource problem is diagnosed, ask what *else* the same cause
  explains. Diagnosing "the agents slowed training" and then relaunching
  training while the agents' memory was still held is drawing too narrow a
  conclusion from a correct observation.

## Measurement

- **Never trust a progress bar's rate estimate.** `tqdm`'s `s/it` extrapolates
  from the first iteration, the least representative one. Use elapsed
  wall-clock divided by steps completed. (Reported 3h43m; the real rate was
  44h.)
- **Before believing a number, ask what besides the hypothesis could produce
  it** — and check it *before* the result exists, not after, when every check
  looks like special pleading.
- **Control for pool size in any comparison that changes the candidate set.**
  It reversed the sign of the chunking result, not merely its magnitude.
- **Verify denominators when a number flatters the project.** Three of this
  project's five measurement errors were self-fulfilling denominators or
  unrepresentative samples, and all three inflated the result.
- **Ask sub-agents what they were unsure about, not just what they produced.**
  Two real design defects passed every mechanical check and surfaced only
  through volunteered doubt.

## Reporting

- Say "no model has been trained" plainly and repeatedly, not in a
  parenthesis. Ambiguous phrasing about what exists wastes the user's time and
  erodes trust in every other claim.
