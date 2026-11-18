# -*- mode: python ; coding: utf-8 -*-
# Build with:  pyinstaller balance_gui.spec   (or just use build.bat / build.sh)
import sys

a = Analysis(
    ['balance_gui.pyw'],
    pathex=[], binaries=[], datas=[], hiddenimports=[],
    hookspath=[], runtime_hooks=[], excludes=[], noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data)

if sys.platform == 'darwin':
    # macOS: onedir inside a proper .app bundle (onefile .apps are deprecated)
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True,
              name='EquationBalancer', console=False, upx=False)
    coll = COLLECT(exe, a.binaries, a.datas, name='EquationBalancer', upx=False)
    app = BUNDLE(
        coll,
        name='EquationBalancer.app',
        icon='icon.icns',
        bundle_identifier='com.lukas.equationbalancer',
        info_plist={'NSHighResolutionCapable': 'True',
                    'CFBundleDisplayName': 'Equation Balancer'},
    )
else:
    # Windows/Linux: single exe
    exe = EXE(pyz, a.scripts, a.binaries, a.datas, [],
              name='EquationBalancer', console=False, upx=False,
              icon='icon.ico' if sys.platform.startswith('win') else None)
