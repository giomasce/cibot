#!/bin/bash

# Taken from http://stackoverflow.com/a/9699771/807307 (see there for counterindications)

SQLITE=sqlite3

if  [ -z "$1" ] ; then
        echo usage: $0  sqlite3.db
        exit
fi

DB="$1"

TABLES=`"$SQLITE" "$DB" .tables`
echo "-- $TABLES" 
echo 'BEGIN TRANSACTION;'

for TABLE in $TABLES ; do
        echo 
        echo "-- $TABLE:";
        COLS=`"$SQLITE" "$DB" "pragma table_info($TABLE)" |
        cut -d'|' -f2 `
        COLS_CS=`echo $COLS | sed 's/ /,/g'`
        echo -e ".mode insert\nselect $COLS_CS from $TABLE;\n" |
        "$SQLITE" "$DB" |
        sed "s/^INSERT INTO table/INSERT INTO $TABLE ($COLS_CS)/"
done
echo 'COMMIT;';
