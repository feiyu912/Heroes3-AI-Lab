## plan /mnt/g/Heroes3-AI-Lab/experiments/battle-terminal-credit-native-20261023/APPROVED_PLAN.md SHA256=b1abd6f84e1f4b23fc3338be3f4c625d1514ba2d73a5436e96ce51983842e05b
7: Actual TRAIN audit found MMAI episodes averaging27.6–28.4 steps versus BattleAI18.6; phase-close unfinished rows22.8–24.3% versus13.4–14.2%. Both still have valid bootstrap. The question is whether observing the continuing episode's real terminal before constructing the final admitted rollout's targets improves learning. This is not a diagnosis that bootstrap was invalid or that missing terminals caused the earlier result.
8: 
9: Both arms start the same full control60 checkpoint: SHA`443863dd26ea0daaed17cd01ab3dd44a6a16544efac73c96a89839f5b72c0e20`, completed_update60, environment_steps30720, cumulative actual_Adam_steps7680. Restore full role models, ordered named Adam states/hyperparameters and Python/NumPy/Torch CPU/CUDA RNG; never weights-only. CPU exact restoration has actually passed in `cpu-01/AUDIT.json`; CUDA remains unexecuted here. Both arms begin a fresh symmetric native epoch and never restore in-flight games.
10: 
11: Unchanged: last-graph mask; headsLR1e-5/bodyLR1e-6; terminal±1 and .5 potential, gamma1, lambda.95, step_cost0; PPO2epochs/microbatch8/clip.2/entropy.005/critic.5/max_gradnorm.5/targetKL.02;16workers; actual native BattleAI and original public CPU ONNX MMAI. No expert/DEV labels.
12: 
13: ## Exact observation/admission budget
14: 
15: Use the existing seed2026102016 registered60-TRAIN-map curriculum, phases0..3 only:16 unique TRAIN cases, each with both roles/opponents,64 admitted transitions per cell. Each phase has4 cases×2roles×2opponents=16 slots. Native seed epoch:2026106800+phase*1000+slot, identical between arms. New independent drain-sampling generator seed2026106980+phase*16+slot; it must not advance the learner's Python/NumPy/Torch CPU/CUDA RNG. A generator draws every suffix action, and all actual outcomes/requests remain recorded.
54: Extra64-step observation budgets are exactly symmetric; trajectories, realized episodes, first-terminal distances, wall time and NPC action counts may diverge after targets change. Report them; they are not equalized by claiming equal compute time. Conditional terminal-within-cap eligibility can depend on policy and should be reported by role/opponent/family. It is a bounded target-extension algorithm, not an unbiased estimate of all eventual returns. Cap fallback includes both wins and losses without outcome selection.
55: 
56: The unchanged PPO implementation may early-stop at targetKL.02. Therefore exact planned128 actual Adam calls/update cannot be guaranteed before real execution. Do not disable KL stopping or add extra updates/rows to force a matched budget: that would change another factor. Before advancing paired phases, compare actual counters. If either arm deviates from planned counts or arms differ, retain the learned outputs and raw evidence, stop the registered matched-budget experiment, and report **optimizer-budget mismatch**, not a game defeat or fabricated exact fairness. An unmatched result is descriptive only and cannot certify this exact-budget comparison. No retries/reseeding to obtain a passing arm.
57: 
58: Native request hard timeout90s; suffix phase wall cap300s; normal64 suffix-step cap. A time/resource error is an engineering stop with raw pending evidence, not a scored loss. The64-step no-terminal cap is a normal algorithm case with original-bootstrap fallback and does not trigger reseeding. Prephase availableRAM>4GiB/swap<256MiB/disk>10GiB; original16-worker staged boot and postupdate>2GiB reserve. Acquire GPU→pool, single learner, serialize arms. Collect suffix CPU payloads without retaining inference graphs; verify available memory before the first actual training stage. This plan starts no process or lease.
59: 
60: ## Final bounded evaluation, only after final68
61: 
62: Register one96-unique-game DEV set: shared control60 parent32 + control-prefix-only final6832 + candidate-extension final6832; cases192..199, both roles, actual BattleAI/original public CPU ONNX MMAI, seedbase2026107600+case_index*100. No interim DEV or checkpoint selection. Use the repaired pending→parent-finalization recorder and full per-step graph/probability/action/native returns. Independently replay all scored games and calculate paired flips/loss efficiency. The existing final test set is not used. Small DEV results remain developmental evidence; no automatic promotion or95% claim.

## learner /mnt/g/Heroes3-AI-Lab/experiments/battle-terminal-credit-native-20261023/learner_impl.py SHA256=060ec0961790bd8a755b8b994ed1315fbfa3f1f27b095134b39f83d766e58478
35:     out=[]
36:     for row in rows:
37:         assert restore.sha(LAB/'data/vcmi/Maps'/row['map'])==row['map_sha256'] and row['scenario_index']<192
38:         role=row['role'];opponent=row['opponent'];out.append(dict(map=row['map'],role=role,opponent=opponent,initial_reset_once=True,
39:             opponent_model='DATA/MMAI/models/lab-upstream-'+('defender' if role=='attacker' else 'attacker')+'.onnx' if opponent=='MMAI_MODEL' else None,
40:             seed=row['seed'],feature_version='upstream-graph-v15',step_cost=0.,family=row['family'],TRAIN_scenario_index=row['scenario_index'],timeout=90,
41:             worker_root=str(LAB/'workers'/run/f'{phase}-{row["slot"]}')))
42:     return out
87:     registered=json.loads((HERE/'REGISTERED_CURRICULUM.json').read_text());records=[];vector=None;latest=str(a.checkpoint);total_suffix=1024*a.phase_start;total_native=2048*a.phase_start;admitted=1024*a.phase_start
88:     report=dict(passed=False,qualified=False,records=records,arm=a.arm,optimizer_steps_before=counter['steps'],inherited_Adam_steps=7680,qualify_only=a.qualify)
89:     try:
90:         for phase in range(a.phase_start,a.phase_stop):
91:             verify(a.freeze);resources=resource();folder=a.out/f'phase-{phase}';folder.mkdir();cfg=configs(registered['phases'][phase],a.out.name,phase);vector=recorded_vector.VectorEnv(cfg,executable=str(LAB/'venv/bin/python'));current=[x['features'] for x in vector.states]
92:             assert all(not x['torch_imported'] for x in vector.states),'Spawned native workers unexpectedly loaded Torch'
93:             atomic_json(folder/'WORKERS.json',dict(configs=cfg,worker_PIDs=[x['pid'] for x in vector.states],torch_imported=[x['torch_imported'] for x in vector.states]))
94:             if phase==a.phase_start:

## worker /mnt/g/Heroes3-AI-Lab/experiments/battle-terminal-credit-native-20261023/recorded_vector.py SHA256=f6395c1b083255c2a8e367024403a6627bb3ebc0cc2cbfe3792cea879110637f
12: def environment_worker(connection, config):
13:     worker_root = config['worker_root']
14:     try:
15:         subprocess.run([sys.executable, '/mnt/g/Heroes3-AI-Lab/research/prepare-worker.py', worker_root],
16:                        check=True, stdout=subprocess.DEVNULL)
17:         os.environ['XDG_DATA_HOME'] = worker_root + '/data'
18:         os.environ['LAB_BATTLEAI_TEACHER'] = '0'
19:         os.environ['LAB_RANDOM_POLICY_SEED'] = str(config['seed'] + 100000)
20:         from battle_features import features, linked_features
27:         spec = importlib.util.spec_from_file_location('lab_env', Path('/mnt/g/Heroes3-AI-Lab/research/lab-env.py'))
28:         lab = importlib.util.module_from_spec(spec)
29:         spec.loader.exec_module(lab)
30:         if config.get('initial_reset_once') and config.get('opponent')!='MMAI_GPU':
31:             # Native VcmiEnv.__init__ resets immediately after connect. For the
46:         env = lab.make_env(config['map'], config['seed'], config['role'], opponent='OTHER_ENV' if config.get('opponent')=='MMAI_GPU' else config.get('opponent', 'BattleAI'),
47:                            max_steps=config.get('max_steps', 400), opponent_model=config.get('opponent_model'),timeout=config.get('timeout',600))
48:         if config.get('opponent')=='MMAI_GPU':
49:             from gpu_opponent import start_opponent
50:             start_opponent(env,config['opponent_connection'])
51:         if config.get('opponent')=='MMAI_GPU' or config.get('initial_reset_once'):

## env_factory /mnt/g/Heroes3-AI-Lab/research/lab-env.py SHA256=bdb325ee5cad7d5df952a35f7d357ef9f3bad4d624fe5bd2233b46a11f0b0dee
1: """Shared fixed-rule v15 environment settings for lab experiments."""
2: from vcmi_gym.envs.v15.vcmi_env import VcmiEnv
3: 
4: 
5: def make_env(mapname, seed, role, opponent='BattleAI', max_steps=400, opponent_model=None, timeout=60):
6:     return VcmiEnv(mapname=mapname, seed=seed, role=role, opponent=opponent,
7:                    opponent_model=opponent_model, max_steps=max_steps, render_mode='ansi', random_heroes=0,
8:                    random_obstacles=0, town_chance=0, warmachine_chance=0,
9:                    random_armies=False, mana_min=0, mana_max=0,
10:                    user_timeout=timeout, vcmi_timeout=timeout, boot_timeout=timeout,
11:                    vcmi_loglevel_global='error', vcmi_loglevel_ai='error')

## prepare /mnt/g/Heroes3-AI-Lab/research/prepare-worker.py SHA256=ca31495945969ea4a589ae6fa2479e894e7500d70255de36d551cee59f7aec9c
5: root = Path('/root/heroes3-ai-lab')
6: worker = Path(sys.argv[1]).resolve()
7: assert worker.is_relative_to(root / 'workers'), 'Worker must stay in the lab workers directory'
8: data = worker / 'data/vcmi'
9: config = data / 'config'
10: config.mkdir(parents=True, exist_ok=True)
11: for name in ['Data', 'Maps', 'Mods']:
12:     link = data / name
13:     target = root / 'data/vcmi' / name
14:     if not link.exists():
15:         link.symlink_to(target, target_is_directory=True)
16:     assert link.resolve() == target.resolve()
17: (config / 'modSettings.json').write_text(json.dumps({
18:     'activePreset': 'default',

## upstream_manifest /mnt/g/Heroes3-AI-Lab/research/upstream-model-manifest.json SHA256=e95465f44f0b8f626e7fcb42e42f0b88a4323d95d745f351c53bae179d71c195
1: [
2:   {
3:     "role": "attacker",
4:     "url": "https://github.com/smanolloff/vcmi-gym/releases/download/v2.0/attacker-pdpyqkrb-202607251913.onnx",
5:     "path": "models\\upstream-v15\\attacker.onnx",
6:     "bytes": 19255061,
7:     "sha256": "62adf45ea34a323d72e9ce953a0c8b6740e60c3cec3651f282bfacee785d3151"
8:   },
9:   {
10:     "role": "defender",
11:     "url": "https://github.com/smanolloff/vcmi-gym/releases/download/v2.0/defender-zvytfdpo-202607230657.onnx",
12:     "path": "models\\upstream-v15\\defender.onnx",
13:     "bytes": 19255061,
14:     "sha256": "73bca79446ebdcab01e47fbbfada0162380df907bc86b19a21d0c502500cfaa9"
15:   }
16: ]

## vcmi_env /root/heroes3-ai-lab/src/gym/vcmi_gym/envs/v15/vcmi_env.py SHA256=cd609f1ac8bb0224e63ba473dec1b8b3363771bad33e31e4cd9dee16ee205ae6
339:         if opponent == "OTHER_ENV":
340:             opp = "MMAI_USER"
341:         else:
342:             opp = opponent
343: 
344:         if role == "attacker":
345:             attacker = "MMAI_USER"
346:             defender = opp
357:         elif role == "defender":
358:             attacker = opp
359:             defender = "MMAI_USER"
360:             attacker_vip = opponent_vip
361:             defender_vip = vip
362:             attacker_har = opponent_har
363:             defender_har = har
364:             attacker_uniform_chance = opponent_uniform_chance
365:             attacker_whitelist = opponent_whitelist
366:             defender_uniform_chance = uniform_chance
367:             defender_whitelist = whitelist
368:             attacker_target_mod = opponent_target_mod
369:             defender_target_mod = target_mod
370:         else:
371:             raise Exception(f"invalid role: {role}")
372: 
373:         if attacker == "MMAI_MODEL":
374:             attacker_model = opponent_model
375:             defender_model = ""
376:         elif defender == "MMAI_MODEL":
377:             attacker_model = ""
378:             defender_model = opponent_model
430:             loglevelNetwork=vcmi_loglevel_network,
431:             loglevelStats=vcmi_loglevel_stats,
432:             red=attacker,
433:             blue=defender,
434:             redModel=attacker_model,
435:             blueModel=defender_model,
436:             statsMode=vcmi_stats_mode,
437:             statsStorage=vcmi_stats_storage,

## connector /root/heroes3-ai-lab/src/gym/vcmi_gym/connectors/v15/threadconnector.h SHA256=e078189037ac4cbd42f214058fe14955177100fb58fa962217e2879f853fd1dd
170:         , red(red)
171:         , redModel(redModel)
172:         , blue(blue)
173:         , blueModel(blueModel)
174:         , initargs(ML::InitArgs{
175:             .temperature=0,
176:             .mapname=mapname,
177:             .maxBattles=0,
178:             .seed=seed,
179:             .randomHeroes=randomHeroes,

## onnx_factory /root/heroes3-ai-lab/src/gym/vcmi/AI/MMAI/BAI/factory.cpp SHA256=9c30c999464a2872f30371c65879367c173d314dcaa573919a3ae17ce022b6cc
39: 		auto opts = Ort::SessionOptions();
40: 		opts.DisableMemPattern();
41: 		opts.SetGraphOptimizationLevel(GraphOptimizationLevel::ORT_DISABLE_ALL);
42: 		opts.SetExecutionMode(ORT_SEQUENTIAL); // ORT_SEQUENTIAL = no inter-op parallelism
43: 		opts.SetInterOpNumThreads(1); // Inter-op threads matter in ORT_PARALLEL
44: 		opts.SetIntraOpNumThreads(4); // Parallelism inside kernels/operators
45: 
46: 		static const auto env = Ort::Env{ORT_LOGGING_LEVEL_WARNING, "vcmi"};
47: 		const auto rpath = ResourcePath(path, EResType::AI_MODEL);
48: 		const auto * rhandler = CResourceHandler::get();
49: 		if(!rhandler->existsResource(rpath))
50: 			throw std::runtime_error("NNBase: resource does not exist: " + rpath.getName());
51: 
52: 		const auto & [data, length] = rhandler->load(rpath)->readAll();
53: 		return std::make_unique<Ort::Session>(env, data.get(), length, opts);
86: 	std::shared_ptr<NNContainer> CreateNNContainer(const std::string & path)
87: 	{
88: 		auto session = load(path);
89: 		auto meminfo = Ort::MemoryInfo::CreateCpu(OrtArenaAllocator, OrtMemTypeDefault);
90: 		auto metadata = session->GetModelMetadata();
91: 		auto allocator = Ort::AllocatorWithDefaultOptions();
92: 		auto version = readVersion(session.get(), allocator, metadata);
93: 		return std::make_shared<NNContainer>(path, std::move(session), std::move(meminfo), std::move(metadata), std::move(allocator), version);
99: std::shared_ptr<MMAI::Schema::IModel> CreateNNModel(const std::string & path, float temperature, uint64_t seed)
100: {
101: 	auto container = CreateNNContainer(path);
102: 
103: 	if(container->version == 13)
104: 		return std::make_shared<V13::NNModel>(container, temperature, seed);
105: 	if(container->version == 15)
106: 		return std::make_shared<V15::NNModel>(container, temperature, seed);

## router /root/heroes3-ai-lab/src/gym/vcmi/AI/MMAI/BAI/router.cpp SHA256=1065c15ca0abfa8cfbf55549d152a98b47203b3100de2added5da60aad9a4f5b
48: 	};
49: 
50: 	std::shared_ptr<ModelRepository> InitModelRepository(Schema::Baggage * baggage = nullptr)
51: 	{
52: 		auto repo = std::make_unique<ModelRepository>();
53: 
54: 		if(baggage)
55: 		{
56: 			repo->seed = baggage->seed;
57: 			repo->temperature = baggage->temperature;
58: 
59: 			// Since ML client cannot load onnx models, it sends PATH
60: 			// "models" whose getName() returns the path to the model to load
61: 			// (in ML mode, the "MMAI" mod hence its config are not present)
62: 			if(baggage->modelLeft->getType() == Schema::ModelType::PATH)
63: 			{
64: 				const auto path = baggage->modelLeft->getName();
65: 				repo->models.try_emplace("attacker", CreateNNModel(path, repo->temperature, repo->seed), path);
66: 				repo->paths.try_emplace("attacker", path);
67: 			}
68: 			if(baggage->modelRight->getType() == Schema::ModelType::PATH)
69: 			{
70: 				const auto path = baggage->modelRight->getName();
71: 				repo->models.try_emplace("defender", CreateNNModel(path, repo->temperature, repo->seed), path);
72: 				repo->paths.try_emplace("defender", path);

## model_sampler /root/heroes3-ai-lab/src/gym/vcmi/AI/MMAI/BAI/v15/nn_model_v15.cpp SHA256=bc139f922b6d678f95aa9b7491da60937b378cee9c94ec54413ce2bf68281345
230: 		auto sample = Sample{};
231: 		auto greedy = Sample{};
232: 
233: 		if(temperature < 0.0f)
234: 			throwf("sample: negative temperature");
235: 
236: 		bool isGreedy = temperature < 1e-5;
237: 
238: 		// Greedy sample: argmax, first tie.
239: 		{
240: 			int best = 0;
241: 			for(int i = 0; i < probs.size(); ++i)
242: 			{
243: 				// Only print probs here if greedy is enabled
244: 				// Otherwise, tempered probs are printed later instead
245: 				if(isMMAIVerbose() && isGreedy)
246: 				{
247: 					const auto action = activeActionIds.at(i);
248: 					const auto * actnode = graph->getNode(ET::NODE_ACTION, action);
249: 					std::cout << "i=" << i << " action=" << action << " prob=" << std::fixed << std::setprecision(3) << probs[i] << " " << actnode->name()
250: 							  << "\n";
251: 				}
252: 
253: 				if(probs[i] > probs[best])
633: 	auto outputs = container->session->Run(Ort::RunOptions(), inputNames.data(), inputs.data(), inputs.size(), outputNames.data(), outputNames.size());
634: 
635: 	if(outputs.size() != 4)
636: 		throwf("getAction: bad output size: want: 4, have: %d", outputs.size());
637: 
638: 	const auto activeActionIds = graph->getActiveActionIds();
639: 	const auto modelGreedyAction = toScalar<int64_t>("action", outputs[0]);
640: 	const auto activeProbs = toVec1D<float>("active_probs", outputs[1], static_cast<int64_t>(activeActionIds.size()));
641: 	const auto value = toScalar<float>("value", outputs[2]);
642: 	const auto activeActionIdsOut = toVec1D<int64_t>("active_action_ids_out", outputs[3], static_cast<int64_t>(activeActionIds.size()));
643: 
644: 	if(activeActionIds.empty())
645: 		throwf("getAction: no active actions");
646: 
647: 	if(activeActionIdsOut != activeActionIds)
648: 		throwf("getAction: active action ids output mismatch");
649: 
650: 	const auto [sample, greedy] = categorical(activeProbs, temperature, rng, activeActionIds, graph);
651: 

## controller /mnt/g/Heroes3-AI-Lab/experiments/battle-terminal-credit-native-20261023/run.py SHA256=0e44486b867a04dcb6f661cfcc47b244d95c783153e3e4af9d588835489b2867
20:     assert restore.sha(restore.DEFAULT_CHECKPOINT)==restore.DEFAULT_SHA
21:     frozen=dict(schema='terminal-drain-prefix-credit-v1',input_sha256=inputs());atomic_json(a.out/'FREEZE.json',frozen)
22:     atomic_json(a.out/'PLAN.json',dict(schema=frozen['schema'],parent_checkpoint=str(restore.DEFAULT_CHECKPOINT),parent_sha256=restore.DEFAULT_SHA,parent_Adam=7680,registered_curriculum=str(HERE/'REGISTERED_CURRICULUM.json'),admitted_per_arm=4096,suffix_per_arm=4096,native_per_arm=8192,planned_Adam_per_arm=1024,global_updates=list(range(61,69)),evaluation=a.evaluate,DEV_games=96,DEV_seed_base=2026107600,execute=a.execute))
23:     if not a.execute:print(json.dumps(dict(plan_only=True,path=str(a.out/'PLAN.json'))));return 0
24:     assert all(os.environ.get(k) in (None,'','0') for k in ['LAB_NATIVE_ONNX_CUDA','LAB_ONNX_CUDA','LAB_BATTLEAI_TEACHER'])
25:     env=dict(os.environ,LAB_PYTHON=str(LAB/'gpu-venv/bin/python'),LAB_STAGED_BOOT='1',LAB_WORKER_ROOT=str(LAB/'workers'/(a.out.name+'-bootstrap')),CUBLAS_WORKSPACE_CONFIG=':4096:8',TERMINAL_CREDIT_LEASE_OWNER='1')
26:     handles=[];result=dict(passed=False,qualification=False,arms={},ability_promotion=False)
