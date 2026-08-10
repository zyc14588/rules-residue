set shell := ["bash", "-eu", "-o", "pipefail", "-c"]

validate:
    python3 tools/validate_project.py

test:
    python3 -m unittest discover -s tests -p "test_*.py" -v

acceptance:
    python3 tools/run_acceptance.py

lock:
    python3 tools/update_lock.py

package:
    python3 tools/build_package.py

clean:
    python3 -c "from pathlib import Path; [p.unlink() for p in Path('dist').glob('*.trpgpkg')]"
