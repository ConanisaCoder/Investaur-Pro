#!/usr/bin/env python3
"""INVESTAUR PRO — Entry point. Run: python main.py  or  python app.py"""

import sys

if __name__ == "__main__":
    try:
        from app import main
        main()
    except ImportError as e:
        print("Missing dependency:", e, file=sys.stderr)
        print("\nInstall with: pip install -r requirements.txt", file=sys.stderr)
        print("Or use the venv: .venv/bin/python main.py", file=sys.stderr)
        sys.exit(1)
