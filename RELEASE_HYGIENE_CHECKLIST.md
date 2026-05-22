# Pre-Release Hardening Checklist (CI Hygiene)

This is the definitive checklist for preparing the Veklom BYOS bundle (and associated packages) for public release. It ensures security, reproducibility, legal compliance, and buyer trust.

## 1) Strip secrets from Git history
*Scan now:* `git log -p | grep -iE '(api|secret|token|password)'` (quick smoke check)

**Rewrite safely (preferred):**
```bash
pipx install git-filter-repo
# Example: remove .env and replace leaked token values everywhere
git filter-repo --path .env --invert-paths
git filter-repo --replace-text replacements.txt   # maps old->new redactions
```

*Alternative (BFG):*
```bash
java -jar bfg.jar --delete-files .env --replace-text replacements.txt  repo.git
```
* Rotate keys that ever touched the repo, even if rewritten.
* Add a pre-commit hook to block future leaks (e.g., detect-secrets or gitleaks).

## 2) Make builds reproducible (bit‑for‑bit)
* **Pin toolchains:** lock files + exact versions (e.g., requirements.txt, poetry.lock, package-lock.json, Docker base image digest).
* **Set build timestamps:** `export SOURCE_DATE_EPOCH=$(git log -1 --pretty=%ct)`.
* **Deterministic flags:** disable embed‑paths/randomness; prefer sorted outputs.
* **Record provenance:** keep build/ manifest with compiler versions, OS, checksums:
  `sha256sum dist/* > dist/SHA256SUMS`

## 3) License + notices (legal hygiene)
* Put a root `LICENSE` (MIT/Apache‑2.0/BSD/etc.).
* If you choose Apache‑2.0, include a `NOTICE` file and carry through third‑party NOTICE obligations.
* Add a short `THIRD_PARTY_LICENSES.md` table (name, license, link).

## 4) Ship an SBOM with every release
SPDX (txt/json) or CycloneDX (json/xml)—both are standard.

**Example (CycloneDX for Node/Python):**
```bash
# Node
npm install -g @cyclonedx/cyclonedx-npm
cyclonedx-npm --output-file sbom.json

# Python (pip)
pip install cyclonedx-bom
cyclonedx-py --format json --outfile sbom.json
```
* Attach `sbom.json` to the GitHub/GitLab release artifacts.

## 5) Release artifacts + integrity
* **Artifacts:** zipped binaries/images + SHA256SUMS + sbom.json + LICENSE + (if Apache) NOTICE.
* **Sign (optional but ideal):** `cosign sign-blob` or `gpg --sign` for tarballs.
* **Publish checks:** CI step that verifies checksums and reproducibility on a clean runner.

## 6) GitHub repo settings (fast wins)
* **Branch protection:** require PR reviews + status checks.
* **Secret scanning:** enable GitHub Advanced Security (or free secret scanning if available).
* **Security policy:** add `.github/SECURITY.md` with contact/process.
* **Dependabot:** enable version + security updates.

## 7) Minimal docs buyers expect
* `README.md`: what it is, how to run, support matrix, quickstart.
* `RELEASE_NOTES.md`: bullets of changes and any migration notes.
* `COMPLIANCE.md` (optional): how you generate SBOM/provenance and how keys/logs are handled.
