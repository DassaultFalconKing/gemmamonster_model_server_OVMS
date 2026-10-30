# Local Wondernutts/Heretic Gemma4-26B-A4B INT4, verified RC4 runtime cohort.
# Default (mem-lean): 2 slots, 4 REST workers, batch1024, dynamic KV, no prefix cache.
# Raise -Seqs 4 / -RestWorkers 8 / -Batch 2048 when you need heavier parallel subagents.
# Tool guidance defaults off for OMP's eval schema. One OVMS only.
# Launch pin: <LEAN_LAUNCH_PIN>
# Full success freeze (DLL+tools+evidence): <FULL_SUCCESS_PIN>
# Full IDENTITY-LOCK.sha256: 8d749326ba76093771db1c4faeb860e99f84c0944a8e06ae6479bc4124d324ae
# Evidence: mem-agent-20261030 + omp-cu-browser-20261030
# ConfigureOnly checks files/settings; it does not run inference.
param(
 [switch]$ConfigureOnly,
 [ValidateRange(1,8)][int]$Seqs=2,
 [ValidateRange(1,8)][int]$RestWorkers=4,
 [ValidateSet(1024,2048,4096,16384)][int]$Batch=1024,
 [ValidateSet('auto','u4')][string]$KvPrecision='auto',
 [switch]$EnablePrefixCaching,
 [switch]$EnableToolGuidedGeneration
)
$ErrorActionPreference='Stop'
$package='<RC4_OVMS_PACKAGE>'
$stackPin='<RUNTIME_COHORT_IDENTITY_LOCK>'
$stackPinSha256='87435d4031b5c3652781dc0f408bfae392a7a2f949fc1e789e6deaac6ed4c221'
$launchPin='<LEAN_LAUNCH_IDENTITY_LOCK>'
$launchPinSha256='fa278704425d17bcb1e12c67a9f32188ef37142f32ac2ad116173b277bc19d52'
$modelPath='<MODEL_ROOT>'
$modelName='gemma26'
function Get-Sha256([string]$Path){
 $stream=[IO.File]::OpenRead($Path);$hash=[Security.Cryptography.SHA256]::Create()
 try{return [BitConverter]::ToString($hash.ComputeHash($stream)).Replace('-','').ToLower()}finally{$stream.Dispose();$hash.Dispose()}
}
foreach($name in @('config.json','openvino_language_model.xml','openvino_language_model.bin','openvino_tokenizer.xml','openvino_tokenizer.bin','openvino_detokenizer.xml','openvino_detokenizer.bin','chat_template.jinja')){
 if(-not(Test-Path (Join-Path $modelPath $name) -PathType Leaf)){throw ('Missing Gemma file: '+$name)}
}
$modelPinPath=Join-Path $PSScriptRoot 'configs\gemma26-model-inputs.json'
$modelPin=Get-Content $modelPinPath -Raw | ConvertFrom-Json
if($modelPin.model_root -ne $modelPath){throw 'Gemma model-input pin points to another model'}
foreach($row in $modelPin.files){if((Get-Sha256 (Join-Path $modelPath $row.path)) -ne $row.sha256){throw ('Gemma launch input changed: '+$row.path)}}
if((Get-Sha256 $stackPin) -ne $stackPinSha256){throw 'Frozen runtime identity lock changed'}
$lock=Get-Content $stackPin -Raw | ConvertFrom-Json
foreach($row in $lock.runtime.files){if((Get-Sha256 (Join-Path $package $row.path)) -ne $row.sha256){throw ('RC4 runtime cohort changed: '+$row.path)}}
if((Get-Sha256 $launchPin) -ne $launchPinSha256){throw 'Frozen Gemma26 lean launch identity lock changed'}
$launchLock=Get-Content $launchPin -Raw | ConvertFrom-Json
if($launchLock.model_root -ne $modelPath){throw 'Lean launch pin points to another model root'}
if($launchLock.launch_defaults.model_name -ne $modelName){throw 'Lean launch pin model_name mismatch'}
# Default parameter pin: overrides are allowed, but the frozen defaults themselves must stay intact in this script.
$d=$launchLock.launch_defaults
if(-not $PSBoundParameters.ContainsKey('Seqs') -and $Seqs -ne [int]$d.seqs){throw 'Lean default Seqs drifted'}
if(-not $PSBoundParameters.ContainsKey('RestWorkers') -and $RestWorkers -ne [int]$d.rest_workers){throw 'Lean default RestWorkers drifted'}
if(-not $PSBoundParameters.ContainsKey('Batch') -and $Batch -ne [int]$d.batch){throw 'Lean default Batch drifted'}
$plugin=@{}
if($KvPrecision -ne 'auto'){$plugin['KV_CACHE_PRECISION']=$KvPrecision}
$pluginJson=$plugin | ConvertTo-Json -Compress
$prefix=if($EnablePrefixCaching){'true'}else{'false'}
$guided=if($EnableToolGuidedGeneration){'true'}else{'false'}
$nativeArgs=@(
 '--rest_port','8137','--rest_bind_address','127.0.0.1','--rest_workers',"$RestWorkers",
 '--log_level','INFO','--model_path',$modelPath,'--model_name',$modelName,
 '--task','text_generation','--pipeline_type','VLM_CB','--target_device','GPU',
 '--plugin_config',$pluginJson,'--tool_parser','gemma4','--reasoning_parser','gemma4',
 '--enable_tool_guided_generation',$guided,'--max_num_seqs',"$Seqs",'--max_num_batched_tokens',"$Batch",
 '--enable_prefix_caching',$prefix,'--dynamic_split_fuse','true','--cache_size','0'
)
$logDir=Join-Path $PSScriptRoot 'logs\gemma26'
[void][IO.Directory]::CreateDirectory($logDir)
$receipt=@{
 model=$modelPath;model_name=$modelName;package=$package;runtime_pin=$stackPin;runtime_pin_sha256=$stackPinSha256
 launch_pin=$launchPin;launch_pin_sha256=$launchPinSha256
 runtime_files_verified=$lock.runtime.files.Count;model_input_pin=$modelPinPath;plugin_config=$plugin
 seqs=$Seqs;rest_workers=$RestWorkers;batch=$Batch;prefix=$prefix;cache_size=0;kv_requested=$KvPrecision;tool_guided_generation=$guided
 pipeline='VLM_CB';device='GPU';tool_parser='gemma4';reasoning_parser='gemma4';native_args=$nativeArgs
 verification='CONFIGURATION_ONLY_NOT_RUNTIME_ACCEPTANCE'
}
$receipt | ConvertTo-Json -Depth 6 | Set-Content -Encoding UTF8 (Join-Path $logDir 'latest-launch-config.json')
if($ConfigureOnly){Write-Output ('PASS: configuration; '+$Seqs+' slots; '+$RestWorkers+' REST workers; '+$lock.runtime.files.Count+' runtime hashes');exit 0}
if(Get-NetTCPConnection -LocalPort 8137 -State Listen -ErrorAction SilentlyContinue){throw 'Port8137 occupied. Stop the other model explicitly; no process was stopped.'}
$env:PYTHONHOME=$null;$env:PYTHONPATH=$null;$env:PYTHONDONTWRITEBYTECODE='1';$env:OPENVINO_LOG_LEVEL=$null
$env:PATH="$package;$env:SystemRoot\System32;$env:SystemRoot"
# Windows PowerShell5.1 native arguments need escaped JSON quotes.
if($PSVersionTable.PSVersion.Major -le 5 -or $PSNativeCommandArgumentPassing -eq 'Legacy'){
 $index=[array]::IndexOf($nativeArgs,'--plugin_config')+1
 $nativeArgs[$index]=$pluginJson.Replace('"','\"')
}
$log=Join-Path $logDir ('gemma26-'+[DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffZ')+'.log')
$nativeArgs+=@('--log_path',$log)
Write-Host ('Model: '+$modelName+' -> '+$modelPath)
Write-Host ('OVMS log: '+$log)
& (Join-Path $package 'ovms.exe') @nativeArgs
exit $LASTEXITCODE
