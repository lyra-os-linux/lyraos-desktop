use super::tests::{TempRoot, whole_disk_plan_with_new_esp};
use super::*;
use crate::service::executor::{ExecutorError, RealExecutor};
use crate::storage::{DiscoveryBackend, GuidedChoice, PlanBuilder, SwapChoice};
use std::cell::RefCell;

struct Recorder(RefCell<Vec<ArgvCommand>>);
impl Executor for Recorder {
    fn run(&self, command: &ArgvCommand) -> Result<String, ExecutorError> {
        self.0.borrow_mut().push(command.clone());
        Ok("root-uuid".into())
    }
    fn run_with_stdin(&self, _: &ArgvCommand, _: &str) -> Result<String, ExecutorError> {
        unreachable!()
    }
}

#[test]
fn bios_gpt_has_unformatted_embedding_area_with_and_without_swap() {
    for swap in [SwapChoice::None, SwapChoice::Zram, SwapChoice::Disk] {
        let (_, mut snapshot) = whole_disk_plan_with_new_esp();
        snapshot.uefi = false;
        let choice = GuidedChoice {
            raw_target: Some(RawTarget::Disk("/dev/sda".into())),
            volume_layer: VolumeLayer::Direct,
            swap,
        };
        let plan = PlanBuilder::new(&snapshot).build(&choice).unwrap();
        let ops = plan_to_operations(&plan, &snapshot).unwrap();
        let recorder = Recorder(RefCell::new(vec![]));
        ops[0].perform(&recorder).unwrap();
        let calls = recorder.0.borrow();
        assert!(
            calls
                .iter()
                .any(|c| c.args == ["-n1:0:+2M", "-t1:ef02", "/dev/sda"])
        );
        assert!(ops.iter().all(|op| !op.describe().contains("ESP")));
        let root = if swap == SwapChoice::Disk {
            "/dev/sda3"
        } else {
            "/dev/sda2"
        };
        assert!(
            ops.iter()
                .any(|op| op.describe() == format!("formatar Btrfs em {root}"))
        );
    }
}

#[test]
fn bios_fstab_never_probes_or_mounts_an_esp() {
    let root = TempRoot::new("bios-fstab");
    let recorder = Recorder(RefCell::new(vec![]));
    WriteFstab {
        target_root: root.0.clone(),
        root_partition: "/dev/vda2".into(),
        esp_partition: None,
        swap_partition: None,
        subvolumes: crate::storage::plan::default_subvolumes(),
    }
    .perform(&recorder)
    .unwrap();
    assert!(
        !fs::read_to_string(root.0.join("etc/fstab"))
            .unwrap()
            .contains("/boot/efi")
    );
    assert_eq!(recorder.0.borrow().len(), 1);
}

#[test]
#[ignore = "requires disposable boot VM from scripts/check-installer-boot-vm.py"]
fn native_firmware_install_and_prepare_boot() {
    let cmdline = fs::read_to_string("/proc/cmdline").unwrap();
    assert!(
        cmdline
            .split_whitespace()
            .any(|v| v == "lyra.boot-test=install")
    );
    assert_eq!(
        fs::read_to_string("/sys/block/vda/serial").unwrap().trim(),
        "lyra-boot-test-only"
    );
    assert_eq!(
        fs::read_dir("/sys/block")
            .unwrap()
            .filter_map(Result::ok)
            .filter(|entry| entry.file_name().to_string_lossy().starts_with("vd"))
            .count(),
        1
    );
    let snapshot = crate::storage::SystemDiscoveryBackend.snapshot().unwrap();
    let choice = GuidedChoice {
        raw_target: Some(RawTarget::Disk("/dev/vda".into())),
        volume_layer: VolumeLayer::Direct,
        swap: SwapChoice::Zram,
    };
    let plan = PlanBuilder::new(&snapshot).build(&choice).unwrap();
    let ops = plan_to_operations(&plan, &snapshot).unwrap();
    let executor = RealExecutor;
    for op in &ops {
        println!("INSTALL {}", op.describe());
        op.perform(&executor).unwrap();
    }
    // Payload contains only public boot tools/libraries and a small boot probe,
    // not the host's accounts, configuration, RPM database or personal data.
    assert!(
        std::process::Command::new("cp")
            .args(["-a", "/payload/.", TARGET_ROOT])
            .status()
            .unwrap()
            .success()
    );
    for source in ["proc", "sys", "dev"] {
        fs::create_dir_all(Path::new(TARGET_ROOT).join(source)).unwrap();
        executor
            .run(&ArgvCommand {
                binary: "mount".into(),
                args: vec![
                    "--bind".into(),
                    format!("/{source}"),
                    format!("{TARGET_ROOT}/{source}"),
                ],
            })
            .unwrap();
    }
    executor
        .run(&ArgvCommand {
            binary: "btrfs".into(),
            args: vec!["subvolume".into(), "set-default".into(), TARGET_ROOT.into()],
        })
        .unwrap();
    let kernel = executor
        .run(&ArgvCommand {
            binary: "chroot".into(),
            args: vec![
                TARGET_ROOT.into(),
                "grub2-mkrelpath".into(),
                "/boot/vmlinuz-test".into(),
            ],
        })
        .unwrap();
    let initrd = executor
        .run(&ArgvCommand {
            binary: "chroot".into(),
            args: vec![
                TARGET_ROOT.into(),
                "grub2-mkrelpath".into(),
                "/boot/initrd-test".into(),
            ],
        })
        .unwrap();
    fs::create_dir_all(Path::new(TARGET_ROOT).join("boot/grub2")).unwrap();
    fs::write(Path::new(TARGET_ROOT).join("boot/grub2/grub.cfg"), format!("serial --unit=0 --speed=115200\nterminal_input serial\nterminal_output serial\nset timeout=0\nmenuentry 'Lyra installer firmware test' {{\n linux {kernel} console=ttyS0 rdinit=/init lyra.boot-test=installed\n initrd {initrd}\n}}\n")).unwrap();
    fs::create_dir_all(Path::new(TARGET_ROOT).join("etc/default")).unwrap();
    fs::write(
        Path::new(TARGET_ROOT).join("etc/default/grub"),
        "GRUB_DISTRIBUTOR=\"Lyra OS\"\n",
    )
    .unwrap();
    boot::InstallBootloader {
        target_root: TARGET_ROOT.into(),
        firmware: plan.firmware,
        disk: "/dev/vda".into(),
    }
    .perform(&executor)
    .unwrap();
    let report =
        fs::read_to_string(Path::new(TARGET_ROOT).join("var/log/lyra-installer-boot.json"))
            .unwrap();
    println!("BOOT_REPORT {report}");
    fs::write(
        Path::new(TARGET_ROOT).join("lyra-boot-marker"),
        "installer-firmware-valid\n",
    )
    .unwrap();
    for source in ["dev", "sys", "proc"] {
        executor
            .run(&ArgvCommand {
                binary: "umount".into(),
                args: vec![format!("{TARGET_ROOT}/{source}")],
            })
            .unwrap();
    }
    for op in ops.iter().rev() {
        op.undo(&executor).unwrap();
    }
    executor
        .run(&ArgvCommand {
            binary: "sync".into(),
            args: vec![],
        })
        .unwrap();
    println!("LYRA_BOOT_INSTALL_PASS firmware={:?}", plan.firmware);
}
