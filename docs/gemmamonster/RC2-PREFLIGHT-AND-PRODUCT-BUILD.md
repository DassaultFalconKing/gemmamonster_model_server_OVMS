# Gemmamonster 2026.4 RC2 product build

`ovms_test.exe` is a test-only Bazel target. It is not part of the RC2 product
artifact and must not be built by the normal candidate build. Test compilation
is an explicit diagnostic operation only (`--with_tests`).

Run the source and toolchain preflight first:

```powershell
rtk proxy pwsh -NoProfile -File .\scripts\gemmamonster\audit-stable-refit.ps1 -RepoRoot $PWD
```

Build the RC2 product candidate without tests:

```powershell
rtk proxy pwsh -NoProfile -File .\scripts\gemmamonster\build-stable-candidate.ps1 `
  -RepoRoot $PWD `
  -RuntimeProfile maintainer-rc2 `
  -Label rc2-product `
  -WithoutTests
```

The product executable is `bazel-bin\src\ovms.exe`. Do not use the presence
or absence of `bazel-bin\src\ovms_test.exe` as an RC2 build result.
