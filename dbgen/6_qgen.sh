#!/bin/bash

if [ -z $SF ]; then
  echo "Please set \$SF (scale factor)" >&2
  exit -1
fi

sf="$SF"
directory="queries_sf${sf//./_}"
mkdir -p $directory
cd queries
for i in $(seq 1 10); do
    echo $i
    ../qgen -d -N -x -s $sf -b ../dists.dss $i | sed -e 's/^where rownum/--where rownum/' > ../$directory/$i.sql
    # -d デフォルト
    # -N rownum 無視（なんかバグってるので取り除く）
    # -x explain
done
