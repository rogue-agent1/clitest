#!/usr/bin/env python3
"""clitest - Test CLI tools with expected output assertions.

One file. Zero deps. Test your CLIs.

Usage:
  clitest.py tests.json              → run all tests
  clitest.py tests.json --verbose    → show output on pass
  clitest.py --example               → print example test file

Test file format:
  [{"name":"greet","cmd":"echo hello","expect":"hello","exit":0}]
"""

import argparse
import json
import re
import subprocess
import sys
import time

EXAMPLE = [
    {"name": "echo works", "cmd": "echo hello", "expect": "hello", "exit": 0},
    {"name": "false fails", "cmd": "false", "exit": 1},
    {"name": "date format", "cmd": "date +%Y", "match": r"^\d{4}$"},
    {"name": "env set", "cmd": "echo $HOME", "contains": "/"},
]


def run_test(test: dict) -> dict:
    name = test.get("name", test["cmd"][:40])
    start = time.monotonic()
    try:
        r = subprocess.run(test["cmd"], shell=True, capture_output=True,
                          text=True, timeout=test.get("timeout", 30))
        elapsed = time.monotonic() - start
        stdout = r.stdout.strip()
        stderr = r.stderr.strip()
        rc = r.returncode
    except subprocess.TimeoutExpired:
        return {"name": name, "pass": False, "reason": "timeout", "time": test.get("timeout", 30)}

    result = {"name": name, "pass": True, "time": round(elapsed, 3),
              "stdout": stdout, "exit": rc}

    # Check exit code
    if "exit" in test and rc != test["exit"]:
        result["pass"] = False
        result["reason"] = f"exit {rc}, expected {test['exit']}"
        return result

    # Check exact match
    if "expect" in test and stdout != test["expect"]:
        result["pass"] = False
        result["reason"] = f"output mismatch"
        result["expected"] = test["expect"]
        result["actual"] = stdout[:200]
        return result

    # Check contains
    if "contains" in test and test["contains"] not in stdout:
        result["pass"] = False
        result["reason"] = f"'{test['contains']}' not in output"
        return result

    # Check not contains
    if "not_contains" in test and test["not_contains"] in stdout:
        result["pass"] = False
        result["reason"] = f"'{test['not_contains']}' found in output"
        return result

    # Check regex match
    if "match" in test and not re.search(test["match"], stdout):
        result["pass"] = False
        result["reason"] = f"regex '{test['match']}' no match"
        return result

    # Check stderr
    if "stderr_contains" in test and test["stderr_contains"] not in stderr:
        result["pass"] = False
        result["reason"] = f"stderr missing '{test['stderr_contains']}'"
        return result

    return result


def main():
    p = argparse.ArgumentParser(description="Test CLI tools")
    p.add_argument("file", nargs="?")
    p.add_argument("-v", "--verbose", action="store_true")
    p.add_argument("--json", action="store_true")
    p.add_argument("--example", action="store_true")
    p.add_argument("--fail-fast", action="store_true")
    args = p.parse_args()

    if args.example:
        print(json.dumps(EXAMPLE, indent=2))
        return 0

    if not args.file:
        p.print_help()
        return 1

    with open(args.file) as f:
        tests = json.load(f)

    results = []
    passed = failed = 0
    start = time.monotonic()

    for test in tests:
        result = run_test(test)
        results.append(result)
        if result["pass"]:
            passed += 1
            icon = "✅"
        else:
            failed += 1
            icon = "❌"

        if not args.json:
            print(f"  {icon} {result['name']} ({result['time']:.3f}s)")
            if not result["pass"]:
                print(f"     {result.get('reason', '?')}")
                if "expected" in result:
                    print(f"     expected: {result['expected'][:60]}")
                    print(f"     actual:   {result['actual'][:60]}")
            elif args.verbose and result.get("stdout"):
                print(f"     → {result['stdout'][:60]}")

        if args.fail_fast and not result["pass"]:
            break

    total_time = time.monotonic() - start

    if args.json:
        print(json.dumps({"passed": passed, "failed": failed, "time": round(total_time, 3),
                          "results": results}, indent=2))
    else:
        print(f"\n  {passed} passed, {failed} failed ({total_time:.2f}s)")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
