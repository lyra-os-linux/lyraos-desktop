# Portal testing manifest requiring Updater 0.2.9

Prepared on 2026-09-28 after the published Updater RPM passed the
[native migration and rollback tests](../portal-updater-native/README.md).
The maintainer signed these exact bytes using the official key on 2026-09-28.
The [signature receipt](signature-verified.json) and
[independent check](independent-signature-check.json) verify the detached
signature against the unchanged public key shipped by the signed 0.2.9 RPM.
The private key was restored only in a temporary RAM directory and removed
after signing. The original handoff request remains unchanged as historical
evidence; the verification receipts record its completion.

Only two fields differ from the preserved
[sequence-1 manifest](../portal-migration-manifest/README.md):

- `minimum_updater_version`: 0.2.7 → **0.2.9**, excluding the versions with the
  observed unprivileged Snapper and automatic offline reboot defects.
- `sequence`: 1 → **2**, identifying a newer manifest without reusing sequence 1.

The two portal RPM identities and hashes, repository URLs, priorities, public
key fingerprints, vendor grants, source/target Lyra 1.1 identity, free-space
requirement and validity window remain unchanged. Every repository targets
Leap 16.1. Status remains `testing`, valid until 2026-10-11 00:00 UTC; no stable
endpoint or production sequence is allocated by this handoff.

Canonical manifest SHA256:
`da0e5194f24d78fdbcfd9174f9dc79dce8d1c832d54053c2917ce5f4e1196218`.
[Preparation receipt](preparation.json) records the exact two-field diff.
The [policy audit](policy-audit.json), using core from the published 0.2.9 source
commit, rejects clients 0.2.5–0.2.8, consumed/replayed sequences, stable-channel
consumption, unrelated package changes and incorrect translation handling.
It accepts 0.2.9 and a previous sequence of 1 without bypassing installed-package
identity checks. Already migrated packages produce no pending migration.

Review these bytes and create a detached signature with the unchanged official
key `01B63EEDBE6B079126A0116EFA7353A131ECEFEB`:

```sh
sha256sum --check SHA256SUMS
gpg --armor --detach-sign \
  --local-user 01B63EEDBE6B079126A0116EFA7353A131ECEFEB \
  --output releases-v1.json.asc -- releases-v1.json
```

Verify against the public key shipped by the signed 0.2.9 RPM before hosting
the pair at an immutable HTTPS testing URL. The earlier lifecycle receipts
use sequence 1 and remain historical evidence; runtime validation of these
new exact signed bytes is still required. Never clear a real installation's
sequence or relax signature verification to accept this testing document.
