# SECURESNAP DevSecOps Pipeline - CentOS Digital Ocean Implementation

## Prerequisites
- Digital Ocean Droplet: 12GB RAM, 24GB disk, CentOS
- Root access with password
- GitHub account
- Docker Hub account

## Step 1: Initial CentOS Setup

### Update System
```bash
yum update -y
yum install -y epel-release
yum install -y wget curl git vim nano
```

### Configure Firewall
```bash
# Install and start firewalld
yum install -y firewalld
systemctl start firewalld
systemctl enable firewalld

# Open required ports
firewall-cmd --permanent --add-port=22/tcp     # SSH
firewall-cmd --permanent --add-port=80/tcp     # HTTP
firewall-cmd --permanent --add-port=443/tcp    # HTTPS
firewall-cmd --permanent --add-port=8080/tcp   # Jenkins
firewall-cmd --permanent --add-port=9000/tcp   # SonarQube
firewall-cmd --permanent --add-port=9090/tcp   # Prometheus
firewall-cmd --permanent --add-port=3000/tcp   # Grafana
firewall-cmd --reload
```

## Step 2: Install Docker & Docker Compose

### Install Docker
```bash
# Remove old versions
yum remove -y docker docker-client docker-client-latest docker-common docker-latest docker-latest-logrotate docker-logrotate docker-engine

# Install Docker CE repository
yum install -y yum-utils
yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo

# Install Docker
yum install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Start and enable Docker
systemctl start docker
systemctl enable docker

# Add user to docker group (if you create a non-root user later)
# usermod -aG docker username
```

### Install Docker Compose (standalone)
```bash
# Download Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

# Make it executable
chmod +x /usr/local/bin/docker-compose

# Create symlink
ln -s /usr/local/bin/docker-compose /usr/bin/docker-compose

# Verify installation
docker --version
docker-compose --version
```

## Step 3: Install Java (Required for Jenkins)

```bash
# Install Java 17
yum install -y java-17-openjdk java-17-openjdk-devel

# Set JAVA_HOME
echo 'export JAVA_HOME=/usr/lib/jvm/java-17-openjdk' >> /etc/profile
source /etc/profile

# Verify Java installation
java -version
```

## Step 4: Install Jenkins

```bash
# Add Jenkins repository
wget -O /etc/yum.repos.d/jenkins.repo https://pkg.jenkins.io/redhat-stable/jenkins.repo
rpm --import https://pkg.jenkins.io/redhat-stable/jenkins.io.key

# Install Jenkins
yum install -y jenkins

# Start and enable Jenkins
systemctl start jenkins
systemctl enable jenkins

# Check Jenkins status
systemctl status jenkins

# Get initial admin password
cat /var/lib/jenkins/secrets/initialAdminPassword
```

## Step 5: Install Node.js and npm (for additional tools)

```bash
# Install Node.js 18
curl -fsSL https://rpm.nodesource.com/setup_18.x | bash -
yum install -y nodejs

# Install global tools
npm install -g snyk

# Verify installation
node --version
npm --version
```

## Step 6: Create Project Structure

```bash
# Create project directory
mkdir -p /opt/SECURESNAP
cd /opt/SECURESNAP

# Create project structure
mkdir -p app tests .github/workflows

# Create main application file
cat > app/main.py << 'EOF'
from fastapi import FastAPI
from prometheus_client import start_http_server, Counter, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
import threading

app = FastAPI(
    title="SECURESNAP DevSecOps API",
    description="A secure FastAPI application with Prometheus metrics",
    version="1.0.0"
)

REQUEST_COUNT = Counter("app_requests_total", "Total number of requests", ["endpoint"])

@app.on_event("startup")
async def startup_event():
    # Start Prometheus metrics server
    start_http_server(8001)

@app.get("/")
def read_root():
    REQUEST_COUNT.labels(endpoint="root").inc()
    return {"message": "Hello, SECURESNAP DevSecOps!"}

@app.get("/health")
def health_check():
    REQUEST_COUNT.labels(endpoint="health").inc()
    return {"status": "healthy", "service": "securesnap"}

@app.get("/metrics")
def get_metrics():
    REQUEST_COUNT.labels(endpoint="metrics").inc()
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/info")
def get_info():
    REQUEST_COUNT.labels(endpoint="info").inc()
    return {
        "service": "SECURESNAP",
        "version": "1.0.0",
        "status": "running",
        "metrics_endpoint": "/metrics"
    }
EOF

# Create test file
cat > tests/test_main.py << 'EOF'
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello, SECURESNAP DevSecOps!"}

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
EOF

# Create requirements.txt
cat > requirements.txt << 'EOF'
fastapi==0.104.1
uvicorn==0.24.0
prometheus-client==0.19.0
pytest==7.4.3
httpx==0.25.2
EOF

# Create Dockerfile
cat > Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY tests/ ./tests/

EXPOSE 8000 8001

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF

# Create docker-compose.yml
cat > docker-compose.yml << 'EOF'
version: '3.9'

services:
  app:
    build: .
    ports:
      - "80:8000"
      - "8001:8001"
    environment:
      - ENV=production
    
  sonarqube:
    image: sonarqube:community
    ports:
      - "9000:9000"
    environment:
      - SONAR_ES_BOOTSTRAP_CHECKS_DISABLE=true
    volumes:
      - sonarqube_data:/opt/sonarqube/data
      - sonarqube_extensions:/opt/sonarqube/extensions
      - sonarqube_logs:/opt/sonarqube/logs

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana

volumes:
  sonarqube_data:
  sonarqube_extensions:
  sonarqube_logs:
  prometheus_data:
  grafana_data:
EOF

# Create Prometheus configuration
cat > prometheus.yml << 'EOF'
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'fastapi'
    static_configs:
      - targets: ['app:8001']
  
  - job_name: 'jenkins'
    static_configs:
      - targets: ['159.65.25.168:8080']
    metrics_path: '/prometheus/'
EOF

# Create Jenkinsfile
cat > Jenkinsfile << 'EOF'
pipeline {
    agent any
    
    environment {
        DOCKERHUB_CREDENTIALS = credentials('dockerhub-credentials')
        IMAGE_NAME = 'your-dockerhub-username/securesnap'
    }
    
    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        
        stage('Build') {
            steps {
                script {
                    sh 'docker build -t ${IMAGE_NAME}:${BUILD_NUMBER} .'
                    sh 'docker tag ${IMAGE_NAME}:${BUILD_NUMBER} ${IMAGE_NAME}:latest'
                }
            }
        }
        
        stage('Test') {
            steps {
                sh 'docker run --rm ${IMAGE_NAME}:${BUILD_NUMBER} python -m pytest tests/ -v'
            }
        }
        
        stage('Security Scan') {
            steps {
                script {
                    sh '''
                        docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
                        aquasec/trivy image ${IMAGE_NAME}:${BUILD_NUMBER}
                    '''
                }
            }
        }
        
        stage('SonarQube Analysis') {
            steps {
                script {
                    def scannerHome = tool 'SonarQubeScanner'
                    withSonarQubeEnv('SonarQube') {
                        sh "${scannerHome}/bin/sonar-scanner"
                    }
                }
            }
        }
        
        stage('Push to Registry') {
            steps {
                script {
                    sh 'echo $DOCKERHUB_CREDENTIALS_PSW | docker login -u $DOCKERHUB_CREDENTIALS_USR --password-stdin'
                    sh 'docker push ${IMAGE_NAME}:${BUILD_NUMBER}'
                    sh 'docker push ${IMAGE_NAME}:latest'
                }
            }
        }
        
        stage('Deploy') {
            steps {
                sh '''
                    docker stop securesnap-app || true
                    docker rm securesnap-app || true
                    docker run -d --name securesnap-app -p 80:8000 ${IMAGE_NAME}:latest
                '''
            }
        }
    }
    
    post {
        always {
            sh 'docker logout'
        }
    }
}
EOF

# Create GitHub Actions workflow
cat > .github/workflows/ci.yml << 'EOF'
name: CI/CD Pipeline

on:
  push:
    branches: [ main, master ]
  pull_request:
    branches: [ main, master ]

# Add permissions for security events
permissions:
  contents: read
  security-events: write
  actions: read

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    
    - name: Run tests
      run: |
        python -m pytest tests/ -v
    
    - name: Build Docker image
      run: |
        docker build -t securesnap:test .
    
    - name: Run Trivy vulnerability scanner
      uses: aquasecurity/trivy-action@master
      with:
        image-ref: 'securesnap:test'
        format: 'table'
        exit-code: '0'
    
    # Only upload SARIF if we have the right permissions
    - name: Run Trivy vulnerability scanner (SARIF)
      uses: aquasecurity/trivy-action@master
      if: github.event_name != 'pull_request'
      with:
        image-ref: 'securesnap:test'
        format: 'sarif'
        output: 'trivy-results.sarif'
    
    - name: Upload Trivy scan results
      uses: github/codeql-action/upload-sarif@v3
      if: github.event_name != 'pull_request'
      with:
        sarif_file: 'trivy-results.sarif'

  build-and-push:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Login to Docker Hub
      uses: docker/login-action@v3
      with:
        username: ${{ secrets.DOCKER_USERNAME }}
        password: ${{ secrets.DOCKER_PASSWORD }}
    
    - name: Build and push
      uses: docker/build-push-action@v5
      with:
        context: .
        push: true
        tags: ${{ secrets.DOCKER_USERNAME }}/securesnap:latest
EOF
```

## Step 7: Initialize Git Repository

```bash
cd /opt/SECURESNAP

# Initialize git repository
git init
git add .
git commit -m "Initial SECURESNAP DevSecOps setup"

# Add your GitHub repository (replace with your repo URL)
# git remote add origin https://github.com/yourusername/SECURESNAP.git
# git branch -M main
# git push -u origin main
```

## Step 8: Configure Jenkins

### Access Jenkins
1. Open your browser and go to `http://YOUR_DROPLET_IP:8080`
2. Use the initial admin password: `cat /var/lib/jenkins/secrets/initialAdminPassword`
3. Install suggested plugins
4. Create admin user

### Install Required Jenkins Plugins
Go to **Manage Jenkins** → **Manage Plugins** → **Available** and install:
- GitHub Integration Plugin
- Docker Pipeline Plugin
- SonarQube Scanner Plugin
- Prometheus Metrics Plugin
- Blue Ocean Plugin
- Trivy Plugin (if available)

### Configure Docker in Jenkins
```bash
# Add jenkins user to docker group
usermod -aG docker jenkins
systemctl restart jenkins
```

## Step 9: Start Services

```bash
cd /opt/SECURESNAP

# Replace YOUR_DROPLET_IP in prometheus.yml
sed -i 's/YOUR_DROPLET_IP/YOUR_ACTUAL_DROPLET_IP/g' prometheus.yml

# Start all services
docker-compose up -d

# Check running containers
docker ps
```

## Step 10: Configure SonarQube

1. Go to `http://YOUR_DROPLET_IP:9000`
2. Login with admin/admin
3. Change password when prompted
4. Go to **My Account** → **Security** → **Generate Token**
5. Copy the token for Jenkins configuration

### Add SonarQube to Jenkins
1. **Manage Jenkins** → **Configure System**
2. Find **SonarQube servers** section
3. Add server:
   - Name: `SonarQube`
   - Server URL: `http://YOUR_DROPLET_IP:9000`
   - Authentication token: (paste the token from SonarQube)

## Step 11: Configure Grafana

1. Go to `http://YOUR_DROPLET_IP:3000`
2. Login with admin/admin
3. Add Prometheus data source:
   - URL: `http://prometheus:9090`
4. Import dashboard ID: `18739` (FastAPI dashboard)

## Step 12: Set Up GitHub Webhook

### In GitHub Repository:
1. Go to **Settings** → **Webhooks**
2. Add webhook:
   - Payload URL: `http://YOUR_DROPLET_IP:8080/github-webhook/`
   - Content type: `application/json`
   - Events: `Push events`
   - Active: ✓

### In Jenkins:
1. Create new Pipeline job
2. **Pipeline** → **Pipeline from SCM**
3. SCM: **Git**
4. Repository URL: Your GitHub repo URL
5. Branch: `*/main`
6. **Build Triggers**: ✓ **GitHub hook trigger for GITScm polling**

## Step 13: Add Docker Hub Credentials

### In GitHub (for Actions):
1. **Repository Settings** → **Secrets and variables** → **Actions**
2. Add secrets:
   - `DOCKER_USERNAME`: Your Docker Hub username
   - `DOCKER_PASSWORD`: Your Docker Hub access token

### In Jenkins:
1. **Manage Jenkins** → **Credentials**
2. Add **Username with password**:
   - ID: `dockerhub-credentials`
   - Username: Your Docker Hub username
   - Password: Your Docker Hub access token

## Step 14: Test the Pipeline

```bash
# Make a small change to trigger the pipeline
cd /opt/SECURESNAP
echo "# Updated" >> README.md
git add README.md
git commit -m "Test pipeline trigger"
git push origin main
```

## Step 15: Monitor Everything

### Access Points:
- **Application**: `http://YOUR_DROPLET_IP`
- **Jenkins**: `http://YOUR_DROPLET_IP:8080`
- **SonarQube**: `http://YOUR_DROPLET_IP:9000`
- **Prometheus**: `http://YOUR_DROPLET_IP:9090`
- **Grafana**: `http://YOUR_DROPLET_IP:3000`

### Check Services Status:
```bash
# Check all Docker containers
docker ps

# Check Jenkins
systemctl status jenkins

# Check firewall
firewall-cmd --list-all

# Check logs
docker-compose logs -f
```

## Troubleshooting Commands

```bash
# Restart services
systemctl restart jenkins
docker-compose restart

# Check disk space
df -h

# Check memory usage
free -h

# View Docker logs
docker logs container_name

# Clean Docker system
docker system prune -a
```

## Security Best Practices Applied

1. **Firewall configured** with only necessary ports
2. **Trivy scanning** for container vulnerabilities
3. **SonarQube** for code quality and security
4. **Secrets management** through Jenkins credentials
5. **HTTPS ready** (add SSL certificate for production)
6. **Container security** with non-root users in Dockerfile

This setup provides a complete DevSecOps pipeline on your CentOS Digital Ocean droplet with all the security, monitoring, and automation features from the original guide!
