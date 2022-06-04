#!/bin/bash

if [ -z $SF ]; then
  echo "Please set \$SF (scale factor)" >&2
  exit -1
fi

sf="$SF"
database="sf${sf//./_}"
psql -d $database -f dss.ri
