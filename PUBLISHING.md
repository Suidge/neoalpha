# NeoAlpha Publishing Checklist

Use this checklist before publishing NeoAlpha to GitHub or ClawHub.

## Skill Quality

- `SKILL.md` includes frontmatter: `name`, `slug`, `version`, `description`.
- `SKILL.md` stays short and points detailed workflows to `references/`.
- Heavy guidance lives in `references/`, scripts, templates, or cron files.
- `README.md` explains purpose, requirements, install steps, thesis storage, scripts, and privacy boundaries.
- `INSTALLATION.md` contains deterministic setup and verification steps.

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

## GitHub

- Use `README.md` as the repository landing page.
- Do not add a license unless the maintainer explicitly chooses one.
- Use `.gitignore` to exclude generated files and private runtime directories.
- Keep examples generic and reproducible.
- Use `gh` body files for issue, PR, or release text containing commands or user-provided content.

## ClawHub

Publish only after the privacy scan is clean:

```bash
clawhub publish ./neoalpha --slug neoalpha --name "NeoAlpha" --version <VERSION> --changelog "<CHANGELOG>"
```

Check the rendered skill page after publish and remove the release immediately if private data appears.
