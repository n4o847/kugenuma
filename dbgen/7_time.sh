#!/bin/bash

if [ -z $SF ]; then
  echo "Please set \$SF (scale factor)" >&2
  exit -1
fi

sf="$SF"
database="sf${sf//./_}"
directory="queries_${database}_without_explain"
for i in $(seq 1 10); do
    # sudo dd if=/dev/zero of=/export/data1/kusodeka.dat bs=1G count=16
    # sync; echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null
    # sudo systemctl restart postgresql-14
    echo -n $i
    time psql -d $database -f $directory/$i.sql > /dev/null
done
