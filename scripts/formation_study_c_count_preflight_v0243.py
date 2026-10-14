"""OFFLINE ONLY: audit every Gemma C schedule entry and frozen fixture prefix.

No client key lookup, send, generation, countTokens, or automation activation.
This checks all fixed histories, not unknowable future model reply texts. The
same exact-body runtime policy is separately tested for arbitrary later bodies.
"""
import collections
import copy
import json
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from formation import study_c_evaluation_v0242 as c
from formation.study_c_count_remedy_v0243 import verified_counts, count_body, ENDPOINT
from formation.transport_retry_v0223 import RetryTransport


def scan(root=c.ROOT):
    root = Path(root)
    f = c.read(root / c.FREEZE)
    source = root / f['Gemma_quota_source']
    from formation.study_b_evaluation_v0235 import output_name
    prior = root / output_name('gemma-4-31b-it')
    sources = [(p/'token-count-receipts.jsonl', p/'transport-retry-state.json',
                c.sha(p/'token-count-receipts.jsonl'), c.sha(p/'transport-retry-state.json'))
               for p in [prior, source]]
    counts = verified_counts(sources)
    cases = {x['id']: x for x in c.read(root / f['probe_files'])}
    cells = c.read(root / f['schedule'])['cells']
    seeds = c.read(root / f['seed_files'])
    fixtures = c.read(root/'studies/formation-study-c-frozen-v0239/free-probe-fixtures.json')
    jobs = c.read(source/'transport-retry-state.json')['jobs']
    current = {e['body_sha256']:e['totalTokens'] for e in c.journal(source/'token-count-receipts.jsonl') if e['event']=='count_complete'}
    native = c.CLASSES['google']('gemma-4-31b-it',SimpleNamespace(model='gemma-4-31b-it'),max_output_tokens=4096)
    items = []; unique = set(); status = collections.Counter(); total = 0
    # Exercise the real remedy on every prefix using in-memory scripted metadata
    # responses, never a network callback. 100 is a stand-in, NOT a token-fit fact.
    temp=tempfile.TemporaryDirectory()
    class MemoryRetry(RetryTransport):
        def save(self):pass
    retry=MemoryRetry(Path(temp.name)/'retry.json',Path(temp.name)/'journal.jsonl')
    retry.state=copy.deepcopy(c.read(source/'transport-retry-state.json'))
    initial_retry_count=retry.state['requests_needing_retry']
    old_jobs=copy.deepcopy(retry.state['jobs']); simulated=[]
    quota=SimpleNamespace(counts=dict(current),guard=lambda:None,save=lambda:None,
        receipts=Path(temp.name)/'receipts.jsonl',state={'metadata_inflight':None,'paused_until':0},ready_at=0)
    def scripted_metadata(endpoint,outer,received):
        assert endpoint==ENDPOINT and outer['generateContentRequest']['model']=='models/gemma-4-31b-it'
        simulated.append(endpoint);received();return {'totalTokens':100}
    dry=SimpleNamespace(model='gemma-4-31b-it',quota=quota,retry=retry,
        reserve=lambda kind:len(simulated),native_send=scripted_metadata)
    for cell in cells:
        prefix_records = []
        compatible = [x for x in fixtures if x['probe_id']==cell['probe_id']]
        # All prespecified stand-in fixture paths, including errors/refusals;
        # never simulate a paid model or claim their token lengths are known.
        for fixture in compatible:
            for turn in range(min(12,len(fixture['packets']))):
                body = native.body(c.SYSTEM,c.seeded_history(cases[cell['probe_id']],cell,fixture['packets'][:turn],seeds))
                digest = c.body_hash(body); unique.add(digest); total += 1
                old = jobs.get('countTokens:'+digest)
                if digest in current:
                    route='existing_usable_receipt'
                elif digest in counts:
                    route='recover_prior_exact_count'
                elif old and old.get('received') and old.get('phase') in ('complete','failed'):
                    route='metadata_only_new_job_required'
                elif old and old.get('phase') not in ('ready',):
                    route='REVIEW_unclosed_metadata'
                else:
                    route='new_metadata_job_no_collision'
                status[route] += 1
                count_body(dry,body,counts)
                prefix_records.append(dict(fixture=fixture['fixture_name'],turn=turn+1,
                    body_sha256=digest,route=route,known_tokens=counts.get(digest,{}).get('totalTokens'),
                    generation_bytes=len(json.dumps(body).encode()),
                    metadata_bytes=len(json.dumps({'generateContentRequest':dict(body,model='models/gemma-4-31b-it')}).encode())))
        items.append(dict(cell=cell,prefixes=prefix_records))
    assert len(items)==540 and len({x['cell']['cell_id'] for x in items})==540
    assert retry.state['requests_needing_retry']==initial_retry_count
    assert all(retry.state['jobs'][key]==value for key,value in old_jobs.items())
    simulated_count=len(simulated);temp.cleanup()
    if any(k.startswith('REVIEW') for k in status):raise ValueError('unclosed inherited metadata requires review')
    blocked='e507615e6e93056a75ffbde22704a26fd0541fc7f9bb54024af1a14456090b12'
    return dict(offline_only=True,HTTP_calls=0,generation_calls=0,scheduled_cells=len(items),
        fixture_prefixes=total,unique_bodies=len(unique),routes=dict(status),
        all_prefixes_exercised_by_real_remedy=True,scripted_metadata_callbacks=simulated_count,
        scripted_counts_are_not_provider_token_validation=True,original_jobs_and_counters_unchanged=True,
        recovered_blocked_body=counts[blocked],source_bindings=[dict(receipts=str(a.relative_to(root)),state=str(b.relative_to(root)),receipt_sha256=x,state_sha256=y) for a,b,x,y in sources],
        scope='All540 fixed seeded histories and all compatible frozen fixture prefixes. Future model replies are unknowable offline; runtime exact-hash policy applies at EVERY turn.',
        items=items)


if __name__=='__main__':
    if len(sys.argv)!=2:raise SystemExit('output JSON path required; offline only')
    result=scan();Path(sys.argv[1]).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('items','source_bindings')}))
