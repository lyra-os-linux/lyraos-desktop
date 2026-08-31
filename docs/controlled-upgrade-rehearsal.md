# Controlled release-upgrade rehearsal

The `1.0 -> 1.1-beta.1` target is a test fixture, not a public Lyra release.
Build it in a dedicated OBS rehearsal project that is not inherited by an
installed image and never publish it in the stable repositories.

Prepare the RPM sources and canonical manifest with:

```sh
./scripts/prepare-controlled-successor.py \
  --output-dir /tmp/lyra-successor \
  --manifest-tool ../lyraos-desktop-updater/scripts/release-manifest.py \
  --repository-url https://download.example.invalid/lyra-successor/ \
  --repository-key-url https://download.example.invalid/lyra-successor/repodata/repomd.xml.key \
  --repository-key-fingerprint 0123456789ABCDEF0123456789ABCDEF01234567 \
  --sequence 1 \
  --valid-from 2026-08-31T00:00:00Z \
  --valid-until 2026-09-30T00:00:00Z \
  --signing-key FEDCBA9876543210FEDCBA9876543210FEDCBA98
```

Replace every example value with the isolated project's real HTTPS URLs and
full fingerprints. The output directory must not exist. The generator derives
the successor spec from the canonical `lyra-release` package, changes both the
version and build ID atomically, and delegates manifest validation/signing to
the updater's canonical producer.

The manifest is deliberately `testing`; the installed baseline must explicitly
opt in through `/etc/lyra-upgrade/channel`. Rehearsal automation must retain the
same disk, NVRAM and installation UUID through offline application, reboot,
verification and rollback. GNOME, KDE and XFCE use the shared contract. LXQt
must join the same matrix when its official image exists.

Do not turn a locally generated artifact into passing release evidence. The
gate accepts a result only after real OBS RPMs, the externally hosted signed
manifest, post-boot target identity and restored baseline have all been
observed.
