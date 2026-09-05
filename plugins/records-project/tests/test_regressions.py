#!/usr/bin/env python3
"""Regression suite for records-project.

**Every test here corresponds to a bug that actually shipped.** The docstring on
each says what went wrong, so a future failure is legible without archaeology.

Stdlib only, to match the constraint on the scripts themselves — no pytest, no
network, no fixtures beyond tempfile. Runs in a couple of seconds:

    python3 plugins/records-project/tests/test_regressions.py
    python3 -m unittest discover -s plugins/records-project/tests -v
"""
import os
import re
import sys
import json
import shutil
import hashlib
import tempfile
import subprocess
import unittest

TESTS = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.dirname(TESTS)
SCRIPTS = os.path.join(PLUGIN, "scripts")


def run(script, *args, expect=None):
    """Run a bundled script. Returns (rc, stdout+stderr)."""
    p = subprocess.run([sys.executable, os.path.join(SCRIPTS, script), *map(str, args)],
                       capture_output=True, text=True)
    out = p.stdout + p.stderr
    if expect is not None and p.returncode != expect:
        raise AssertionError(f"{script} {' '.join(map(str, args))}\n"
                             f"expected rc={expect}, got {p.returncode}\n{out}")
    return p.returncode, out


def build(target, *extra, subject="Anna Petrova", preset="health", advisors=("Dr. Chen:cardiologist",)):
    args = [target, "--preset", preset, "--subject", subject]
    for a in advisors:
        args += ["--advisor", a]
    args += list(extra)
    run("scaffold.py", *args, expect=0)
    return target


def tree_hashes(root, skip=(".records-project.json",)):
    h = {}
    for dp, _, fns in os.walk(root):
        for fn in fns:
            if fn in skip:
                continue
            p = os.path.join(dp, fn)
            h[os.path.relpath(p, root)] = hashlib.md5(open(p, "rb").read()).hexdigest()
    return h


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="rp-test-")
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)

    def path(self, *p):
        return os.path.join(self.dir, *p)

    def read(self, vault, rel):
        with open(os.path.join(vault, rel), encoding="utf-8") as f:
            return f.read()

    def write_file(self, path, body):
        with open(path, "w", encoding="utf-8") as f:
            f.write(body)

    def config(self, vault):
        with open(os.path.join(vault, ".records-project.json"), encoding="utf-8") as f:
            return json.load(f)


# ---------------------------------------------------------------- scaffolding

class TestScaffold(Base):
    def test_fresh_build_validates(self):
        for preset in ("health", "generic"):
            v = build(self.path(preset), "--obsidian", preset=preset)
            self.assertIn("vault valid", run("validate_vault.py", v, expect=0)[1])

    def test_write_verifies_non_zero(self):
        """Cloud-only files copy as 0 bytes and fail silently. write() must catch it."""
        v = build(self.path("v"))
        for dp, _, fns in os.walk(v):
            for fn in fns:
                p = os.path.join(dp, fn)
                self.assertGreater(os.path.getsize(p), 0, f"0-byte file written: {p}")

    def test_no_unrendered_template_syntax(self):
        v = build(self.path("v"), "--obsidian", "--co-user", "P", "--co-user", "A")
        for dp, _, fns in os.walk(v):
            for fn in fns:
                if not fn.endswith(".md"):
                    continue
                body = open(os.path.join(dp, fn), encoding="utf-8").read()
                self.assertNotIn("{{", body, f"unrendered syntax in {fn}")


class TestOverwriteGuard(Base):
    """SHIPPED: re-running scaffold.py on a live vault reset the Master Summary,
    the settled register, every question list and the Timeline to empty templates.
    No warning, exit 0, success message. The only guard was a sentence in SKILL.md."""

    CURATED = "SYNTHETIC-MARKER-DO-NOT-REPLACE-WITH-REAL-VALUES"

    def _curate(self, v):
        for rel in ("01 Master/Master Summary.md",
                    "01 Master/Settled — do not re-open.md",
                    "01 Master/Questions — Dr. Chen.md",
                    "02 Chronicle/Timeline.md"):
            with open(os.path.join(v, rel), "a", encoding="utf-8") as f:
                f.write(f"\n- {self.CURATED}\n")

    def test_refuses_to_scaffold_over_an_existing_vault(self):
        v = build(self.path("v"), "--obsidian")
        self._curate(v)
        before = tree_hashes(v)
        rc, out = run("scaffold.py", v, "--preset", "health", "--subject", "Anna Petrova",
                      "--advisor", "Dr. Chen:cardiologist")
        self.assertNotEqual(rc, 0, "scaffolding over a live vault must fail")
        self.assertIn("already a records project", out)
        self.assertIn("--reconfigure", out, "must name the safe alternative")
        self.assertEqual(before, tree_hashes(v), "refusal must not touch a single byte")

    def test_curation_survives_the_refusal(self):
        v = build(self.path("v"), "--obsidian")
        self._curate(v)
        run("scaffold.py", v, "--preset", "health", "--subject", "Anna Petrova",
            "--advisor", "Dr. Chen:cardiologist")
        for rel in ("01 Master/Master Summary.md", "01 Master/Questions — Dr. Chen.md",
                    "02 Chronicle/Timeline.md"):
            self.assertIn(self.CURATED, self.read(v, rel), f"{rel} was destroyed")

    def test_force_still_permits_deliberate_teardown(self):
        v = build(self.path("v"), "--obsidian")
        self._curate(v)
        run("scaffold.py", v, "--preset", "health", "--subject", "Anna Petrova",
            "--advisor", "Dr. Chen:cardiologist", "--force", expect=0)
        self.assertNotIn(self.CURATED, self.read(v, "01 Master/Master Summary.md"))

    def test_scaffolds_alongside_unrelated_content(self):
        """A folder with the person's own files is not a vault; build alongside it."""
        os.makedirs(self.path("v"))
        keep = self.path("v", "old-scan.pdf")
        self.write_file(keep, "x")
        build(self.path("v"), "--obsidian")
        self.assertTrue(os.path.isfile(keep), "pre-existing file was removed")
        self.assertIn("vault valid", run("validate_vault.py", self.path("v"), expect=0)[1])


# --------------------------------------------------------------- reconfigure

class TestReconfigure(Base):
    """SHIPPED: --reconfigure promised to 'carry forward everything the caller did
    not explicitly override' but carried only preset, co-users and obsidian. A bare
    --reconfigure --provider dropbox rewrote CLAUDE.md with subject 'the subject',
    no advisors and no decision-maker. The subject's name simply disappeared.

    The prior 'verification' re-supplied every flag — the one case that cannot fail.
    These tests deliberately supply as little as possible."""

    def _full(self, target):
        return build(target, "--dob", "1945-06-12", "--operator", "Peter",
                     "--decision-maker", "Peter", "--conservatism", "conservative",
                     "--situation", "Newly diagnosed AF.", "--language", "Polish",
                     "--provider", "gdrive", "--store-sensitive", "--obsidian",
                     "--advisor", "Dr. Okafor:PCP")

    def test_bare_reconfigure_is_a_byte_level_noop(self):
        v = self._full(self.path("v"))
        before = tree_hashes(v)
        run("scaffold.py", v, "--reconfigure", expect=0)
        self.assertEqual(before, tree_hashes(v))

    def test_changing_one_field_preserves_all_others(self):
        v = self._full(self.path("v"))
        run("scaffold.py", v, "--reconfigure", "--provider", "dropbox", expect=0)
        engine = self.read(v, "CLAUDE.md")
        self.assertIn("Anna Petrova", engine, "subject was blanked")
        self.assertNotIn("the subject", engine, "placeholder leaked into the record")
        self.assertIn("Peter", engine, "decision-maker was blanked")
        self.assertIn("conservative", engine, "conservatism dial was reset")
        self.assertIn("## Language", engine, "language rule was dropped")
        self.assertRegex(engine.lower(), r"dropbox", "the requested change did not apply")

    def test_curated_content_is_never_touched(self):
        v = self._full(self.path("v"))
        marker = "SYNTHETIC-CURATION-MARKER — do not lose this"
        with open(os.path.join(v, "01 Master/Master Summary.md"), "a", encoding="utf-8") as f:
            f.write(f"\n{marker}\n")
        run("scaffold.py", v, "--reconfigure", "--provider", "icloud", expect=0)
        self.assertIn(marker, self.read(v, "01 Master/Master Summary.md"))

    def test_persisted_config_covers_every_rendered_field(self):
        """If a field renders into CLAUDE.md but is not persisted, --reconfigure
        will silently replace it with a placeholder. That is the bug's shape."""
        v = self._full(self.path("v"))
        cfg = self.config(v)
        for key in ("subject", "dob", "operator", "decision_maker", "advisors",
                    "conservatism", "situation", "language", "preset", "provider",
                    "snapshot_trigger", "store_sensitive", "memory", "obsidian",
                    "co_users", "shared", "title"):
            self.assertIn(key, cfg, f"{key} is not persisted; --reconfigure will lose it")

    def test_refuses_without_an_existing_config(self):
        os.makedirs(self.path("empty"))
        rc, out = run("scaffold.py", self.path("empty"), "--reconfigure")
        self.assertNotEqual(rc, 0)
        self.assertIn("records-project.json", out)


# ------------------------------------------------------------ template engine

class TestTemplateRendering(Base):
    """SHIPPED: {{VAR}} raised KeyError on an unknown key but {{#if X}} used
    ctx.get(), so a mistyped condition silently deleted its block. {{#if SHARED}}
    (the key is lowercase 'shared') dropped the records-sync-status row from every
    shared project. The typo was the symptom; the asymmetry was the bug."""

    def _render(self, text, ctx):
        sys.path.insert(0, SCRIPTS)
        try:
            import importlib
            mod = importlib.import_module("scaffold")
            return mod.render(text, ctx)
        finally:
            sys.path.pop(0)

    def test_unknown_condition_raises_rather_than_deleting_silently(self):
        with self.assertRaises(KeyError):
            self._render("{{#if NOPE}}x{{/if}}", {"nope": True})

    def test_unknown_variable_raises(self):
        with self.assertRaises(KeyError):
            self._render("{{NOPE}}", {})

    def test_known_condition_still_works_both_ways(self):
        self.assertEqual(self._render("{{#if on}}yes{{/if}}", {"on": True}), "yes")
        self.assertEqual(self._render("{{#if on}}yes{{/if}}", {"on": False}), "")

    def test_every_template_condition_is_a_real_context_key(self):
        """Catches the {{#if SHARED}} class across all templates at once."""
        used = set()
        for dp, _, fns in os.walk(os.path.join(PLUGIN, "templates")):
            for fn in fns:
                if fn.endswith(".tmpl"):
                    body = open(os.path.join(dp, fn), encoding="utf-8").read()
                    used |= set(re.findall(r"\{\{#if (\w+)\}\}", body))
        v = build(self.path("v"), "--co-user", "P", "--co-user", "A", "--obsidian")
        # Rendering succeeded, so every condition resolved. Guard the naming rule too.
        for key in used:
            self.assertEqual(key, key.lower(),
                             f"{{{{#if {key}}}}} is upper-case; context keys are lower-case")


# ------------------------------------------------------------------ validator

class TestValidator(Base):
    def test_nonexistent_target_fails(self):
        """SHIPPED: validating a nonexistent folder printed 'vault valid'."""
        rc, out = run("validate_vault.py", self.path("nope"))
        self.assertNotEqual(rc, 0)
        self.assertNotIn("vault valid", out)

    def test_zero_byte_file_fails(self):
        v = build(self.path("v"), "--obsidian")
        open(os.path.join(v, "01 Master", "Master Summary.md"), "w").close()
        rc, _ = run("validate_vault.py", v)
        self.assertNotEqual(rc, 0)

    def test_eviction_is_not_reported_as_a_fork(self):
        """SHIPPED: both said SYNC CONFLICT COPY, sending people to look for a
        merge that does not exist. Different causes, different fixes."""
        v = build(self.path("v"), "--provider", "icloud", "--obsidian")
        self.write_file(os.path.join(v, "01 Master", ".Master Summary.md.icloud"), "stub")
        rc, out = run("validate_vault.py", v)
        self.assertNotEqual(rc, 0)
        self.assertIn("EVICTED", out)
        self.assertIn("Optimise Mac Storage", out)
        self.assertNotIn("SYNC CONFLICT COPY", out)

    def test_fork_is_not_reported_as_eviction(self):
        v = build(self.path("v"), "--provider", "icloud", "--obsidian")
        src = os.path.join(v, "01 Master", "Master Summary.md")
        shutil.copy(src, os.path.join(v, "01 Master", "Master Summary 2.md"))
        rc, out = run("validate_vault.py", v)
        self.assertNotEqual(rc, 0)
        self.assertIn("SYNC CONFLICT COPY", out)
        self.assertNotIn("EVICTED", out)

    def test_settled_register_is_not_a_false_positive(self):
        """SHIPPED: the OneDrive conflict pattern flagged 'Settled — do not
        re-open.md'. The tightened pattern still matched because the validator
        compiles case-insensitively."""
        v = build(self.path("v"), "--provider", "onedrive", "--obsidian")
        self.assertIn("vault valid", run("validate_vault.py", v, expect=0)[1])

    def test_language_drift_fails(self):
        """SHIPPED risk: config says Polish but CLAUDE.md lost its Language section,
        so every future chat silently reverts to English."""
        v = build(self.path("v"), "--language", "Polish", "--obsidian")
        engine = os.path.join(v, "CLAUDE.md")
        with open(engine, encoding="utf-8") as f:
            body = f.read()
        i, j = body.index("## Language"), body.index("## Classify each message")
        self.write_file(engine, body[:i] + body[j:])
        rc, out = run("validate_vault.py", v)
        self.assertNotEqual(rc, 0)
        self.assertIn("Language", out)

    def test_leftover_canary_fails(self):
        """Preflight cannot delete its own canary under Cowork's deletion
        protection, so the validator must not let it be forgotten."""
        v = build(self.path("v"), "--obsidian")
        self.write_file(os.path.join(v, ".preflight-canary"), "x")
        rc, out = run("validate_vault.py", v)
        self.assertNotEqual(rc, 0)
        self.assertIn("preflight-canary", out)


# ------------------------------------------------------------------ preflight

class TestPreflight(Base):
    """SHIPPED: preflight wrote a fresh canary and read that back, which always
    succeeds. It proved you could WRITE; it never proved the files already there
    could be READ. An evicted file reads as 0 bytes rather than erroring, and the
    danger is a successful-looking empty read that gets summarised and written back."""

    def test_fresh_target_passes(self):
        rc, out = run("preflight.py", self.path("new"))
        self.assertEqual(rc, 0)
        self.assertIn("preflight OK", out)

    def test_unmounted_path_fails_without_searching(self):
        rc, out = run("preflight.py", "/nope/never/here")
        self.assertNotEqual(rc, 0)
        self.assertIn("Do NOT search", out)

    def test_healthy_existing_vault_passes(self):
        v = build(self.path("v"), "--obsidian")
        rc, out = run("preflight.py", v)
        self.assertEqual(rc, 0)
        self.assertIn("reads are trustworthy", out)

    def test_evicted_vault_refuses(self):
        v = build(self.path("v"), "--provider", "icloud", "--obsidian")
        self.write_file(os.path.join(v, "01 Master", ".Master Summary.md.icloud"), "stub")
        rc, out = run("preflight.py", v)
        self.assertNotEqual(rc, 0)
        self.assertIn("evicted", out.lower())

    def test_zero_byte_curated_file_refuses(self):
        v = build(self.path("v"), "--obsidian")
        open(os.path.join(v, "01 Master", "Master Summary.md"), "w").close()
        rc, out = run("preflight.py", v)
        self.assertNotEqual(rc, 0)
        self.assertIn("zero-byte", out.lower())

    def test_warns_on_non_empty_target(self):
        os.makedirs(self.path("v"))
        self.write_file(self.path("v", "something.pdf"), "x")
        rc, out = run("preflight.py", self.path("v"))
        self.assertEqual(rc, 0)
        self.assertIn("NOT empty", out)


# ---------------------------------------------------------------- shared mode

class TestSharedMode(Base):
    def test_one_co_user_stays_solo(self):
        """A co-user is a peer; shared mode needs two or more. One name must not
        half-enable it."""
        v = build(self.path("v"), "--co-user", "Peter", "--obsidian")
        self.assertFalse(self.config(v)["shared"])
        self.assertFalse(os.path.isdir(os.path.join(v, "_sync")))

    def test_two_co_users_enable_shared(self):
        v = build(self.path("v"), "--co-user", "Peter", "--co-user", "Anna", "--obsidian")
        self.assertTrue(self.config(v)["shared"])
        self.assertTrue(os.path.isfile(os.path.join(v, "_sync", "_sync.md")))

    def test_sync_status_row_renders(self):
        """SHIPPED: {{#if SHARED}} dropped this row from every shared project — the
        one line telling co-users how to check whether the other is working."""
        v = build(self.path("v"), "--co-user", "P", "--co-user", "A", "--obsidian")
        self.assertIn("records-sync-status", self.read(v, "CLAUDE.md"))

    def test_reconfigure_into_shared_writes_the_folder_note(self):
        """SHIPPED: it created _sync/ with makedirs but skipped the template walk,
        so the validator failed immediately. Only the retrofit path was affected —
        which is the common one, since projects become shared later."""
        v = build(self.path("v"), "--obsidian")
        run("scaffold.py", v, "--reconfigure", "--co-user", "Peter", "--co-user", "Anna", expect=0)
        self.assertTrue(os.path.isfile(os.path.join(v, "_sync", "_sync.md")))
        self.assertIn("vault valid", run("validate_vault.py", v, expect=0)[1])

    def test_marker_tie_break_at_equal_timestamps(self):
        """A start and its stop can land in the same second; 'started' would
        otherwise win and report a finished session as active."""
        v = build(self.path("v"), "--co-user", "P", "--co-user", "A", "--obsidian")
        sync = os.path.join(v, "_sync")
        stamp = "2026-01-01T00-00-00Z"
        for kind in ("started", "stopped"):
            self.write_file(os.path.join(sync, f"{stamp}__Peter__{kind}.md"), f"kind: {kind}\n")
        _, out = run("sync_status.py", v, "--status", expect=0)
        self.assertNotIn("ACTIVE", out, "a stopped session was reported as active")


class TestOnboarding(Base):
    """00 START HERE.md must onboard a SECOND person on a different machine. The
    setup that actually matters is provider-specific and, if skipped, produces
    silent data loss rather than an error."""

    def _start(self, v):
        return self.read(v, "00 START HERE.md")

    def test_offline_instruction_is_provider_specific(self):
        expected = {
            "gdrive": "Available offline",
            "icloud": "Optimise Mac Storage",
            "onedrive": "Always keep on this device",
            "dropbox": "Smart Sync",
        }
        for prov, phrase in expected.items():
            v = build(self.path(prov), "--provider", prov, "--obsidian")
            self.assertIn(phrase, self._start(v), f"{prov} onboarding lacks its own setup step")

    def test_local_provider_gets_no_cloud_ceremony(self):
        v = build(self.path("v"), "--provider", "local", "--obsidian")
        body = self._start(v)
        self.assertIn("on local disk", body)
        for phrase in ("Available offline", "Optimise Mac Storage", "Smart Sync"):
            self.assertNotIn(phrase, body)

    def test_onboarding_names_cowork_setup_and_a_first_prompt(self):
        v = build(self.path("v"), "--provider", "gdrive", "--obsidian")
        body = self._start(v)
        self.assertIn("Add Folder", body, "must say how to point Cowork at the folder")
        self.assertIn("preflight", body, "must tell a new user to verify reads")
        self.assertIn("orient", body, "must give a first prompt")

    def test_co_user_guidance_only_in_shared_mode(self):
        solo = build(self.path("solo"), "--provider", "gdrive", "--obsidian")
        self.assertNotIn("co-user, not a guest", self._start(solo))
        shared = build(self.path("shared"), "--provider", "gdrive", "--obsidian",
                       "--co-user", "Peter", "--co-user", "Anna")
        body = self._start(shared)
        self.assertIn("co-user, not a guest", body)
        self.assertIn("Anna", body, "must name the other co-user")
        self.assertIn("Prompt Log", body, "must say how to see the other person's work")
        self.assertIn("started on desktop", body, "must explain the mobile constraint")


# ------------------------------------------------------------- chat companion

class TestChatCompanion(Base):
    def test_refuses_a_non_project(self):
        os.makedirs(self.path("plain"))
        rc, out = run("chat_companion.py", self.path("plain"))
        self.assertNotEqual(rc, 0)
        self.assertIn("not a records project", out)

    def test_inherits_settings_and_warns_off_gdrive(self):
        v = build(self.path("v"), "--decision-maker", "Peter",
                  "--conservatism", "conservative", "--provider", "icloud", "--obsidian")
        rc, out = run("chat_companion.py", v, expect=0)
        self.assertIn("WARN", out)
        body = self.read(v, "06 Reference/Chat companion — project instructions.md")
        self.assertIn("Peter", body)
        self.assertIn("conservative", body)
        self.assertIn("download_file_content", body,
                      "must name the working read tool; read_file_content returns empty for .md")
        self.assertIn("03 Inbox", body, "must state the write restriction")
        self.assertNotIn("{{", body)


class TestMigrate(Base):
    """SHIPPED IN DEVELOPMENT: migrate.py --apply on a vault whose old config lacked
    'subject' re-rendered CLAUDE.md with the placeholder "the subject" over the
    person's name — and printed "vault valid" and "migrated" while doing it. The
    finding said the value was unknown; applying anyway was the bug. Same shape as
    the --reconfigure blanking, arriving through a new door."""

    def _age(self, v, version="0.4.0", keep=("preset", "co_users", "obsidian", "provider",
                                             "conflict_patterns", "created")):
        p = os.path.join(v, ".records-project.json")
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        old = {k: d[k] for k in keep if k in d}
        old["plugin_version"] = version
        self.write_file(p, json.dumps(old, indent=2))

    def test_report_is_the_default_and_writes_nothing(self):
        v = build(self.path("v"), "--obsidian")
        self._age(v)
        before = tree_hashes(v, skip=())
        rc, out = run("migrate.py", v)
        self.assertEqual(rc, 0)
        self.assertIn("REPORT ONLY", out)
        self.assertEqual(before, tree_hashes(v, skip=()), "report mode wrote something")

    def test_current_vault_reports_nothing_to_do(self):
        v = build(self.path("v"), "--obsidian")
        _, out = run("migrate.py", v, expect=0)
        self.assertIn("up to date", out)

    def test_refuses_to_apply_with_unknown_settings(self):
        v = build(self.path("v"), "--subject", "Anna Petrova", "--obsidian")
        self._age(v)
        rc, out = run("migrate.py", v, "--apply", "--no-snapshot")
        self.assertNotEqual(rc, 0)
        self.assertIn("would be written as placeholders", out)
        self.assertIn("Anna Petrova", self.read(v, "CLAUDE.md"), "the name was blanked")

    def test_supplying_the_unknowns_migrates_cleanly(self):
        v = build(self.path("v"), "--subject", "Anna Petrova", "--obsidian")
        self._age(v)
        run("migrate.py", v, "--apply", "--no-snapshot", "--subject", "Anna Petrova",
            "--operator", "Peter", "--decision-maker", "Peter",
            "--advisor", "Dr. Chen:cardiologist", "--conservatism", "balanced",
            "--language", "English", "--snapshot", "master", "--provider", "local",
            expect=0)
        engine = self.read(v, "CLAUDE.md")
        self.assertIn("Anna Petrova", engine)
        self.assertNotIn("the subject", engine)
        self.assertEqual(self.config(v)["plugin_version"],
                         json.load(open(os.path.join(PLUGIN, ".claude-plugin",
                                                     "plugin.json")))["version"])

    def test_curated_content_is_never_modified(self):
        v = build(self.path("v"), "--subject", "Anna Petrova", "--obsidian")
        marker = "SYNTHETIC-CURATION-MARKER"
        for rel in ("01 Master/Master Summary.md", "02 Chronicle/Timeline.md"):
            with open(os.path.join(v, rel), "a", encoding="utf-8") as f:
                f.write(f"\n- {marker}\n")
        self._age(v)
        run("migrate.py", v, "--apply", "--no-snapshot", "--subject", "Anna Petrova",
            "--operator", "Peter", "--decision-maker", "Peter",
            "--advisor", "Dr. Chen:cardiologist", "--conservatism", "balanced",
            "--language", "English", "--snapshot", "master", "--provider", "local",
            expect=0)
        for rel in ("01 Master/Master Summary.md", "02 Chronicle/Timeline.md"):
            self.assertIn(marker, self.read(v, rel), f"{rel} was modified by migration")

    def test_refuses_a_folder_that_is_not_a_vault(self):
        os.makedirs(self.path("plain"))
        rc, out = run("migrate.py", self.path("plain"))
        self.assertNotEqual(rc, 0)
        self.assertIn("not a records project", out)

    def test_adopt_requires_a_subject(self):
        v = build(self.path("v"), "--obsidian")
        os.remove(os.path.join(v, ".records-project.json"))
        rc, out = run("migrate.py", v, "--adopt", "--apply", "--no-snapshot")
        self.assertNotEqual(rc, 0)
        self.assertIn("--subject", out)

    def test_adopts_a_config_less_vault(self):
        v = build(self.path("v"), "--subject", "Anna Petrova", "--obsidian")
        os.remove(os.path.join(v, ".records-project.json"))
        _, out = run("migrate.py", v)
        self.assertIn("predates self-description", out)
        run("migrate.py", v, "--adopt", "--apply", "--no-snapshot", "--preset", "health",
            "--subject", "Anna Petrova", "--operator", "Peter", "--decision-maker", "Peter",
            "--advisor", "Dr. Chen:cardiologist", expect=0)
        self.assertEqual(self.config(v)["subject"], "Anna Petrova")


# ------------------------------------------------------------------- packaging

class TestPackaging(Base):
    def test_frontmatter_is_portable(self):
        run("lint_frontmatter.py", expect=0)

    def test_no_subject_data_ships(self):
        """Includes this file. A test fixture is as public as any other line of code —
        the first run of this suite failed here because a real value was used as a
        curation marker."""
        run("lint_privacy.py", expect=0)

    def test_every_skill_is_listed_in_the_manifest(self):
        skills = {d for d in os.listdir(os.path.join(PLUGIN, "skills"))
                  if os.path.isdir(os.path.join(PLUGIN, "skills", d))}
        for s in skills:
            self.assertTrue(os.path.isfile(os.path.join(PLUGIN, "skills", s, "SKILL.md")),
                            f"{s} has no SKILL.md")

    def test_scripts_are_stdlib_only(self):
        """The scripts must run on any surface, including bridged copies where only
        scripts/ and templates/ were transferred."""
        allowed = {"os", "re", "sys", "json", "glob", "time", "shutil", "hashlib",
                   "zipfile", "argparse", "datetime", "subprocess", "tempfile",
                   "unittest", "importlib", "collections", "pathlib", "io", "csv"}
        for fn in os.listdir(SCRIPTS):
            if not fn.endswith(".py"):
                continue
            body = open(os.path.join(SCRIPTS, fn), encoding="utf-8").read()
            for mod in re.findall(r"^\s*(?:import|from)\s+([A-Za-z_][\w]*)", body, re.M):
                self.assertIn(mod, allowed, f"{fn} imports non-stdlib '{mod}'")


if __name__ == "__main__":
    unittest.main(verbosity=2)
