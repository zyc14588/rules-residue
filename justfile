set shell := ["bash", "-eu", "-o", "pipefail", "-c"]

validate:
    python3 tools/validate_project.py

test:
    python3 -m unittest discover -s tests -p "test_*.py" -v

acceptance:
    python3 tools/run_acceptance.py

codex-route request output:
    python3 tools/codex_route.py generate --request "{{request}}" --output "{{output}}"

codex-route-check route:
    python3 tools/codex_route.py check --map "{{route}}" --route-id M1-CODEX-ROUTE-BASELINE --mode ACCEPT --milestone M1 --batch-id M1-B001

codex-check:
    python3 tools/codex_route.py self-check --request .codex/routes/baseline-request.json --route-id M1-CODEX-ROUTE-BASELINE --mode ACCEPT --milestone M1 --batch-id M1-B001
    python3 -m unittest tests.test_codex_route.CodexRouteNegativeProbeTests -v

r2-validate:
    python3 tools/validate_r2_install.py

story-governance-validate:
    python3 tools/validate_story_construction_governance.py

lock:
    python3 tools/update_lock.py

package:
    python3 tools/build_package.py

clean:
    python3 -c "from pathlib import Path; [p.unlink() for p in Path('dist').glob('*.trpgpkg')]"
