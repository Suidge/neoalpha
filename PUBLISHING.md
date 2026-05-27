# NeoAlpha Publishing Workflow

Use this workflow before publishing NeoAlpha to GitHub or ClawHub.

Canonical local source:

```bash
cd "$HOME/.openclaw/workspace/skills/neoalpha"
```

## Skill Quality

- `SKILL.md` includes frontmatter: `name`, `slug`, `version`, `description`.
- `SKILL.md` stays short and points detailed workflows to `references/`.
- Heavy guidance lives in `references/`, scripts, templates, or cron files.
- `README.md` explains purpose, requirements, install steps, thesis storage, scripts, and privacy boundaries.
- `INSTALLATION.md` contains deterministic setup and verification steps.
- `references/architecture.md` version matches `SKILL.md` when the release changes behavior.

## Version Check

Check the latest public ClawHub version before choosing the next version:

```bash
clawhub inspect neoalpha
```

Set `SKILL.md` to a version higher than ClawHub `Latest`. ClawHub does not automatically sync from GitHub, so every public update needs a fresh `clawhub publish`.

## Privacy

Do not publish:

- Personal thesis files.
- Portfolio transactions, current positions, generated strategy files, live-state files, or owner prompts.
- User IDs, chat IDs, email addresses, family names, travel plans, private schedules, or absolute local user paths.
- API keys, OAuth tokens, cookie/session data, credential paths, or environment files.

Run:

```bash
rg -n "(/Users/[^/ ]+|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}|api[_-]?key|token|secret|password|Bearer|Authorization|ou_[0-9a-z]+|oc_[0-9a-z]+)" .
```

Review every match. Some generic documentation matches are acceptable only if they do not reveal actual private values.

## Validation

Run from the NeoAlpha skill root:

```bash
python3 -m compileall -q scripts
python3 scripts/setup_cron.py --help >/tmp/neoalpha-setup-cron-help.txt
python3 scripts/screen_stocks.py --help >/tmp/neoalpha-screen-stocks-help.txt
python3 scripts/market_strategy_engine.py --help >/tmp/neoalpha-engine-help.txt
git status --short --branch
```

Remove temporary help files and `__pycache__` before finishing:

```bash
find scripts -type d -name __pycache__ -prune -print
find /tmp -maxdepth 1 -name "neoalpha-*" -print
```

## GitHub

- Use `README.md` as the repository landing page.
- Do not add a license unless the maintainer explicitly chooses one.
- Use `.gitignore` to exclude generated files and private runtime directories.
- Keep examples generic and reproducible.
- Use `gh` body files for issue, PR, or release text containing commands or user-provided content.
- Prefer GitHub noreply identity for public commits:

```bash
git config user.name "Suidge"
git config user.email "Suidge@users.noreply.github.com"
```

Commit with explicit staging:

```bash
git status --short
git add <explicit paths>
git diff --cached --name-only
git commit -m "<message>"
git push origin main
```

Create a GitHub Release for every ClawHub-distributed public version:

```bash
gh release view v<VERSION> --repo Suidge/neoalpha
git ls-remote --tags origin v<VERSION>
gh release create v<VERSION> --repo Suidge/neoalpha --target <commit-sha> --title "NeoAlpha v<VERSION>" --notes-file /tmp/neoalpha-v<VERSION>-release-notes.md
```

Use a release notes file. Do not pass long notes inline.

## ClawHub

Publish only after the privacy scan is clean:

```bash
cd "$HOME/.openclaw/workspace/skills"
clawhub whoami
clawhub publish neoalpha --slug neoalpha --name "NeoAlpha" --version <VERSION> --changelog "<CHANGELOG>"
```

Notes from the 2026-05-26 release:

- ClawHub CLI v0.8.0 uses `-V` or `--cli-version` for CLI version; global `--version` is invalid.
- Publishing from the skill parent directory with `neoalpha` as the path is the most reliable form.
- If `clawhub publish .` or another path reports `SKILL.md required`, retry from the skill parent directory with `neoalpha`.

## Post-Publish Verification

```bash
git status --short --branch
git log -1 --pretty=fuller
gh release view v<VERSION> --repo Suidge/neoalpha
clawhub inspect neoalpha
clawhub inspect neoalpha --files
```

Required result:

- GitHub `main` is even with `origin/main`.
- GitHub Release `v<VERSION>` exists and targets the intended commit.
- `clawhub inspect neoalpha` shows `Latest: <VERSION>`.
- No real private data appears in rendered metadata or listed files.
- Temporary `/tmp/neoalpha-*` files and `scripts/__pycache__` are removed.

Remove the ClawHub release immediately if private data appears.
