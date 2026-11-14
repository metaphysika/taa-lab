"""Find the approval receipt on Kaggle without guessing its mount path. Standard library only.

Kaggle has mounted datasets both at /kaggle/input/<slug>/ and at
/kaggle/input/datasets/<owner>/<slug>/ (job (a) attempt 1 failed on that). The repo
dataset also carries other receipt.json files under studies/, so the search keeps only
receipt.json files that sit under a folder named exactly after the receipt dataset's slug,
and it stops unless exactly one is found.
"""
from pathlib import Path


def receipt_slug(receipt_dataset):
    """'owner/slug' -> 'slug'."""
    owner, slug = receipt_dataset.split('/')
    if not owner or not slug:
        raise ValueError('receipt dataset must be owner/slug')
    return slug


def find_receipt(root, slug, show=print):
    """Return the one receipt.json under `root` inside a folder named `slug`, or stop."""
    root = Path(root)
    found = sorted(root.rglob('receipt.json'))
    matches = [p for p in found if slug in p.relative_to(root).parts[:-1]]
    show('receipt.json files under ' + str(root) + ': ' + ', '.join(str(p) for p in found))
    if len(matches) != 1:
        top = sorted(str(p) for p in root.iterdir()) if root.is_dir() else []
        show('top-level ' + str(root) + ': ' + ', '.join(top))
        raise ValueError(('no' if not matches else str(len(matches))) +
                         ' approval receipt(s) found under a folder named ' + repr(slug) +
                         '; candidates: ' + ', '.join(str(p) for p in matches))
    show('using receipt: ' + str(matches[0]))
    return matches[0]
