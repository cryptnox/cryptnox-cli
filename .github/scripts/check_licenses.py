#!/usr/bin/env python3
"""
Check that every installed dependency is distributed under an allowed license.

Run it with the interpreter of an environment that holds the project, its
dependencies and nothing else:

    python -m venv ../license-check
    ../license-check/bin/python -m pip install .
    ../license-check/bin/python .github/scripts/check_licenses.py

Every license a distribution declares must be allowed: the License-Expression,
each "License ::" classifier, and the free-text License field. A distribution
that declares none fails. Operators in an expression are not interpreted, so
"A OR B" needs both A and B to be allowed.

A distribution that fails and has been reviewed by hand goes in EXCEPTIONS,
together with the licenses it declared at the time. If those change, the check
fails again, so the review is repeated.
"""

import importlib.metadata
import re
import sys

PROJECT = "cryptnox-cli"

ALLOWED_SPDX = {
    "0BSD",
    "Apache-2.0",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "CNRI-Python",
    "ISC",
    "MIT",
    "MIT-0",
    "MPL-2.0",
    "PSF-2.0",
    "Python-2.0",
    "Unlicense",
    "Zlib",
}

ALLOWED_CLASSIFIERS = {
    "Apache Software License",
    "BSD License",
    "ISC License (ISCL)",
    "MIT License",
    "MIT No Attribution License (MIT-0)",
    "Mozilla Public License 2.0 (MPL 2.0)",
    "Public Domain",
    "Python Software Foundation License",
    "Repoze Public License",
    "The Unlicense (Unlicense)",
    "zlib/libpng License",
}

# Values of the free-text License field that are not SPDX expressions.
ALLOWED_TEXT = {
    "Apache 2.0",
    "Apache License 2.0",
    "BSD, Public Domain",
    "BSD-derived (http://www.repoze.org/LICENSE.txt)",
    "BSD-like (http://repoze.org/license.html)",
    "Python Software Foundation License",
}

# Reviewed by hand: name -> (licenses declared at review time, reason).
EXCEPTIONS = {
    "cryptnox-sdk-py": (
        {"GNU Lesser General Public License v3 (LGPLv3)", "Other/Proprietary License", "LGPL-3.0"},
        "Cryptnox SDK, offered under the same terms as this project",
    ),
    "jsonalias": (
        set(),
        "MIT according to its project page; the wheel declares no license",
    ),
    "pyscard": (
        {"GNU Lesser General Public License v2 or later (LGPLv2+)"},
        "used as a library, unmodified",
    ),
    "solders": (
        set(),
        "Apache-2.0 according to the LICENSE file in its wheel; the metadata declares none",
    ),
}

# Installers, not dependencies of the project.
TOOLING = {"pip", "setuptools", "wheel"}

OPERATORS = {"AND", "OR", "WITH"}


def normalize(name):
    """Distribution name in the canonical form of PEP 503."""
    return re.sub(r"[-_.]+", "-", name).lower()


def declared_licenses(metadata):
    """(source, value) for every license a distribution declares."""
    found = []
    expression = (metadata.get("License-Expression") or "").strip()
    if expression:
        found.append(("expression", expression))
    for classifier in metadata.get_all("Classifier") or []:
        parts = [part.strip() for part in classifier.split("::")]
        # "License :: OSI Approved" on its own names no license
        if len(parts) > 1 and parts[0] == "License" and parts[-1] != "OSI Approved":
            found.append(("classifier", parts[-1]))
    text = (metadata.get("License") or "").strip()
    if text and text.upper() != "UNKNOWN":
        found.append(("field", text))
    return found


def spdx_allowed(expression):
    """True when every identifier in an SPDX-style expression is allowed."""
    allowed = {identifier.lower() for identifier in ALLOWED_SPDX}
    identifiers = [
        token for token in re.findall(r"[^\s()]+", expression) if token.upper() not in OPERATORS
    ]
    return bool(identifiers) and all(token.lower() in allowed for token in identifiers)


def is_allowed(source, value):
    if source == "classifier":
        return value in ALLOWED_CLASSIFIERS
    if source == "field" and value in ALLOWED_TEXT:
        return True
    return spdx_allowed(value)


def installed_distributions(path=None):
    """One distribution per name; the first found on the path wins, as for imports."""
    distributions = {}
    for distribution in importlib.metadata.distributions(path=path or sys.path):
        name = distribution.metadata["Name"]
        if name:
            distributions.setdefault(normalize(name), distribution)
    return distributions


def check(distributions):
    """Returns (report lines, failure count, notices)."""
    lines, failures, notices = [], 0, []
    exceptions = {normalize(name): entry for name, entry in EXCEPTIONS.items()}
    for key in sorted(distributions):
        if key in TOOLING or key == normalize(PROJECT):
            continue
        distribution = distributions[key]
        label = f"{distribution.metadata['Name']} {distribution.version}"
        licenses = declared_licenses(distribution.metadata)
        shown = "; ".join(value.splitlines()[0][:60] for _, value in licenses) or "none declared"
        rejected = [value for source, value in licenses if not is_allowed(source, value)]

        if key in exceptions:
            recorded, reason = exceptions[key]
            if {value for _, value in licenses} == recorded:
                lines.append(f"ok      {label:<36} {shown} (reviewed: {reason})")
                if licenses and not rejected:
                    notices.append(f"{label} passes without its exception; the entry can go")
            else:
                failures += 1
                was = "; ".join(sorted(recorded)) or "none"
                lines.append(
                    f"FAILED  {label:<36} {shown} "
                    f"(declared licenses changed since review; recorded: {was})"
                )
        elif not licenses:
            failures += 1
            lines.append(f"FAILED  {label:<36} declares no license")
        elif rejected:
            failures += 1
            lines.append(f"FAILED  {label:<36} {shown} (not allowed: {'; '.join(rejected)})")
        else:
            lines.append(f"ok      {label:<36} {shown}")

    for name in sorted(exceptions):
        if name not in distributions:
            notices.append(
                f"exception for {name} matches no installed distribution; the entry can go"
            )
    return lines, failures, notices


def main(argv):
    path = [argv[argv.index("--path") + 1]] if "--path" in argv else None
    distributions = installed_distributions(path)
    lines, failures, notices = check(distributions)
    print("\n".join(lines))
    for notice in notices:
        print("notice: " + notice)
    checked = len(lines)
    if failures:
        print(
            f"\n{failures} of {checked} distributions have a license that is not allowed. "
            "Replace the dependency, or review its license and add it to ALLOWED_* or "
            f"EXCEPTIONS in {__file__}."
        )
        return 1
    print(f"\nAll {checked} distributions have allowed licenses.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
