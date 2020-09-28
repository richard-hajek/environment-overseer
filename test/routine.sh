#!/usr/bin/env bash

export OVERSEER_PHRASE_OVERRIDE=1
export FAKETIME_TIMESTAMP_FILE="/time"

SUCCESSES=()
FAILURES=()

function overseer {
  cd /app || exit
  python -m overseer.main "$@"
}

function prepare {
  activity=$1
  rm -rf "/etc/overseer"
  overseer --prepare
  cp "/app/test/activities/${activity}" "/etc/overseer/activities/"
}

function settime {
  TIME=$1
  DATE=${2:-"2000-01-01"}
  echo "${DATE} ${TIME}" > "${FAKETIME_TIMESTAMP_FILE}"
  sleep 8
}

function startoverseer {
  echo Starting overseer
  overseer --verbose &
  sleep 1
  overseer --reset
  sleep 3
}

function announce() {
  NAME=$1
  SUCCESS=$2

  if [[ $SUCCESS == 0 ]]; then
    echo "[TEST] Test $NAME succeeded"
    SUCCESSES+=( "$NAME" )
  else
    echo "[TEST] Test $NAME failed"
    FAILURES+=( "$NAME" )
  fi
}

function final() {
  sleep 1
  echo "Succeeded: ${#SUCCESSES[@]}: "
  for t in "${SUCCESSES[@]}"; do printf "--" "-${t}\n" ; done
  echo "Failed: ${#FAILURES[@]}: "
  for t in "${FAILURES[@]}"; do printf "--" "-${t}\n" ; done
}

function test_limit {
  settime "00:00:00"
  prepare "limit.json"
  startoverseer
  overseer -e limit
  settime "01:00:00"
  overseer -t
  announce "limit" "`overseer -l | grep -q disabled; echo $?`"
  overseer -s
}

function test_control {
  settime "00:00:00"
  prepare "limit.json"
  startoverseer
  announce "initial disable" "`overseer -l | grep -q disabled; echo $?`"
  overseer -e limit
  announce "manual enable" "`overseer -l | grep -q 'enabled!'; echo $?`"
  overseer -d limit
  announce "manual disable" "`overseer -l | grep -q 'enabled!'; echo $?`"
  overseer -s
}

test_limit
test_control
final