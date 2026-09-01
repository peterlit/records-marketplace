---
name: records-critique
description: Critique a recommendation received from a doctor, lawyer, or other advisor - the strongest case for it, the strongest case against, what it assumes, how it interacts with other advice already on file, and what to ask next. Use whenever someone reports what a professional advised or prescribed, asks for a second opinion or a sanity check on advice, wants to know whether a recommendation is sound, or asks what an expert critic would say about it. Also use when two advisors have said different things and the conflict needs laying out.
license: MIT
---

# Critique a recommendation

Produces a genuinely two-sided assessment of advice received. Not a verdict — the named decision-maker decides.

## Before writing

Read `CLAUDE.md` (**who is the decision-maker, and what is the conservatism dial set to?**), the Settled register, the Master Summary, the relevant question lists, and any prior critiques of the same advisor. Then research the actual evidence — do not critique from memory. Current guidelines and trial results change.

## Structure

Write to `04 Critiques/YYYY-MM-DD <Advisor> - <topic>.md`.

### 1. What was recommended
State it precisely, in their words where you have them, with the date and who said it. If you are working from a paraphrase, say so — a critique of a misremembered recommendation is worthless.

### 2. The steelman — the strongest case *for*
Make the best version of their argument, better than they made it if you can. What evidence supports it? What are they seeing that a layperson would miss? What is the cost of *not* doing it? **If the recommendation is straightforwardly correct, say so plainly** — a critique that manufactures doubt to seem balanced is a failure.

### 3. The strongest case *against*
- What would have to be true for this to be the wrong call?
- What contrary evidence exists — including trials that *failed* to show benefit for this approach?
- What does it assume about this person specifically that might not hold?
- Is it standard of care, or one defensible option among several?
- Is there a cheaper, safer, or more reversible option that gets most of the benefit?

Distinguish **"this is wrong"** from **"this is one reasonable choice among several"** from **"this is outside mainstream practice."** These are very different critiques and collapsing them is the commonest error.

### 4. Interactions and contradictions
- How does this interact with everything else already in place?
- **Does it contradict another advisor on file?** Name both positions, both dates, and what each assumes. Do not resolve it for them — an unresolved disagreement between advisors is *itself* the finding, and it needs an owner.
- Does it re-open something in the Settled register? If so, say what new evidence would justify that.

### 5. Questions it raises
Concrete, askable questions — added to the relevant `01 Master/Questions — <advisor>.md` under Urgent or Next.

### 6. Options, not a directive
End with the realistic options and what distinguishes them. **Respect the conservatism dial** set in `CLAUDE.md`:

- `conservative` — lead with the least-invasive path; name what would have to change to justify escalating.
- `balanced` — equal weight and comparable depth to each path.
- `interventionist` — where evidence supports acting, say so directly and early; still give the cautious case.

**Never end with "you should."** Name who decides, and what they'd need to know to decide well.

## Standards

- **Cite specifics.** Named trials, guideline bodies, dates. "Studies show" is not a critique.
- **Say when the evidence is weak or contested**, including when that undercuts a point you just made.
- **Be fair to the advisor.** They examined the person; you read a file. Assume competence and look for the reasoning you might be missing before concluding they're wrong.
- **Limited trust cuts both ways** — it means not deferring automatically, not assuming bad judgment.
- **Flag your own uncertainty** rather than smoothing it over.
- Close with the appropriate disclaimer from `CLAUDE.md` and a reminder of who decides.

## Afterwards

Add a Timeline row, a Prompt Log entry, update the question lists, and follow the project's snapshot rule.
