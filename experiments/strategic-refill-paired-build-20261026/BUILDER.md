# Isolated Ubuntu paired builder

`build-contract-v1.json` is the registered source/factor/path contract. `build_pair.py`
never configures or builds in the accepted profile. Its `prepare` action creates
a fresh scratch source/build/install root, checks all ordinary copied files have
independent inodes, preserves only the four explicitly reviewed source links,
and applies the nine frozen baseline payloads. It never copies old objects/PCH.

Each action requires a fresh `--out` directory. Commands:

```text
python3 build_pair.py prepare --out prepare-01
python3 build_pair.py configure --out configure-NN
python3 build_pair.py baseline --out baseline-build-NN
python3 build_pair.py candidate --out candidate-build-NN
```

Configuration can discover missing package metadata before the target closure
is complete. A successful exploratory configuration has
`CONFIGURED.json.dependency_closure=null` and cannot admit compilation. Once the
closure is complete, run configuration again to bind its exact certificate and
the exact core toolchain certificate.

The final prefix `TARGET_DEPENDENCY_CLOSURE.json` must contain `passed=true`,
`files` mapping toolchain-root-relative paths (for example `sysroot/usr/...`) to
SHA256 strings, and optional `links` mapping equivalent paths to exact link
target strings. The builder checks every file/link before and after commands.

Before either full build, the parent reviews the actual graph/dependencies and
writes scratch `BUILD_ADMISSION.json` with these fields:

```text
passed: true
contract_sha256: SHA256 of the registered contract
configured_sha256: SHA256 of scratch CONFIGURED.json
build_ninja_sha256: SHA256 of scratch build/build.ninja
compile_commands_sha256: SHA256 of scratch build/compile_commands.json
dependency_closure_sha256: SHA256 of prefix TARGET_DEPENDENCY_CLOSURE.json
```

Every configure/build holds the original GPU then pool nonblocking locks. A
child entrypoint verifies inherited FD/device/inode and independent-open lock
conflict immediately before executing CMake/Ninja. Owned process groups must
be empty before release, including on interruption. RSS observations are sampled
every 500ms and may miss transient aggregate peaks; the actual child rusage
maximum is saved separately and is not an aggregate concurrent RSS claim.

The candidate action first verifies the archived baseline source and binary
attestation, then changes only the registered CPP. Both arms use the same
physical scratch path, graph, flags, qualified prefix and environment. It may
reuse unchanged objects produced by this new baseline. DirectorAI compilation
must appear in each arm's real verbose build log.

Each capsule includes the full independent source snapshot, source-link review,
three actual binaries/config, manifests and an attestation linking both configure
and build command/FD/resource evidence. No restoration fields are emitted:
accepted inputs are protected and compared, never modified.

Initial actual results: `prepare-01` passed; `configure-01` failed on a missing
Boost CMake helper and is retained; `configure-02` passed after the exact helper
was supplied. No full VCMI build, native game or optimizer update has run here.
The successful graph contains 720 compile entries (707 ordinary TUs plus 13 PCH
entries), using explicit GNU11/sysroot, Release/O3, C++20, PCH ON and LTO OFF.
This is an engineering result and does not establish the refill mechanism or
game strength. Native regression/qualification and normal terminal/drain remain
separate mandatory runtime gates.
