"""Legacy entry point. Collect real evidence instead of rendering canned PASS logs."""
from collect_evidence import main

if __name__ == "__main__":
    print("Use scripts/collect_evidence.py. This compatibility entry point runs the same verification.")
    main()
