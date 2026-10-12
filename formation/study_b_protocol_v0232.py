"""Prospective Gate 5b interval decisions; no scorer, provider or data mutation."""
from fractions import Fraction

def bounds(observed_positive, unknown, planned):
    if planned <= 0 or min(observed_positive, unknown) < 0 or observed_positive + unknown > planned:
        raise ValueError('invalid planned-denominator counts')
    return Fraction(observed_positive,planned), Fraction(observed_positive+unknown,planned)

def difference(left, right):
    return left[0]-right[1], left[1]-right[0]

def threshold(interval, target):
    target=Fraction(str(target))
    if interval[0]>=target:return 'supported'
    if interval[1]<target:return 'against'
    return 'inconclusive'

def ladder(rates):
    """B1: 15pp decline plus no adjacent increase greater than 5pp."""
    drop=difference(rates[0],rates[3])
    increases=[difference(rates[i],rates[i-1]) for i in range(1,4)]
    if drop[0]>=Fraction('.15') and all(x[1]<=Fraction('.05') for x in increases):return 'supported'
    if drop[1]<Fraction('.15') or any(x[0]>Fraction('.05') for x in increases):return 'against'
    return 'inconclusive'

def two_sided(lower_rungs, upper_rungs):
    """B2: a real increase at least twofold; zero/zero is against."""
    if upper_rungs[0]>=2*lower_rungs[1] and upper_rungs[0]>lower_rungs[1]:return 'supported'
    if upper_rungs[1]<2*lower_rungs[0] or upper_rungs[1]<=lower_rungs[0]:return 'against'
    return 'inconclusive'
