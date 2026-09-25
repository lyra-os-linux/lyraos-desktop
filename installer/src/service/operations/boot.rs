//! Firmware-specific boot installation. A verified on-disk UEFI fallback is
//! mandatory; NVRAM registration is an additional capability, not a prerequisite.
use std::fs;
use std::path::{Path, PathBuf};

use super::super::executor::ExecutorError;
use super::{ArgvCommand, Executor, OperationError, PrivilegedOperation, io_error, path_str};
use crate::storage::FirmwareMode;

pub(super) struct InstallBootloader {
    pub target_root: PathBuf,
    pub firmware: FirmwareMode,
    pub disk: PathBuf,
}

impl InstallBootloader {
    fn chroot(&self, executor: &dyn Executor, args: &[&str]) -> Result<String, ExecutorError> {
        let mut argv = vec![path_str(&self.target_root)];
        argv.extend(args.iter().map(|arg| (*arg).to_string()));
        executor.run(&ArgvCommand {
            binary: "chroot".into(),
            args: argv,
        })
    }

    fn install_uefi(&self, executor: &dyn Executor) -> Result<&'static str, OperationError> {
        // Use Leap's signed shim/GRUB payload and config generator for both
        // the distribution path and portable path; never an unsigned EFI build.
        for removable in [false, true] {
            let mut args = vec![
                "shim-install",
                "--efi-directory=/boot/efi",
                "--config-file=/boot/grub2/grub.cfg",
                "--no-nvram",
            ];
            if removable {
                args.push("--removable");
            }
            self.chroot(executor, &args)?;
        }
        // This disk has a fresh ESP. Avoid a helper that attempts implicit
        // NVRAM enrollment/reset on a machine explicitly using portable boot.
        let fallback_helper = self.target_root.join("boot/efi/EFI/boot/fallback.efi");
        match fs::remove_file(&fallback_helper) {
            Ok(()) => {}
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => {}
            Err(error) => return Err(io_error(error)),
        }
        for relative in [
            "EFI/lyra/shim.efi",
            "EFI/lyra/grub.efi",
            "EFI/lyra/grub.cfg",
            "EFI/boot/bootx64.efi",
            "EFI/boot/grub.efi",
            "EFI/boot/MokManager.efi",
            "EFI/boot/grub.cfg",
        ] {
            require_nonempty_file(&self.target_root.join("boot/efi").join(relative))?;
        }
        // The root is freshly deployed from the trusted image. Do not accept a
        // partial copy or a different executable at the firmware fallback path.
        let efi = self.target_root.join("boot/efi/EFI");
        for (left, right) in [
            ("lyra/shim.efi", "boot/bootx64.efi"),
            ("lyra/grub.efi", "boot/grub.efi"),
        ] {
            if fs::read(efi.join(left)).map_err(io_error)?
                != fs::read(efi.join(right)).map_err(io_error)?
            {
                return Err(OperationError::Io(
                    "cópia EFI de recuperação inconsistente".into(),
                ));
            }
        }
        let variables = self.target_root.join("sys/firmware/efi/efivars");
        if let Err(error) = fs::create_dir_all(&variables) {
            return match error.raw_os_error() {
                Some(1 | 2 | 13 | 19 | 30) => Ok("uefi-fallback-no-variables"),
                _ => Err(io_error(error)),
            };
        }
        match executor.run(&ArgvCommand {
            binary: "mount".into(),
            args: vec![
                "-t".into(),
                "efivarfs".into(),
                "efivarfs".into(),
                path_str(&variables),
            ],
        }) {
            Ok(_) => {}
            Err(ExecutorError::NonZeroExit { .. }) => return Ok("uefi-fallback-no-variables"),
            Err(error) => return Err(error.into()),
        }
        // Only create an entry for this disk; never delete another installation's
        // entries or infer success from shim-install ignoring an efibootmgr error.
        let registration = self.chroot(
            executor,
            &[
                "efibootmgr",
                "--create",
                "--disk",
                &path_str(&self.disk),
                "--part",
                "1",
                "--label",
                "Lyra OS",
                "--loader",
                "\\EFI\\lyra\\shim.efi",
            ],
        );
        let cleanup = executor.run(&ArgvCommand {
            binary: "umount".into(),
            args: vec![path_str(&variables)],
        });
        // A retained mount is an installation failure, including after fallback.
        if let Err(error) = cleanup {
            return Err(OperationError::Cleanup {
                operation: Box::new(registration.err().map(OperationError::from).unwrap_or_else(
                    || OperationError::Io("entrada EFI criada; desmontagem pendente".into()),
                )),
                cleanup: Box::new(error.into()),
            });
        }
        match registration {
            Ok(_) => Ok("uefi-nvram"),
            Err(ExecutorError::NonZeroExit { .. }) => Ok("uefi-fallback-nvram-unavailable"),
            Err(error) => Err(error.into()),
        }
    }
}

impl PrivilegedOperation for InstallBootloader {
    fn describe(&self) -> String {
        match self.firmware {
            FirmwareMode::Bios => "instalar GRUB para BIOS no disco selecionado".into(),
            FirmwareMode::Uefi => {
                "instalar shim e GRUB assinados; NVRAM quando disponível e boot alternativo UEFI"
                    .into()
            }
        }
    }

    fn perform(&self, executor: &dyn Executor) -> Result<(), OperationError> {
        let mode = match self.firmware {
            FirmwareMode::Bios => {
                self.chroot(
                    executor,
                    &[
                        "grub2-install",
                        "--target=i386-pc",
                        "--recheck",
                        &path_str(&self.disk),
                    ],
                )?;
                require_nonempty_file(&self.target_root.join("boot/grub2/i386-pc/core.img"))?;
                "bios"
            }
            FirmwareMode::Uefi => self.install_uefi(executor)?,
        };
        let config = self.target_root.join("etc/sysconfig/bootloader");
        let existing = match fs::read_to_string(&config) {
            Ok(content) => content,
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => String::new(),
            Err(error) => return Err(io_error(error)),
        };
        let (loader, secure, location) = match self.firmware {
            FirmwareMode::Bios => ("grub2", "no", "mbr"),
            FirmwareMode::Uefi => ("grub2-efi", "yes", "none"),
        };
        let mut lines: Vec<String> = existing
            .lines()
            .filter(|line| {
                let key = line.trim_start().split('=').next().unwrap_or("").trim();
                ![
                    "LOADER_TYPE",
                    "SECURE_BOOT",
                    "LOADER_LOCATION",
                    "UPDATE_NVRAM",
                ]
                .contains(&key)
            })
            .map(str::to_string)
            .collect();
        lines.extend([
            format!("LOADER_TYPE={loader}"),
            format!("SECURE_BOOT={secure}"),
            format!("LOADER_LOCATION={location}"),
            format!(
                "UPDATE_NVRAM={}",
                if mode == "uefi-nvram" { "yes" } else { "no" }
            ),
        ]);
        fs::create_dir_all(config.parent().unwrap()).map_err(io_error)?;
        fs::write(config, lines.join("\n") + "\n").map_err(io_error)?;
        if self.firmware == FirmwareMode::Bios {
            // libbootloader uses this list for later bootloader reinstalls.
            fs::write(
                self.target_root.join("etc/default/grub_installdevice"),
                format!("{}\n", self.disk.display()),
            )
            .map_err(io_error)?;
        }
        let report = self.target_root.join("var/log/lyra-installer-boot.json");
        fs::create_dir_all(report.parent().unwrap()).map_err(io_error)?;
        let report_data = serde_json::json!({"schema": 1, "mode": mode,
            "fallback": mode.starts_with("uefi-fallback"),
            "message": if mode.starts_with("uefi-fallback") { "NVRAM indisponível; use a opção de boot UEFI do disco instalado." } else { "Bootloader instalado." }});
        fs::write(
            report,
            serde_json::to_vec_pretty(&report_data)
                .map_err(|error| OperationError::Io(error.to_string()))?,
        )
        .map_err(io_error)?;
        Ok(())
    }
}

fn require_nonempty_file(path: &Path) -> Result<(), OperationError> {
    let metadata = fs::symlink_metadata(path).map_err(io_error)?;
    if !metadata.is_file() || metadata.len() == 0 {
        return Err(OperationError::Io(format!(
            "arquivo de boot ausente ou inválido: {}",
            path.display()
        )));
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::super::tests::TempRoot;
    use super::*;
    use std::cell::RefCell;

    struct BootExecutor {
        calls: RefCell<Vec<ArgvCommand>>,
        fail: Option<&'static str>,
    }
    impl Executor for BootExecutor {
        fn run(&self, command: &ArgvCommand) -> Result<String, ExecutorError> {
            self.calls.borrow_mut().push(command.clone());
            let name = if command.binary == "chroot" {
                command.args[1].as_str()
            } else {
                &command.binary
            };
            if self.fail == Some(name) {
                return Err(ExecutorError::NonZeroExit {
                    binary: command.binary.clone(),
                    code: Some(1),
                    stderr: "injected failure".into(),
                });
            }
            Ok(String::new())
        }
        fn run_with_stdin(&self, _: &ArgvCommand, _: &str) -> Result<String, ExecutorError> {
            unreachable!()
        }
    }
    fn fixture(mode: FirmwareMode) -> (TempRoot, InstallBootloader) {
        let root = TempRoot::new("firmware-boot");
        for path in [
            "etc/default",
            "boot/grub2/i386-pc",
            "boot/efi/EFI/lyra",
            "boot/efi/EFI/boot",
        ] {
            fs::create_dir_all(root.0.join(path)).unwrap();
        }
        for file in [
            "boot/grub2/i386-pc/core.img",
            "boot/efi/EFI/lyra/shim.efi",
            "boot/efi/EFI/lyra/grub.efi",
            "boot/efi/EFI/lyra/grub.cfg",
            "boot/efi/EFI/boot/bootx64.efi",
            "boot/efi/EFI/boot/grub.efi",
            "boot/efi/EFI/boot/MokManager.efi",
            "boot/efi/EFI/boot/grub.cfg",
            "boot/efi/EFI/boot/fallback.efi",
        ] {
            fs::write(root.0.join(file), "test payload").unwrap();
        }
        let op = InstallBootloader {
            target_root: root.0.clone(),
            disk: PathBuf::from("/dev/vda"),
            firmware: mode,
        };
        (root, op)
    }
    fn executor(fail: Option<&'static str>) -> BootExecutor {
        BootExecutor {
            calls: RefCell::new(vec![]),
            fail,
        }
    }

    #[test]
    fn bios_never_mounts_efi_or_runs_shim_and_persists_bootloader_type() {
        let (root, op) = fixture(FirmwareMode::Bios);
        let executor = executor(None);
        op.perform(&executor).unwrap();
        let calls = executor.calls.borrow();
        assert_eq!(calls.len(), 1);
        assert_eq!(
            calls[0].args,
            vec![
                path_str(&root.0),
                "grub2-install".into(),
                "--target=i386-pc".into(),
                "--recheck".into(),
                "/dev/vda".into()
            ]
        );
        let config = fs::read_to_string(root.0.join("etc/sysconfig/bootloader")).unwrap();
        assert!(config.contains("LOADER_TYPE=grub2\n"));
        assert!(config.contains("SECURE_BOOT=no\n"));
        assert_eq!(
            fs::read_to_string(root.0.join("etc/default/grub_installdevice")).unwrap(),
            "/dev/vda\n"
        );
    }

    #[test]
    fn uefi_no_variables_or_full_nvram_uses_checked_portable_boot() {
        for failure in [Some("mount"), Some("efibootmgr"), None] {
            let (root, op) = fixture(FirmwareMode::Uefi);
            let executor = executor(failure);
            op.perform(&executor).unwrap();
            let calls = executor.calls.borrow();
            assert!(calls[0].args.contains(&"--no-nvram".into()));
            assert!(calls[1].args.contains(&"--removable".into()));
            assert!(!root.0.join("boot/efi/EFI/boot/fallback.efi").exists());
            let config = fs::read_to_string(root.0.join("etc/sysconfig/bootloader")).unwrap();
            assert!(config.contains("SECURE_BOOT=yes"));
            assert!(config.contains(if failure.is_some() {
                "UPDATE_NVRAM=no"
            } else {
                "UPDATE_NVRAM=yes"
            }));
            let report: serde_json::Value = serde_json::from_slice(
                &fs::read(root.0.join("var/log/lyra-installer-boot.json")).unwrap(),
            )
            .unwrap();
            assert_eq!(report["fallback"], failure.is_some());
            if failure != Some("mount") {
                assert_eq!(calls.last().unwrap().binary, "umount");
            } else {
                assert!(
                    !calls
                        .iter()
                        .any(|c| c.args.iter().any(|a| a == "efibootmgr"))
                );
            }
        }
    }

    #[test]
    fn unexpected_efi_path_error_is_not_hidden_as_fallback() {
        let (root, op) = fixture(FirmwareMode::Uefi);
        fs::create_dir_all(root.0.join("sys/firmware/efi")).unwrap();
        std::os::unix::fs::symlink(
            "/proc/lyra-no-such-entry",
            root.0.join("sys/firmware/efi/efivars"),
        )
        .unwrap();
        // An unexpected symlink/EEXIST must fail, not be mistaken for firmware
        // unavailability. The real EPERM/EROFS path is covered by the VM.
        assert!(op.perform(&executor(None)).is_err());
    }

    #[test]
    fn bootloader_and_cleanup_failures_never_report_success() {
        for (mode, failure) in [
            (FirmwareMode::Bios, "grub2-install"),
            (FirmwareMode::Uefi, "shim-install"),
            (FirmwareMode::Uefi, "umount"),
        ] {
            let (root, op) = fixture(mode);
            assert!(op.perform(&executor(Some(failure))).is_err());
            assert!(!root.0.join("var/log/lyra-installer-boot.json").exists());
        }
    }

    #[test]
    fn incomplete_or_inconsistent_efi_payload_never_attempts_nvram() {
        for changed in ["missing", "empty", "different"] {
            let (root, op) = fixture(FirmwareMode::Uefi);
            let path = root.0.join("boot/efi/EFI/boot/bootx64.efi");
            match changed {
                "missing" => fs::remove_file(&path).unwrap(),
                "empty" => fs::write(&path, "").unwrap(),
                _ => fs::write(&path, "wrong executable").unwrap(),
            }
            let executor = executor(None);
            assert!(op.perform(&executor).is_err());
            assert!(!executor.calls.borrow().iter().any(|c| c.binary == "mount"));
        }
    }
}
