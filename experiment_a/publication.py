"""Publish closed episode chains and their raw root prefix before proceeding."""
import hashlib
import json
import os
from pathlib import Path
import re
import time

from experiment_a import config
from experiment_a.credentials import scan
from experiment_a.state import State
from experiment_a.continuation import frames
from live_demo.evidence import encoded, verify
from live_demo.adapter import Stop

BRANCH = 'experiment-a-evidence'
SPEC = dict(version=1, branch=BRANCH, contents='closed episode chains and raw root prefixes')

class PublicationJournal:
    def __init__(self, journal): self.journal=journal
    def write(self, kind, value):
        self.journal.write(kind.replace('state_','evidence_',1),value)

class Publisher(State):
    branch = BRANCH

    def __init__(self, root=None, *, run_root=None, sleeper=None):
        self.root=Path(root or os.environ.get('TAA_EXPERIMENT_EVIDENCE_WORKTREE','/workspace/taa-experiment-evidence')).resolve()
        self.run_root=Path(run_root or config.ROOT).resolve()
        self.failed=False;self.base=None;self.evidence=None
        self.sleeper=time.sleep if sleeper is None else sleeper
        try:
            if (self.root.is_relative_to(self.run_root) or self.run_root.is_relative_to(self.root) or
                    not (self.root/'.git').is_file() or
                    self._git('branch','--show-current') not in ('',BRANCH) or
                    self._git('rev-parse','--path-format=absolute','--git-common-dir') !=
                    self._git('rev-parse','--path-format=absolute','--git-common-dir',cwd=self.run_root)):
                raise ValueError('separate evidence worktree required')
            self.require_current()
        except (Stop,ValueError,OSError):
            raise Stop('evidence_publication_failed') from None

    def validate_files(self):
        if json.loads((self.root/'evidence.json').read_bytes()) != SPEC:
            raise ValueError('evidence manifest')
        for name in filter(None,self._git('ls-files','-z').split('\0')):
            if name!='evidence.json' and not re.fullmatch(r'runs/[0-9a-f]{64}/(?:root/(?:[0-9]{6}|checkpoint)\.json|episode-[0-9]{4}/(?:[0-9]{6}|checkpoint)\.json)',name):
                raise ValueError('evidence-only branch')
            p=self.root/name
            if p.is_symlink() or any(x.is_symlink() for x in p.parents if x!=self.root.parent):
                raise ValueError('evidence symlink')

    def publish_episode(self, child, root_journal, *, source_root=None):
        """Scan before copying; immutable existing files; exact-SHA publication."""
        self.evidence=PublicationJournal(root_journal)
        try:
            self.require_current()
            verify(child)
            source_root=Path(source_root or root_journal.directory)
            if source_root==root_journal.directory:frames(source_root,root_journal)
            else:verify(source_root)
            identity=hashlib.sha256(str(source_root).encode()).hexdigest()
            dest=self.root/'runs'/identity
            source={dest/'root'/p.name:p for p in sorted(source_root.glob('[0-9]*.json'))}
            if (source_root/'checkpoint.json').exists():source[dest/'root'/'checkpoint.json']=source_root/'checkpoint.json'
            source.update({dest/child.name/p.name:p for p in sorted(child.glob('*.json'))})
            # Nothing is staged, copied or pushed until ALL files pass.
            for target,p in source.items():
                if p.is_symlink():raise ValueError('symlink')
                scan(str(target.relative_to(self.root)),p.read_bytes())
                if target.exists() and target.read_bytes()!=p.read_bytes():raise ValueError('immutable evidence')
            paths=[]
            for target,p in source.items():
                if not target.exists():
                    target.parent.mkdir(parents=True,exist_ok=True)
                    with target.open('xb') as f:
                        f.write(p.read_bytes());f.flush();os.fsync(f.fileno())
                    paths.append(target)
            if paths:
                parent=self.base
                self._git('add','--',*[str(p.relative_to(self.root)) for p in paths])
                self._git('commit','-m','Experiment A evidence: '+child.name)
                commit=self._git('rev-parse','HEAD')
                self.publication_local(commit,parent)
                try:self._git('push','origin',commit+':refs/heads/'+BRANCH)
                except Stop:
                    self.confirm_publication(commit,parent)
                else:
                    outcome=self.observe_publication(commit,parent,dict(attempt=0,delay_seconds=0,phase='initial'))
                    if outcome!='exact_commit':self.confirm_publication(commit,parent)
            root_journal.write('episode_published',dict(episode=child.name,branch=BRANCH,commit=self.base,
                checkpoint=verify(child),credential_scan='zero_matches'))
        except BaseException as error:
            self.failed=True
            if isinstance(error,Stop) and error.reason=='evidence_credential_scan_failed':raise
            if isinstance(error,(Stop,OSError,ValueError,KeyError,TypeError)):
                raise Stop('evidence_publication_failed') from None
            raise
