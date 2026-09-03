# Controlled release-upgrade rehearsal

The `1.1 -> 1.2-beta.1` target is a test fixture, not a public Lyra release.
The next public milestone remains Lyra OS `1.1 Beta 1` on openSUSE Leap 16.1;
the synthetic `1.2-beta.1` identity exists only to exercise an actual
cross-release upgrade from an installed Lyra OS 1.1 baseline. Build it in a
dedicated OBS rehearsal project that is not inherited by an installed image
and never publish it in the stable repositories.

Prepare the RPM sources and canonical manifest with:

```sh
./scripts/prepare-controlled-successor.py \
  --output-dir /tmp/lyra-successor \
  --manifest-tool ../lyraos-desktop-updater/scripts/release-manifest.py \
  --repositories rehearsal/controlled-repositories-leap-16.1.json \
  --sequence 1 \
  --valid-from 2026-08-31T00:00:00Z \
  --valid-until 2026-09-30T00:00:00Z \
  --signing-key FEDCBA9876543210FEDCBA9876543210FEDCBA98
```

The repository input must contain exactly `repo-oss`, `repo-non-oss`,
`repo-packman-essentials`, `repo-lyra`, `repo-vega`, `repo-fina` and
`lyra-controlled-successor`, each with its real HTTPS base/key URLs, full
fingerprint and target priority. Omitting an installed source would invalidate
metadata revalidation or orphan installed packages, so the generator rejects
partial sets. Replace every other example value with its real value. The output
directory must not exist. The generator derives
the successor spec from the canonical `lyra-release` package, changes both the
version and build ID atomically, and delegates manifest validation/signing to
the updater's canonical producer.

The manifest is deliberately `testing`; the installed baseline must explicitly
opt in through `/etc/lyra-upgrade/channel`. Rehearsal automation must retain the
same disk, NVRAM and installation UUID through offline application, reboot,
verification and rollback. GNOME, KDE and XFCE use the shared contract.

The controlled route requires updater 0.2.3 or newer because that is the first
version that keeps stable URLs compiled while allowing an explicit external
manifest base URL only after the administrative `testing` opt-in.

Do not turn a locally generated artifact into passing release evidence. The
gate accepts a result only after real OBS RPMs, the externally hosted signed
manifest, post-boot target identity and restored baseline have all been
observed.

## Current isolated fixture

The OBS project `home:rodrigosbrito:lyra:upgrade-rehearsal` is the current
non-production fixture. Its repository key fingerprint is
`FC29F72CD7A021D88CD01D713A2AFF9457B7B5DA`. Revision 4 of `lyra-release`
contains RPM version `1.2~beta.1` and product version `1.2-beta.1`; it built
successfully for Leap 16.0 and 16.1 on 2026-09-03. This fixture does not alter
the public 1.1 release sequence or the Leap 16.1 base.

The first single-repository manifest draft was invalidated after preflight
review proved that every enabled baseline alias must remain represented. A new
canonical manifest still needs the complete seven-repository input and remains
unsigned because the release private key is intentionally absent from the
development host. Until an authorized signing environment produces
the detached signature and an external HTTPS endpoint publishes both files,
the fixture is not eligible for VM execution or release evidence.

The checked-in repository input records public URLs and fingerprints verified
directly from each repository key on 2026-08-31. The successor key URL remains
unusable until OBS publishes that repository; generation is not proof of URL
availability, and the VM rehearsal must re-fetch and verify all seven keys.
