#!/usr/bin/env python3
"""
Pytest Plugin & Cache Auditor Tool
Bypasses broken plugins, programmatically audits the test suite configuration,
and inspects the pytest test cache to report last failed tests.
"""

import os
import sys
import json
import subprocess
import shutil

# ANSI Color Codes for premium UI formatting
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
MAGENTA = "\033[35m"
RESET = "\033[0m"
BOLD = "\033[1m"


def print_banner():
    print(f"{MAGENTA}{'=' * 65}{RESET}")
    print(f"{MAGENTA}{BOLD}           Veklom OS Pytest Plugin & Cache Auditor           {RESET}")
    print(f"{MAGENTA}{'=' * 65}{RESET}")


def get_pytest_path():
    # Check for venv python/pytest
    venv_pytest = os.path.join(".venv", "Scripts", "pytest.exe") if os.name == "nt" else os.path.join(".venv", "bin", "pytest")
    if os.path.exists(venv_pytest):
        return venv_pytest
    return "pytest"


def audit_plugins():
    print(f"\n{CYAN}{BOLD}[1/3] Querying Registered & Active Pytest Plugins...{RESET}")
    pytest_bin = get_pytest_path()
    
    # We pass '-p no:pytest_ethereum' to bypass known eth_typing import failures
    cmd = [pytest_bin, "-p", "no:pytest_ethereum", "--trace-config", "-k", "not_a_real_test"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        output = result.stdout or result.stderr
        
        # Parse the active plugins block from trace-config
        in_plugins_block = False
        active_plugins = []
        for line in output.splitlines():
            if "active plugins:" in line:
                in_plugins_block = True
                continue
            if in_plugins_block:
                if line.startswith("rootdir:") or not line.strip() or line.startswith("==="):
                    in_plugins_block = False
                    continue
                # Line format: "    plugin_name   : path_or_module"
                if ":" in line:
                    parts = line.split(":", 1)
                    name = parts[0].strip()
                    loc = parts[1].strip()
                    active_plugins.append((name, loc))
                    
        if active_plugins:
            print(f"{GREEN}[OK] Successfully loaded active pytest plugin registries:{RESET}")
            for name, loc in active_plugins:
                print(f"  * {BOLD}{name:<12}{RESET} : {loc}")
        else:
            print(f"{YELLOW}[WARN] Could not parse active plugins from pytest output.{RESET}")
            
    except Exception as e:
        print(f"{RED}[ERROR] Failed to audit plugins via subprocess: {e}{RESET}")


def audit_cache():
    print(f"\n{CYAN}{BOLD}[2/3] Inspecting Pytest Test Cache (.pytest_cache)...{RESET}")
    cache_dir = os.path.join(".pytest_cache", "v", "cache")
    last_failed_file = os.path.join(cache_dir, "lastfailed")
    nodeids_file = os.path.join(cache_dir, "nodeids")
    
    if not os.path.exists(cache_dir):
        print(f"{YELLOW}[WARN] No pytest cache found. Run pytest at least once to populate the cache.{RESET}")
        return
        
    print(f"{GREEN}[OK] Cache directory located: {BOLD}.pytest_cache{RESET}")
    
    # Total tests tracked in cache
    if os.path.exists(nodeids_file):
        try:
            with open(nodeids_file, "r") as f:
                nodeids = json.load(f)
                print(f"  * Total Tracked Tests in Cache: {BOLD}{len(nodeids)}{RESET}")
        except Exception:
            pass
            
    # Check for last failed tests
    if os.path.exists(last_failed_file):
        try:
            with open(last_failed_file, "r") as f:
                last_failed = json.load(f)
                if last_failed:
                    print(f"  * {YELLOW}{BOLD}[WARN] Last Failed Tests Detected in Cache ({len(last_failed)} items):{RESET}")
                    for test_id, failed in last_failed.items():
                        if failed:
                            print(f"    - {RED}{test_id}{RESET}")
                else:
                    print(f"  * {GREEN}[OK] Last run clean! Zero failed tests detected in cache.{RESET}")
        except Exception as e:
            print(f"{RED}  [ERROR] Error reading lastfailed cache file: {e}{RESET}")
    else:
        print(f"  * {GREEN}[OK] No previous failed tests found in cache.{RESET}")


def show_pytest_guide():
    print(f"\n{CYAN}{BOLD}[3/3] Pytest Operational Guide & Best Practices:{RESET}")
    print(f"  * To run {BOLD}ONLY failed tests{RESET} from the last session:")
    print(f"    {GREEN}pytest -p no:pytest_ethereum --lf{RESET}")
    print(f"  * To run {BOLD}all tests but failed ones first{RESET}:")
    print(f"    {GREEN}pytest -p no:pytest_ethereum --ff{RESET}")
    print(f"  * To {BOLD}clear the entire pytest cache{RESET}:")
    print(f"    {GREEN}pytest -p no:pytest_ethereum --cache-clear{RESET}")
    print(f"  * To bypass the {RED}pytest_ethereum ImportError{RESET} automatically:")
    print(f"    {GREEN}Always append -p no:pytest_ethereum to your command.{RESET}")
    print(f"\n{MAGENTA}{'=' * 65}{RESET}\n")


if __name__ == "__main__":
    # Force output stream encoding to utf-8 if supported, or fall back to ascii
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass
    print_banner()
    audit_plugins()
    audit_cache()
    show_pytest_guide()
