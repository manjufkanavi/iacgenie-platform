#!/bin/bash
# ==============================================================================
# System Audit Script (macOS / Linux)
# Performs a comprehensive audit of network interfaces, open ports, active
# connections, and running processes.
# Outputs a tabular summary of collection status and the commands run.
# ==============================================================================

OS="$(uname -s)"
HOSTNAME="$(hostname)"
TIMESTAMP="$(date +"%Y-%m-%d_%H-%M-%S")"
OUTDIR="$(pwd)"
OUTFILE="$OUTDIR/audit_report_${HOSTNAME}_${TIMESTAMP}.txt"

echo "=========================================================="
echo " System Audit Initialization"
echo " OS Detected: $OS"
echo "=========================================================="
echo "Running background data collection..."

echo "Audit Timestamp: $(date)" > "$OUTFILE"
echo "Hostname: $HOSTNAME" >> "$OUTFILE"
echo "Operating System: $OS" >> "$OUTFILE"
echo "-----------------------------------------" >> "$OUTFILE"

# Variables to hold status
STATUS_NET="FAILED"
STATUS_PORTS="FAILED"
STATUS_CONNS="FAILED"
STATUS_PROCS="FAILED"

# Variables to hold executed commands
CMD_NET=""
CMD_PORTS=""
CMD_CONNS=""
CMD_PROCS=""

if [ "$OS" = "Linux" ]; then
    CMD_NET="ip a || ifconfig"
    echo -e "\n=== Network Interfaces ===" >> "$OUTFILE"
    if ip a >> "$OUTFILE" 2>/dev/null || ifconfig >> "$OUTFILE" 2>/dev/null; then STATUS_NET="PASSED"; fi

    CMD_PORTS="ss -tulpn || netstat -tulpn"
    echo -e "\n=== Open Ports (Listening) ===" >> "$OUTFILE"
    if ss -tulpn | grep LISTEN >> "$OUTFILE" 2>/dev/null || netstat -tulpn | grep LISTEN >> "$OUTFILE" 2>/dev/null; then STATUS_PORTS="PASSED"; fi

    CMD_CONNS="ss -tunp || netstat -tunp"
    echo -e "\n=== Active Network Connections ===" >> "$OUTFILE"
    if ss -tunp | grep ESTAB >> "$OUTFILE" 2>/dev/null || netstat -tunp | grep ESTABLISHED >> "$OUTFILE" 2>/dev/null; then STATUS_CONNS="PASSED"; fi

    CMD_PROCS="ps aux"
    echo -e "\n=== Running Processes ===" >> "$OUTFILE"
    if ps aux >> "$OUTFILE" 2>/dev/null; then STATUS_PROCS="PASSED"; fi
    
    TOTAL_PORTS=$(ss -tulpn 2>/dev/null | grep -c LISTEN || netstat -tulpn 2>/dev/null | grep -c LISTEN || echo 0)
    TOTAL_CONNS=$(ss -tunp 2>/dev/null | grep -c ESTAB || netstat -tunp 2>/dev/null | grep -c ESTABLISHED || echo 0)

elif [ "$OS" = "Darwin" ]; then
    CMD_NET="ifconfig"
    echo -e "\n=== Network Interfaces ===" >> "$OUTFILE"
    if ifconfig >> "$OUTFILE" 2>/dev/null; then STATUS_NET="PASSED"; fi

    CMD_PORTS="lsof -i -P -n | grep LISTEN"
    echo -e "\n=== Open Ports (Listening) ===" >> "$OUTFILE"
    if lsof -i -P -n | grep LISTEN >> "$OUTFILE" 2>/dev/null; then STATUS_PORTS="PASSED"; fi

    CMD_CONNS="netstat -an | grep ESTABLISHED"
    echo -e "\n=== Active Network Connections ===" >> "$OUTFILE"
    if netstat -an | grep ESTABLISHED >> "$OUTFILE" 2>/dev/null; then STATUS_CONNS="PASSED"; fi

    CMD_PROCS="ps aux"
    echo -e "\n=== Running Processes ===" >> "$OUTFILE"
    if ps aux >> "$OUTFILE" 2>/dev/null; then STATUS_PROCS="PASSED"; fi
    
    TOTAL_PORTS=$(lsof -i -P -n 2>/dev/null | grep -c LISTEN || echo 0)
    TOTAL_CONNS=$(netstat -an 2>/dev/null | grep -c ESTABLISHED || echo 0)

else
    echo "[-] Unsupported Operating System: $OS"
    exit 1
fi

TOTAL_PROCS=$(ps aux 2>/dev/null | wc -l | tr -d ' ' || echo 0)

# Colors for Pass/Fail output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

format_status() {
    if [ "$1" = "PASSED" ]; then
        printf "${GREEN}[ PASSED ]${NC}"
    else
        printf "${RED}[ FAILED ]${NC}"
    fi
}

echo ""
echo "=========================================================="
echo " SYSTEM AUDIT REPORT SUMMARY                              "
echo "=========================================================="
printf " %-40s | %-15s\n" "Audit Module" "Status"
echo "----------------------------------------------------------"
printf " %-40s | $(format_status $STATUS_NET)\n" "Network Interfaces Collection"
printf "   └─ Checks run: %s\n" "$CMD_NET"
echo "----------------------------------------------------------"
printf " %-40s | $(format_status $STATUS_PORTS)\n" "Open Ports (Listening) Collection"
printf "   └─ Checks run: %s\n" "$CMD_PORTS"
echo "----------------------------------------------------------"
printf " %-40s | $(format_status $STATUS_CONNS)\n" "Active Connections Collection"
printf "   └─ Checks run: %s\n" "$CMD_CONNS"
echo "----------------------------------------------------------"
printf " %-40s | $(format_status $STATUS_PROCS)\n" "Running Processes Collection"
printf "   └─ Checks run: %s\n" "$CMD_PROCS"
echo "=========================================================="
echo " Metrics Overview:"
echo " - Total Running Processes      : $TOTAL_PROCS"
echo " - Total Open Listening Ports   : $TOTAL_PORTS"
echo " - Total Active Connections     : $TOTAL_CONNS"
echo "=========================================================="
echo " Detailed report saved to:"
echo " -> $OUTFILE"
echo "=========================================================="
