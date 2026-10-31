## learner /mnt/g/Heroes3-AI-Lab/experiments/battle-terminal-credit-native-20261023/learner_impl.py SHA256=060ec0961790bd8a755b8b994ed1315fbfa3f1f27b095134b39f83d766e58478
35:     out=[]
36:     for row in rows:
37:         assert restore.sha(LAB/'data/vcmi/Maps'/row['map'])==row['map_sha256'] and row['scenario_index']<192
38:         role=row['role'];opponent=row['opponent'];out.append(dict(map=row['map'],role=role,opponent=opponent,initial_reset_once=True,
39:             opponent_model='DATA/MMAI/models/lab-upstream-'+('defender' if role=='attacker' else 'attacker')+'.onnx' if opponent=='MMAI_MODEL' else None,
40:             seed=row['seed'],feature_version='upstream-graph-v15',step_cost=0.,family=row['family'],TRAIN_scenario_index=row['scenario_index'],timeout=90,
41:             worker_root=str(LAB/'workers'/run/f'{phase}-{row["slot"]}')))
42:     return out
91:             verify(a.freeze);resources=resource();folder=a.out/f'phase-{phase}';folder.mkdir();cfg=configs(registered['phases'][phase],a.out.name,phase);vector=recorded_vector.VectorEnv(cfg,executable=str(LAB/'venv/bin/python'));current=[x['features'] for x in vector.states]
92:             assert all(not x['torch_imported'] for x in vector.states),'Spawned native workers unexpectedly loaded Torch'
93:             atomic_json(folder/'WORKERS.json',dict(configs=cfg,worker_PIDs=[x['pid'] for x in vector.states],torch_imported=[x['torch_imported'] for x in vector.states]))

## worker /mnt/g/Heroes3-AI-Lab/experiments/battle-terminal-credit-native-20261023/recorded_vector.py SHA256=f6395c1b083255c2a8e367024403a6627bb3ebc0cc2cbfe3792cea879110637f
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
5: def make_env(mapname, seed, role, opponent='BattleAI', max_steps=400, opponent_model=None, timeout=60):
6:     return VcmiEnv(mapname=mapname, seed=seed, role=role, opponent=opponent,
7:                    opponent_model=opponent_model, max_steps=max_steps, render_mode='ansi', random_heroes=0,
8:                    random_obstacles=0, town_chance=0, warmachine_chance=0,
9:                    random_armies=False, mana_min=0, mana_max=0,
10:                    user_timeout=timeout, vcmi_timeout=timeout, boot_timeout=timeout,
11:                    vcmi_loglevel_global='error', vcmi_loglevel_ai='error')

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

## model_sampler /root/heroes3-ai-lab/src/gym/vcmi/AI/MMAI/BAI/v15/nn_model_v15.cpp SHA256=bc139f922b6d678f95aa9b7491da60937b378cee9c94ec54413ce2bf68281345
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

## controller /mnt/g/Heroes3-AI-Lab/experiments/battle-terminal-credit-native-20261023/run.py SHA256=0e44486b867a04dcb6f661cfcc47b244d95c783153e3e4af9d588835489b2867
24:     assert all(os.environ.get(k) in (None,'','0') for k in ['LAB_NATIVE_ONNX_CUDA','LAB_ONNX_CUDA','LAB_BATTLEAI_TEACHER'])
25:     env=dict(os.environ,LAB_PYTHON=str(LAB/'gpu-venv/bin/python'),LAB_STAGED_BOOT='1',LAB_WORKER_ROOT=str(LAB/'workers'/(a.out.name+'-bootstrap')),CUBLAS_WORKSPACE_CONFIG=':4096:8',TERMINAL_CREDIT_LEASE_OWNER='1')
26:     handles=[];result=dict(passed=False,qualification=False,arms={},ability_promotion=False)