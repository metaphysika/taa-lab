import runpy, sys, os
os.chdir(r"C:/t/track-a-resume")
sys.path.insert(0, r"C:/t/track-a-resume")
from run import load_keys
load_keys(r"C:/Users/lahn0/T3/taa-lab/keys.env")
S = r"C:/Users/lahn0/AppData/Local/Temp/claude/d99cd6a227119a89/81873166-4811-4161-a9f0-8a244ef54b49/scratchpad"
sys.argv = ["recount", "resume", "--results-folder", r"C:/t/track-a-run/results/2026-11-21 v0.24.102 track-a recount sonnet55-haiku55 r1 a713838f49224b0c9fe2a3904ec21e8dfc944781e26baf8fc1960f3f228c9471",
            "--packets", S + "/run-build/packets.jsonl", "--receipt", S + "/receipt-resume.json", "--detach-friendly"]
runpy.run_module("exploratory.track_a.recount", run_name="__main__")
