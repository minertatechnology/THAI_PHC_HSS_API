#!/bin/bash
# =============================================================
# K6 Load Test Runner for Kubernetes
# =============================================================
# รัน k6 test ภายใน k8s cluster เพื่อหลีกเลี่ยง network bottleneck
#
# Usage:
#   bash tests/k6s/run-k8s.sh <project> <test_type>
#   bash tests/k6s/run-k8s.sh thaiphc2 smoke
#   bash tests/k6s/run-k8s.sh smartosmapi stress
#   bash tests/k6s/run-k8s.sh elearning admin
#
# Projects: thaiphc2, smartosmapi, elearning
# Tests:    smoke, test, stress, admin
#
# Options:
#   --save    บันทึก logs ลงไฟล์ใน results/<project>/cluster/
#   --delete  ลบ job เก่าถ้ามีอยู่ (default: ถามก่อน)
# =============================================================

set -euo pipefail

NAMESPACE="aorsormor-system"
IMAGE="registry.digitalocean.com/minerta-k8s/k6-loadtest:latest"
PROJECT="${1:-}"
TEST_TYPE="${2:-}"
SAVE_RESULTS=false
AUTO_DELETE=false

# Parse optional flags
for arg in "$@"; do
  case "$arg" in
    --save) SAVE_RESULTS=true ;;
    --delete) AUTO_DELETE=true ;;
  esac
done

# --- Validation ---
if [[ -z "$PROJECT" || -z "$TEST_TYPE" ]]; then
  echo "Usage: bash tests/k6s/run-k8s.sh <project> <test_type> [--save] [--delete]"
  echo ""
  echo "Projects: thaiphc2, smartosmapi, elearning"
  echo "Tests:    smoke, test, stress, admin"
  echo ""
  echo "Examples:"
  echo "  bash tests/k6s/run-k8s.sh thaiphc2 smoke"
  echo "  bash tests/k6s/run-k8s.sh thaiphc2 stress --save"
  echo "  bash tests/k6s/run-k8s.sh smartosmapi admin --save --delete"
  exit 1
fi

if [[ ! "$PROJECT" =~ ^(thaiphc2|smartosmapi|elearning)$ ]]; then
  echo "ERROR: Invalid project '$PROJECT'. Use: thaiphc2, smartosmapi, elearning"
  exit 1
fi

if [[ ! "$TEST_TYPE" =~ ^(smoke|test|stress|admin|capacity-1k|capacity-2k|capacity-3k|capacity-5k|capacity-10k|capacity-20k)$ ]]; then
  echo "ERROR: Invalid test type '$TEST_TYPE'. Use: smoke, test, stress, admin, capacity-1k, capacity-2k, capacity-3k, capacity-5k, capacity-10k, capacity-20k"
  exit 1
fi

JOB_NAME="k6-${PROJECT}-${TEST_TYPE}"

# Map capacity test types to script + env var
CAPACITY_LEVEL=""
case "$TEST_TYPE" in
  capacity-1k)
    SCRIPT_PATH="${PROJECT}/capacity.js"
    CAPACITY_LEVEL="1000"
    ;;
  capacity-2k)
    SCRIPT_PATH="${PROJECT}/capacity.js"
    CAPACITY_LEVEL="2000"
    ;;
  capacity-3k)
    SCRIPT_PATH="${PROJECT}/capacity.js"
    CAPACITY_LEVEL="3000"
    ;;
  capacity-5k)
    SCRIPT_PATH="${PROJECT}/capacity.js"
    CAPACITY_LEVEL="5000"
    ;;
  capacity-10k)
    SCRIPT_PATH="${PROJECT}/capacity.js"
    CAPACITY_LEVEL="10000"
    ;;
  capacity-20k)
    SCRIPT_PATH="${PROJECT}/capacity.js"
    CAPACITY_LEVEL="20000"
    ;;
  *)
    SCRIPT_PATH="${PROJECT}/${TEST_TYPE}.js"
    ;;
esac

# --- Determine env vars based on project ---
case "$PROJECT" in
  thaiphc2)
    BASE_URL_KEY="THAIPHC2_BASE_URL"
    EXTRA_ENV=""
    ;;
  smartosmapi)
    BASE_URL_KEY="SMARTOSM_BASE_URL"
    EXTRA_ENV='            - name: LOGIN_URL
              valueFrom:
                configMapKeyRef:
                  name: k6-loadtest-config
                  key: SMARTOSM_LOGIN_URL'
    ;;
  elearning)
    BASE_URL_KEY="ELEARNING_BASE_URL"
    EXTRA_ENV='            - name: LOGIN_URL
              valueFrom:
                configMapKeyRef:
                  name: k6-loadtest-config
                  key: ELEARNING_LOGIN_URL'
    ;;
esac

# --- Check if job already exists ---
if kubectl get job "$JOB_NAME" -n "$NAMESPACE" &>/dev/null; then
  if [[ "$AUTO_DELETE" == "true" ]]; then
    echo "Deleting existing job '$JOB_NAME'..."
    kubectl delete job "$JOB_NAME" -n "$NAMESPACE" --wait=true
  else
    echo "Job '$JOB_NAME' already exists."
    echo "Delete it first? (y/n)"
    read -r answer
    if [[ "$answer" == "y" ]]; then
      kubectl delete job "$JOB_NAME" -n "$NAMESPACE" --wait=true
    else
      echo "Aborted."
      exit 1
    fi
  fi
fi

# --- Set resource limits based on test type ---
if [[ -n "$CAPACITY_LEVEL" ]]; then
  REQ_CPU="2000m"; REQ_MEM="2Gi"; LIM_CPU="4000m"; LIM_MEM="4Gi"
else
  REQ_CPU="200m"; REQ_MEM="256Mi"; LIM_CPU="1000m"; LIM_MEM="512Mi"
fi

# --- Generate Job YAML ---
JOB_YAML=$(cat <<EOF
apiVersion: batch/v1
kind: Job
metadata:
  name: ${JOB_NAME}
  namespace: ${NAMESPACE}
  labels:
    app: k6-loadtest
    project: ${PROJECT}
    test-type: ${TEST_TYPE}
spec:
  backoffLimit: 0
  ttlSecondsAfterFinished: 3600
  template:
    metadata:
      labels:
        app: k6-loadtest
        project: ${PROJECT}
        test-type: ${TEST_TYPE}
    spec:
      restartPolicy: Never
      containers:
      - name: k6
        image: ${IMAGE}
        command: ["k6", "run", "/scripts/${SCRIPT_PATH}"]
        resources:
          requests:
            cpu: "${REQ_CPU}"
            memory: "${REQ_MEM}"
          limits:
            cpu: "${LIM_CPU}"
            memory: "${LIM_MEM}"
        env:
            - name: BASE_URL
              valueFrom:
                configMapKeyRef:
                  name: k6-loadtest-config
                  key: ${BASE_URL_KEY}
            - name: USERNAME
              valueFrom:
                configMapKeyRef:
                  name: k6-loadtest-config
                  key: USERNAME
            - name: PASSWORD
              valueFrom:
                configMapKeyRef:
                  name: k6-loadtest-config
                  key: PASSWORD
            - name: CLIENT_ID
              valueFrom:
                configMapKeyRef:
                  name: k6-loadtest-config
                  key: CLIENT_ID
            - name: USER_TYPE
              valueFrom:
                configMapKeyRef:
                  name: k6-loadtest-config
                  key: USER_TYPE
            - name: RESULT_MODE
              valueFrom:
                configMapKeyRef:
                  name: k6-loadtest-config
                  key: RESULT_MODE
            - name: ORIGIN_HOST
              value: ""
            - name: CAPACITY_LEVEL
              value: "${CAPACITY_LEVEL}"
${EXTRA_ENV}
EOF
)

# --- Apply ConfigMap first (idempotent) ---
echo "=== Applying ConfigMap ==="
kubectl apply -f "$(dirname "$0")/../../k8s/k6-loadtest-job.yaml"

# --- Create Job ---
echo ""
echo "=== Creating Job: ${JOB_NAME} ==="
echo "    Project:  ${PROJECT}"
echo "    Test:     ${TEST_TYPE}"
echo "    Script:   ${SCRIPT_PATH}"
echo ""
echo "$JOB_YAML" | kubectl apply -f -

# --- Wait & stream logs ---
echo ""
echo "=== Waiting for pod to start... ==="
kubectl wait --for=condition=ready pod -l "job-name=${JOB_NAME}" -n "$NAMESPACE" --timeout=120s 2>/dev/null || true

echo ""
echo "=== K6 Output ==="
echo "=================================================="
kubectl logs -f "job/${JOB_NAME}" -n "$NAMESPACE"
echo "=================================================="

# --- Get job status ---
echo ""
JOB_STATUS=$(kubectl get job "$JOB_NAME" -n "$NAMESPACE" -o jsonpath='{.status.conditions[0].type}' 2>/dev/null || echo "Unknown")
echo "Job status: ${JOB_STATUS}"

# --- Save results ---
if [[ "$SAVE_RESULTS" == "true" ]]; then
  RESULTS_DIR="$(dirname "$0")/results/${PROJECT}/cluster"
  mkdir -p "$RESULTS_DIR"

  # Save full output
  RESULT_FILE="${RESULTS_DIR}/${TEST_TYPE}-output.txt"
  kubectl logs "job/${JOB_NAME}" -n "$NAMESPACE" > "$RESULT_FILE"
  echo "Full output saved to: ${RESULT_FILE}"

  # Extract JSON summary (between markers)
  JSON_FILE="${RESULTS_DIR}/${TEST_TYPE}-summary.json"
  if grep -q '###JSON_SUMMARY_START###' "$RESULT_FILE"; then
    sed -n '/###JSON_SUMMARY_START###/,/###JSON_SUMMARY_END###/p' "$RESULT_FILE" \
      | grep -v '###JSON_SUMMARY' > "$JSON_FILE"
    echo "JSON summary saved to: ${JSON_FILE}"
    echo ""
    echo "=== Quick Stats ==="
    # Extract key metrics from JSON
    if command -v python3 &>/dev/null; then
      python3 -c "
import json, sys
with open('${JSON_FILE}') as f:
    d = json.load(f)
m = d.get('metrics', {})
reqs = m.get('http_reqs', {}).get('values', {})
dur = m.get('http_req_duration', {}).get('values', {})
checks = m.get('checks', {}).get('values', {})
iters = m.get('iterations', {}).get('values', {})
vus = m.get('vus_max', {}).get('values', {})
print(f\"  VUs:          {vus.get('max', 'N/A')}\")
print(f\"  Requests:     {reqs.get('count', 'N/A')}\")
print(f\"  Throughput:   {reqs.get('rate', 0):.1f} req/s\")
print(f\"  Iterations:   {iters.get('count', 'N/A')}\")
print(f\"  Avg Duration: {dur.get('avg', 0):.0f}ms\")
print(f\"  p(95):        {dur.get('p(95)', 0):.0f}ms\")
print(f\"  Max:          {dur.get('max', 0):.0f}ms\")
print(f\"  Pass Rate:    {checks.get('rate', 0)*100:.1f}%\")
" 2>/dev/null || echo "  (install python3 for quick stats)"
    fi
  else
    echo "WARNING: No JSON summary markers found in output"
  fi
fi

echo ""
echo "=== Done ==="
echo "To delete job: kubectl delete job ${JOB_NAME} -n ${NAMESPACE}"
echo ""
if [[ "$SAVE_RESULTS" == "true" ]]; then
  echo "Files saved:"
  echo "  ${RESULT_FILE}   (full k6 text output)"
  echo "  ${JSON_FILE}     (JSON summary - download via Termius)"
fi
