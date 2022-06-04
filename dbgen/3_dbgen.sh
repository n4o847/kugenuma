#!/bin/bash

if [ -z $SF ]; then
  echo "Please set \$SF (scale factor)" >&2
  exit -1
fi

sf="$SF"
directory="tables_sf${sf//./_}"
mkdir -p $directory
cd $directory
../dbgen -s $sf -b ../dists.dss
