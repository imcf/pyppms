#!/bin/bash
#
# simple script to filter facility-specific stuff from the cached responses

set -e

DEBUG="true"

debug() {
    [ -z "$DEBUG" ] && return
    echo "$@"
}

filter_pyppms() {
    TMPFILE="${1}_tmp"
    debug "Using tempfile: $TMPFILE"
    set +e # the greps below do not match for all files, so they might return non-zero
    grep -E '^(login,id,booked_hours,used_hours,last_res,last_train|Core facility ref,System id,Type,Name,Localisation,Active,Schedules,Stats,Bookable,Autonomy Required,Autonomy Required After Hours)' "$1" >"$TMPFILE"
    set -e
    grep -E '(pyppms|admin|Python Development System)' "$1" >>"$TMPFILE"
    mv "$TMPFILE" "$1"
}

filter_pyppms "tests/cached_responses/stage_0/getadmins/response.txt"
filter_pyppms "tests/cached_responses/stage_0/getsysrights/id--31.txt"
filter_pyppms "tests/cached_responses/stage_0/getgroups/response.txt"
filter_pyppms "tests/cached_responses/stage_0/getuserexp/response.txt"
filter_pyppms "tests/cached_responses/stage_0/getusers/active--true.txt"
filter_pyppms "tests/cached_responses/stage_0/getusers/response.txt"
filter_pyppms "tests/cached_responses/stage_0/getsystems/response.txt"
filter_pyppms "tests/cached_responses/stage_1/getsysrights/id--31.txt"
filter_pyppms "tests/cached_responses/stage_2/getsysrights/id--31.txt"
