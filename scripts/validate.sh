#!/usr/bin/env bash
set -euo pipefail

nixpkgs=${1:?usage: validate.sh NIXPKGS_CHECKOUT point|new-line}
tier=${2:?usage: validate.sh NIXPKGS_CHECKOUT point|new-line}

case "$tier" in
  point|new-line) ;;
  *)
    echo "unknown validation tier: $tier" >&2
    exit 2
    ;;
esac

cd "$nixpkgs"

python3 pkgs/os-specific/linux/kernel/update-liquorix_test.py
nix-shell -p nixfmt-rfc-style --run \
  "nixfmt --check pkgs/os-specific/linux/kernel/liquorix-kernel.nix \
  maintainers/maintainer-list.nix pkgs/top-level/aliases.nix \
  pkgs/top-level/all-packages.nix pkgs/top-level/linux-kernels.nix"
nix-instantiate --eval --strict -A linux_lqx.version
nix-build lib/tests/maintainers.nix --no-out-link
nix-build -A linux_lqx.tests.versionDoesNotDependOnPatchesEtc --no-out-link
nix-build -A linux_lqx.configfile --no-out-link
nix-build -A linux_lqx --no-out-link
nix-build -A linux_lqx.tests.testsForKernel --no-out-link

# Representative open-source out-of-tree modules. An unavailable module is a
# real compatibility signal and must not be silently skipped.
nix-build -A linuxPackages_lqx.v4l2loopback --no-out-link
nix-build -A linuxPackages_lqx.virtualbox --no-out-link

if [[ "$tier" == new-line ]]; then
  if ! command -v nixpkgs-review >/dev/null; then
    echo "new-line validation requires nixpkgs-review" >&2
    exit 2
  fi
  # A new kernel package exposes every Nixpkgs external module as a newly
  # reachable attribute. Building that unbounded set conflates known,
  # version-gated upstream incompatibilities with Liquorix regressions. Keep
  # this broader than the point-release gate, but intentionally bounded.
  nixpkgs-review wip --no-shell \
    -p linux_lqx \
    -p linuxPackages_lqx.acpi_call \
    -p linuxPackages_lqx.evdi \
    -p linuxPackages_lqx.r8125 \
    -p linuxPackages_lqx.v4l2loopback \
    -p linuxPackages_lqx.virtualbox \
    -p linuxPackages_lqx.xpadneo
fi
