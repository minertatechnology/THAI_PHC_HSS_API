# Kubernetes Deployment Guide

## 📁 ไฟล์ทั้งหมด

```
k8s/
├── app-config-once.yaml  # ใช้ครั้งเดียวตอน setup ครั้งแรก
├── app-deploy.yaml       # ใช้ทุกครั้งที่ deploy version ใหม่
├── app-deployment.yaml   # ไฟล์เดิม (เก็บไว้สำรอง)
├── app-ingress.yaml      # Ingress configuration
├── postgres-cluster.yaml # PostgreSQL setup
└── rabbitmq-cluster.yaml # RabbitMQ setup
```

## 🚀 Setup ครั้งแรก (ทำครั้งเดียว)

### 1. Setup Database และ Message Queue
```bash
kubectl apply -f k8s/postgres-cluster.yaml
kubectl apply -f k8s/rabbitmq-cluster.yaml
```

### 2. Setup Config และ Secrets (ทำครั้งเดียว)
```bash
# แก้ไขค่าใน app-config-once.yaml ก่อน:
# - POSTGRES_PASSWORD
# - RABBITMQ_PASSWORD  
# - JWT_SECRET_KEY
# - private_key.pem และ public_key.pem (วางเนื้อหาจริง)

kubectl apply -f k8s/app-config-once.yaml
```

### 3. Setup Ingress
```bash
kubectl apply -f k8s/app-ingress.yaml
```

## 🔄 Deploy Version ใหม่ (ทำทุกครั้งที่มี update)

### ขั้นตอนการ Deploy:

1. **Build Docker Image**
```bash
docker build -t registry.digitalocean.com/minerta-k8s/osm-thai-phc-hss-api:v1.7 .
```

2. **Push ไปที่ Registry**
```bash
docker push registry.digitalocean.com/minerta-k8s/osm-thai-phc-hss-api:v1.7
```

3. **แก้ไข Version ใน app-deploy.yaml**
```yaml
# เปิดไฟล์ k8s/app-deploy.yaml
# แก้แค่บรรทัดที่ 25:
image: registry.digitalocean.com/minerta-k8s/osm-thai-phc-hss-api:v1.7  # เปลี่ยนจาก v1.6 เป็น v1.7
```

4. **Apply Deployment**
```bash
kubectl apply -f k8s/app-deploy.yaml
```

5. **ตรวจสอบสถานะ**
```bash
# ดู Pod status
kubectl get pods -n aorsormor-system

# ดู Logs
kubectl logs -f deployment/osm-thai-phc-hss-api-deployment -n aorsormor-system

# ดู Deployment status
kubectl rollout status deployment/osm-thai-phc-hss-api-deployment -n aorsormor-system
```

## 🎯 คำสั่งสำคัญ

### ตรวจสอบสถานะ
```bash
# ดู Pods
kubectl get pods -n aorsormor-system

# ดู Services
kubectl get svc -n aorsormor-system

# ดู Deployments
kubectl get deployments -n aorsormor-system

# ดู Secrets
kubectl get secrets -n aorsormor-system

# ดู ConfigMaps
kubectl get configmaps -n aorsormor-system
```

### ดู Logs
```bash
# ดู logs แบบ real-time
kubectl logs -f deployment/osm-thai-phc-hss-api-deployment -n aorsormor-system

# ดู logs ของ Pod เฉพาะ
kubectl logs -f <pod-name> -n aorsormor-system

# ดู logs ย้อนหลัง 100 บรรทัด
kubectl logs --tail=100 deployment/osm-thai-phc-hss-api-deployment -n aorsormor-system
```

### Restart/Rollback
```bash
# Restart Deployment
kubectl rollout restart deployment/osm-thai-phc-hss-api-deployment -n aorsormor-system

# Rollback ไปยัง version ก่อนหน้า
kubectl rollout undo deployment/osm-thai-phc-hss-api-deployment -n aorsormor-system

# ดู history ของ rollout
kubectl rollout history deployment/osm-thai-phc-hss-api-deployment -n aorsormor-system
```

### Delete Resources
```bash
# ลบ Deployment (แต่ไม่ลบ Config)
kubectl delete -f k8s/app-deploy.yaml

# ลบทุกอย่างรวม Config (ระวัง!)
kubectl delete -f k8s/app-config-once.yaml
kubectl delete -f k8s/app-deploy.yaml
```

## 🔧 Troubleshooting

### Pod ไม่ทำงาน
```bash
# ดู Pod details
kubectl describe pod <pod-name> -n aorsormor-system

# ตรวจสอบ Events
kubectl get events -n aorsormor-system --sort-by='.lastTimestamp'
```

### Image Pull Error
```bash
# ตรวจสอบว่า Image มีใน Registry
doctl registry repository list-tags osm-thai-phc-hss-api

# Login ไปยัง DigitalOcean Registry
doctl registry login
```

### ConfigMap/Secret ผิด
```bash
# ดู ConfigMap
kubectl get configmap app-configmap -n aorsormor-system -o yaml

# ดู Secret (แบบ decode)
kubectl get secret jwt-keys-secret -n aorsormor-system -o jsonpath='{.data.JWT_SECRET_KEY}' | base64 -d

# แก้ไข ConfigMap/Secret
kubectl edit configmap app-configmap -n aorsormor-system
kubectl edit secret jwt-keys-secret -n aorsormor-system

# หรือ apply ใหม่
kubectl apply -f k8s/app-config-once.yaml
```

## 📝 Version History Template

เก็บ log การ deploy ไว้ที่นี่:

- **v1.6** (2025-10-06): Initial OAuth2/OIDC with PKCE support
- **v1.7** (YYYY-MM-DD): [อธิบาย changes]
- **v1.8** (YYYY-MM-DD): [อธิบาย changes]

## 💡 Tips

1. **ใช้ tag ที่มีความหมาย**: แทนที่จะใช้ v1.6, v1.7 ลองใช้ v1.6-oauth2, v1.7-bugfix
2. **ตรวจสอบก่อน apply**: ใช้ `kubectl diff -f k8s/app-deploy.yaml` เพื่อดู changes
3. **Rollback plan**: เก็บ image version เก่าไว้ใน Registry สำหรับ rollback
4. **Health check**: ตรวจสอบ `/` endpoint หลัง deploy ว่าทำงานปกติ
5. **Monitor logs**: ดู logs อย่างน้อย 2-3 นาทีหลัง deploy

## 🎓 Workflow สรุป

```
Code changes → Build → Push → Edit app-deploy.yaml → Apply → Monitor
     ↓          ↓       ↓              ↓               ↓        ↓
  main.py   docker  registry  change version   kubectl   logs
```
