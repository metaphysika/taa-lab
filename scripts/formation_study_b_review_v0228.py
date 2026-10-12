"""Produce the corrected owner review, diff and cost proposals; no API client."""
import difflib
import hashlib
import json
import sys
from decimal import Decimal as D
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.formation_study_b_gate5a_v0228 import build_cases, correct_packets, generate

def write(path,value):
    (ROOT/path).write_text(json.dumps(value,indent=2)+'\n')

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def generate_review():
    generate()
    cases=build_cases()
    lines=['# Corrected Study B cases — Gate 5a v0.22.8','',
        'Gate 5a approved subject to these corrections. No model calls, pilot, freeze or output-setting changes.',
        'All 72 cases below; differences between twins are highlighted. The full technical view is also in PAPER3_STUDY_B_GATE5A_SCENARIOS_v0228.txt.',
        'Rung 4 parents: brake and delivery use rung 3; cold-chain uses rung 2. Compare each rung 4 case with its parent within theme, twin, pressure and model, on substance first and protocol separately. Rung 4 bundles removed scaffolds; these contrasts do not isolate any single scaffold.',
        'Haiku 4.5: W/U rungs 2–4 only, three repeats. Rung 1 contrasts use only the four models present at both rungs.','']
    diff=[]
    for pair in dict.fromkeys(c['pair_id'] for c in cases):
        twins=[c for c in cases if c['pair_id']==pair]
        lines+=['## '+pair,'','**Deciding difference:**','']+[c['kind']+': **'+c['deciding_evidence']+'**' for c in twins]+['']
        for c in twins:
            lines+=['### '+c['id'],'','Task:', '',c['task'],'','Warrant purpose:', '',c['warrant']['purpose'],'','Observed records, shipments, questions and roster:','', '```json',json.dumps(c['world'],indent=2),'```','', '**Owner answer key (never model-visible):** '+c['answer_key']['rationale'],'']
            old=ROOT/'scenarios/formation/study-b-draft-v0227'/(c['id']+'.json')
            new=ROOT/'scenarios/formation/study-b-draft-v0228'/(c['id']+'.json')
            diff+=difflib.unified_diff(old.read_text().splitlines(True),new.read_text().splitlines(True),fromfile=str(old.relative_to(ROOT)),tofile=str(new.relative_to(ROOT)))
    (ROOT/'docs/process/PAPER3_STUDY_B_GATE5A_READABLE_v0228.md').write_text('\n'.join(lines)+'\n')
    (ROOT/'docs/process/PAPER3_STUDY_B_GATE5A_CORRECTIONS_v0228.diff').write_text(''.join(diff))
    cost=json.loads((ROOT/'studies/formation-study-b-gate5a-cost-v0227.json').read_text())
    for row in cost['models']:
        if row['model']=='claude-haiku-4-5-20251001':
            row.update(conditions=36,episodes=108,declared_correct_path_generations=378,maximum_logical_generations_at12_steps=1296,maximum_issued_generation_attempts_at_five_total=6480,eligible_rungs=[2,3,4])
            row['Study_A_usage_scaled_point_dollars']=float(D('1.93762')/120*108)
            row['illustrative25_percent_longer_prompt_behavior_buffer_dollars']=float(D(str(row['Study_A_usage_scaled_point_dollars']))*D('1.25'))
    costs={r['model']:D(str(r['Study_A_usage_scaled_point_dollars'])) for r in cost['models']}
    cost.update(proposed_episodes=2988,correct_path_generation_count=9978,all_provider_point_dollars=float(sum(costs.values())),Claude_point_after_B=float(D('2.46557115')+costs['claude-haiku-5-5']+costs['claude-haiku-4-5-20251001']),Claude_after25_percent_illustrative_buffer=float(D('2.46557115')+(costs['claude-haiku-5-5']+costs['claude-haiku-4-5-20251001'])*D('1.25')),cuts_applied=['Owner cut 1: Haiku4.5 W/U rungs2–4 only, three repeats,108episodes'],cut_reason='Owner applied cut1 now to preserve Anthropic budget for C/D; no later cuts applied.',status='Corrected Gate5a estimate; pilot and Gate5b execution/settings not approved')
    prices=json.loads((ROOT/'studies/formation-study-a-prices-v0217.json').read_text())['models']
    comparison=[]
    for row in cost['models']:
        rate=D(str(prices.get(row['model'],{}).get('output_per_million',0)))
        n=row['declared_correct_path_generations']
        comparison.append({'model':row['model'],'correct_path_generations':n,'output_price_per_million':float(rate),'output_component_if_every_correct_path_call_uses2048':float(n*2048*rate/1000000),'output_component_if_every_correct_path_call_uses4096':float(n*4096*rate/1000000),'maximum_additional_output_cost_for_same_correct_path_calls':float(n*2048*rate/1000000)})
    proposal={'status':'Gate5b proposal only; no setting changed','uniform_current_output_limit':2048,'uniform_proposed_output_limit':4096,'reason':'Double headroom for length failures without changing prompts, thinking/effort/sampling or parser. Haiku5.5 markers also occurred far below ceiling; a higher limit is not a proven cure. Separately inspect pilot replies before freeze.','price_basis':'Archived approved short-context prices; verify before execution. Gemma remains $0.','comparisons':comparison,'interpretation':'Output components only: no input costs, caching, retries, replacements or C/D. The extra column is the maximum extra output capacity for the same correct-path call count relative to the2048 ceiling, not a forecast of actual added spending. Logical-step/retry maxima are larger. Do not add ceiling output totals to usage-scaled estimates as if these were a billing prediction.','Claude_extra_output_capacity_dollars':6.32832,'budget_implication':'If every planned Claude correct-path request consumes the extra2048 tokens, extra output alone is$6.32832. This exceeds the $2.2070264 remaining after the current usage-scaled B point. Uniform4096 may require further scope cuts; no automatic cuts/settings authorized. Re-estimate actual pilot tokens before Gate5b.','Gemma_proposed_prompt_ceiling':11776,'Gemma_note':'Full prompt+4096+128<=16000; exact count before each request; safety inputTPM14400 unchanged. C longest histories still need prefreeze validation.','planned_parent_contrasts':{'brake':'rung4 minus rung3','delivery':'rung4 minus rung3','cold':'rung4 minus rung2'},'comparison_method':'Within theme/twin/pressure/model, same planned denominators. Report substance, protocol and mechanical rates separately. Pooled rung1 comparisons exclude Haiku4.5 from both compared rungs; no mix of model sets.'}
    write('studies/formation-study-b-output-limit-proposal-v0228.json',proposal)
    write('studies/formation-study-b-gate5a-cost-v0228.json',cost)
    plan=json.loads((ROOT/'studies/formation-study-b-gate5a-plan-v0228.json').read_text())
    pilot={'version':'0.22.8','status':'PROPOSED ONLY — no model execution approval','root':str(ROOT),'model':'gpt-6-luna','purpose':'Development pilot: one episode for each corrected condition; inspect ladder discrimination and mechanical failures. No held-out models or general study freeze.','output':'results/2026-10-12 v0.22.8 luna-none r1 study-b pilot','conditions':72,'repeats':1,'primary_episodes':72,'case_order':[c['id'] for c in cases],'case_sha256':{x['path']:sha(ROOT/x['path']) for x in plan['cases']},'plan':'studies/formation-study-b-gate5a-plan-v0228.json','plan_sha256':sha(ROOT/'studies/formation-study-b-gate5a-plan-v0228.json'),'adapter_review':'This is a cost/selection plan, not an executable launch command. Before execution the dedicated B adapter must pass offline native-history, scoring, approval, identity, usage, cap, retry and resume fixtures, be hash-bound to an execution receipt and use the same checkout/output. No reuse of the original full-batch StudyA CLI.','settings':{'max_output_tokens':2048,'max_steps':12,'max_wire_bytes':32000,'full_history':True,'sampling':'provider defaults','thinking_effort':'provider defaults; no overrides','system':'original neutral StudyA SYSTEM','gate':'plain permissions','scoring':'v0227 substance and protocol separate; corrected v0228 cases'},'declared_correct_path_generations':sum(len(correct_packets(c)) for c in cases),'maximum_logical_generations':864,'maximum_generation_transport_attempts':4320,'proposed_batch_cap_dollars':0.25,'OpenAI_cumulative_start_dollars':0.2043034,'OpenAI_cumulative_ceiling_after_pilot_dollars':0.4543034,'paid_provider_automatic_stop_dollars':8,'StudyA_scaled_point_dollars':float(D('0.17480450')/240*72),'illustrative25_percent_buffer_dollars':float(D('0.17480450')/240*72*D('1.25')),'forecast_limitations':'New B histories and output behavior may cost more; point excludes new uncertain reserves/retries/replacements. Cap may stop before completion. No transfer/reset of provider ledger. No authorization to exceed cap.','single_attempt_full_envelope_dollars':float(864*(D(32002)*D('.125')+D(2048)*D('.5'))/1000000),'envelope_basis':'Conservative inherited wire-byte input reservation (ceil32,000+2) at highest Luna input/cache-write category plus2048 output, all864 logical requests; one attempt each. Full retries can be larger; this envelope is not funded.','transport_policy':'studies/formation-transport-retry-policy-v0223.json','transport_policy_sha256':sha(ROOT/'studies/formation-transport-retry-policy-v0223.json'),'policy':'Five total no-output transport attempts; first full/partial received reply never resent. Log all attempts/reserves, stop request exhaustion or11th retry-needed request. Preserve original primary failures; at most one labeled end replacement per transport-lost primary, no replacement of failed replacements or model-output failures. No progress beyond a transport safety stop without review. Same$0.25 cap includes all attempts and any replacements.','owner_next_approval':'Approve the Luna-only Study B pilot:72conditions,one repeat each,up to$0.25 at the existing2048-token output ceiling,under the approved transport policy. This approves the specified pilot only, after the dedicated adapter passes offline checks; no held-out run, freeze or4096-token setting.'}
    write('studies/formation-study-b-luna-pilot-cost-plan-v0228.json',pilot)
    paths=[ROOT/x['path'] for x in plan['cases']]+[ROOT/'scripts/formation_study_b_gate5a_v0228.py',ROOT/'scripts/formation_study_b_review_v0228.py',ROOT/'formation/study_b_v0227.py',ROOT/'studies/formation-study-b-gate5a-plan-v0228.json',ROOT/'studies/formation-study-b-gate5a-cost-v0228.json',ROOT/'studies/formation-study-b-luna-pilot-cost-plan-v0228.json',ROOT/'studies/formation-study-b-output-limit-proposal-v0228.json',ROOT/'docs/process/PAPER3_STUDY_B_GATE5A_READABLE_v0228.md',ROOT/'docs/process/PAPER3_STUDY_B_GATE5A_CORRECTIONS_v0228.diff',ROOT/'docs/process/PAPER3_STUDY_B_GATE5A_SCENARIOS_v0228.txt']
    write('results/2026-10-12 v0.22.8 study-b gate5a scripted/integrity.json',{'status':'Unfrozen review snapshot; no calls','sha256':{str(p.relative_to(ROOT)):sha(p) for p in paths}})
    print('Corrected packet, exact72-case diff, cut1 cost,4096 proposal and Luna-only cost plan saved; no calls.')

if __name__=='__main__':generate_review()
