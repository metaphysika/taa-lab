"""Read-only audit of the once-only approved neutral check; no transport import."""
import base64
from decimal import Decimal as D
import hashlib
import json
from pathlib import Path
import subprocess
from live_demo.evidence import encoded, verify

ROOT=Path('/workspace/taa-lab')
EXTERNAL=Path('/workspace/taa-experiment-a-evidence/neutral-37cf7203-attempt2-20261026')
EVIDENCE=EXTERNAL/'anthropic-attempt-2'
OUT=Path(__file__).parent
frames=[json.loads(p.read_bytes()) for p in sorted(EVIDENCE.glob('*.json')) if p.stem.isdigit()]
replies=[json.loads(base64.b64decode(f['value']['base64'])) for f in frames if f['kind']=='native_reply']
requests=[f['value']['body'] for f in frames if f['kind']=='request']
before=json.loads((EXTERNAL/'before.json').read_text())
assert len(requests)==len(replies)==2
assert encoded(dict(role='assistant',content=replies[0]['content']))==encoded(requests[1]['messages'][1])
assert requests[1]['messages'][2]['content'][0]['tool_use_id']==replies[0]['content'][0]['id']
assert json.loads(requests[1]['messages'][2]['content'][0]['content'])=={'value':'neutral-check'}
assert all(reply['model']=='claude-sonnet-5-5' for reply in replies)
assert [r['stop_reason'] for r in replies]==['tool_use','end_turn']
state=Path('/workspace/taa-experiment-state')
def git(*args):return subprocess.check_output(['git','-C',str(state),*args],text=True).strip()
STATE_HEAD='472d761352715650f1746982843e80340b6052ee'
def state_blob(name):return subprocess.check_output(['git','-C',str(state),'show',STATE_HEAD+':'+name])
state_files=set(git('ls-tree','-r','--name-only',STATE_HEAD).splitlines())
for name,digest in before['old_markers'].items():assert hashlib.sha256(state_blob(name)).hexdigest()==digest
assert 'check-anthropic-000002.once' in state_files
assert 'run.once' not in state_files and 'active-run.json' not in state_files
charges=[f['value'] for f in frames if f['kind']=='usage']
charged=sum(D(row['charged']) for row in charges)
assert charged==D('0.002542')
provider=json.loads(state_blob('ledgers/claude.json'))['estimated_api_dollars']
step=state_blob('step-budget.txt').decode().strip()
assert D(provider)==D(before['anthropic'])+charged
assert D(step)==D(before['step'])+charged
assert json.loads(state_blob('ledgers/google.json'))['estimated_api_dollars']==before['google']
assert [r['usage']['output_tokens_details']['thinking_tokens'] for r in replies]==[0,0]
commits=[dict(commit=line.split(' ',1)[0],message=line.split(' ',1)[1]) for line in git('log',before['state_head']+'..'+STATE_HEAD,'--format=%H %s').splitlines()]
claim=next(c['commit'] for c in commits if c['message']=='Experiment A: claim check-anthropic-000002.once')
checkpoint=verify(EVIDENCE)
result=dict(claim='[Descriptive] Approved Anthropic neutral attempt2 at exact37cf7203; no retry/pilot',stop=json.loads((EXTERNAL/'launch-report.json').read_text())['stop'],run_commit=before['run_head'],model_returned='claude-sonnet-5-5',physical_requests=2,finish_reasons=[r['stop_reason'] for r in replies],native_usage=[r['usage'] for r in replies],thinking_blocks_returned=[any(b['type'] in ('thinking','redacted_thinking') for b in r['content']) for r in replies],thinking_continuity='not exercised: no thinking/redacted-thinking blocks returned',assistant_content_replayed_byte_identically=True,request2_accepted_tool_result=True,observed_thinking_tokens=0,observed_visible_output_tokens=74,observed_thinking_to_visible_ratio='0/74 = 0',charge_dollars=str(charged),new_retained_reserve='0',before=before,after=dict(anthropic=provider,google=before['google'],step=step,state_head=STATE_HEAD),state_claim_commit=claim,state_commits=commits,old_marker_hashes_unchanged=True,attempt2_marker_sha256=hashlib.sha256(state_blob('check-anthropic-000002.once')).hexdigest(),state_clean=True,run_once=False,active_lease=False,evidence_directory=str(EVIDENCE),checkpoint=checkpoint,mapper_note='Native output_tokens_details.thinking_tokens explicitly reports zero. Generic mapped thinking_tokens_reported remains null/not separately reported at the approved runtime; use retained native field here. Output tokens already include thinking for billing; no double count or runtime change.')
(OUT/'check-summary.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps({k:result[k] for k in ('stop','model_returned','finish_reasons','charge_dollars','after','state_claim_commit','checkpoint')},indent=2))
