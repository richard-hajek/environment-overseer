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

  if (( ${#FAILURES[@]} > 0 )) ; then
    exit 1
  else
    exit 0
  fi
}

function test_limit {
  settime "00:00:00"
  prepare "limit.json"
  startoverseer
  overseer --enable limit
  settime "01:00:00"
  overseer --tick
  announce "limit" "`overseer -l | grep -q disabled; echo $?`"
  overseer --stop
}

function test_control {
  settime "00:00:00"
  prepare "limit.json"
  startoverseer
  announce "initial disable" "`overseer -l | grep -q disabled; echo $?`"
  overseer --enable limit
  announce "manual enable" "`overseer -l | grep -q 'enabled!'; echo $?`"
  overseer --disable limit
  announce "manual disable" "`overseer -l | grep -q 'disabled'; echo $?`"
  overseer --stop
}

function test_interrupt {
  settime "00:00:00"
  prepare "inter.json"
  sleep 1
  startoverseer
  overseer --enable inter
  settime "01:00:00"
  overseer --tick
  announce "interrupt" "`overseer -l | grep -q 'interrupt'; echo $?`"
  settime "02:00:00"
  sleep 4 # for some reasons theses sleeps are necessary /shrug
  overseer --tick
  sleep 4
  announce "interrupt end" "`overseer -l | grep -q 'disabled'; echo $?`"
  overseer --stop
}

# The sleeps everywhere are necessary because they seem to fix issues with bad timing

sleep 2
test_limit && sleep 3
test_control && sleep 3
test_interrupt && sleep 3
final