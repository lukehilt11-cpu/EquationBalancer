# Equation Balancer

A small tkinter app that balances chemical equations (exact fraction math, no dependencies).
Type something like `Fe + O2 -> Fe2O3` and get `4Fe + 3O2 → 2Fe2O3`.

## Folder layout

```
EquationBalancer/
├── .github/workflows/release.yml   # CI: build, release, deploy site
├── site/                           # GitHub Pages download page
│   ├── index.html
│   └── icon.png
├── balance_gui.pyw                 # the app
├── balance_gui.spec                # PyInstaller config
├── installer.iss                   # Inno Setup script (Windows installer)
├── icon.ico / icon.icns            # Windows / macOS icons
├── make_icon.py                    # regenerates the icons (needs Pillow)
├── build.bat                       # local Windows build + installer
├── build.sh                        # local macOS build + install
└── .gitignore
```

## Run it directly

```
python balance_gui.pyw
```

## Build locally

Requires `pip install pyinstaller`. PyInstaller can't cross-compile, so build on the OS you want.

**Windows**: also install [Inno Setup 6](https://jrsoftware.org/isdl.php), then run `build.bat`.
It builds silently, moves the exe into `app\`, deletes `build\` and `dist\`, compiles
`installer\EquationBalancer_Setup.exe`, and launches it. The installer adds a Start Menu entry
and an Apps & features entry with an uninstaller.

**macOS**: run `chmod +x build.sh` once, then `./build.sh` (or `./build.sh --no-install` to skip
installing). It builds the `.app` into `out/`, cleans up `build/` and `dist/`, ad-hoc signs it, and
copies it to `/Applications` (or `~/Applications` if that isn't writable).

## Releasing with GitHub Actions

The workflow builds Windows (`windows-latest`) and macOS Apple Silicon (`macos-14`), creates a
GitHub Release with `EquationBalancer_Setup.exe` and `EquationBalancer-macOS-arm64.dmg` plus
auto-generated notes, then redeploys the GitHub Pages site.

**Cut a release**

```
git tag v1.0.0
git push origin v1.0.0
```

Or: **Actions → Build, Release & Deploy Site → Run workflow** and enter a version (no leading `v`).

## One-time GitHub setup (Pages)

1. Push this repo to GitHub.
2. **Settings → Pages → Build and deployment → Source:** choose **GitHub Actions**.
3. **Settings → Environments → github-pages → Deployment branches and tags:** add a tag rule
   `v*`. Without this, tag-triggered runs fail with "not allowed to deploy to github-pages due to
   environment protection rules". This is the step that's easy to forget.
4. If the release step fails with a permissions error: **Settings → Actions → General → Workflow
   permissions → Read and write**.
5. Run a release (see above). The site appears at `https://<username>.github.io/<repo>/` within a
   minute or two of the workflow finishing.

Private repos need a paid GitHub plan for Pages. Releases work either way.

## Notes

- Builds are unsigned. Windows: SmartScreen → *More info* → *Run anyway*. macOS: right-click the
  app → *Open* the first time (or `xattr -dr com.apple.quarantine /Applications/EquationBalancer.app`).
- To change the version shown by local Windows builds, edit the default in `installer.iss`;
  CI sets it from the tag automatically.
- To change the icon, edit `make_icon.py`, run it, and copy the new `icon.ico` / `icon.icns`
  (and a 256px `site/icon.png`) into place.
- If you change the app's file name, update the `Analysis(...)` line in `balance_gui.spec`.
