"""Reuse the committed full regression fixture, without replacing the RPM payload."""
import pathlib,shutil,sys
baseline=pathlib.Path(sys.argv[1]).resolve()
out=pathlib.Path(sys.argv[2]).resolve();out.mkdir(exist_ok=True)
for file in baseline.iterdir():
 if file.suffix in ['.py','.c','.cil','.js'] or file.name=='org.gnome.Shell.Screencast':shutil.copy2(file,out/file.name)
p=out/'exercise.py';text=p.read_text()
old="    # Exact SUSE source plus upstream success-response fix; original is snapshotted.\n    shutil.copyfile('/root/shortcuts-portal-build/src/xdg-desktop-portal-gnome','/usr/libexec/xdg-desktop-portal-gnome')"
new="""    # Qualify the installed RPM, not the earlier uninstalled build-tree binary.
    expected=json.loads(P('/root/portal-rpm-expected.json').read_text())
    assert run(['rpm','-q','xdg-desktop-portal-gnome']).strip()==expected['nevra']
    assert run(['rpm','-V','xdg-desktop-portal-gnome'])==''
    observed=hashlib.sha256(P('/usr/libexec/xdg-desktop-portal-gnome').read_bytes()).hexdigest()
    assert observed==expected['binary_sha256']
    records.append(dict(fixture='installed-portal-rpm',**expected))"""
assert text.count(old)==1
p.write_text(text.replace(old,new))
print(out)
