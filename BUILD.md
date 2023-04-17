# Build

`./make.py`

# Uploading

```
STEAMUSER=
for file in */steamcmd.txt; do
  steamcmd +login $STEAMUSER +workshop_build_item "$PWD/${file}" +quit
done
```

