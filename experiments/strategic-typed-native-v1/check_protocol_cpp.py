"""Compile and exercise the actual standalone C++ wire helper, not a Python copy."""
import copy,hashlib,json,subprocess,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
HEADER=HERE/'candidate/AI/DirectorAI/TypedPolicyProtocol.h'
valid={'schema':'strategy-typed-action-response-v1','selected_index':1,'decision_id':17,'player':0,
       'hero':2,'own_turn':3,'op':'end_turn','request_sha256':hashlib.sha256(b'abc').hexdigest(),'classification':'diagnostic_only'}
cases=[('valid',json.dumps(valid)+'\n',True)]
for key,value in [('own_turn',True),('own_turn',4),('hero',3),('decision_id',18),('player',1),
                  ('selected_index',2),('op','move'),('classification','expert'),('request_sha256','0'*64),('schema','strategy-candidates-v3')]:
    item=copy.deepcopy(valid);item[key]=value;cases.append((key+'='+str(value),json.dumps(item)+'\n',False))
item=copy.deepcopy(valid);item['extra']=0;cases.append(('extra_key',json.dumps(item)+'\n',False))
item=copy.deepcopy(valid);del item['op'];cases.append(('missing_op',json.dumps(item)+'\n',False))
cases.extend([('plain_integer','1\n',False),('duplicate_key',json.dumps(valid)[:-1]+',"op":"end_turn"}\n',False),
              ('trailing_object',json.dumps(valid)+'{}\n',False),('missing_newline',json.dumps(valid),False)])
with tempfile.TemporaryDirectory(prefix='typed-cpp-wire-') as tmp:
    root=Path(tmp);source=root/'check.cpp';binary=root/'check'
    source.write_text('#include "'+str(HEADER)+'"\n#include <iostream>\nint main(int argc,char**argv){std::string raw((std::istreambuf_iterator<char>(std::cin)),{});if(std::string(argv[1])=="hash"){std::cout<<LabTypedPolicy::sha256(raw);return 0;}try{auto r=LabTypedPolicy::parseResponse(raw,17,0,2,3,LabTypedPolicy::sha256("abc"),{"move","end_turn"});std::cout<<r.index<<" "<<r.op;return 0;}catch(const std::exception&e){std::cerr<<e.what();return 2;}}')
    compiled=subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-O2',str(source),'-o',str(binary)],capture_output=True,text=True)
    assert compiled.returncode==0,compiled.stderr
    hashes=[]
    for data in [b'',b'abc',b'a'*55,b'a'*56,b'a'*64,b'a'*1000,bytes(range(256))]:
        result=subprocess.run([str(binary),'hash'],input=data,capture_output=True)
        assert result.returncode==0 and result.stdout.decode()==hashlib.sha256(data).hexdigest()
        hashes.append(len(data))
    checks=[]
    for label,raw,expected in cases:
        result=subprocess.run([str(binary),'parse'],input=raw,text=True,capture_output=True)
        assert (result.returncode==0)==expected,(label,result.stdout,result.stderr)
        checks.append({'case':label,'accepted':result.returncode==0})
report={'passed':True,'actual_cpp_compiled':True,'header_sha256':hashlib.sha256(HEADER.read_bytes()).hexdigest(),
        'sha256_input_lengths':hashes,'response_checks':checks,'native_game_runs':0,'optimizer_steps':0}
out=HERE/'cpp-wire-cpu-01';out.mkdir(exist_ok=False);(out/'AUDIT.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
