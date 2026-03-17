#!/bin/bash
# KasirToko Local Deployment Script
# Usage: ./deploy.sh [vercel|docker|local]

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

DEPLOY_TYPE=${1:-local}

log "🚀 Deploy KasirToko: $DEPLOY_TYPE"

case $DEPLOY_TYPE in
    vercel)
        log "📦 Deploying to Vercel..."
        
        # Check vercel CLI
        if ! command -v vercel &> /dev/null; then
            warn "Installing Vercel CLI..."
            npm install -g vercel
        fi
        
        # Login check
        vercel whoami &> /dev/null || vercel login
        
        # Deploy
        vercel --prod
        
        log "✅ Deployed to Vercel!"
        log "⚠️  Jangan lupa set environment variables di Vercel Dashboard"
        ;;
        
    docker)
        log "🐳 Deploying with Docker..."
        
        # Check docker
        if ! command -v docker &> /dev/null; then
            error "Docker tidak terinstall. Install terlebih dahulu: https://docs.docker.com/get-docker/"
        fi
        
        # Check docker-compose
        if ! command -v docker-compose &> /dev/null; then
            error "Docker Compose tidak terinstall."
        fi
        
        # Generate secret key if not exists
        if [ ! -f .env ]; then
            log "🔑 Generating .env file..."
            SECRET_KEY=$(openssl rand -hex 32)
            echo "SECRET_KEY=$SECRET_KEY" > .env
            warn "File .env dibuat. Edit untuk konfigurasi tambahan."
        fi
        
        # Build and run
        log "🔨 Building Docker image..."
        docker-compose build
        
        log "🚀 Starting containers..."
        docker-compose up -d
        
        log "✅ Docker deployment complete!"
        log "🌐 Aplikasi berjalan di: http://localhost:5000"
        log ""
        log "Commands:"
        log "  View logs:  docker-compose logs -f"
        log "  Stop:       docker-compose down"
        log "  Restart:    docker-compose restart"
        ;;
        
    vps)
        log "🖥️  Deploying to VPS..."
        
        # Check if domain provided
        if [ -z "$2" ]; then
            error "Usage: ./deploy.sh vps your-domain.com"
        fi
        
        DOMAIN=$2
        
        # Copy deploy script to server
        read -p "Enter server IP: " SERVER_IP
        read -p "Enter SSH user (default: root): " SSH_USER
        SSH_USER=${SSH_USER:-root}
        
        log "📤 Copying files to server..."
        scp -r deploy/deploy-vps.sh "$SSH_USER@$SERVER_IP:/tmp/"
        
        log "🔧 Running deployment script..."
        ssh "$SSH_USER@$SERVER_IP" "chmod +x /tmp/deploy-vps.sh && /tmp/deploy-vps.sh $DOMAIN"
        ;;
        
    local|dev)
        log "💻 Running local development..."
        
        # Check Python
        if ! command -v python3 &> /dev/null; then
            error "Python 3 tidak terinstall."
        fi
        
        # Setup venv if not exists
        if [ ! -d "venv" ]; then
            log "🔧 Creating virtual environment..."
            python3 -m venv venv
        fi
        
        # Activate venv
        source venv/bin/activate || source venv/Scripts/activate
        
        # Install dependencies
        log "📦 Installing dependencies..."
        pip install -r requirements.txt
        
        # Generate secret key if not exists
        if [ ! -f .env ]; then
            log "🔑 Generating .env file..."
            SECRET_KEY=$(openssl rand -hex 32)
            cat > .env << EOF
SECRET_KEY=$SECRET_KEY
FLASK_ENV=development
FLASK_DEBUG=1
EOF
        fi
        
        # Load env
        export $(grep -v '^#' .env | xargs)
        
        log "🚀 Starting development server..."
        log "🌐 Aplikasi akan berjalan di:"
        log "   Local:   http://localhost:5000"
        log "   Network: http://$(hostname -I | awk '{print $1}'):5000"
        log ""
        warn "Tekan Ctrl+C untuk stop"
        log ""
        
        python app.py
        ;;
        
    *)
        echo "Usage: ./deploy.sh [vercel|docker|vps|local]"
        echo ""
        echo "Options:"
        echo "  vercel   Deploy ke Vercel (serverless)"
        echo "  docker   Deploy dengan Docker Compose"
        echo "  vps      Deploy ke VPS (Ubuntu)"
        echo "  local    Run local development server"
        echo ""
        echo "Examples:"
        echo "  ./deploy.sh local"
        echo "  ./deploy.sh docker"
        echo "  ./deploy.sh vps kasir.tokoku.com"
        exit 1
        ;;
esac
