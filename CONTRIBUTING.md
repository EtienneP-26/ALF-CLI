# Contributing

Thanks for your interest! Contributions are welcome, following the
process below.

## Before you start

1. **Open an issue** describing what you want to do (new feature, fix,
   improvement).
2. **Wait for the maintainer's approval** before writing code.
3. Ask for access to the repository if you do not have it (forks are
   forbidden by the license).

## Workflow

All branches start from `dev`, never from `main`.

```bash
git checkout dev
git pull origin dev
git checkout -b feat/short-name-of-the-feature
```

Naming conventions:

- `feat/...`: new feature
- `fix/...`: bug fix
- `docs/...`: documentation

Then:

1. Make your commits (clear messages, one topic per commit).
2. Push your branch: `git push origin feat/short-name`.
3. Open a Pull Request **against `dev`** (never against `main`),
   describing what was done and referencing the issue (`Closes #12`).
4. Wait for review. Changes may be requested.

## Rules

- One PR, one topic.
- No direct pushes to `main` or `dev`.
- `main` is updated only by the maintainer, from `dev`.
- By contributing, you accept article 5 of the [LICENCE](./LICENCE).
