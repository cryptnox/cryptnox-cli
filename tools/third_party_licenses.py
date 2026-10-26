"""
Write the licenses of the Python packages a frozen cryptnox-cli bundles.

    python tools/third_party_licenses.py OUTPUT

Run it with the interpreter of the build environment; setup.spec calls it
during the build. Starting from install_requires in setup.cfg, it follows
the requirements of each installed package that apply to this platform and
writes the name, version and declared license of every package reached,
followed by the license files the package ships, and the license of the
Python runtime.
"""

import configparser
import importlib.metadata
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SETUP_CFG = os.path.join(os.path.dirname(HERE), "setup.cfg")
LICENSE_NAME = re.compile(r"(licen[cs]e|copying|notice|authors)", re.IGNORECASE)
RULE = "=" * 78


def normalize(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def applies(requirement):
    """
    True or False for this platform, extras excluded, or None when the
    marker cannot be evaluated because packaging is not installed.
    """
    if ";" not in requirement:
        return True
    marker = requirement.split(";", 1)[1].strip()
    try:
        from packaging.markers import Marker  # pylint: disable=import-outside-toplevel
    except ImportError:
        return False if "extra" in marker else None
    return Marker(marker).evaluate({"extra": ""})


def requirement_name(requirement):
    return normalize(re.match(r"\s*([A-Za-z0-9][A-Za-z0-9._-]*)", requirement).group(1))


def root_requirements(setup_cfg):
    parser = configparser.ConfigParser()
    parser.read(setup_cfg, encoding="utf-8")
    lines = parser.get("options", "install_requires").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]


def dependency_closure(roots):
    """Installed distributions reached from roots, and required ones that are missing."""
    found, missing = {}, []
    queue = [(requirement_name(r), applies(r)) for r in roots]
    while queue:
        name, needed = queue.pop(0)
        if needed is False or name in found or name in missing:
            continue
        try:
            dist = importlib.metadata.distribution(name)
        except importlib.metadata.PackageNotFoundError:
            if needed:
                missing.append(name)
            continue
        found[name] = dist
        queue.extend((requirement_name(r), applies(r)) for r in dist.requires or [])
    return found, missing


def declared_license(dist):
    meta = dist.metadata
    expression = meta.get("License-Expression")
    if expression:
        return expression
    classifiers = [c.split("::")[-1].strip() for c in meta.get_all("Classifier") or []
                   if c.startswith("License ::") and c.strip() != "License :: OSI Approved"]
    field = (meta.get("License") or "").strip()
    if field and "\n" not in field and len(field) < 80:
        classifiers.append(field)
    return "; ".join(dict.fromkeys(classifiers)) or "not declared"


def license_texts(dist):
    texts = []
    for path in dist.files or []:
        parts = path.parts
        if not parts[0].endswith((".dist-info", ".egg-info")):
            continue
        if "licenses" in parts[1:-1] or LICENSE_NAME.search(parts[-1]):
            try:
                with open(path.locate(), encoding="utf-8", errors="replace") as f:
                    text = f.read()
            except OSError:
                continue
            if text and text not in texts:
                texts.append(text)
    return texts


def python_license():
    for name in ("LICENSE.txt", "LICENSE"):
        path = os.path.join(sys.base_prefix, name)
        if os.path.isfile(path):
            with open(path, encoding="utf-8", errors="replace") as f:
                return f.read()
    return None


def write_licenses(output, setup_cfg=SETUP_CFG):
    found, missing = dependency_closure(root_requirements(setup_cfg))
    if missing:
        raise SystemExit("Not installed in the build environment, so their licenses cannot be "
                         "collected: " + ", ".join(sorted(missing)))
    out = [
        "Third-party software in the cryptnox-cli executable",
        "",
        "The executable bundles the Python runtime and the Python packages below.",
        "Each is distributed under its own license, reproduced here.",
        "",
    ]
    runtime = python_license()
    out += [RULE, f"Python {sys.version.split()[0]}", RULE, ""]
    out += [runtime.rstrip() if runtime else "License: https://docs.python.org/3/license.html", ""]
    for name in sorted(found):
        dist = found[name]
        out += [RULE, f"{dist.metadata['Name']} {dist.version}",
                f"License: {declared_license(dist)}", RULE, ""]
        texts = license_texts(dist)
        if not texts:
            home = dist.metadata.get("Home-page") or ""
            out += [f"The installed package ships no license file. {home}", ""]
        for text in texts:
            out += [text.rstrip(), ""]
    with open(output, "w", encoding="utf-8", newline="\r\n" if os.name == "nt" else None) as f:
        f.write("\n".join(out) + "\n")
    return sorted(found)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    names = write_licenses(sys.argv[1])
    print(f"{len(names)} packages written to {sys.argv[1]}")
