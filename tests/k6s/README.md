# K6 Load Testing — thaiphc2 / smartosmapi / elearning

## โครงสร้างโปรเจค

```
scripts/
  thaiphc2/          # thai_phc_v2 API
  smartosmapi/       # Smart OSM API
  elearning/         # E-Learning Backend API
    admin.js         # Admin endpoints (ramp 10→30→50 VUs, 2m30s)
    smoke.js         # Smoke test (5 VUs, 30s)
    stress.js        # Stress test (500 VUs, 2m)
    test.js          # Load test (ramp 50→100→200 VUs, 5m)
results/
  thaiphc2/
    host/            # ผลลัพธ์จากการยิงผ่าน domain
    ip/              # ผลลัพธ์จากการยิงตรง IP
  smartosmapi/
    host/
    ip/
  elearning/
    host/
    ip/
```

## Auth Flow

| Project | Login |
|---------|-------|
| **thaiphc2** | `POST /api/v1/auth/login/json` โดยตรง |
| **smartosmapi** | Login ผ่าน thaiphc2 แล้วเอา token มาใช้กับ smartosmapi |
| **elearning** | Login ผ่าน thaiphc2 แล้ว SSO เข้า elearning (`POST /api/v1/auth/login`) |

---

## ตั้งค่า .env

### Mode 1: ยิงผ่าน Domain (Host)

```env
RESULT_MODE=host

THAIPHC2_BASE_URL=https://api-thaiphc.hss.moph.go.th
THAIPHC2_ORIGIN_HOST=

SMARTOSM_BASE_URL=https://api-smartosm.hss.moph.go.th
SMARTOSM_ORIGIN_HOST=
SMARTOSM_LOGIN_URL=https://api-thaiphc.hss.moph.go.th

ELEARNING_BASE_URL=https://api-elearning.hss.moph.go.th
ELEARNING_ORIGIN_HOST=
ELEARNING_LOGIN_URL=https://api-thaiphc.hss.moph.go.th
```

### Mode 2: ยิงตรง IP (Origin)

เปลี่ยน `BASE_URL` เป็น IP จริง แล้วใส่ `ORIGIN_HOST` เป็น domain เดิม

```env
RESULT_MODE=ip

THAIPHC2_BASE_URL=http://<THAIPHC2_IP>
THAIPHC2_ORIGIN_HOST=api-thaiphc.hss.moph.go.th

SMARTOSM_BASE_URL=http://<SMARTOSM_IP>
SMARTOSM_ORIGIN_HOST=api-smartosm.hss.moph.go.th
SMARTOSM_LOGIN_URL=http://<THAIPHC2_IP>

ELEARNING_BASE_URL=http://<ELEARNING_IP>
ELEARNING_ORIGIN_HOST=api-elearning.hss.moph.go.th
ELEARNING_LOGIN_URL=http://<THAIPHC2_IP>
```

> `ORIGIN_HOST` จะถูกส่งเป็น `Host` header เพื่อให้ server รู้ว่ายิงมาจาก domain ไหน

---

## คำสั่งรัน

### Build

```bash
docker compose build
```

### รันทีละตัว

```bash
# thaiphc2
docker compose run --rm thaiphc2-smoke
docker compose run --rm thaiphc2-admin
docker compose run --rm thaiphc2-test
docker compose run --rm thaiphc2-stress

# smartosmapi
docker compose run --rm smartosm-smoke
docker compose run --rm smartosm-admin
docker compose run --rm smartosm-test
docker compose run --rm smartosm-stress

# elearning
docker compose run --rm elearning-smoke
docker compose run --rm elearning-admin
docker compose run --rm elearning-test
docker compose run --rm elearning-stress
```

### รันทั้ง project พร้อมกัน

```bash
# รัน smoke ทุก project
docker compose run --rm thaiphc2-smoke & \
docker compose run --rm smartosm-smoke & \
docker compose run --rm elearning-smoke & \
wait

# รันทุกตัวของ thaiphc2
docker compose run --rm thaiphc2-smoke && \
docker compose run --rm thaiphc2-admin && \
docker compose run --rm thaiphc2-test && \
docker compose run --rm thaiphc2-stress
```

---

## ดู Results

ผลลัพธ์เป็น JSON อยู่ใน:

```
results/<project>/<mode>/<type>-summary.json
```

ตัวอย่าง:
- `results/thaiphc2/host/smoke-summary.json` — thaiphc2 smoke ผ่าน domain
- `results/smartosmapi/ip/admin-summary.json` — smartosmapi admin ผ่าน IP
- `results/thaiphc2/cluster/smoke-output.txt` — thaiphc2 smoke จาก k8s cluster

---

## Credentials

```
username: 1234567890123
password: password
client_id: 6acd9b4a-bc0f-4a09-b7fa-a6f5ea4d8b7f
user_type: officer
```

---

## Test Types

| Type | VUs | Duration | จุดประสงค์ |
|------|-----|----------|-----------|
| **smoke** | 5 | 30s | ทดสอบว่า API ทำงานได้ปกติ |
| **admin** | 10→30→50 | 2m30s | ทดสอบ admin/dashboard endpoints |
| **test** | 50→100→200 | 5m | ทดสอบ scaling ทีละขั้น |
| **stress** | 500 | 2m | ทดสอบโหลดสูงสุด |

---

## Mode 3: รันภายใน K8s Cluster

เพื่อหลีกเลี่ยง network bottleneck จากการยิงภายนอก สามารถรัน k6 เป็น Pod ภายใน cluster เดียวกับ API ได้

### Setup ครั้งแรก

```bash
# 1. Build & push k6 image ไป registry
cd tests/k6s
docker build -t registry.digitalocean.com/minerta-k8s/k6-loadtest:latest .
docker push registry.digitalocean.com/minerta-k8s/k6-loadtest:latest

# 2. Apply ConfigMap (แก้ service URLs ใน k8s/k6-loadtest-job.yaml ก่อน)
kubectl apply -f k8s/k6-loadtest-job.yaml
```

### แก้ Service URLs

แก้ไฟล์ `k8s/k6-loadtest-job.yaml` ให้ตรงกับ service name จริงใน cluster:

```yaml
# thaiphc2 → service/osm-thai-phc-hss-api-service
THAIPHC2_BASE_URL: "http://osm-thai-phc-hss-api-service"

# smartosmapi → service/osm-api
SMARTOSM_BASE_URL: "http://osm-api"

# elearning → service/elearning-api
ELEARNING_BASE_URL: "http://elearning-api"
```

> อยู่ namespace เดียวกัน (aorsormor-system) ไม่ต้องใส่ FQDN ยาว

### รัน Test

```bash
# รันทีละตัว
bash tests/k6s/run-k8s.sh thaiphc2 smoke
bash tests/k6s/run-k8s.sh thaiphc2 admin
bash tests/k6s/run-k8s.sh thaiphc2 test
bash tests/k6s/run-k8s.sh thaiphc2 stress

# รัน smartosmapi
bash tests/k6s/run-k8s.sh smartosmapi smoke

# รัน elearning
bash tests/k6s/run-k8s.sh elearning smoke

# บันทึกผลลัพธ์ลงไฟล์
bash tests/k6s/run-k8s.sh thaiphc2 smoke --save

# ลบ job เก่าอัตโนมัติ (ไม่ต้องถาม)
bash tests/k6s/run-k8s.sh thaiphc2 stress --save --delete
```

### ลำดับการ test แนะนำ

```bash
# Step 1: Smoke test - ตรวจว่า API ทำงานปกติ
bash tests/k6s/run-k8s.sh thaiphc2 smoke --save --delete

# Step 2: Admin test - ทดสอบ dashboard endpoints
bash tests/k6s/run-k8s.sh thaiphc2 admin --save --delete

# Step 3: Load test - ทดสอบ scaling
bash tests/k6s/run-k8s.sh thaiphc2 test --save --delete

# Step 4: Stress test - ทดสอบโหลดสูงสุด
bash tests/k6s/run-k8s.sh thaiphc2 stress --save --delete
```

### ดูผลลัพธ์

```bash
# ดู logs ของ job ที่รันอยู่
kubectl logs -f job/k6-thaiphc2-smoke -n aorsormor-system

# ดูผลที่บันทึกไว้ (ถ้าใช้ --save)
cat tests/k6s/results/thaiphc2/cluster/smoke-output.txt

# ดู job ทั้งหมด
kubectl get jobs -n aorsormor-system -l app=k6-loadtest

# ลบ job ทั้งหมด
kubectl delete jobs -n aorsormor-system -l app=k6-loadtest
```

### Rebuild image เมื่อแก้ scripts

```bash
cd tests/k6s
docker build -t registry.digitalocean.com/minerta-k8s/k6-loadtest:latest .
docker push registry.digitalocean.com/minerta-k8s/k6-loadtest:latest
```
