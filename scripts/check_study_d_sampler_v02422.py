"""Free static CI: no Modal access, model imports, downloads or GPU use."""
import ast
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(name):
    return (ROOT/'scripts'/name).read_text()


def seed_check(source):
    """Every SamplingParams construction/clone must receive a seed locally.

    Check ordering too: a seed assignment after generate/enqueue is insufficient.
    The frozen science owner thread transports the same params via its queue.
    """
    tree = ast.parse(source)
    count = 0
    for function in ast.walk(tree):
        if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        # Do not mix assignments from nested functions into their parent scope.
        nodes = []
        def visit(node):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node is not function:
                return
            nodes.append(node)
            for child in ast.iter_child_nodes(node): visit(child)
        visit(function)
        for node in nodes:
            if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call): continue
            call = node.value
            constructor = (isinstance(call.func, ast.Name) and call.func.id == 'SamplingParams')
            clone = (isinstance(call.func, ast.Attribute) and call.func.attr == 'clone'
                     and 'get_default_sampling_params' in ast.unparse(call))
            if not (constructor or clone): continue
            count += 1
            if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
                raise AssertionError('untracked sampling params')
            name = node.targets[0].id
            seeded = any(k.arg == 'seed' and not (isinstance(k.value, ast.Constant) and k.value.value is None)
                         for k in call.keywords)
            for later in sorted((n for n in nodes if getattr(n, 'lineno', 0) > node.lineno), key=lambda n:n.lineno):
                if isinstance(later, ast.Assign):
                    for target in later.targets:
                        if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == name and target.attr == 'seed':
                            if isinstance(later.value, ast.Constant) and later.value.value is None:
                                raise AssertionError('None is not an explicit seed')
                            seeded = True
                if isinstance(later, ast.Call) and isinstance(later.func, ast.Attribute) and later.func.attr in ('generate','put','add_request'):
                    if not seeded: raise AssertionError('sampling params dispatched before explicit seed')
            if not seeded: raise AssertionError('missing explicit sampling seed')
    if count == 0: raise AssertionError('no sampling construction checked')
    return count


def child_check(source):
    tree = ast.parse(source)
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == 'Popen']
    if len(calls) != 1: raise AssertionError('review every new child launch')
    if not any(k.arg == 'env' and isinstance(k.value, ast.Name) and k.value.id == 'child_env' for k in calls[0].keywords):
        raise AssertionError('every live/merge/merged child requires explicit guarded env')
    if "child_env=load('sampler_guard','sampler_guard.py').child_env(os.environ)" not in source:
        raise AssertionError('child env must use reviewed sampler guard')
    bench = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == 'bench')
    statements = [ast.unparse(n) for n in bench.body]
    configure = next(i for i,s in enumerate(statements) if 'guard.configure()' in s)
    imported = next(i for i,s in enumerate(statements) if s.startswith('from vllm import'))
    if configure >= imported: raise AssertionError('sampler env configured after vLLM import')
    init = next(i for i,s in enumerate(statements) if 'LLM.from_engine_args' in s)
    checked = next(i for i,s in enumerate(statements) if 'guard.check_log' in s)
    request = next(i for i,s in enumerate(statements) if s.startswith('def request('))
    if not init < checked < request: raise AssertionError('native log guard must precede generation')


def main():
    runtime = read('study_d_gemma_speed_runtime_v02422.py')
    child_check(runtime)
    # Current benchmark and inherited science requests; archived launches are not enabled.
    assert seed_check(runtime) == 1
    assert seed_check(read('study_d_gemma_stages_runtime_v02420.py')) == 1
    app = read('study_d_gemma_speed_app_v02422.py')
    assert "'VLLM_USE_FLASHINFER_SAMPLER':'0'" in app
    future = read('study_d_gemma_future_serving_v02422.py')
    assert future.index('guard.configure()') < future.index("legacy = load(")
    assert 'super().__init__' in future and 'guard.check_log' in future
    assert '.child_env(parent)' in future and "if __name__" not in future
    spec = importlib.util.spec_from_file_location('guard', ROOT/'scripts/study_d_gemma_sampler_v02422.py')
    guard = importlib.util.module_from_spec(spec); spec.loader.exec_module(guard)
    assert guard.child_env({guard.VARIABLE:'1'})[guard.VARIABLE] == '0'
    fixtures = ROOT/'tests/fixtures/study_d_sampler_v02422'
    assert guard.check_log((fixtures/'healthy.log').read_text())['status'] == 'PASS'
    try: guard.check_log((fixtures/'v02421-engine.log').read_text())
    except RuntimeError: pass
    else: raise AssertionError('v02421 engine log was accepted')
    print('PASS: child environments, explicit science/benchmark seeds and native sampler log fixtures')


if __name__ == '__main__': main()
