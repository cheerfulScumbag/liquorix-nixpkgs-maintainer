# Liquorix Nixpkgs maintainer

This repository contains the maintenance automation for the `linux_lqx`
package in Nixpkgs. It is intentionally separate from Nixpkgs: Nixpkgs remains
the source of the package, while this project detects releases, prepares
updates, validates them, and opens draft pull requests for human review.

The automation never merges a pull request or applies an AI-generated patch.
Kenn (`@cheerfulScumbag`) remains responsible for reviewing every update and
for responding to build failures and upstream changes.

## Maintenance policy

- Target: Nixpkgs `master`, `x86_64-linux`.
- Detection: daily.
- Update batching: weekly, plus manual dispatch for urgent releases.
- Point release: updater tests, formatting, evaluation, maintainer checks,
  config generation, kernel build, a NixOS boot/module smoke test, and the
  `v4l2loopback` and VirtualBox out-of-tree modules.
- New kernel line: all point-release checks plus a bounded
  `nixpkgs-review` set covering display, input, network, virtualization, and
  utility modules.
- Liquorix configuration drift is a hard stop for human review.
- AI triage is optional, receives a sanitized and size-limited build log, and
  writes recommendations only.

ZFS is not used as a release gate while Nixpkgs marks its module broken for the
current kernel line. Its status should still be called out in the upstream PR
when relevant; it must not be represented as a Liquorix-specific regression.
An unbounded review is also informational rather than a release gate: adding a
kernel package makes every external module appear newly reachable, including
modules already known to lag the latest kernel API.

## Repository setup

1. Create `cheerfulScumbag/liquorix-nixpkgs-maintainer` and push this directory.
2. Fork `NixOS/nixpkgs` to `cheerfulScumbag/nixpkgs`.
3. Add a repository secret named `NIXPKGS_PAT`. It must be able to push to the
   fork and create a pull request in the public upstream repository. At present
   that normally means a short-lived classic token with `public_repo`; rotate
   it regularly and do not grant unrelated scopes.
4. Optionally add `OPENAI_API_KEY` to enable failure triage. Without it, the
   workflow still records and uploads the validation log.
5. Enable GitHub Actions and allow the workflow to create issues.

The workflow uses `NIXPKGS_PAT` to push a candidate branch to the fork and the
GitHub CLI to open a draft pull request against `NixOS/nixpkgs`. The built-in
`GITHUB_TOKEN` is used only for issues and artifacts in this repository.

## Local use

From this repository, with a Nixpkgs checkout next to it:

```console
./scripts/maintain.py check --nixpkgs ../nixpkgs
./scripts/maintain.py update --nixpkgs ../nixpkgs --output update.json
./scripts/validate.sh ../nixpkgs point
```

For a new `major.minor` kernel line, use the broader gate:

```console
./scripts/validate.sh ../nixpkgs new-line
```

Optional AI triage:

```console
OPENAI_API_KEY=... ./scripts/triage.py validation.log > triage.md
```

The default triage model is `gpt-5.6-terra`; override it with
`OPENAI_MODEL`. Logs are scrubbed for common credentials, home paths, and Nix
store hashes before they leave the runner.

## Updating a release branch

Nixpkgs stable branches are updated only where `linux_lqx` is already present.
Run the manual workflow, enter the exact branch name, and review the resulting
draft PR separately. Do not introduce the package into an old stable branch as
part of a routine point update.
