# คู่มือลดขนาด Docker Image: Next.js Node.js Server → Static Files + Nginx

สรุปจากการทำจริงกับโปรเจกต์ THAI_PHC_WEB_ADMIN และ E-Learning Web
ใช้เป็นแนวทางสำหรับโปรเจกต์ Next.js อื่นๆ ที่ต้องการลดขนาด Docker Image

---

## ผลลัพธ์ที่ได้จริง

| รายการ              | ก่อน (Node.js Server)              | หลัง (Static + Nginx)           |
|---------------------|------------------------------------|---------------------------------|
| Runtime             | Bun/Node.js server port 3000      | Nginx Alpine port 3000          |
| ขนาด Image          | หลาย GB (node_modules + .next)    | 68.6 MB (THAI_PHC_WEB_ADMIN)   |
|                     |                                    | 25 MB (E-Learning Web)          |
| ลดลง               | -                                  | ~95-99%                         |
| K8s Service/Ingress | ไม่ต้องแก้                          | ไม่ต้องแก้                       |
| Port                | 3000                               | 3000 (เหมือนเดิม)               |

---

## ขั้นตอนที่ 1: ตรวจสอบว่าโปรเจกต์ทำได้หรือไม่

ก่อนเริ่มต้องตรวจสอบว่าโปรเจกต์ไม่มีสิ่งเหล่านี้:

[ต้องไม่มี]
- getServerSideProps ในหน้าใดๆ
- middleware.ts / middleware.js ที่ root
- API Routes ที่ใช้งานจริง (pages/api/)
- next/headers หรือ next/server imports ในหน้าเว็บ
- Dynamic routes ที่ใช้ fallback: true ใน getStaticPaths

[ต้องมี / เป็นอยู่แล้ว]
- ทุกหน้าเป็น Client-Side Rendering (CSR)
- ใช้ dynamic(() => import(...), { ssr: false }) หรือ useEffect fetch data
- API calls ไปที่ backend แยก (ไม่ใช้ API Routes ใน Next.js)

คำสั่งตรวจสอบ:
  grep -r "getServerSideProps" pages/
  grep -r "getStaticPaths" pages/
  find . -maxdepth 1 -name "middleware.*"
  ls pages/api/ 2>/dev/null
  grep -r "next/headers" pages/ components/
  grep -r "next/server" pages/ components/

ถ้าไม่เจอ = ทำได้

---

## ขั้นตอนที่ 2: แก้ไข next.config.js

เพิ่ม/แก้ไข 3 จุด:

### 2.1 เพิ่มตัวแปร EXPORT_MODE
```
const isExport = process.env.EXPORT_MODE === "true";
```

### 2.2 เพิ่ม output แบบมีเงื่อนไข
```
const nextConfig = {
  ...(isExport && { output: "export" }),
  ...(!isExport && { output: "standalone" }),
  // ... config อื่นๆ
};
```

### 2.3 แก้ images.unoptimized ให้รองรับ export mode
```
images: {
  unoptimized: isExport || isDev,
  // ... config อื่นๆ
},
```

### 2.4 แก้ rewrites ให้ return [] เมื่อ export mode
```
async rewrites() {
  if (isExport) return [];
  return [
    // ... rewrites ปกติ
  ];
},
```

หมายเหตุ: Static export ไม่รองรับ rewrites, redirects, headers
แต่ไม่กระทบเพราะ app เรียก API ตรงผ่าน axios อยู่แล้ว

---

## ขั้นตอนที่ 3: แก้ไข package.json build script

build script ต้องส่ง EXPORT_MODE=true เพื่อ activate output: "export"

ตัวอย่าง (Bun):
```
"build": "bun --bun ./node_modules/cross-env/src/bin/cross-env.js ENV_MODE=production NEXT_PUBLIC_ENV_MODE=production NEXT_PUBLIC_EXPORT_MODE=true NEXT_PUBLIC_DEBUG_MODE=false ./node_modules/next/dist/bin/next build"
```

ตัวอย่าง (Node.js/npm):
```
"build": "cross-env ENV_MODE=production NEXT_PUBLIC_ENV_MODE=production EXPORT_MODE=true NEXT_PUBLIC_EXPORT_MODE=true NEXT_PUBLIC_DEBUG_MODE=false next build"
```

สำคัญ: ต้องมี EXPORT_MODE=true (ไม่ใช่แค่ NEXT_PUBLIC_EXPORT_MODE)
เพราะ next.config.js ทำงานฝั่ง server ต้องการ EXPORT_MODE โดยตรง

ผลลัพธ์: build เสร็จจะได้โฟลเดอร์ out/ แทน .next/

---

## ขั้นตอนที่ 4: สร้าง nginx.conf

สร้างไฟล์ nginx.conf ที่ root ของโปรเจกต์:

```
server {
    listen 3000;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    # Gzip compression - ลดขนาด transfer
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml application/json
               application/javascript application/xml+rss
               application/atom+xml image/svg+xml;

    # Static assets cache (1 year) - ไฟล์ที่มี hash ในชื่อ
    location /_next/static/ {
        expires 365d;
        add_header Cache-Control "public, immutable";
    }

    # Static files cache (30 days)
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 30d;
        add_header Cache-Control "public";
    }

    # SPA fallback - ลอง file -> .html -> directory -> index.html
    location / {
        try_files $uri $uri.html $uri/ /index.html;
    }
}
```

หมายเหตุเรื่อง try_files:
- ใช้ $uri.html ไม่ใช่ $uri/
- เพราะ Next.js static export สร้างทั้ง courses.html และ courses/ directory
- ถ้าใช้ $uri/ จะเจอ directory ที่ไม่มี index.html แล้ว return 403
- $uri.html จะหา courses.html เจอแล้ว serve ได้ถูกต้อง

ถ้ามี route เฉพาะที่ต้องการ fallback แยก เช่น admin:
```
    location /admin/ {
        try_files $uri $uri.html /index.html;
    }
```

---

## ขั้นตอนที่ 5: แก้ไข Dockerfile

### Dockerfile เดิม (Node.js Server) - หนัก:
```
FROM oven/bun:1-alpine AS deps
FROM oven/bun:1-alpine AS builder
FROM oven/bun:1-alpine AS runner    <-- ใช้ bun runtime
  COPY .next/standalone ./          <-- copy Node.js server
  COPY node_modules ./              <-- copy node_modules ทั้งหมด
  CMD ["bun", "run", "start"]       <-- รัน Node.js server
```

### Dockerfile ใหม่ (Static + Nginx) - เบา:
```
# Stage 1: Dependencies
FROM oven/bun:1-alpine AS deps
WORKDIR /app
COPY package.json bun.lock* ./
RUN bun install --frozen-lockfile

# Stage 2: Builder
FROM oven/bun:1-alpine AS builder
WORKDIR /app

# Build arguments (ส่งตอน docker build)
ARG NEXT_PUBLIC_APP_NAME
ARG NEXT_PUBLIC_ENV_MODE
ARG NEXT_PUBLIC_API_BASE_URL
ARG NEXT_PUBLIC_CLIENT_ID
ARG NEXT_PUBLIC_DEBUG_MODE
ARG NEXT_PUBLIC_EXPORT_MODE
ARG ENV_MODE
ARG EXPORT_MODE
# เพิ่ม ARG อื่นๆ ตามที่โปรเจกต์ต้องการ

COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN bun run build

# Stage 3: Serve static files (เอาแค่ผลลัพธ์ ไม่เอา node_modules)
FROM nginx:alpine AS runner
COPY --from=builder /app/out /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 3000
CMD ["nginx", "-g", "daemon off;"]
```

ถ้าโปรเจกต์ใช้ npm แทน bun:
```
# Stage 1: Dependencies
FROM node:20-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci

# Stage 2: Builder
FROM node:20-alpine AS builder
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=deps /app/node_modules ./node_modules
COPY . .
COPY .env.production .env.production
RUN rm -f .env.local
RUN npm run build

# Stage 3: Serve static files
FROM nginx:alpine AS runner
COPY --from=builder /app/out /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 3000
CMD ["nginx", "-g", "daemon off;"]
```

หลักการสำคัญ:
- Stage 1-2 ใช้สำหรับ build เท่านั้น (จะถูกทิ้งหลัง build)
- Stage 3 (runner) มีแค่ nginx:alpine + static files จาก out/
- ไม่มี Node.js, ไม่มี node_modules, ไม่มี source code

---

## ขั้นตอนที่ 6: Build และทดสอบในเครื่อง

### 6.1 Build image
```
docker build \
  --build-arg ENV_MODE=production \
  --build-arg EXPORT_MODE=true \
  --build-arg NEXT_PUBLIC_ENV_MODE=production \
  --build-arg NEXT_PUBLIC_EXPORT_MODE=true \
  --build-arg NEXT_PUBLIC_DEBUG_MODE=false \
  --build-arg NEXT_PUBLIC_API_BASE_URL=https://your-api-url.com/api/v1 \
  -t your-image-name:tag .
```

### 6.2 ตรวจสอบขนาด
```
docker images your-image-name --format "table {{.Tag}}\t{{.Size}}"
```

### 6.3 ทดสอบ run
```
docker run -d --name test-app -p 3001:3000 your-image-name:tag
```

### 6.4 ทดสอบ routes
```
curl -s -o /dev/null -w "HTTP %{http_code}" http://localhost:3001/
curl -s -o /dev/null -w "HTTP %{http_code}" http://localhost:3001/Dashboard
curl -s -o /dev/null -w "HTTP %{http_code}" http://localhost:3001/your-route
```

ทุก route ต้องได้ HTTP 200

### 6.5 Cleanup
```
docker stop test-app && docker rm test-app
```

---

## ขั้นตอนที่ 7: Push ขึ้น Registry และ Deploy K8s

### 7.1 Build ด้วย tag สำหรับ registry
```
docker build \
  --build-arg ENV_MODE=production \
  --build-arg EXPORT_MODE=true \
  --build-arg NEXT_PUBLIC_ENV_MODE=production \
  --build-arg NEXT_PUBLIC_EXPORT_MODE=true \
  --build-arg NEXT_PUBLIC_DEBUG_MODE=false \
  -t registry.digitalocean.com/minerta-k8s/your_image:tag .
```

### 7.2 Push ขึ้น registry
```
docker push registry.digitalocean.com/minerta-k8s/your_image:tag
```

### 7.3 อัพเดท K8s deployment
```
kubectl set image deployment/your-deployment \
  your-container=registry.digitalocean.com/minerta-k8s/your_image:tag \
  -n your-namespace
```

### 7.4 ตรวจสอบ
```
kubectl get pods -n your-namespace -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{range .spec.containers[*]}{.image}{"\n"}{end}{end}'
```

---

## ทำไม K8s ไม่กระทบ

- Port ยังเป็น 3000 เหมือนเดิม
- Service ชี้ไป targetPort: 3000 เหมือนเดิม
- Ingress ชี้ไป Service เหมือนเดิม
- เปลี่ยนแค่ image ใน Deployment
- ข้างในจะรัน Node.js หรือ Nginx ไม่สำคัญ ขอแค่ port + response เดิม

---

## ข้อจำกัดของ Static Export ที่ต้องรู้

1. ไม่มี API Routes        - ทุก API ต้องอยู่ที่ backend แยก
2. ไม่มี SSR               - ทุกอย่างเป็น Client-Side Rendering
3. ไม่มี Middleware         - auth/redirect ทำที่ frontend
4. ไม่มี Rewrites/Redirects - จัดการผ่าน nginx config แทน
5. Image Optimization       - ต้องตั้ง unoptimized: true
6. Dynamic routes           - ทำงานผ่าน nginx try_files fallback

---

## Checklist ก่อนทำแต่ละโปรเจกต์

[ ] ตรวจสอบไม่มี getServerSideProps
[ ] ตรวจสอบไม่มี middleware.ts/js
[ ] ตรวจสอบ API Routes ไม่ได้ใช้งานจริง
[ ] แก้ next.config.js (output, images.unoptimized, rewrites)
[ ] แก้ package.json build script (EXPORT_MODE=true)
[ ] สร้าง nginx.conf
[ ] แก้ Dockerfile (multi-stage + nginx:alpine)
[ ] Build ทดสอบในเครื่อง
[ ] ทดสอบทุก route ได้ HTTP 200
[ ] Push ขึ้น registry
[ ] อัพเดท K8s deployment
[ ] ตรวจสอบ pods ใช้ image version ใหม่
[ ] ทดสอบเว็บจริงบน production

---

## โปรเจกต์ที่ทำสำเร็จแล้ว

1. E-Learning Web (e_learning_web)
   - ก่อน: ~2.8 GB
   - หลัง: ~25 MB

2. THAI PHC WEB ADMIN (thai_phc_web_admin)
   - ก่อน: หลาย GB
   - หลัง: 68.6 MB
   - Tag: dev100
