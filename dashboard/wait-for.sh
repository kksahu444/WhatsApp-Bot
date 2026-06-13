#!/usr/bin/env bash
# wait-for.sh host port [timeout] -- command...
host=$1; port=$2; shift 2
# allow passing optional timeout as 3rd arg (if not using --)
if [[ "$1" =~ ^[0-9]+$ ]]; then
  timeout=$1
  shift 1
else
  timeout=${WAIT_TIMEOUT:-60}
fi

# if there is a leading -- remove it
if [ "$1" = "--" ]; then shift; fi

echo "Waiting for $host:$port (timeout=${timeout})..."
for i in $(seq 1 $timeout); do
  if command -v nc >/dev/null 2>&1 && nc -z "$host" "$port" 2>/dev/null; then
    echo "$host:$port ready (nc)"
    exec "$@"
  fi
  if (echo > /dev/tcp/"$host"/"$port") >/dev/null 2>&1; then
    echo "$host:$port ready (tcp)"
    exec "$@"
  fi
  sleep 1
done
echo "Timeout waiting for $host:$port" >&2
exit 1
