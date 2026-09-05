#!/usr/bin/env python3
import sys, time, re
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from enhance_all import load_indexes, resolve_pokemon
from rebuild_pokemon_256 import worker, OUT_DIR

def main():
    load_indexes()
    names=[]
    for p in sorted(OUT_DIR.glob("*.png")):
        m=re.match(r"(\d+)", p.name)
        if not m or int(m.group(1)) not in {201,412,413,555,646,649}:
            continue
        src,tag=resolve_pokemon(p.name)
        if tag=="256-addr":
            names.append(p.name)
    print(f"rebuild {len(names)} proto-mapped originals", flush=True)
    t0=time.time(); ok=skip=err=0
    with ProcessPoolExecutor(max_workers=4) as ex:
        futs=[ex.submit(worker,n) for n in names]
        for i,fut in enumerate(as_completed(futs),1):
            name,status=fut.result()
            if status.startswith("ok"): ok+=1
            elif status.startswith("skip"): skip+=1
            else:
                err+=1; print(name,status,flush=True)
            if i%100==0 or i==len(names):
                print(f"  {i}/{len(names)} ok={ok} skip={skip} err={err} {time.time()-t0:.0f}s", flush=True)
    print(f"done ok={ok} skip={skip} err={err}", flush=True)

if __name__ == "__main__":
    main()
