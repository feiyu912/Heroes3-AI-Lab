param([ValidateRange(1,512)][int]$Updates = 64)
$ErrorActionPreference = 'Stop'
$labRoot = $PSScriptRoot
$labStatePath = Join-Path $labRoot 'research\training-state.json'
$labState = Get-Content -LiteralPath $labStatePath -Raw | ConvertFrom-Json
$labRun = [DateTime]::Now.ToString('yyyyMMdd-HHmmss')
$labResult = "/mnt/g/Heroes3-AI-Lab/research/training-$labRun.json"
$labEvaluation = "/mnt/g/Heroes3-AI-Lab/research/training-$labRun-evaluation.json"
$labCudaCommand = 'LAB_PYTHON=/root/heroes3-ai-lab/gpu-venv/bin/python'
$labPolicy = 'model'
if ($labState.policy) { $labPolicy = $labState.policy }
$labResumeArgs = @()
if ($labState.resume_available -ne $false) { $labResumeArgs = @('--resume') }
$labOpponents = @('BattleAI')
if ($labState.opponents) { $labOpponents = @($labState.opponents) }
$labTrainingArgs = @()
if ($labState.training_scenarios) { $labTrainingArgs += @('--scenario-file', $labState.training_scenarios) }
if ($null -ne $labState.training_config.shaping) { $labTrainingArgs += @('--shaping', $labState.training_config.shaping) }
if ($null -ne $labState.training_config.step_cost) { $labTrainingArgs += @('--step-cost', $labState.training_config.step_cost) }
if ($labState.training_config.native_opponent_device) { $labTrainingArgs += @('--native-opponent-device', $labState.training_config.native_opponent_device) }
if ($labState.trainer_family -eq 'graph' -or $labPolicy -eq 'recovered') {
    foreach ($option in @('gamma','gae_lambda')) {
        if ($null -ne $labState.training_config.$option) { $labTrainingArgs += @('--' + $option.Replace('_','-'), $labState.training_config.$option) }
    }
}
if ($labState.trainer_family -eq 'graph') {
    if ($labState.training_config.no_auto_microbatch) { $labTrainingArgs += @('--no-auto-microbatch') }
    foreach ($option in @('microbatch','epochs','learning_rate','head_learning_rate','rotate_every','entropy_coef')) {
        if ($null -ne $labState.training_config.$option) { $labTrainingArgs += @('--' + $option.Replace('_','-'), $labState.training_config.$option) }
    }
    & wsl -d Ubuntu-22.04 -- env $labCudaCommand LAB_STAGED_BOOT=1 bash /mnt/g/Heroes3-AI-Lab/research/run-lab.sh /mnt/g/Heroes3-AI-Lab/research/train-graph-finetune.py --mode $labState.finetuning_mode --workers $labState.workers --updates $Updates @labResumeArgs --checkpoint $labState.checkpoint --seed $labState.seed --rollout $labState.rollout --opponents @labOpponents @labTrainingArgs --output $labResult
} elseif ($labPolicy -eq 'recovered') {
    if ($labState.training_config.balanced_configs) { $labTrainingArgs += @('--balanced-configs') }
    foreach ($option in @('learning_rate','entropy_coef')) {
        if ($null -ne $labState.training_config.$option) { $labTrainingArgs += @('--' + $option.Replace('_','-'), $labState.training_config.$option) }
    }
    & wsl -d Ubuntu-22.04 -- env $labCudaCommand LAB_STAGED_BOOT=1 bash /mnt/g/Heroes3-AI-Lab/research/run-lab.sh /mnt/g/Heroes3-AI-Lab/research/train-recovered-heads.py --workers $labState.workers --updates $Updates @labResumeArgs --checkpoint $labState.checkpoint --seed $labState.seed --rollout $labState.rollout --opponents @labOpponents @labTrainingArgs --output $labResult
} else {
    & wsl -d Ubuntu-22.04 -- env $labCudaCommand LAB_STAGED_BOOT=1 bash /mnt/g/Heroes3-AI-Lab/research/run-lab.sh /mnt/g/Heroes3-AI-Lab/research/train-ppo.py --workers $labState.workers --updates $Updates @labResumeArgs --checkpoint $labState.checkpoint --validation-report $labState.validation_report --scenarios $labState.scenarios --seed $labState.seed --rollout $labState.rollout --batch-size $labState.batch_size --epochs $labState.epochs --rotate-every $labState.rotate_every --inference-device cuda --training-device cuda --cache-next-value --opponents @labOpponents --output $labResult
}
if ($LASTEXITCODE -ne 0) { throw 'Training failed; the last validated checkpoint is preserved.' }
$labResultWindows = Join-Path $labRoot "research\training-$labRun.json"
$labCompleted = Get-Content -LiteralPath $labResultWindows -Raw | ConvertFrom-Json
if (-not $labCompleted.completed) { throw 'Training did not complete.' }
& wsl -d Ubuntu-22.04 -- python3 /mnt/g/Heroes3-AI-Lab/research/evaluate-battles.py --checkpoint $labCompleted.checkpoint --policies $labPolicy --workers 12 --scenario-file $labState.scenarios --scenarios 20 21 22 23 24 25 --seeds 4 --output $labEvaluation
if ($LASTEXITCODE -ne 0) { throw 'Battle validation failed; the prior validated checkpoint is preserved.' }
$labEvalWindows = Join-Path $labRoot "research\training-$labRun-evaluation.json"
$labValidated = Get-Content -LiteralPath $labEvalWindows -Raw | ConvertFrom-Json
if ($labValidated.summary[0].truncated -ne 0 -or $labValidated.summary[0].invalid_actions -ne 0) {
    throw 'Battle validation found truncated battles or illegal actions; the prior checkpoint is preserved.'
}
$labUpdatedState = [pscustomobject]@{
    workers = $labState.workers
    policy = $labPolicy
    trainer_family = $labState.trainer_family
    finetuning_mode = $labState.finetuning_mode
    training_config = $labCompleted.config
    training_scenarios = $labState.training_scenarios
    resume_available = $true
    opponents = $labOpponents
    checkpoint = $labCompleted.checkpoint
    validation_report = $labEvaluation
    training_report = $labResult
    completed_updates = $labCompleted.resumed_from_updates + $labCompleted.records.Count
    seed = $labState.seed
    scenarios = $labState.scenarios
    rollout = $labState.rollout
    batch_size = $labState.batch_size
    epochs = $labState.epochs
    rotate_every = $labState.rotate_every
    inference_device = 'cuda'
    training_device = 'cuda'
    note = 'Latest runnable checkpoint; this does not mean best competitive policy.'
}
[System.IO.File]::WriteAllText($labStatePath, ($labUpdatedState | ConvertTo-Json -Depth 8), [System.Text.UTF8Encoding]::new($false))
Write-Host "Training and validation completed. Progress saved in $labStatePath"
