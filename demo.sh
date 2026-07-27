#!/usr/bin/env bash
# Quick interview walkthrough of the whole project: tests, live server,
# crash recovery, and the throughput benchmark. Run each section with
# `bash demo.sh <section>` or `bash demo.sh` for everything.
set -e

PORT=6380
DATA_DIR=/tmp/kv-demo-data

step() { echo; echo "=== $1 ==="; }

run_tests() {
    step "1. Run the test suite"
    source venv/bin/activate
    pytest tests/ -v
}

run_server_demo() {
    step "2. Start the server"
    rm -rf "$DATA_DIR"
    source venv/bin/activate
    KV_PORT=$PORT KV_DATA_DIR=$DATA_DIR python -m kvstore.server &
    SERVER_PID=$!
    sleep 1

    step "3. Talk to it over raw TCP (the actual wire protocol)"
    exec 3<>/dev/tcp/127.0.0.1/$PORT
    printf 'SET name Alice\r\n'   >&3; read -r -u3 reply; echo "SET name Alice   -> $reply"
    printf 'GET name\r\n'         >&3; read -r -u3 reply; echo "GET name         -> $reply"
    printf 'SET age 30\r\n'       >&3; read -r -u3 reply; echo "SET age 30       -> $reply"
    printf 'SCAN age name\r\n'    >&3; read -r -u3 reply; echo "SCAN age name    -> $reply"
    printf 'DELETE age\r\n'       >&3; read -r -u3 reply; echo "DELETE age       -> $reply"
    printf 'GET age\r\n'          >&3; read -r -u3 reply; echo "GET age          -> $reply"
    exec 3<&-
    exec 3>&-

    step "4. Kill -9 the server mid-run, then reopen the data directory"
    kill -9 $SERVER_PID
    sleep 1
    python -c "
from kvstore.store import KVStore
from kvstore.wal import WAL
wal = WAL(directory='$DATA_DIR/wal')
store = KVStore(wal=wal, sst_dir='$DATA_DIR/sst')
print('name survived kill -9:', store.get('name'))
"
}

run_benchmark() {
    step "5. Real measured throughput (never hardcoded)"
    source venv/bin/activate
    python benchmark.py
}

case "${1:-all}" in
    tests)    run_tests ;;
    server)   run_server_demo ;;
    bench)    run_benchmark ;;
    all)      run_tests; run_server_demo; run_benchmark ;;
    *)        echo "usage: bash demo.sh [tests|server|bench|all]"; exit 1 ;;
esac
