"""
veklom CLI -- a tiny command-line tool for the Veklom governed inference platform.

Commands
--------
    veklom ask  "<prompt>"      One-shot completion (streams by default)
    veklom chat                 Interactive multi-turn REPL
    veklom models               List available models
    veklom providers            Show provider routing table
    veklom status               Platform health check

Auth
----
    Set VEKLOM_API_KEY in the environment, or pass --key / --token.
    Set VEKLOM_BASE_URL to override the default https://veklom.com/api/v1.

Examples
--------
    export VEKLOM_API_KEY="your-token"

    veklom ask "Summarise the Veklom governance model in one sentence"
    veklom ask "Write a haiku" --model gemini-2.5-flash --no-stream
    veklom chat
    veklom chat --session my-project
    veklom models
    veklom status
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import textwrap
import uuid

# Force UTF-8 on Windows so we can print any Unicode safely
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except AttributeError:
        pass
from typing import Optional

# Colours (graceful fallback on Windows without ANSI support)
try:
    import colorama  # type: ignore
    colorama.init()
    _ANSI = True
except ImportError:
    _ANSI = False

_R = "\033[0m"
_B = "\033[1m"
_DIM = "\033[2m"
_CYAN = "\033[36m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_RED = "\033[31m"
_MAGENTA = "\033[35m"

def _c(code: str, text: str) -> str:
    if _ANSI or sys.platform != "win32":
        return f"{code}{text}{_R}"
    return text


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_client(args: argparse.Namespace):
    """Lazily import and construct the client so the CLI starts fast."""
    from veklom.client import VeklomClient
    token = getattr(args, "key", None) or getattr(args, "token", None) or os.getenv("VEKLOM_API_KEY")
    if not token:
        _die(
            "No API key found.\n"
            "  Set VEKLOM_API_KEY, or pass --key <token>."
        )
    base = getattr(args, "base_url", None) or os.getenv("VEKLOM_BASE_URL", "https://veklom.com/api/v1")
    return VeklomClient(access_token=token, base_url=base)


def _die(msg: str, code: int = 1) -> None:
    print(_c(_RED, f"[ERR] {msg}"), file=sys.stderr)
    sys.exit(code)


def _print_meta(data: dict) -> None:
    """Print a compact governance metadata footer."""
    parts = []
    if "provider" in data:
        parts.append(f"provider={_c(_CYAN, data['provider'])}")
    if "model" in data:
        parts.append(f"model={_c(_CYAN, data['model'])}")
    if "latency_ms" in data:
        parts.append(f"latency={_c(_GREEN, str(data['latency_ms'])+'ms')}")
    if "cost_usd" in data:
        cost_val = data["cost_usd"]
        parts.append(f"cost={_c(_GREEN, f'${cost_val:.6f}')}")
    if "audit_id" in data:
        parts.append(f"audit_id={_c(_DIM, str(data['audit_id']))}")
    if "cache_hit" in data and data["cache_hit"]:
        parts.append(_c(_YELLOW, f"cache={data['cache_hit']}"))
    if parts:
        print("\n" + _c(_DIM, "  ─── ") + "  ".join(parts))


# ---------------------------------------------------------------------------
# Sub-commands
# ---------------------------------------------------------------------------

def cmd_ask(args: argparse.Namespace) -> None:
    """One-shot prompt → answer, with optional streaming."""
    prompt = " ".join(args.prompt)
    if not prompt.strip():
        _die("Provide a prompt: veklom ask \"your question here\"")

    client = _get_client(args)
    model = args.model or "llama3.2:latest"
    temperature = float(args.temperature)

    if args.no_stream:
        # Non-streaming path
        try:
            resp = client.complete(prompt, model=model, temperature=temperature)
        except Exception as exc:
            _die(str(exc))
        text = resp.get("response_text", "")
        print(text)
        if args.verbose:
            _print_meta(resp)
        if args.json:
            print(json.dumps(resp, indent=2))
    else:
        # Streaming path — prints chunks as they arrive
        print()  # blank line before answer
        try:
            had_output = False
            for chunk in client.complete_stream(prompt, model=model, temperature=temperature):
                print(chunk, end="", flush=True)
                had_output = True
            if not had_output:
                # Server didn't stream; fall back to complete()
                resp = client.complete(prompt, model=model, temperature=temperature)
                print(resp.get("response_text", ""))
                if args.verbose:
                    _print_meta(resp)
        except Exception as exc:
            _die(str(exc))
        print()  # newline after streamed content


def cmd_chat(args: argparse.Namespace) -> None:
    """Interactive multi-turn REPL."""
    client = _get_client(args)
    model = args.model or "llama3.2:latest"
    session_id = args.session or f"cli-{uuid.uuid4().hex[:8]}"

    print(_c(_B, "\n  Veklom Chat") + _c(_DIM, f"  (session: {session_id}, model: {model})"))
    print(_c(_DIM, "  Type 'exit' or Ctrl-C to quit. '/clear' resets session memory.\n"))

    while True:
        try:
            user_input = input(_c(_CYAN, "you › ")).strip()
        except (KeyboardInterrupt, EOFError):
            print(_c(_DIM, "\n  Goodbye."))
            break

        if not user_input:
            continue

        if user_input.lower() in {"exit", "quit", ":q"}:
            print(_c(_DIM, "  Goodbye."))
            break

        if user_input == "/clear":
            # Best-effort memory clear (requires auth; may 404 if not wired)
            try:
                with __import__("httpx").Client(
                    headers=client._headers, timeout=10
                ) as http:
                    http.delete(
                        f"{client.base_url}/ai/chat/memory",
                        params={"session_id": session_id},
                    )
                print(_c(_YELLOW, "  ✓ Session memory cleared."))
            except Exception:
                print(_c(_YELLOW, "  ✓ (memory clear requested)"))
            continue

        try:
            resp = client.chat(user_input, session_id=session_id, model=model)
        except Exception as exc:
            print(_c(_RED, f"  ✗ {exc}"))
            continue

        answer = resp.get("response_text", "")
        # Wrap long lines for readability
        wrapped = textwrap.fill(answer, width=88, subsequent_indent="     ")
        print(_c(_MAGENTA, "vklm") + " › " + wrapped)

        if args.verbose:
            _print_meta(resp)
        print()


def cmd_models(args: argparse.Namespace) -> None:
    """List available models."""
    client = _get_client(args)
    try:
        models = client.models()
    except Exception as exc:
        _die(str(exc))

    if args.json:
        print(json.dumps(models, indent=2))
        return

    print(_c(_B, "\n  Available Models\n"))
    fmt = "  {:<40} {:<14} {:>8}  {}"
    print(_c(_DIM, fmt.format("ID", "Provider", "Context", "Cost/1k in")))
    print(_c(_DIM, "  " + "─" * 80))
    for m in models:
        ctx = f"{m.get('context_window', '?'):,}"
        cost = f"${m.get('cost_per_1k_input', 0):.5f}"
        print(fmt.format(
            _c(_CYAN, m.get("id", "?")),
            m.get("provider", "?"),
            ctx,
            cost,
        ))
    print()


def cmd_providers(args: argparse.Namespace) -> None:
    """Show provider routing info."""
    client = _get_client(args)
    try:
        data = client.providers()
    except Exception as exc:
        _die(str(exc))

    if args.json:
        print(json.dumps(data, indent=2))
        return

    print(_c(_B, "\n  Provider Routing\n"))
    providers = data.get("providers", [])
    order = data.get("default_order", {})
    for p in providers:
        pri = order.get(p, "?")
        print(f"  {_c(_CYAN, p):<30} priority={_c(_GREEN, str(pri))}")
    print()


def cmd_status(args: argparse.Namespace) -> None:
    """Platform health check — no auth required."""
    from veklom.client import VeklomClient, VeklomError
    token = (
        getattr(args, "key", None)
        or getattr(args, "token", None)
        or os.getenv("VEKLOM_API_KEY")
        or "nokey"
    )
    base = getattr(args, "base_url", None) or os.getenv("VEKLOM_BASE_URL", "https://veklom.com/api/v1")
    client = VeklomClient(access_token=token, base_url=base)

    try:
        data = client.health()
    except VeklomError as exc:
        _die(f"Health check failed: {exc}")
    except Exception as exc:
        _die(f"Could not reach {base}: {exc}")

    status = data.get("status", "unknown")
    icon = _c(_GREEN, "[OK] ") if status == "healthy" else _c(_RED, "[ERR]")
    print(f"\n  {icon}  Platform: {_c(_B, status)}")
    for k, v in data.items():
        if k != "status":
            print(f"     {_c(_DIM, k)}: {v}")
    print()


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="veklom",
        description="Veklom governed inference CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Auth:
              Set VEKLOM_API_KEY in the environment, or pass --key <token>.
              Set VEKLOM_BASE_URL to override https://veklom.com/api/v1.

            Examples:
              veklom ask "What is Veklom?"
              veklom ask "Write a haiku" --model gemini-2.5-flash
              veklom chat --session my-session
              veklom models
              veklom status
        """),
    )

    # Global flags
    p.add_argument("--key", metavar="TOKEN", help="API key / Bearer token (overrides VEKLOM_API_KEY)")
    p.add_argument("--token", metavar="TOKEN", help="Alias for --key")
    p.add_argument("--base-url", dest="base_url", metavar="URL", help="Override API base URL")
    p.add_argument("--json", action="store_true", help="Output raw JSON")
    p.add_argument("-v", "--verbose", action="store_true", help="Print governance metadata footer")

    sub = p.add_subparsers(dest="command", metavar="<command>")
    sub.required = True

    # --- ask ---
    ask = sub.add_parser("ask", help="One-shot completion", description="Send a one-shot prompt and print the response.")
    ask.add_argument("prompt", nargs="+", help="The prompt text (no quotes needed)")
    ask.add_argument("-m", "--model", metavar="MODEL", help="Model ID (default: llama3.2:latest)")
    ask.add_argument("-t", "--temperature", metavar="FLOAT", default="0.7", help="Sampling temperature (default: 0.7)")
    ask.add_argument("--no-stream", action="store_true", help="Disable streaming, wait for full response")

    # --- chat ---
    chat = sub.add_parser("chat", help="Interactive multi-turn REPL")
    chat.add_argument("-m", "--model", metavar="MODEL", help="Model ID")
    chat.add_argument("-s", "--session", metavar="ID", help="Session ID for memory persistence")

    # --- models ---
    sub.add_parser("models", help="List available models")

    # --- providers ---
    sub.add_parser("providers", help="Show provider routing table")

    # --- status ---
    sub.add_parser("status", help="Platform health check")

    return p


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    dispatch = {
        "ask": cmd_ask,
        "chat": cmd_chat,
        "models": cmd_models,
        "providers": cmd_providers,
        "status": cmd_status,
    }

    handler = dispatch.get(args.command)
    if handler is None:
        parser.print_help()
        sys.exit(1)

    handler(args)


if __name__ == "__main__":
    main()
