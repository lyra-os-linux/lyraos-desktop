// SHELL-01 manifest audit against the Updater 0.2.9 core (commit 3cc51f7).
// Inventory: the RC 3 image ships gnome-shell, gnome-shell-lang and
// gnome-extensions; -calendar and -devel are optional extras.
use lyra_upgrade_core::{InstalledPackage, ManifestChannelPolicy, ManifestError,
    PackageAction, PackageChange, ReleaseManifest, validate_manifest_route};
use lyra_upgrade_core::migration::{pending_migration, validate_migration_plan};
use serde_json::json;

fn main() {
    let data = std::fs::read("releases-v1.json").unwrap();
    let m: ReleaseManifest = serde_json::from_slice(&data).unwrap();
    let route = |channel, sequence, version| validate_manifest_route(&m, &m.source, sequence, version, channel);
    assert_eq!(route(ManifestChannelPolicy::Testing, None, "0.2.9"), Ok(()));
    assert_eq!(route(ManifestChannelPolicy::Stable, None, "0.2.9"), Err(ManifestError::NotAvailable));
    for old in ["0.2.5", "0.2.6", "0.2.7", "0.2.8"] {
        assert_eq!(route(ManifestChannelPolicy::Testing, None, old), Err(ManifestError::UpdaterTooOld));
    }
    // Sequences 1 and 2 were testing-only portal manifests; 3 follows them.
    assert_eq!(route(ManifestChannelPolicy::Testing, Some(1), "0.2.9"), Ok(()));
    assert_eq!(route(ManifestChannelPolicy::Testing, Some(2), "0.2.9"), Ok(()));
    assert_eq!(route(ManifestChannelPolicy::Testing, Some(3), "0.2.9"), Err(ManifestError::MigrationAlreadyApplied));
    assert_eq!(route(ManifestChannelPolicy::Testing, Some(4), "0.2.9"), Err(ManifestError::Replay));
    assert_eq!(m.sequence, 3);
    assert_eq!(m.source, m.target);
    let packages = m.package_migration.as_ref().unwrap();
    assert_eq!(packages.len(), 5);
    let installed = |p: &lyra_upgrade_core::migration::PackageMigration| InstalledPackage {
        name: p.name.clone(), architecture: p.architecture.clone(), version: p.from_version.clone(), vendor: p.from_vendor.clone(),
    };
    let change = |p: &lyra_upgrade_core::migration::PackageMigration| PackageChange {
        name: p.name.clone(), architecture: p.architecture.clone(), action: PackageAction::Upgrade,
        current_version: Some(p.from_version.clone()), proposed_version: Some(p.to_version.clone()),
        current_vendor: Some(p.from_vendor.clone()), proposed_vendor: Some(p.to_vendor.clone()),
        repository_alias: Some(p.repository_alias.clone()), download_bytes: 1,
        installed_size_before: 1, installed_size_after: 1,
    };
    let image = ["gnome-shell", "gnome-shell-lang", "gnome-extensions"];
    let in_image: Vec<_> = packages.iter().filter(|p| image.contains(&p.name.as_str())).collect();
    let inv: Vec<_> = in_image.iter().map(|p| installed(p)).collect();
    let plan: Vec<_> = in_image.iter().map(|p| change(p)).collect();
    // RC 3 image: exactly the three installed subpackages are pending.
    assert_eq!(pending_migration(&m, &inv).unwrap().len(), 3);
    assert!(validate_migration_plan(&m, &inv, &plan).is_ok());
    // Omitting gnome-extensions or gnome-shell-lang from the solver plan fails.
    assert!(validate_migration_plan(&m, &inv, &plan[..2]).is_err());
    // An optional package that is absent must not be added.
    let calendar = packages.iter().find(|p| p.name == "gnome-shell-calendar").unwrap();
    let mut with_absent = plan.clone(); with_absent.push(change(calendar));
    assert!(validate_migration_plan(&m, &inv, &with_absent).is_err());
    // When it is installed, it is pending and must move too.
    let mut inv_cal = inv.clone(); inv_cal.push(installed(calendar));
    assert_eq!(pending_migration(&m, &inv_cal).unwrap().len(), 4);
    assert!(validate_migration_plan(&m, &inv_cal, &plan).is_err());
    assert!(validate_migration_plan(&m, &inv_cal, &with_absent).is_ok());
    // gnome-shell alone (minimal install) is a valid one-package transaction.
    let shell = packages.iter().find(|p| p.name == "gnome-shell").unwrap();
    assert!(!shell.if_installed);
    assert!(validate_migration_plan(&m, &[installed(shell)], &[change(shell)]).is_ok());
    // Unrelated same-vendor change, unknown source and applied state.
    let mut extra = plan.clone();
    let mut unrelated = plan[0].clone(); unrelated.name = "unrelated-package".into();
    unrelated.proposed_vendor = unrelated.current_vendor.clone(); extra.push(unrelated);
    assert!(validate_migration_plan(&m, &inv, &extra).is_err());
    let mut drift = inv.clone(); drift[0].version = "48.8-160100.2.2".into();
    assert!(pending_migration(&m, &drift).is_err());
    let applied: Vec<_> = in_image.iter().map(|p| InstalledPackage {
        name: p.name.clone(), architecture: p.architecture.clone(), version: p.to_version.clone(), vendor: p.to_vendor.clone(),
    }).collect();
    assert!(pending_migration(&m, &applied).unwrap().is_empty());
    println!("{}", serde_json::to_string_pretty(&json!({
        "passed": true, "kind": "SHELL-01 testing manifest parsed by Updater 0.2.9 core (3cc51f7); no signature or VM execution",
        "testing_route": true, "stable_refused": true, "rejected_versions": ["0.2.5", "0.2.6", "0.2.7", "0.2.8"],
        "accepts_after_sequences": [1, 2], "consumed_sequence_refused": true, "higher_consumed_sequence_refused": true,
        "rc3_inventory_pending": image, "rc3_plan_accepted": true, "omitting_installed_subpackage_refused": true,
        "adding_absent_optional_refused": true, "installed_optional_required": true, "shell_only_accepted": true,
        "unrelated_same_vendor_change_refused": true, "unknown_source_refused": true, "already_applied_empty": true
    })).unwrap());
}
