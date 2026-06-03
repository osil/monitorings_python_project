#!/bin/bash

set -u

# Resolve project directory from this script location (no hardcoded path).
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"
VENV_ACTIVATE="$PROJECT_DIR/venv/bin/activate"
LOG_DIR="$PROJECT_DIR/logs"
RUN_LOG="$LOG_DIR/monitoring_$(date +%F).log"
LOCK_DIR="$PROJECT_DIR/.monitoring.lock"
PHASE_TIMEOUT_SECONDS="${PHASE_TIMEOUT_SECONDS:-180}"
LOG_RETENTION_DAYS="${LOG_RETENTION_DAYS:-30}"

mkdir -p "$LOG_DIR"
find "$LOG_DIR" -type f -name 'monitoring_*.log' -mtime "+$LOG_RETENTION_DAYS" -delete 2>/dev/null || true

# Prevent overlapping runs when a previous cycle takes longer than 10 minutes.
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
	echo "⚠️ [RMU-UOMS] ข้ามรอบนี้ เพราะรอบก่อนหน้ายังทำงานอยู่: $(date)" >> "$RUN_LOG"
	exit 0
fi

cleanup() {
	rmdir "$LOCK_DIR" >/dev/null 2>&1 || true
}
trap cleanup EXIT

run_phase() {
	phase_name="$1"
	script_name="$2"

	echo "📌 [$phase_name] กำลังรัน $script_name ..." >> "$RUN_LOG"

	python3 "$script_name" >> "$RUN_LOG" 2>&1 &
	phase_pid=$!
	phase_start_ts=$(date +%s)

	while kill -0 "$phase_pid" 2>/dev/null; do
		now_ts=$(date +%s)
		elapsed=$((now_ts - phase_start_ts))

		if [ "$elapsed" -ge "$PHASE_TIMEOUT_SECONDS" ]; then
			echo "⏱️ [TIMEOUT] $script_name ใช้เวลามากกว่า ${PHASE_TIMEOUT_SECONDS}s - ยุติการทำงาน" >> "$RUN_LOG"
			kill "$phase_pid" 2>/dev/null || true
			sleep 2
			kill -9 "$phase_pid" 2>/dev/null || true
			wait "$phase_pid" 2>/dev/null || true
			return 124
		fi

		sleep 1
	done

	wait "$phase_pid"
	return $?
}

# 1. กำหนดเส้นทางโฟลเดอร์หลักของโปรเจกต์
cd "$PROJECT_DIR" || exit 1

# 2. เปิดใช้งานระบบจำลอง Python Virtual Environment (venv)
if [ ! -f "$VENV_ACTIVATE" ]; then
	echo "❌ [RMU-UOMS] ไม่พบไฟล์ venv activate: $VENV_ACTIVATE" >> "$RUN_LOG"
	exit 1
fi
source "$VENV_ACTIVATE"

# 3. พิมพ์บันทึกเวลาเริ่มรันระบบเข้า Log File
echo "=========================================================" >> "$RUN_LOG"
echo "⏳ [RMU-UOMS] เริ่มต้นคิวงานตรวจสอบระบบรอบเวลา: $(date)" >> "$RUN_LOG"
echo "=========================================================" >> "$RUN_LOG"

# 4. ลำดับการรันเอเจนต์ทั้ง 3 ระบบ
run_phase "เฟสที่ 1" "web_agent.py"
if [ $? -ne 0 ]; then
	echo "⚠️ [เฟสที่ 1] จบแบบผิดปกติ" >> "$RUN_LOG"
fi

run_phase "เฟสที่ 2" "network_agent.py"
if [ $? -ne 0 ]; then
	echo "⚠️ [เฟสที่ 2] จบแบบผิดปกติ" >> "$RUN_LOG"
fi

run_phase "เฟสที่ 3" "printer_agent_direct.py"
if [ $? -ne 0 ]; then
	echo "⚠️ [เฟสที่ 3] จบแบบผิดปกติ" >> "$RUN_LOG"
fi

echo "=========================================================" >> "$RUN_LOG"
echo "✅ [RMU-UOMS] จบกระบวนการทำงานทุกระบบประจำรอบ: $(date)" >> "$RUN_LOG"
echo "=========================================================" >> "$RUN_LOG"

# 5. ออกจากระบบจำลอง venv
deactivate