#!/usr/bin/env python3
"""Install real BIOS/UEFI boot files on disposable GPT/Btrfs disks and boot them.

No ISO qualification: payload is a minimal public boot-tool fixture, not GNOME.
The second QEMU invocation boots the disk through firmware, without -kernel.
"""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

REPO = Path(__file__).resolve().parents[1]
TEST = 'service::operations::firmware_tests::native_firmware_install_and_prepare_boot'

def validate_log(case, phase, content):
    marker = 'LYRA_BOOT_INSTALL_PASS' if phase == 'install' else 'LYRA_BOOT_DISK_PASS'
    if marker not in content:
        raise ValueError('missing success marker')
    if phase == 'install' and 'LYRA_BOOT_TEST_EXIT=0' not in content:
        raise ValueError('installer test did not succeed')
    expected = {'bios': 'bios', 'uefi': 'uefi-nvram',
                'uefi-no-nvram': 'uefi-fallback-no-variables', 'secure-boot': 'uefi-nvram'}[case]
    if f'"mode": "{expected}"' not in content:
        raise ValueError('unexpected installed firmware mode')
    if phase == 'boot':
        if ('LYRA_BOOT_BIOS' if case == 'bios' else 'LYRA_BOOT_UEFI') not in content:
            raise ValueError('unexpected boot firmware')
        if case == 'secure-boot' and 'secureboot: Secure boot enabled' not in content:
            raise ValueError('Secure Boot was not enabled in the booted kernel')

def main():
    os.environ['PATH'] = os.environ.get('PATH', '') + ':/usr/sbin:/sbin'
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kernel', type=Path, required=True)
    parser.add_argument('--modules-dir', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--case', choices=['bios', 'uefi', 'uefi-no-nvram', 'secure-boot'], action='append')
    args = parser.parse_args()
    if not args.kernel.is_file() or not args.modules_dir.is_dir():
        parser.error('readable kernel and matching modules directory required')
    args.output_dir.mkdir(parents=True, exist_ok=True)
    built = subprocess.run(['cargo', 'test', '--offline', '--locked', '--no-run', '-p', 'lyra-installer-core',
                            '--lib', '--message-format=json'], cwd=REPO / 'installer', capture_output=True, text=True, check=True)
    executable, = [Path(row['executable']) for row in map(json.loads, built.stdout.splitlines())
                    if row.get('executable') and row['target']['name'] == 'lyra_installer_core']
    with tempfile.TemporaryDirectory(prefix='lyra-installer-boot-') as temporary:
        base = Path(temporary)
        root = base / 'root'
        for name in ['usr/bin', 'dev', 'proc', 'sys', 'tmp', 'run', 'etc/default', 'boot', 'var/log']:
            (root / name).mkdir(parents=True)
        for name, target in [('bin', 'usr/bin'), ('sbin', 'usr/bin'), ('usr/sbin', 'bin')]:
            (root / name).symlink_to(target)
        copied = set()
        def copy(source, destination):
            source = Path(source); dest = root / str(destination).lstrip('/')
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                dest.chmod(dest.stat().st_mode | 0o200)
            shutil.copyfile(source, dest)
            dest.chmod(source.stat().st_mode & 0o777)
        def binary(source, destination):
            source = Path(source)
            copy(source, destination)
            if source in copied: return
            copied.add(source)
            with source.open('rb') as stream:
                if stream.read(4) != b'\x7fELF': return
            linked = subprocess.check_output(['ldd', str(source)], text=True)
            for library in re.findall(r'(?:=>\s+|^\s*)(/[^\s]+)', linked, re.M):
                copy(library, library)
                if '/glibc-hwcaps/' in library:
                    dynamic = subprocess.check_output(['readelf', '-d', library], text=True)
                    soname = re.search(r'\(SONAME\).*\[([^]]+)\]', dynamic)
                    if soname:
                        baseline = Path(library.split('/glibc-hwcaps/')[0]) / soname[1]
                        copy(baseline, baseline)
        tools = ['bash', 'mount', 'umount', 'mkdir', 'modprobe', 'lsblk', 'systemctl', 'sgdisk', 'wipefs',
                 'mkfs.btrfs', 'mkfs.vfat', 'mkswap', 'btrfs', 'chattr', 'blkid', 'chroot', 'cp', 'sync',
                 'grub2-install', 'grub2-bios-setup', 'grub2-probe', 'grub2-mkrelpath', 'grub2-mkimage',
                 'grub2-editenv', 'shim-install', 'efibootmgr', 'uname', 'tr', 'cut', 'grep', 'sed',
                 'cat', 'rm', 'mv', 'ln', 'readlink', 'dirname', 'basename', 'stat', 'awk', 'iconv',
                 'head', 'tail', 'find', 'sort', 'touch', 'chmod', 'sleep', 'wc', 'df', 'mountpoint']
        for name in tools:
            source = shutil.which(name)
            if not source: parser.error('missing fixture tool: ' + name)
            binary(source, '/usr/bin/' + name)
        (root / 'usr/bin/sh').symlink_to('bash')
        (root / 'usr/bin/fgrep').symlink_to('grep')
        binary(executable, '/test-installer')
        for source in ['/usr/share/grub2/i386-pc', '/usr/share/grub2/x86_64-efi', '/usr/share/efi/x86_64']:
            shutil.copytree(source, root / source.lstrip('/'), symlinks=True)
        for optional in ['/usr/share/grub2/unicode.pf2', '/usr/share/zoneinfo/UTC', '/etc/ld.so.cache']:
            if Path(optional).is_file(): copy(optional, optional)
        # Only public module metadata and required module dependency closures.
        module_root = root / 'usr/lib/modules' / args.modules_dir.name
        module_root.mkdir(parents=True)
        (root / 'lib').mkdir(exist_ok=True)
        (root / 'lib/modules').symlink_to('../usr/lib/modules')
        for source in args.modules_dir.glob('modules.*'): shutil.copyfile(source, module_root / source.name)
        for name in ['virtio_blk', 'virtio_pci', 'btrfs', 'vfat', 'nls_cp437', 'nls_iso8859_1', 'efivarfs']:
            dependencies = subprocess.check_output(['modprobe', '--show-depends', '-S', args.modules_dir.name, name], text=True)
            for line in dependencies.splitlines():
                if line.startswith('insmod '):
                    source = Path(line.split()[1]); relative = source.resolve().relative_to(args.modules_dir.resolve())
                    target = module_root / relative; target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(source, target)
        (root / 'etc/os-release').write_text('ID=opensuse-leap\nNAME="openSUSE Leap"\nVERSION_ID=16.1\n')
        (root / 'etc/default/grub').write_text('GRUB_DISTRIBUTOR="Lyra OS"\n')
        def archive(destination):
            files = b'\0'.join(str(path.relative_to(root)).encode() for path in root.rglob('*')) + b'\0'
            packed = subprocess.run(['cpio', '--null', '-o', '-H', 'newc', '--owner=0:0', '--quiet'],
                                    input=files, cwd=root, capture_output=True, check=True)
            with gzip.open(destination, 'wb', compresslevel=1) as stream: stream.write(packed.stdout)
        common = '''#!/bin/bash
export PATH=/usr/bin:/bin
mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t devtmpfs devtmpfs /dev
modprobe virtio_pci
modprobe virtio_blk
modprobe btrfs
modprobe vfat
'''
        (root / 'init').write_text(common + '''
mkdir -p /installed
mount -t btrfs -o ro,subvol=@ /dev/vda2 /installed || exit 1
if [ "$(cat /installed/lyra-boot-marker)" = installer-firmware-valid ]; then
    echo LYRA_BOOT_DISK_PASS
    cat /installed/var/log/lyra-installer-boot.json
    if [ -d /sys/firmware/efi ]; then echo LYRA_BOOT_UEFI; else echo LYRA_BOOT_BIOS; fi
fi
umount /installed
systemctl --force --force poweroff
'''); (root / 'init').chmod(0o755)
        boot_initrd = base / 'boot-initrd.gz'; archive(boot_initrd)
        # Copy only tools/public libraries; never /proc, /dev or host state.
        payload = base / 'payload'; payload.mkdir()
        for name in ['usr', 'bin', 'sbin', 'lib', 'lib64', 'etc']:
            source = root / name
            if source.is_symlink(): (payload / name).symlink_to(source.readlink())
            elif source.exists(): shutil.copytree(source, payload / name, symlinks=True)
        (payload / 'boot').mkdir(); shutil.copyfile(args.kernel, payload / 'boot/vmlinuz-test')
        shutil.copyfile(boot_initrd, payload / 'boot/initrd-test')
        shutil.move(payload, root / 'payload')
        (root / 'init').write_text(common + f'''
mount -t tmpfs tmpfs /run
mount -t efivarfs efivarfs /sys/firmware/efi/efivars 2>/dev/null || true
/test-installer --ignored --exact {TEST} --nocapture --test-threads=1
result=$?
echo LYRA_BOOT_TEST_EXIT=$result
sync
systemctl --force --force poweroff
'''); (root / 'init').chmod(0o755)
        install_initrd = base / 'install-initrd.gz'; archive(install_initrd)
        results = []
        for case in args.case or ['bios', 'uefi', 'uefi-no-nvram']:
            print('Running ' + case, flush=True)
            disk = base / (case + '.raw')
            with disk.open('wb') as stream: stream.truncate(40 * 1024 ** 3)
            firmware = []
            if case != 'bios':
                prefix = 'ovmf-x86_64-suse-4m' if case == 'secure-boot' else 'ovmf-x86_64-4m'
                variables = base / (case + '-vars.bin')
                shutil.copyfile('/usr/share/qemu/' + prefix + '-vars.bin', variables)
                firmware = ['-drive', f'if=pflash,format=raw,unit=0,readonly=on,file=/usr/share/qemu/{prefix}-code.bin',
                            '-drive', f'if=pflash,format=raw,unit=1,file={variables}']
            base_command = ['qemu-system-x86_64', '-accel', 'kvm', '-accel', 'tcg', '-machine', 'q35',
                '-cpu', 'Nehalem', '-smp', '2', '-m', '2048', *firmware,
                '-drive', f'file={disk},format=raw,if=none,id=target',
                '-device', 'virtio-blk-pci,drive=target,serial=lyra-boot-test-only',
                '-display', 'none', '-serial', 'stdio', '-monitor', 'none', '-nic', 'none', '-no-reboot']
            for phase in ['install', 'boot']:
                command = base_command.copy()
                if phase == 'install':
                    append = 'rdinit=/init console=ttyS0 panic=1 lyra.boot-test=install'
                    if case == 'uefi-no-nvram': append += ' efi=noruntime'
                    command += ['-kernel', str(args.kernel.resolve()), '-initrd', str(install_initrd), '-append', append]
                log_path = args.output_dir / f'{case}-{phase}.log'
                with log_path.open('w') as log:
                    result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=300)
                content = log_path.read_text(errors='replace')
                try:
                    validate_log(case, phase, content)
                    if result.returncode:
                        raise ValueError('QEMU exited unsuccessfully')
                except ValueError as error:
                    print(content[-10000:]); raise SystemExit(f'FAIL: {log_path}: {error}')
                results.append({'case': case, 'phase': phase, 'status': 'passed', 'log_sha256': hashlib.sha256(log_path.read_bytes()).hexdigest()})
                print(f'PASS {case} {phase}', flush=True)
        (args.output_dir / 'result.json').write_text(json.dumps({'schema': 1, 'status': 'passed', 'checks': results,
            'limits': 'Minimal boot-tool fixture, not a full ISO or GNOME session; firmware boot uses installed disk, no direct kernel.'}, indent=2) + '\n')
    print('PASS: disposable VMs/disks/initrds removed; logs retained', flush=True)

if __name__ == '__main__': main()
