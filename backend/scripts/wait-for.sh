#!/usr/bin/env bash
# =============================================================================
# wait-for.sh - Wait for a service to be available before starting
# =============================================================================
# Usage: ./wait-for.sh host port [timeout] command [args...]
#
# Examples:
#   ./wait-for.sh redis 6379 60 uvicorn main:app --host 0.0.0.0
#   ./wait-for.sh postgres 5432 30 python -m backend.scripts.migrate
#
# Why this exists:
#   docker-compose depends_on only controls START ORDER, not readiness.
#   This script actually waits for the TCP port to be accepting connections.
# =============================================================================

set -e

# Parse arguments
host="$1"
shift
port="$1"
shift

# Optional timeout (default 60 seconds)
if [[ "$1" =~ ^[0-9]+$ ]]; then
    timeout="$1"
    shift
else
    timeout=60
fi

# Remaining args are the command to run
cmd="$@"

echo "⏳ Waiting for $host:$port (timeout: ${timeout}s)..."

# Wait loop
for i in $(seq 1 $timeout); do
    # Try to connect using multiple methods (nc, bash, python)
    if command -v nc >/dev/null 2>&1; then
        if nc -z "$host" "$port" 2>/dev/null; then
            echo "✅ $host:$port is available after ${i}s"
            exec $cmd
        fi
    elif command -v bash >/dev/null 2>&1; then
        if (echo > /dev/tcp/$host/$port) 2>/dev/null; then
            echo "✅ $host:$port is available after ${i}s"
            exec $cmd
        fi
    else
        # Fallback to Python (always available in our images)
        if python -c "import socket; s=socket.socket(); s.settimeout(1); s.connect(('$host', $port)); s.close()" 2>/dev/null; then
            echo "✅ $host:$port is available after ${i}s"
            exec $cmd
        fi
    fi
    
    # Show progress every 5 seconds
    if [ $((i % 5)) -eq 0 ]; then
        echo "   Still waiting... (${i}/${timeout}s)"
    fi
    
    sleep 1
done

echo "❌ Timeout: $host:$port not available after ${timeout}s" >&2
exit 1
