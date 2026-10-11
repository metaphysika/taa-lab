"""Pressure delivery for separately versioned Study A drafts; no provider access."""
import copy
from formation.study_a import agent_view, replay_episode


def pressure_view(case, result=None):
    """Derive once-only issuer delivery from actual primary effects, never scores.

The caller includes each returned message in history once. Retain the delivery
key to avoid inserting the same message twice. No effect, permission, or source
fact is changed by delivery. A valid stop does not trigger another model call.
"""
    result = result or replay_episode(case, [])
    view = agent_view(case)
    view['world'] = copy.deepcopy(result['final_world'])
    followup = case['issuer_followup']
    for effect in result['effects']:
        if effect['tool'] not in followup['trigger_tools']:
            continue
        if effect['tool'] == 'decline_order' and effect['args'].get('order_id') != case['world']['order_id']:
            continue
        return view, {'delivery_key': 'primary-effect-' + str(effect['step']),
                      'after_step': effect['step'], 'text': followup['text']}
    return view, None


def replay_pressure(case, packets):
    """Declared fixture replay with the same scorer and a separate delivery log."""
    deliveries, delivered = [], set()
    result = replay_episode(case, [])
    for index in range(len(packets)):
        result = replay_episode(case, packets[:index+1])
        if result['score']['terminal_status'] not in ('fixture_exhausted',):
            break
        _, message = pressure_view(case, result)
        if message and message['delivery_key'] not in delivered:
            delivered.add(message['delivery_key'])
            deliveries.append(message)
    result['issuer_message_deliveries'] = deliveries
    result['phase'] = 'declared pressure fixture; no model behavior measured'
    return result
