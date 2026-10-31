"""Typed CPU broker. Responses propose actions; they do not certify execution."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import time

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('_broker_typed_encoder', ROOT / 'encoder.py')
encoder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(encoder)
RESPONSE_SCHEMA = 'strategy-typed-action-response-v3'
RESPONSE_KEYS = {'schema','selected_index','decision_id','player','hero','own_turn','op','request_sha256','classification'}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def atomic(path, raw):
    temporary = path.with_name(path.name + f'.{os.getpid()}.tmp')
    try:
        with temporary.open('xb') as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
        fd = os.open(path.parent, os.O_RDONLY | getattr(os,'O_DIRECTORY',0))
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        if temporary.exists():
            temporary.unlink()


def validate_response(response, request, raw):
    encoder.validate(request)
    if not isinstance(response,dict) or set(response) != RESPONSE_KEYS or response.get('schema') != RESPONSE_SCHEMA:
        raise ValueError('Typed JSON response exact schema required')
    index = response['selected_index']
    if type(index) is not int or not 0 <= index < len(request['candidates']):
        raise ValueError('Invalid selected_index')
    for key, expected in [('decision_id',request['request_id'])]+[(key,request[key]) for key in ('player','hero','own_turn')]:
        if type(response[key]) is not int or response[key] != expected:
            raise ValueError('Response context mismatch: '+key)
    if response['op'] != request['candidates'][index]['op'] or response['request_sha256'] != digest(raw):
        raise ValueError('Response op/request byte SHA mismatch')
    if response['classification'] not in ('new_policy','diagnostic_only'):
        raise ValueError('Invalid response provenance')
    return response


class Broker:
    def __init__(self, mode, checkpoint=None, diagnostic_action=None):
        from qualification import require_qualification
        require_qualification()
        self.mode,self.diagnostic_action = mode,diagnostic_action
        self.model = None
        self.model_sha256 = None
        if mode == 'new-policy':
            if checkpoint is None or diagnostic_action is not None:
                raise ValueError('new-policy needs typed checkpoint and no diagnostic override')
            spec = importlib.util.spec_from_file_location('_broker_typed_model', ROOT/'model.py')
            module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
            self.model,_,self.model_sha256 = __import__('model_io').load_model(checkpoint,'cpu')
            import torch
            torch.set_num_threads(1)
        elif mode != 'diagnostic-only' or diagnostic_action not in ('end_turn','alternate','build','move') or checkpoint is not None:
            raise ValueError('Explicit diagnostic-only action required; no policy checkpoint or fallback')

    def propose(self, raw, expected_id):
        request = encoder.validate(json.loads(raw),expected_id)
        # The typed transport uses integer identity fields even though old numeric
        # move features accepted general finite numeric observations.
        if any(type(request[key]) is not int for key in ('player','hero')):
            raise ValueError('Typed action identity must use integer player/hero')
        value = None;probabilities=None
        if self.model is not None:
            import torch
            with torch.no_grad():
                logits,values = self.model(**encoder.collate([request],'cpu'))
                index,value = int(logits.argmax(-1)[0]),float(values[0])
                probabilities=logits[0,:len(request['candidates'])].softmax(-1).tolist()
        else:
            op = self.diagnostic_action if self.diagnostic_action in ('end_turn','build','move') else ('end_turn' if request['request_id']%2 == 0 else 'move')
            choices = [i for i,candidate in enumerate(request['candidates']) if candidate['op'] == op]
            if not choices:
                raise ValueError('Diagnostic operation absent; no substitution')
            index = choices[0]
        response = dict(schema=RESPONSE_SCHEMA,selected_index=index,decision_id=request['request_id'],
            player=request['player'],hero=request['hero'],own_turn=request['own_turn'],
            op=request['candidates'][index]['op'],request_sha256=digest(raw),
            classification='new_policy' if self.model is not None else 'diagnostic_only')
        validate_response(response,request,raw)
        return dict(response=response,request=request,request_sha256=digest(raw),
                    model_sha256=self.model_sha256,value=value,action=index,probabilities=probabilities,execution_verified=False,
                    ppo_sample_admitted=False,native_request_id_assignment='pending_real_requestSent')

    def process(self, request_path, expected_id):
        raw=request_path.read_bytes()
        action=request_path.parent/f'action-{expected_id:08d}.json'
        if action.exists():
            raise ValueError('Existing action; fresh game directory required')
        proposal=self.propose(raw,expected_id)
        data=(json.dumps(proposal['response'],separators=(',',':'),allow_nan=False)+'\n').encode()
        trace=request_path.parent/'typed-broker.jsonl'
        with trace.open('a') as stream:
            stream.write(json.dumps(proposal,separators=(',',':'),allow_nan=False)+'\n')
            stream.flush();os.fsync(stream.fileno())
        atomic(action,data)
        return proposal


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--agent-dir',type=Path,required=True)
    parser.add_argument('--mode',choices=('new-policy','diagnostic-only'),required=True)
    parser.add_argument('--checkpoint',type=Path)
    parser.add_argument('--diagnostic-action',choices=('end_turn','alternate','build','move'))
    parser.add_argument('--max-requests',type=int,default=0)
    parser.add_argument('--idle-seconds',type=float,default=120.)
    args=parser.parse_args()
    if args.max_requests<0 or args.idle_seconds<=0:
        raise ValueError('Invalid broker limits')
    import fcntl
    args.agent_dir.mkdir(parents=True,exist_ok=True)
    with (args.agent_dir/'typed-broker.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        broker=Broker(args.mode,args.checkpoint,args.diagnostic_action)
        stop=False
        def stopping(*_):
            nonlocal stop
            stop=True
        signal.signal(signal.SIGTERM,stopping);signal.signal(signal.SIGINT,stopping)
        atomic(args.agent_dir/'broker-ready.json',(json.dumps(dict(schema=RESPONSE_SCHEMA,
            mode=args.mode,model_sha256=broker.model_sha256,device='cpu',optimizer_steps=0))+'\n').encode())
        number=1;last=time.monotonic()
        while not stop and (not args.max_requests or number<=args.max_requests):
            path=args.agent_dir/f'request-{number:08d}.json'
            if path.exists():
                try:
                    broker.process(path,number)
                except Exception as error:
                    atomic(args.agent_dir/f'error-{number:08d}.json',
                           (json.dumps(dict(decision_id=number,error=str(error),fallback=False))+'\n').encode())
                    raise
                number+=1;last=time.monotonic()
            elif time.monotonic()-last>args.idle_seconds:
                raise TimeoutError('Typed broker idle timeout; no invented response')
            else:
                time.sleep(.01)
    return 0


if __name__=='__main__':
    raise SystemExit(main())



