#!/bin/bash
CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1}')
MEMORY_USAGE=$(free | grep Mem | awk '{print $3/$2 * 100.0}')
echo "CPU Usage: $CPU_USAGE%"
echo "Memory Usage: $MEMORY_USAGE%"

if (( $(echo "$CPU_USAGE > 75" | bc -l) )); then
    echo "CPU usage exceeded 75%. Triggering auto-scaling..."
    # Add GCP auto-scaling logic here
fi

