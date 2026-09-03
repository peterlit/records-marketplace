#!/usr/bin/env python3
"""Static triggering check over evals/evals.json.

⚠️ WHAT THIS IS NOT
This does not measure triggering. Real triggering depends on Claude reading the
descriptions and choosing, which needs Claude in the loop - use skill-creator's
`run_eval.py` for that. This is a cheap proxy that catches two failure classes
you can find without running anything:

  1. COMPETITION - two skills whose descriptions score nearly equally on the same
     prompt. Whichever wins is close to arbitrary, and it will differ between
     runs and models.
  2. LEAKAGE - a near-miss prompt ("organise my Downloads", "what am I missing"
     about a pull request) that scores high against a skill. Over-eager
     descriptions fire on the keyword rather than the situation.

A clean run here means the descriptions are not obviously ambiguous. It does not
mean the skills fire correctly. Do not report it as if it did.

  lint_triggering.py [--verbose]
"""
import os, re, sys, json, glob, argparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STOP = set("""a an and are as at be but by can do does for from has have how i if in into is it
its me my of on or our so than that the their them then there these they this to us was we what
when where which who will with you your just some thing things able want need help please""".split())

# Flag only genuine ambiguity: the wrong skill winning, or a dead heat. An
# arbitrary larger margin produced false alarms on prompts where the right skill
# won comfortably - word overlap measures vocabulary, not meaning, so a modest
# lead is not a problem.
COMPETITION_MARGIN = 0.02
# Score at or above which a negative prompt counts as leaking into a skill.
LEAKAGE_THRESHOLD = 0.34


def words(text):
    return {w for w in re.findall(r"[a-z]+", text.lower()) if w not in STOP and len(w) > 2}


def load_skills():
    out = {}
    for f in sorted(glob.glob(os.path.join(ROOT, "skills", "*", "SKILL.md"))):
        name = os.path.basename(os.path.dirname(f))
        txt = open(f, encoding="utf-8").read()
        m = re.search(r"^description:\s*(.+?)(?=\n[a-z-]+:|\n---)", txt, re.S | re.M)
        out[name] = words(m.group(1)) if m else set()
    return out


def score(prompt_words, desc_words):
    """Overlap normalised by prompt length - how much of what the user said the
    description accounts for."""
    if not prompt_words:
        return 0.0
    return len(prompt_words & desc_words) / len(prompt_words)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true")
    a = ap.parse_args()

    skills = load_skills()
    ev_path = os.path.join(ROOT, "evals", "evals.json")
    if not os.path.isfile(ev_path):
        print(f"FAIL no eval corpus at {ev_path}"); return 2
    evals = json.load(open(ev_path, encoding="utf-8"))["evals"]

    problems = 0
    print(f"  {len(skills)} skills, {len(evals)} eval prompts "
          f"({sum(1 for e in evals if e['expect_skill'] is None)} near-miss negatives)\n")

    for e in evals:
        pw = words(e["prompt"])
        ranked = sorted(((score(pw, d), n) for n, d in skills.items()), reverse=True)
        top_score, top_name = ranked[0]
        want = e["expect_skill"]

        if want is None:
            if top_score >= LEAKAGE_THRESHOLD:
                print(f"  ⚠️  LEAKAGE  #{e['id']}: negative prompt scores {top_score:.2f} "
                      f"against {top_name}")
                print(f"             {e['prompt'][:78]}")
                problems += 1
            elif a.verbose:
                print(f"  ok  #{e['id']}: negative, top={top_name} {top_score:.2f}")
            continue

        if want not in skills:
            print(f"  ❌ #{e['id']}: expects unknown skill {want!r}"); problems += 1; continue

        want_score = score(pw, skills[want])
        rival_score, rival = next(((s, n) for s, n in ranked if n != want), (0.0, None))
        if want_score == 0.0:
            print(f"  ❌ NO MATCH #{e['id']}: {want} description shares NO vocabulary "
                  f"with this prompt")
            print(f"             {e['prompt'][:78]}")
            problems += 1
        elif rival and (want_score - rival_score) < COMPETITION_MARGIN:
            print(f"  ⚠️  COMPETE  #{e['id']}: {want} {want_score:.2f} vs "
                  f"{rival} {rival_score:.2f} (margin {want_score-rival_score:+.2f})")
            print(f"             {e['prompt'][:78]}")
            problems += 1
        elif a.verbose:
            print(f"  ok  #{e['id']}: {want} {want_score:.2f}, next {rival} {rival_score:.2f}")

    print(f"\n  {problems} potential triggering problem(s)")
    print("  NOTE: a proxy for ambiguity only. Real triggering needs Claude in the")
    print("        loop - see skill-creator's run_eval.py.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
