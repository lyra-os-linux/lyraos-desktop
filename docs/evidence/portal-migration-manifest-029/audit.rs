use lyra_upgrade_core::{InstalledPackage, ManifestChannelPolicy, ManifestError,
    PackageAction, PackageChange, ReleaseManifest, validate_manifest_route};
use lyra_upgrade_core::migration::{pending_migration, validate_migration_plan};
use serde_json::json;

fn main() {
    let data = std::fs::read("../canonical/releases-v1.json").unwrap();
    let m: ReleaseManifest = serde_json::from_slice(&data).unwrap();
    let route = |channel, sequence, version| validate_manifest_route(&m, &m.source, sequence, version, channel);
    assert_eq!(route(ManifestChannelPolicy::Testing, None, "0.2.9"), Ok(()));
    assert_eq!(route(ManifestChannelPolicy::Stable, None, "0.2.9"), Err(ManifestError::NotAvailable));
    assert_eq!(route(ManifestChannelPolicy::Testing, None, "0.2.5"), Err(ManifestError::UpdaterTooOld));
    assert_eq!(route(ManifestChannelPolicy::Testing, Some(2), "0.2.9"), Err(ManifestError::MigrationAlreadyApplied));
    assert_eq!(route(ManifestChannelPolicy::Testing, Some(3), "0.2.9"), Err(ManifestError::Replay));
    for old_version in ["0.2.5", "0.2.6", "0.2.7", "0.2.8"] {
        assert_eq!(route(ManifestChannelPolicy::Testing, None, old_version), Err(ManifestError::UpdaterTooOld));
    }
    assert_eq!(route(ManifestChannelPolicy::Testing, Some(1), "0.2.9"), Ok(()));
    assert_eq!(m.sequence, 2);
    assert_eq!(m.minimum_updater_version, "0.2.9");
    assert_eq!(m.source, m.target);
    let packages = m.package_migration.as_ref().unwrap();
    assert_eq!(packages.len(), 2);
    let all: Vec<_> = packages.iter().map(|p| InstalledPackage {
        name: p.name.clone(), architecture: p.architecture.clone(), version: p.from_version.clone(), vendor: p.from_vendor.clone(),
    }).collect();
    let changes: Vec<_> = packages.iter().map(|p| PackageChange {
        name: p.name.clone(), architecture: p.architecture.clone(), action: PackageAction::Upgrade,
        current_version: Some(p.from_version.clone()), proposed_version: Some(p.to_version.clone()),
        current_vendor: Some(p.from_vendor.clone()), proposed_vendor: Some(p.to_vendor.clone()),
        repository_alias: Some(p.repository_alias.clone()), download_bytes: 1,
        installed_size_before: 1, installed_size_after: 1,
    }).collect();
    assert_eq!(pending_migration(&m, &all[..1]).unwrap().len(), 1);
    assert_eq!(pending_migration(&m, &all).unwrap().len(), 2);
    assert!(validate_migration_plan(&m, &all[..1], &changes[..1]).is_ok());
    assert!(validate_migration_plan(&m, &all, &changes).is_ok());
    assert!(validate_migration_plan(&m, &all[..1], &changes).is_err());
    assert!(validate_migration_plan(&m, &all, &changes[..1]).is_err());
    let mut extra = changes.clone();
    let mut unrelated = changes[0].clone(); unrelated.name = "unrelated-package".into();
    unrelated.proposed_vendor = unrelated.current_vendor.clone(); extra.push(unrelated);
    assert!(validate_migration_plan(&m, &all, &extra).is_err());
    let mut drift = all.clone(); drift[0].version = "unknown-version".into();
    assert!(pending_migration(&m, &drift).is_err());
    let mut applied = all.clone();
    for (current,p) in applied.iter_mut().zip(packages) { current.version=p.to_version.clone(); current.vendor=p.to_vendor.clone(); }
    assert!(pending_migration(&m, &applied).unwrap().is_empty());
    println!("{}", serde_json::to_string_pretty(&json!({
        "passed": true, "kind": "real candidate manifest parsed by Updater 0.2.9 core; no signature or VM execution",
        "testing_route": true, "stable_refused": true, "older_updater_refused": true, "rejected_versions": ["0.2.5", "0.2.6", "0.2.7", "0.2.8"], "accepts_sequence_after_one": true,
        "consumed_sequence_refused": true, "lower_sequence_refused": true,
        "unchanged_product_identity": true, "without_language": true, "with_language": true,
        "adding_absent_language_refused": true, "omitting_present_language_refused": true,
        "unrelated_same_vendor_change_refused": true, "unknown_source_refused": true,
        "already_applied_empty": true
    })).unwrap());
}
