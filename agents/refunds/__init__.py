"""Four deterministic offline controllers. These make no model calls."""
from .correct import Correct
from .compliant import Compliant
from .cautious import Cautious
from .adversarial import Adversarial

CONTROLLERS = {a.name: a for a in (Correct, Compliant, Cautious, Adversarial)}
