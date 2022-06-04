#!/bin/bash

if [ -z $SF ]; then
  echo "Please set \$SF (scale factor)" >&2
  exit -1
fi

sf="$SF"
database="sf${sf//./_}"
cd "tables_$database"
for table in $(ls *.tbl); do
    table=${table%.tbl}
    echo $table
    sed -e 's/|$//' $table.tbl | psql -d $database -c "copy $table from STDIN (delimiter '|');"
done
