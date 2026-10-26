"""Local-only Git remotes/worktrees for durable-state tests; no provider traffic."""
import json
from pathlib import Path
import subprocess
from experiment_a.state import SPEC


class GitStateFixture:
    def __init__(self, root, *, reconstructed=False):
        self.root = Path(root)
        self.root.mkdir(parents=True)
        self.remote, self.repo, self.state = [self.root / name for name in ('origin.git', 'run', 'state')]
        self.git('init', '--bare', str(self.remote), cwd=self.root)
        self.git('init', '-b', 'run', str(self.repo), cwd=self.root)
        self.git('config', 'user.name', 'Offline State Test')
        self.git('config', 'user.email', 'offline@example.invalid')
        self.git('config', 'commit.gpgsign', 'false')
        self.git('commit', '--allow-empty', '-m', 'Offline run checkout')
        self.git('remote', 'add', 'origin', str(self.remote))
        self.git('worktree', 'add', '--orphan', '-b', 'experiment-state', str(self.state))
        self.write('state.json', SPEC)
        totals = ('6.201251249999988', '3.6689896000000046') if reconstructed else ('0', '0')
        for path, total in zip(('ledgers/claude.json', 'ledgers/google.json'), totals):
            self.write(path, dict(estimated_api_dollars=total))
        (self.state/'step-budget.txt').write_text('0.39615025' if reconstructed else '0')
        if reconstructed:
            for provider in ('anthropic', 'google'):
                self.write('check-'+provider+'-000001.once', dict(used=True, provenance='reconstructed test fixture'))
        self.git('add', '.', cwd=self.state)
        self.git('commit', '-m', 'Offline state fixture', cwd=self.state)
        self.git('push', '-u', 'origin', 'HEAD:refs/heads/experiment-state', cwd=self.state)

    def git(self, *args, cwd=None):
        return subprocess.run(['git','-C',str(cwd or self.repo),*args],capture_output=True,
                              check=True,text=True).stdout.strip()

    def write(self, path, value):
        dest=self.state/path;dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')

    def second(self):
        path=self.root/'second-state'
        self.git('worktree','add','--detach',str(path),'origin/experiment-state')
        return path

    def refresh(self, path):
        self.git('fetch','origin','refs/heads/experiment-state',cwd=path)
        self.git('merge','--ff-only','FETCH_HEAD',cwd=path)
