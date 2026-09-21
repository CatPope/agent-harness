#!/usr/bin/env python3
"""Manifest consistency check for the harness repo.

The portability linter (check_skill.py) looks inside a skill. This one looks at
the layer above it: whether what is on disk and what the manifests claim agree.

A skill that is not listed in any manifest is never installed by install.ps1 /
install.sh. It still passes the portability linter, so nothing catches it -- it
simply is not there on the target machine, and that is only noticed much later.

Checks:
  M1  every manifest's `id` matches its filename
  M2  every skill listed in a manifest exists on disk
  M3  every skill directory under skills/<group>/ is listed in the matching
      manifest (skills/_core is exempt: it installs with every workflow)
  M4  a skills/<group>/ directory has a manifest at workflows/ or packs/
  M5  tools/check_skill.py forwards to a linter that actually exists

Standard library only. Run from the repo root:

    python tools/check_manifests.py
"""
import json
import os
import sys

OK, WARN, FAIL = "  ok ", "warn ", "FAIL "
rows = []
failed = False


def add(level, code, msg):
    global failed
    rows.append((level, code, msg))
    if level == FAIL:
        failed = True


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main(root):
    skills_dir = os.path.join(root, "skills")
    if not os.path.isdir(skills_dir):
        add(FAIL, "M0", "skills/ not found -- run this from the repo root")
        return

    # 매니페스트를 모은다. group 이름은 skills/ 아래 폴더명과 같아야 한다.
    manifests = {}          # group -> (kind, path, data)
    for kind in ("workflows", "packs"):
        d = os.path.join(root, kind)
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".json"):
                continue
            p = os.path.join(d, fn)
            data = load(p)
            stem = fn[:-5]
            # M1
            if data.get("id") != stem:
                add(FAIL, "M1", "{}/{}: id={!r} does not match the filename"
                    .format(kind, fn, data.get("id")))
            else:
                add(OK, "M1", "{}/{}: id matches filename".format(kind, fn))
            if stem in manifests:
                add(FAIL, "M1", "{}: declared twice ({} and {})"
                    .format(stem, manifests[stem][0], kind))
            manifests[stem] = (kind, p, data)

    # M2 — 매니페스트가 부르는 스킬이 실제로 있는가
    for group, (kind, p, data) in sorted(manifests.items()):
        listed = data.get("skills") or []
        if not listed:
            add(WARN, "M2", "{}/{}.json lists no skills (status={})"
                .format(kind, group, data.get("status")))
            continue
        missing = [s for s in listed
                   if not os.path.isdir(os.path.join(skills_dir, group, s))]
        if missing:
            add(FAIL, "M2", "{}/{}.json lists skills with no folder: {}"
                .format(kind, group, ", ".join(missing)))
        else:
            add(OK, "M2", "{}/{}.json: all {} skill(s) present"
                .format(kind, group, len(listed)))

    # M3 / M4 — 디스크에 있는데 아무 매니페스트도 부르지 않는 것
    for group in sorted(os.listdir(skills_dir)):
        gdir = os.path.join(skills_dir, group)
        if not os.path.isdir(gdir):
            continue
        if group == "_core":
            n = len([x for x in os.listdir(gdir)
                     if os.path.isdir(os.path.join(gdir, x))])
            add(OK, "M3", "_core: {} skill(s), installed with every workflow "
                          "-- no manifest needed".format(n))
            continue
        if group not in manifests:
            add(FAIL, "M4", "skills/{}/ has no manifest in workflows/ or packs/ "
                            "-- nothing installs it".format(group))
            continue
        listed = set(manifests[group][2].get("skills") or [])
        on_disk = set(x for x in os.listdir(gdir)
                      if os.path.isdir(os.path.join(gdir, x)))
        orphan = sorted(on_disk - listed)
        if orphan:
            add(FAIL, "M3", "skills/{}/: not listed in {}/{}.json, so never "
                            "installed: {}".format(group, manifests[group][0],
                                                   group, ", ".join(orphan)))
        else:
            add(OK, "M3", "skills/{}/: every folder is listed".format(group))

    # M5 — 런처가 가리키는 정본이 실제로 있는가
    launcher = os.path.join(root, "tools", "check_skill.py")
    canonical = os.path.join(root, "skills", "skillcraft",
                             "portable-skill-authoring", "scripts",
                             "check_skill.py")
    if not os.path.isfile(launcher):
        add(WARN, "M5", "tools/check_skill.py not found")
    elif not os.path.isfile(canonical):
        add(FAIL, "M5", "tools/check_skill.py forwards to a linter that is not "
                        "there: {}".format(os.path.relpath(canonical, root)))
    else:
        add(OK, "M5", "linter launcher resolves to the canonical copy")


if __name__ == "__main__":
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    main(os.path.abspath(root))
    print("\n=== manifest consistency ===")
    for level, code, msg in rows:
        print("  [{}] {}: {}".format(level, code, msg))
    n_fail = sum(1 for r in rows if r[0] == FAIL)
    n_warn = sum(1 for r in rows if r[0] == WARN)
    print("\n--- summary: {} check(s), {} failing, {} warning(s) ---"
          .format(len(rows), n_fail, n_warn))
    sys.exit(1 if failed else 0)
