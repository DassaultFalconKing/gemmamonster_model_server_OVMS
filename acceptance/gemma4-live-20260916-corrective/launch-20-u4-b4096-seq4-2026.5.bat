@echo off
REM CORRECTIVE LIVE ACCEPTANCE - Profile 20-u4-b4096-seq4-2026.5
REM MANDATORY binary: dist 2026.5 freeze package. NEVER C:\llm\ovms\ovms.exe
REM KV route: U4 ONLY via --plugin_config (dedicated --kv_cache_precision flag documents u8/empty only, no u4). Never both.
set OVMS_DIR=C:\git\gemma4-upstream-refit-clean-20260915\dist\windows\ovms
set PYTHONHOME=C:\git\gemma4-upstream-refit-clean-20260915\dist\windows\ovms\python
set "PATH=C:\git\gemma4-upstream-refit-clean-20260915\dist\windows\ovms;C:\git\gemma4-upstream-refit-clean-20260915\dist\windows\ovms\python;C:\git\gemma4-upstream-refit-clean-20260915\dist\windows\ovms\python\Scripts;%PATH%"
set ESPEAK_DATA_PATH=C:\git\gemma4-upstream-refit-clean-20260915\dist\windows\ovms\espeak-ng-data
"%OVMS_DIR%\ovms.exe" --rest_port 18091 --rest_bind_address 127.0.0.1 --model_path "C:\llm\models\OpenVINO\Wondernutts\gemma-4-26B-A4B-it-qat-q4_0-unquantized-uncensored-heretic-int4-ov" --model_name gemma4-26-heretic --target_device GPU --pipeline_type VLM_CB --reasoning_parser gemma4 --tool_parser gemma4 --enable_tool_guided_generation true --dynamic_split_fuse true --cache_size 0 --cache_dir "C:\llm\cache\gemmamonster" --log_level INFO --plugin_config "{\"KV_CACHE_PRECISION\":\"u4\"}" --enable_prefix_caching true --max_num_batched_tokens 4096 --max_num_seqs 4 >> "C:\git\gemma4-upstream-refit-clean-20260915\acceptance\gemma4-live-20260916-corrective\logs\ovms-20-u4-b4096-seq4-2026.5.log" 2>&1
