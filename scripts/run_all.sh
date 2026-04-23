#!/bin/bash
# اسکریپت اجرای همزمان همه ماژول‌ها

echo "Starting Mothership..."
python -m mothership.api &
MOTHER_PID=$!

sleep 2

echo "Starting WebSocket Collector..."
python -m collector.websocket_client &
COLLECTOR_PID=$!

echo "Starting Dashboard..."
cd dashboard && python -m http.server 8080 &
DASHBOARD_PID=$!

echo "All services started"
echo "Mothership PID: $MOTHER_PID"
echo "Collector PID: $COLLECTOR_PID"
echo "Dashboard: http://localhost:8080"

# منتظر بمون تا Ctrl+C بخوره
wait
