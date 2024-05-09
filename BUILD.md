# Requirements

Python: srctools

[Diagraphers-Stellaris-Mods](https://github.com/kuyan-judith/Diagraphers-Stellaris-Mods)

# Build

```
WDI=""
for MID in 1995601384 2949397716 2762644349 1623423360 1587178040 1866576239; do
  WDI="${WDI} +workshop_download_item 281990 ${MID}"
done
steamcmd +login anonymous ${WDI} +quit
./make.py
```

# Uploading

```
STEAMUSER=
WBI=""
for file in workshop/mod*/steamcmd.txt; do
  WBI="${WBI} +workshop_build_item /code/${file}"
done
podman run -v $PWD:/code:ro -v steamcmd-root:/root/.local/share/Steam -it steamcmd/steamcmd:debian-12 \
  +login $STEAMUSER ${WBI} +quit
```

