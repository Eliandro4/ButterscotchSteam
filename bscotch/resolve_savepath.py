#!/usr/bin/env python3
import os
import struct
import sys

BINARY_VDF_TYPES = {
    0x00: "dict",
    0x01: "string",
    0x02: "int32",
    0x03: "float32",
    0x04: "ptr",
    0x05: "wstring",
    0x06: "color",
    0x07: "uint64",
    0x08: "end",
    0x0A: "int64",
}


def _read_name(data, pos, string_table):
    if string_table is not None:
        idx = struct.unpack_from("<I", data, pos)[0]
        pos += 4
        return (string_table[idx] if idx < len(string_table) else str(idx)), pos
    end = data.index(b"\x00", pos)
    name = data[pos:end].decode("utf-8", "replace")
    return name, end + 1


def _parse_kv(data, pos, string_table):
    result = {}
    n = len(data)
    while pos < n:
        t = data[pos]
        pos += 1
        if t == 0x08:
            break
        name, pos = _read_name(data, pos, string_table)
        kind = BINARY_VDF_TYPES.get(t, "unknown")
        if kind == "dict":
            sub, pos = _parse_kv(data, pos, string_table)
            result[name] = sub
        elif kind == "string":
            end = data.index(b"\x00", pos)
            result[name] = data[pos:end].decode("utf-8", "replace")
            pos = end + 1
        elif kind in ("int32", "ptr"):
            result[name] = struct.unpack_from("<i", data, pos)[0]
            pos += 4
        elif kind == "uint64":
            result[name] = struct.unpack_from("<Q", data, pos)[0]
            pos += 8
        elif kind == "int64":
            result[name] = struct.unpack_from("<q", data, pos)[0]
            pos += 8
        elif kind == "float32":
            result[name] = struct.unpack_from("<f", data, pos)[0]
            pos += 4
        elif kind == "color":
            result[name] = struct.unpack_from("<I", data, pos)[0]
            pos += 4
        elif kind == "wstring":
            end = data.find(b"\x00\x00", pos)
            if end == -1:
                end = n
            result[name] = data[pos:end].decode("utf-16-le", "replace")
            pos = end + 2
        else:
            break
    return result, pos


def _parse_string_table(data, offset):
    if offset <= 0 or offset >= len(data):
        return []
    count = struct.unpack_from("<I", data, offset)[0]
    pos = offset + 4
    table = []
    for _ in range(count):
        end = data.index(b"\x00", pos)
        table.append(data[pos:end].decode("utf-8", "replace"))
        pos = end + 1
    return table


def _parse_blob(blob, string_table):
    if string_table is None and _vdf is not None:
        try:
            kv = _vdf.binary_loads(blob)
        except Exception:
            kv = _parse_kv(blob, 0, string_table)[0]
    else:
        kv = _parse_kv(blob, 0, string_table)[0]
    if isinstance(kv, dict) and "appinfo" in kv and len(kv) == 1:
        return kv["appinfo"]
    return kv


def parse_appinfo(path, appid):
    with open(path, "rb") as f:
        data = f.read()
    if len(data) < 12:
        return None
    magic = struct.unpack_from("<I", data, 0)[0]
    version = magic & 0xFF
    pos = 8
    string_table = None
    if version >= 41:
        string_table_offset = struct.unpack_from("<Q", data, 8)[0]
        string_table = _parse_string_table(data, string_table_offset)
        pos = 16

    n = len(data)
    fixed = 60
    while pos + 8 <= n:
        cur_appid = struct.unpack_from("<I", data, pos)[0]
        pos += 4
        if cur_appid == 0xFFFFFFFF or cur_appid == 0:
            break
        if cur_appid != appid:
            if pos + 4 > n:
                break
            size = struct.unpack_from("<I", data, pos)[0]
            pos += 4 + size
            continue
        size = struct.unpack_from("<I", data, pos)[0]
        pos += 4
        blob_len = size - fixed
        if blob_len <= 0 or pos + fixed + blob_len > n:
            return None
        blob = data[pos + fixed:pos + fixed + blob_len]
        return _parse_blob(blob, string_table)
    return None


_CANONICAL = {
    "GameInstall", "SteamUserData", "WinAppDataLocal", "WinAppDataLocalLow",
    "WinAppDataRoaming", "WinMyDocuments", "WinSavedGames", "WinProgramData",
    "LinuxHome", "LinuxXdgDataHome", "LinuxXdgConfigHome", "MacHome",
    "MacAppSupport", "Root",
}

_ALIASES = {
    "gameinstall": "GameInstall",
    "steamuserdata": "SteamUserData",
    "steamuserbasestorage": "SteamUserData",
    "winappdatalocal": "WinAppDataLocal",
    "winappdatalow": "WinAppDataLocalLow",
    "winappdataroaming": "WinAppDataRoaming",
    "winmydocuments": "WinMyDocuments",
    "steamclouddocuments": "WinMyDocuments",
    "winsavedgames": "WinSavedGames",
    "winprogramdata": "WinProgramData",
    "linuxhome": "LinuxHome",
    "linuxxdgdatahome": "LinuxXdgDataHome",
    "linuxxdgconfighome": "LinuxXdgConfigHome",
    "machome": "MacHome",
    "macappsupport": "MacAppSupport",
    "root": "Root",
    "windowshome": "Root",
    "root_mod": "Root",
}


def pathtype_from(key):
    if key is None:
        return None
    k = key.strip().strip("%").strip()
    if k in _CANONICAL:
        return k
    return _ALIASES.get(k.lower())


def resolve_steam_account_id(client_path, appid):
    userdata = os.path.join(client_path, "userdata")
    if not os.path.isdir(userdata):
        return None
    candidates = []
    try:
        for name in os.listdir(userdata):
            if not name.isdigit():
                continue
            if os.path.isdir(os.path.join(userdata, name, str(appid))):
                candidates.append(name)
    except OSError:
        return None
    if not candidates:
        return None
    candidates.sort()
    return candidates[0]


def root_base_path(root, ctx):
    if root == "GameInstall":
        return ctx["install"]
    return os.path.join(ctx["client"], "userdata", ctx["accountid"], str(ctx["appid"]), "ac", root)


def substitute(path, ctx):
    return (path or "").replace("\\", "/") \
        .replace("{64BitSteamID}", ctx["steamid64"]) \
        .replace("{Steam3AccountID}", ctx["accountid"])


def build_patterns(appinfo):
    ufs = (appinfo.get("ufs") if isinstance(appinfo, dict) else None) or {}
    rootoverrides = []
    raw_overrides = ufs.get("rootoverrides")
    if isinstance(raw_overrides, dict):
        for ov in raw_overrides.values():
            if not isinstance(ov, dict):
                continue
            oslist = ov.get("oslist", "") or ""
            osv = ov.get("os", "") or ""
            is_windows = "windows" in (osv.lower()) or \
                any(p.strip().lower() == "windows" for p in str(oslist).split(",") if p.strip())
            if not is_windows:
                continue
            from_root = pathtype_from(ov.get("root"))
            to_root = pathtype_from(ov.get("useinstead"))
            if from_root is None or to_root is None:
                continue
            transforms = []
            raw_tf = ov.get("pathtransforms")
            if isinstance(raw_tf, dict):
                for tf in raw_tf.values():
                    if isinstance(tf, dict):
                        transforms.append((tf.get("find", ""), tf.get("replace", "")))
            rootoverrides.append({
                "from": from_root,
                "to": to_root,
                "addpath": (ov.get("addpath") or "").replace("\\", "/").strip("/"),
                "transforms": transforms,
            })

    savefiles = []
    raw_files = ufs.get("savefiles")
    if isinstance(raw_files, dict):
        for sf in raw_files.values():
            if not isinstance(sf, dict):
                continue
            platforms = sf.get("platforms")
            if isinstance(platforms, dict):
                plats = [str(v).lower() for v in platforms.values()]
                if plats and "windows" not in plats:
                    continue
            original_root = pathtype_from(sf.get("root"))
            if original_root is None:
                continue
            original_path = sf.get("path", "") or ""
            if original_path in (".", "/"):
                original_path = ""
            original_path = original_path.replace("\\", "/").strip("/")
            remap = next((r for r in rootoverrides if r["from"] == original_root), None)
            if remap:
                if remap["addpath"]:
                    local_path = remap["addpath"]
                    if original_path:
                        local_path = local_path + "/" + original_path.strip("/")
                else:
                    local_path = original_path
                for find, repl in remap["transforms"]:
                    if find:
                        local_path = local_path.replace(find, repl)
                local_root = remap["to"]
            else:
                local_root = original_root
                local_path = original_path
            savefiles.append({
                "root": local_root,
                "path": local_path,
                "pattern": sf.get("pattern", "") or "",
                "uploadRoot": original_root,
                "uploadPath": original_path,
            })
    return savefiles, rootoverrides


def resolve_savepaths(appinfo, ctx):
    savefiles, _ = build_patterns(appinfo)
    out = []
    for sf in savefiles:
        base = root_base_path(sf["root"], ctx)
        if not base:
            continue
        rel = substitute(sf["path"], ctx)
        full = os.path.join(base, rel) if rel else base
        out.append(full)
    return list(dict.fromkeys(out))


def _first_subdir(base):
    subs = [d for d in os.listdir(base)
            if os.path.isdir(os.path.join(base, d))
            and d not in ("Microsoft", "CEF", "Steam")]
    return os.path.join(base, subs[0]) if subs else base


def naive_discovery(ctx):
    appid = ctx["appid"]
    client = ctx["client"]
    data_path = ctx["data_path"]
    install = ctx["install"]

    userdata = os.path.join(client, "userdata")
    ac_dir = None
    if os.path.isdir(userdata):
        for root, _dirs, _files in os.walk(userdata):
            r = root.replace("\\", "/")
            if r.endswith("/ac/WinAppDataLocal") and ("/%s/" % appid) in r:
                ac_dir = root
                break
    if ac_dir and os.path.isdir(ac_dir):
        return _first_subdir(ac_dir)

    if data_path:
        local_appdata = os.path.join(data_path, "pfx", "drive_c", "users", "steamuser", "AppData", "Local")
        if os.path.isdir(local_appdata):
            return _first_subdir(local_appdata)
    return install


def main():
    appid = int(os.environ.get("SteamAppId", "0") or "0")
    client = os.environ.get("STEAM_COMPAT_CLIENT_INSTALL_PATH", "")
    install = os.environ.get("STEAM_COMPAT_INSTALL_PATH", "")
    data_path = os.environ.get("STEAM_COMPAT_DATA_PATH", "")
    appinfo_path = os.path.join(client, "appcache", "appinfo.vdf") if client else ""

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--appid" and i + 1 < len(args):
            appid = int(args[i + 1]); i += 2
        elif a == "--appinfo" and i + 1 < len(args):
            appinfo_path = args[i + 1]; i += 2
        elif a == "--client" and i + 1 < len(args):
            client = args[i + 1]; i += 2
        elif a == "--install" and i + 1 < len(args):
            install = args[i + 1]; i += 2
        else:
            i += 1

    if not appid:
        print("ERROR: no appid (set SteamAppId or pass --appid)", file=sys.stderr)
        sys.exit(2)

    appinfo_path = os.path.join(client, "appcache", "appinfo.vdf") if client else appinfo_path

    accountid = resolve_steam_account_id(client, appid) or "0"
    steamid64 = str((int(accountid) & 0xFFFFFFFF) | 0x110000100000000) if accountid != "0" else "0"
    ctx = {
        "appid": appid,
        "accountid": accountid,
        "steamid64": steamid64,
        "client": client,
        "install": install,
        "data_path": data_path,
    }

    candidates = []
    uses_cloud = False
    parsed_appinfo = None
    if appinfo_path and os.path.isfile(appinfo_path):
        try:
            parsed_appinfo = parse_appinfo(appinfo_path, appid)
            if parsed_appinfo:
                ufs = parsed_appinfo.get("ufs")
                savefiles = (ufs or {}).get("savefiles")
                if isinstance(savefiles, dict) and savefiles:
                    uses_cloud = True
                    candidates = resolve_savepaths(parsed_appinfo, ctx)
                else:
                    print("INFO: app %d has no Steam Cloud (ufs.savefiles empty)" % appid,
                          file=sys.stderr)
        except Exception as e:
            print("WARN: appinfo parse failed: %s" % e, file=sys.stderr)

    gamename = "game"
    if parsed_appinfo:
        cn = parsed_appinfo.get("common")
        if isinstance(cn, dict) and cn.get("name"):
            gamename = cn["name"]
    elif install:
        gamename = os.path.basename(install.rstrip("/")) or "game"

    if uses_cloud and candidates:
        existing = [p for p in candidates if os.path.isdir(p)]
        chosen = existing[0] if existing else candidates[0]
        if chosen and not os.path.isdir(chosen) and os.path.isdir(os.path.dirname(chosen)):
            chosen = os.path.dirname(chosen)
        print("INFO: Steam Cloud save path: %s" % chosen, file=sys.stderr)
    elif uses_cloud:
        chosen = naive_discovery(ctx)
        print("INFO: cloud patterns resolved to nothing; heuristic fallback: %s" % chosen,
              file=sys.stderr)
    else:
        chosen = os.path.expanduser(os.path.join("~", ".config", gamename))
        os.makedirs(chosen, exist_ok=True)
        print("INFO: not using Steam Cloud; save path = %s" % chosen, file=sys.stderr)

    print(chosen)


if __name__ == "__main__":
    main()
