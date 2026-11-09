#!/usr/bin/env bash
# Reports whether the local backend (8000) and frontend (3000) answer. Read-only.
b=$(curl -s -o /dev/null -m 3 -w "%{http_code}" http://127.0.0.1:8000/api/ || true)
f=$(curl -s -o /dev/null -m 3 -w "%{http_code}" http://127.0.0.1:3000/login || true)
[ "$b" = "200" ] && echo "backend  OK  (http://127.0.0.1:8000)" || echo "backend  DOWN (HTTP ${b:-none})"
[ "$f" = "200" ] && echo "frontend OK  (http://localhost:3000)" || echo "frontend DOWN (HTTP ${f:-none})"
