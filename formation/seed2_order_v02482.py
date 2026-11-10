"""Documented reconstruction, authorized after an exact 2,000-position match."""
import json
import random

def order(shuffle_seed, optimizer_seed):
    """Sort T0001..T2000 by integer suffix int(id[1:]), then Random.shuffle.

    Both arms use this one order through the unchanged SequentialSampler.
    This procedure was reconstructed, not recovered from original code.
    """
    ids = sorted(('T%04d' % i for i in range(1, 2001)), key=lambda ident: int(ident[1:]))
    random.Random(shuffle_seed).shuffle(ids)
    return dict(high=dict(seed=shuffle_seed, record_ids=ids, same_order_all_arms=True),
                optimizer_seed=optimizer_seed, evaluation_order_seed=247053)


def encode(shuffle_seed, optimizer_seed):
    return (json.dumps(order(shuffle_seed, optimizer_seed), indent=2)+'\n').encode('utf-8')
