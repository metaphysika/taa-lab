"""Out-of-band failure injection at actual non-transactional host boundaries.

Neither agent arguments nor permission decisions can request these hooks. This
module imports no core, conventional, reference, oracle or scoring code.
"""
NOT_APPLICABLE = {
    'after_stage': 'No staging phase: business effects are written directly.',
    'during_token_consumption': 'No security tokens or token consumption.',
    'during_duty_update': 'No internal duty engine or duty-update phase.',
    'during_revision_advance': 'No transaction revision-commit boundary; ordinary writes update their own counters.',
}
BOUNDARIES = ('after_validate', 'during_effect_commit', 'during_receipt_write', 'before_log_write')


class NotApplicableByDesign(ValueError):
    pass


class InjectedBusinessFault(RuntimeError):
    pass


class FaultAdapter:
    def __init__(self, point):
        if point in NOT_APPLICABLE:
            raise NotApplicableByDesign(NOT_APPLICABLE[point])
        if point not in BOUNDARIES:
            raise ValueError('Unknown business fault boundary')
        self.point = point

    def hit(self, boundary):
        if self.point == boundary:
            raise InjectedBusinessFault(boundary)
