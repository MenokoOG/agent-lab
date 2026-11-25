#!/usr/bin/env bash
# Run every module's offline tests and print one line per folder.
# Usage: ./test_all.sh            (from the agent-lab folder, with your venv active)
set -u
cd "$(dirname "$0")"
fail=0
for dir in $(ls -d m*/ 2>/dev/null | sort -V) f1-langgraph/ f2-strands/ agentkit/; do
  [ -d "$dir" ] || continue
  case "$dir" in
    f1-langgraph/) need=langgraph ;;
    f2-strands/)   need=strands ;;
    agentkit/)     need=mcp ;;
    *)             need="" ;;
  esac
  if [ -n "$need" ] && ! python -c "import $need" 2>/dev/null; then
    printf '%-22s ----  skipped: pip install -r %srequirements.txt\n' "$dir" "$dir"
    continue
  fi
  if [ -d "${dir}tests" ]; then
    if out=$(cd "$dir" && python -m unittest discover -s tests -t . 2>&1); then
      printf '%-22s PASS  %s\n' "$dir" "$(echo "$out" | grep -E '^Ran ' | tail -1)"
    else
      printf '%-22s FAIL  (cd %s && python -m unittest discover -s tests -t . -v)\n' "$dir" "$dir"
      fail=1
    fi
  elif ls "$dir"test_*.py >/dev/null 2>&1; then
    if out=$(cd "$dir" && python -m unittest 2>&1); then
      printf '%-22s PASS  %s\n' "$dir" "$(echo "$out" | grep -E '^Ran ' | tail -1)"
    else
      printf '%-22s FAIL  (cd %s && python -m unittest -v)\n' "$dir" "$dir"
      fail=1
    fi
  else
    printf '%-22s ----  no tests (use --dry-run)\n' "$dir"
  fi
done
exit $fail
