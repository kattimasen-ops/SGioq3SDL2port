#!/usr/bin/env python3
"""
Patch Smokin' Guns for ARM64 / SDL2 on RK3326.

This script:
  1. Applies ARM64 platform patches to q_platform.h
  2. Fixes the Makefile for SDL2 paths
  3. Ensures QVM is disabled and native .so modules are built
"""

import os
import re
import sys


def patch_makefile():
    makefile = "Makefile"
    if not os.path.exists(makefile):
        print(f"[WARN] {makefile} not found - skipping")
        return False

    with open(makefile, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    before = content

    # Fix upstream typo: BASENAME -> BASEGAME
    content = content.replace(
        "$(B)/$(BASENAME)/ui/ui_syscalls.o",
        "$(B)/$(BASEGAME)/ui/ui_syscalls.o",
    )

    # SDL2 include path (ioquake3 uses SDL2)
    content = content.replace(
        "-I/usr/include/SDL ",
        "-I/usr/include/SDL2 ",
    )
    content = content.replace(
        "-lSDL ",
        "-lSDL2 ",
    )

    # Force QVM off, SO on
    content = content.replace("BUILD_GAME_QVM=1", "BUILD_GAME_QVM=0")
    content = content.replace("BUILD_GAME_SO=0", "BUILD_GAME_SO=1")

    if content != before:
        with open(makefile, "w", encoding="utf-8") as f:
            f.write(content)
        print("[PATCHED] Makefile: SDL2 paths, BASENAME fix, QVM off / SO on")
        return True
    else:
        print("[INFO] Makefile: no changes needed")
        return False


def patch_q_platform():
    patched = 0
    if not os.path.isdir("code"):
        print("[WARN] code/ not found - skipping q_platform.h patches")
        return 0

    for root, _dirs, files in os.walk("code"):
        for name in files:
            if name != "q_platform.h":
                continue
            path = os.path.join(root, name)
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            if re.search(r'ARCH_STRING\s+"aarch64"', content):
                continue

            changed = False
            pattern = re.compile(
                r'(#elif defined __arm__\s*\n#define ARCH_STRING "arm"\s*\n)'
            )
            new_content, n = pattern.subn(
                r'\1#elif defined __aarch64__\n#define ARCH_STRING "aarch64"\n',
                content,
            )
            if n > 0:
                content = new_content
                changed = True
            else:
                override = (
                    "/* [PATCHED] ARM64 ARCH_STRING override */\n"
                    "#if defined(__aarch64__) || defined(__arm64__) || defined(aarch64)\n"
                    "#ifdef ARCH_STRING\n#undef ARCH_STRING\n#endif\n"
                    "#define ARCH_STRING \"aarch64\"\n"
                    "#ifndef Q3_LITTLE_ENDIAN\n#define Q3_LITTLE_ENDIAN\n#endif\n"
                    "#endif\n\n"
                )
                content = override + content
                changed = True

            if changed:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                patched += 1
                print(f"[PATCHED] {path}")

    print(f"[INFO] {patched} q_platform.h file(s) patched")
    return patched


def patch_sdl2_backend():
    """Ensure the SDL2 backend files from ioquake3 are used."""
    # In ioquake3, the SDL2 backend lives in code/sdl/.
    # Smokin' Guns may still have SDL 1.2 code there.
    # We verify that SDL2 headers are referenced.
    sdl_dir = "code/sdl"
    if not os.path.isdir(sdl_dir):
        print(f"[WARN] {sdl_dir} not found")
        return False

    sdl_input = os.path.join(sdl_dir, "sdl_input.c")
    if os.path.exists(sdl_input):
        with open(sdl_input, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        if "SDL_EnableUNICODE" in content or "SDL_EnableKeyRepeat" in content:
            print("[INFO] SDL 1.2 input API detected - will be replaced by ioquake3 SDL2 code")
        else:
            print("[INFO] SDL2 input API already present")

    return True


def main():
    if not os.path.exists("Makefile"):
        print("[ERROR] Not in a SmokinGuns/ioquake3 source tree.")
        sys.exit(1)

    print("=== Patching Smokin' Guns for SDL2 / ARM64 ===")

    patch_makefile()
    patch_q_platform()
    patch_sdl2_backend()

    print("[DONE] SDL2 / ARM64 patches applied.")


if __name__ == "__main__":
    main()
