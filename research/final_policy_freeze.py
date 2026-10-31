"""Byte-identical model backup and selection binding before independent testing."""
import hashlib
import os
from pathlib import Path
import shutil
import time
from lab_io import atomic_json


def checksum(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(selection):
    research=Path(__file__).resolve().parent
    assert not list(research.glob('fresh-*-vs-*.json')),'Independent testing already started; do not replace its frozen candidate'
    source=Path(selection['checkpoint']);digest=checksum(source)
    folder=research.parent/'models/goal-final-freeze';folder.mkdir(parents=True,exist_ok=True)
    target=folder/'policy.pt';temporary=target.with_name(target.name+'.tmp-'+str(os.getpid()))
    try:
        shutil.copyfile(source,temporary)
        with temporary.open('rb') as stream:os.fsync(stream.fileno())
        assert checksum(temporary)==digest==checksum(source)
        os.replace(temporary,target)
    finally:
        if temporary.exists():temporary.unlink()
    record=dict(frozen_unix=time.time(),name=selection['name'],policy=selection['policy'],
        source_checkpoint=str(source),backup_checkpoint=str(target),sha256=digest,
        selection=selection,validation_sha256=checksum(research/'goal-v5-validation.json'),
        final_test_read=False)
    atomic_json(research/'final-policy-freeze.json',record)
    return record
