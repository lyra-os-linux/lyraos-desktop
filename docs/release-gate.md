# Desktop Alpha 7 release gate

> Alpha 8 (plan in issue #28, approved 2026-10-07) adds one fail-closed result
> to this baseline, `i18n`, and does not require `hardware-matrix`. The build
> tooling selects these requirements from `release.toml`; Alpha 7 remains
> reproducible with its original seven-result gate. See
> [Alpha 8 changes](#alpha-8-changes).
>
> RC 1 (maintainer decision, 2026-10-14) keeps the Alpha 8 result set and adds
> the detached release signature required from Beta onwards (ADR 0005). See
> [RC 1 changes](#rc-1-changes). RC 2 (2026-10-24) repeats the RC 1 gate for
> vegad 5.1.39; see [RC 2 changes](#rc-2-changes).

This checklist is the versioned go/no-go contract for the standard Lyra OS
Desktop Alpha 7 ISO. A release coordinator may declare **GO** only when every blocking
item below has passed and its evidence is included in the final image evidence
manifest. Missing evidence is a failure, not an implicit exception.

The current final-release scope is one GNOME Desktop ISO, with optional NVIDIA
installation through Vega. GNOME is the only Desktop edition. Package
CI, staging upload and local preview installation do not satisfy the ISO gate;
evidence must refer to the exact candidate. See [GNOME status](status-gnome.md).

## Severity and blocking policy

- **P0 — stop immediately:** data loss, credential disclosure, corrupted
  installation media, or an exploitable default configuration.
- **P1 — release blocker:** failure to boot the live or installed system;
  failure of the Lyra Installer; broken basic network, update, Snapper or
  rollback; invalid repository/package signatures; an unpublished mandatory
  package; or a regression without a safe workaround.
- **P2 — known issue:** degraded optional functionality with a tested,
  documented workaround. It must appear in the release notes.
- **P3 — follow-up:** cosmetic or low-impact defect that does not invalidate a
  supported scenario. It must have a tracking issue when not fixed.

No P0 or P1 issue may remain open at publication time. A P2 may be accepted
only when the decision record names its issue, workaround, owner and residual
risk.

## Candidate identity

- [ ] source tree is clean and the full commit is recorded;
- [ ] `release.toml`, KIWI metadata, ISO filename and installed `VERSION_ID`
  agree;
- [ ] the ISO package inventory contains exact OBS source revisions;
- [ ] every enabled RPM repository targets Leap 16.1 and no Leap 16.0 URL is
  present in the candidate;
- [ ] the candidate is tagged only after all blocking checks pass.

### Preserve and publish the tested candidate

The ISO identified by its filename, source commit and SHA-256 is the release
candidate. As soon as that exact ISO passes every blocking gate, freeze it,
generate the remaining files with `--artifacts-only`, and upload the bundle in
the same release run. Do not rebuild an approved ISO merely to prepare or
publish artifacts.

Preserve the tested ISO while resolving packaging, evidence or upload-tool
problems. Any source or image-content change creates a new candidate with a new
checksum and requires the applicable gates to be repeated; evidence from the
discarded ISO must not be relabeled for the replacement. This ordering avoids
spending a complete validation cycle on an image that is never published.

## Required evidence

Each file is structured JSON with schema 1 and top-level
`"status": "passed"`. `scripts/image-build.py artifact-manifest` also checks
the expected mode, nonempty passing checks, final rollback phase, OBS project
content and hardware coverage; a bare green status is rejected:

- [ ] `obs-repositories`: release projects published; provenance, repository
  metadata, keys and RPM signatures verified by `obs-release.py health`;
- [ ] `live-session`: autologin, GNOME, offline startup, basic devices and
  absence of critical journal failures;
- [ ] `installer`: Lyra Installer completes against the candidate ISO without
  a fallback installer;
- [ ] `first-boot`: installed disk boots, the created account works and no
  live-session artifact remains;
- [ ] `uefi-secure-boot`: supported UEFI and Secure Boot scenarios pass;
- [ ] `rollback`: update, Snapper snapshots and GRUB rollback pass;
- [ ] `hardware-matrix`: required real/virtual hardware scenarios are recorded.
- [ ] `v1.0-alpha.6` remains available as the immutable Leap 16.0 rollback
  baseline and the 16.0 → 16.1 upgrade/rollback rehearsal is recorded.

## RC 2 changes

RC 1 (`v16.1-rc.1`) was published. On 2026-10-24 the maintainer brought two
vegad bug fixes into the candidate (vegad 5.1.39: Firewall.Status reports the
real active zone, vegad#83/#85; Snapshots.ClearProgress is declared in the
introspection, vegad#86). Image content changes, so RC 2 (`16.1-rc.2`) is a new
candidate and repeats the RC 1 gate below with the same results and scope. In
addition:

On 2026-10-25 the unpublished RC 2 build was superseded by a rebuild with the
batched fixes: tuned-ppd (#167), XDG_DATA_DIRS (#169), the installer version
label (#183), libvulkan_intel/libvulkan_radeon (#185/#186), vegad 5.1.41
(vegad#78/#89, and vegad#90 for the firewall zone found by the gate) and
the Tauri vega-gtk 5.2.0 (vega#159, freeze exception
approved by the maintainer). The candidate keeps the `16.1-rc.2` identity.
On 2026-10-27 build #7 (parental controls) was superseded by build #8 with
vegad 5.1.44 and vega-gtk 5.3.2 (vegad#93/#94, vega#161/#163), for the Bluetooth
defect found by its gate on a machine without an adapter.

- [ ] the image rejects vegad older than 5.1.44 and vega-gtk older than 5.3.2
  (`check-gnome-image.py`);
- [ ] on the installed system, Vega's firewall status reports the `public`
  zone;
- [ ] GNOME shows the power mode selector and `tuned-ppd` is active;
- [ ] Vega 5.3.2 opens every page without errors in the journal;
- [ ] on a machine without a Bluetooth adapter, the Vega Bluetooth page shows
  "Nenhum adaptador Bluetooth encontrado" at once, and neither the Painel nor
  Serviços flags `bluetooth.service`;
- [ ] the installer header shows "RC 2";
- [ ] the bundle is built by `scripts/build-desktop-rc2.sh` and published by
  `scripts/upload-desktop-rc2-sourceforge.sh`, which sign and verify the
  checksum with the official release key (ADR 0005); the RC 1 wrappers keep
  guarding `16.1-rc.1` only;
- [ ] a non-trivial defect found during the gate stops the promotion and
  produces RC 3; criteria are never relaxed to keep the date.

## RC 1 changes

By maintainer decision on 2026-10-14 the Desktop cycle moves from Alpha 8
straight to RC 1 (`16.1-rc.1`), to be published by 2026-10-31; the final
`16.1` is rebuilt from openSUSE Leap 16.1 GA packages (2026-11-03) and
published on 2026-11-05. RC 1 starts the strict freeze: only bug, crash,
security and critical performance fixes to packages already shipped.

Required results are the Alpha 8 set, `obs-repositories`, `live-session`,
`installer`, `first-boot`, `uefi-secure-boot`, `rollback` and `i18n`, with
the same scope (new installations only, qualified in virtual machines;
`hardware-matrix` and `upgrade-rehearsal` are not required). In addition:

- [ ] the bundle carries `*.iso.sha256.asc`, a detached signature of the
  checksum by the official release key `01B63EEDBE6B079126A0116EFA7353A131ECEFEB`;
  `scripts/build-desktop-rc1.sh` signs it and
  `scripts/upload-desktop-rc1-sourceforge.sh` verifies it before and after
  upload (ADR 0005);
- [ ] `obs-repositories` comes from `scripts/obs-release.py health` on the
  release channels after the 2026-10-14 vega baseline reconciliation (#164);
- [ ] a non-trivial defect found during the gate stops the promotion and
  produces RC 2; criteria are never relaxed to keep the date.

## Alpha 8 changes

Alpha 8 covers new installations only, tested in virtual machines. Its
required results are `obs-repositories`, `live-session`, `installer`,
`first-boot`, `uefi-secure-boot`, `rollback` and:

- [ ] `i18n`: every supported Lyra-owned interface passes in `en-US`, `pt-BR`
  and Spanish (`es-ES`), with `en-US` as the explicit fallback;
- [ ] reconcile every fix in [the ISO fix tracker](iso-fix-tracker.md) with
  candidate contents and exact-checksum evidence; local repair alone does not
  close an ISO item.

Not required for Alpha 8:

- `hardware-matrix`: no physical hardware is tested; the release notes state
  that the candidate was qualified only in virtual machines;
- `upgrade-rehearsal`: upgrading an Alpha 7 installation is not supported or
  tested; the release notes state that Alpha 8 is a new installation only.

Declared in the release notes instead of structured evidence:

- **Parental controls (16.1 RC 2 onward):** the basic parental controls are
  gated by [docs/parental-controls-gate.md](parental-controls-gate.md)
  (`installed-gate.sh parental` plus the manual list). Before RC 2:
- **ECA Digital:** the candidate ships no parental control, no supervised
  account enrollment and no age signal to applications, and retains no age
  evidence. The notes state this scope explicitly;
- **Feature freeze:** no new functionality enters after the plan is approved.
  At publication the coordinator records in the notes that no P0 or P1 issue
  applicable to the shipped scope remains open; any other state is `NO-GO`.

## Release signing key

Per [ADR 0005](adr/0005-release-signing-starts-at-beta1.md), Desktop Alpha 7
is published with SHA-256 but without a detached GPG signature. The release
key is created and made mandatory starting with Beta 1. RPM repository and
package signatures remain mandatory in every stage and are not affected by
this temporary artifact-signing exception.

From Beta 1 onward, the ISO checksum is signed with the release coordinator's
own GPG key, not a key this repository generates or holds. The key fingerprint
and public key must be added here before the first Beta 1 candidate; no
placeholder or disposable Alpha key is trusted. The canonical identity selected
before the first signed Beta 1 candidate is:

- **Fingerprint:** `01B6 3EED BE6B 0791 26A0  116E FA73 53A1 31EC EFEB`
- **UID:** `Lyra OS Release <rodrigo@lyraos.com.br>`
- **Public key:** [`docs/release-signing-key.asc`](release-signing-key.asc)

The unused draft identity `E765 8249 6F86 597D A854 7BA4 FE28 7BB5 4891
BA80` was replaced before any Beta artifact was signed because its private key
could not be recovered. It never authorized an official release signature.

Starting with Beta 1, verification instructions must name the canonical
fingerprint and public-key file. Any later rotation replaces both in the same
commit that publishes the first candidate signed by the new key.

## Artifact and publication checks

- [ ] ISO, package inventory, KIWI verification/report and both SBOM formats
  are present;
- [ ] SHA-256 is generated and independently verified; starting with Beta 1,
  it is also signed with the canonical release key and the signature verified;
- [ ] release notes list requirements, limitations, P2/P3 issues and tested
  workarounds;
- [ ] the evidence manifest is generated from a clean commit and contains all
  required green results;
- [ ] the exact tested ISO and its evidence are uploaded to SourceForge
  immediately after GO; Alpha 7 does not require a post-upload redownload, but
  independent local checksum verification remains mandatory; signature
  verification is additionally mandatory from Beta 1 onward;
- [ ] #1 records coordinator, decision time, evidence URLs, accepted P2/P3
  risks and the exact source commit.

## Decision record

Record this block in #1 for every candidate:

```text
Decision: GO | NO-GO
Candidate commit:
ISO filename:
SHA-256:
Coordinator:
Decision time (UTC):
Evidence manifest:
Accepted P2/P3 issues and workarounds:
Residual risks:
```

## Current Desktop Alpha 7 state

**NO-GO enquanto a candidata limpa e as evidências da Alpha 7 não passarem.**
As validações da Alpha 6 continuam úteis como baseline, mas não substituem a
repetição completa sobre o Leap 16.1. O gate atual inclui explicitamente boot,
instalação, NVIDIA, áudio, codecs, upgrade e rollback. A Alpha 7 permanece sem
assinatura GPG destacada da ISO conforme a ADR 0005;
checksum, assinaturas de RPM/repositório e evidências estruturadas continuam
obrigatórios.

If a defect is found after publication, hide or remove the affected files on
SourceForge, record their checksums as withdrawn, stage and review the fix, and
publish a replacement candidate with a new evidence manifest. Never overwrite
an already distributed ISO while retaining its old checksum or decision record.
