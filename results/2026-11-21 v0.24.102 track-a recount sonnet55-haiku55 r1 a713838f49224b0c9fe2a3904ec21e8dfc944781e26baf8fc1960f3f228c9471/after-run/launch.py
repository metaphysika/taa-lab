import runpy, sys
sys.path.insert(0, r"C:/t/track-a-run")
from run import load_keys
load_keys(r"C:/Users/lahn0/T3/taa-lab/keys.env")
S = r"C:/Users/lahn0/AppData/Local/Temp/claude/d99cd6a227119a89/81873166-4811-4161-a9f0-8a244ef54b49/scratchpad"
sys.argv = ["recount", "run", "--packets", S + "/run-build/packets.jsonl", "--receipt", S + "/receipt.json"]
runpy.run_module("exploratory.track_a.recount", run_name="__main__")
