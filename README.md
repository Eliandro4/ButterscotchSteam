# ButterscotchSteam
A Steam compatibility tool that runs GameMaker games on Linux by using [Butterscotch](https://github.com/ButterscotchRunner/Butterscotch) runner.
Instead of relying on Proton/Wine, this bundles a native Butterscotch build so supported games launch directly on Linux.

## Building
Requires CMake, Ninja, GCC, `pkg-config`, and the SDL2 + bzip2 development libraries.

On Debian/Ubuntu:
```sh
sudo apt-get install cmake ninja-build gcc pkg-config libsdl2-dev libbz2-dev
```
On Arch
```sh
sudo pacman -S cmake ninja gcc pkgconf sdl2 bzip2
```
On Fedora
```sh
sudo dnf install cmake ninja-build gcc pkgconf-pkg-config SDL2-devel bzip2-devel
```


run the build script
```sh
./build.sh
```
This produces the ready-to-install `bscotch-build/` directory.

## Installing

1. Build (or grab the `bscotch-build.zip` artifact from the nightly release).
2. Extract it into Steam's compatibility tools folder, e.g.:
   `~/.steam/steam/compatibilitytools.d/butterscotch/`
3. Restart Steam.
4. Right-click the game you want to use it → **Properties → Compatibility → Force the use of a specific Steam Play compatibility tool**, then select **Butterscotch**.

## Credits
- **Eliandro4** — author and maintainer of this Steam compatibility tool wrapper.
- **MrPowerGamerBR** and the **Butterscotch contributors** — responsible for the [Butterscotch](https://github.com/ButterscotchRunner/Butterscotch) runner.
- The VDF parsing logic in `bscotch/resolve_savepath.py` was inspired by [mexus/steam-vdf-parser](https://github.com/mexus/steam-vdf-parser), which is dual-licensed under MIT and/or Apache-2.0.
- licensed under the Mozilla Public License 2.0. (the same as butterscotch)