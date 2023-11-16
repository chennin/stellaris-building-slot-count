# Build

`./make.py`

# Uploading

```
STEAMUSER=
for file in workshop/mod*/steamcmd.txt; do
  echo
  echo $file
  steamcmd +login $STEAMUSER +workshop_build_item "$PWD/${file}" +quit
done
```

