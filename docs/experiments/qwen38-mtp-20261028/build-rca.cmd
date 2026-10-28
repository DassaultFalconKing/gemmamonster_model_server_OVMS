@echo off
call C:\BuildTools\VC\Auxiliary\Build\vcvars64.bat
if errorlevel 1 exit /b %errorlevel%
set "SDK=C:\gm\qwenmonster\semantic-refit-2026.4-sdk\extracted\openvino_genai_windows_2026.4.0.0rc1_x86_64\runtime"
cl /nologo /EHsc /MD /std:c++17 /I"%SDK%\include" "%~dp0rca_probe.cpp" /Fo"C:\gm\qwenmonster\benchmarks\qwen38-mtp-20261028\rca\rca_probe.obj" /Fe"C:\gm\qwenmonster\benchmarks\qwen38-mtp-20261028\rca\rca_probe.exe" /link /LIBPATH:"%SDK%\lib\intel64\Release" openvino.lib openvino_genai.lib
exit /b %errorlevel%
