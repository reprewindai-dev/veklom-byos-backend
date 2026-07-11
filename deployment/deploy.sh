#!/bin/bash

# Veklom Governance Gateway Deployment Script
# This script deploys the complete Phase 0A + 0B system

set -e

echo "🚀 Starting Veklom Governance Gateway Deployment"

# Configuration
PROJECT_NAME="veklom-governance"
COMPOSE_FILE="docker-compose.yml"
ENV_FILE=".env"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check if Docker Compose is installed
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check if .env file exists
    if [ ! -f "$ENV_FILE" ]; then
        log_warning ".env file not found. Creating from template..."
        cp .env.example .env
        log_warning "Please edit .env file with your configuration before continuing."
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Build services
build_services() {
    log_info "Building services..."
    
    # Build governance gateway
    log_info "Building Governance Gateway (Inside MCP)..."
    docker-compose build governance-gateway
    
    # Build edge gateway
    log_info "Building Edge Gateway (Edge MCP)..."
    docker-compose build edge-gateway
    
    # Build backend if needed
    if [ "$BUILD_BACKEND" = "true" ]; then
        log_info "Building Backend API..."
        docker-compose build backend
    fi
    
    log_success "All services built successfully"
}

# Deploy services
deploy_services() {
    log_info "Deploying services..."
    
    # Start database and redis first
    log_info "Starting database and Redis..."
    docker-compose up -d postgres redis
    
    # Wait for database to be ready
    log_info "Waiting for database to be ready..."
    sleep 10
    
    # Start backend
    log_info "Starting Backend API..."
    docker-compose up -d backend
    
    # Wait for backend to be ready
    log_info "Waiting for backend to be ready..."
    sleep 15
    
    # Start governance gateway
    log_info "Starting Governance Gateway..."
    docker-compose up -d governance-gateway
    
    # Wait for governance gateway to be ready
    log_info "Waiting for Governance Gateway to be ready..."
    sleep 10
    
    # Start edge gateway
    log_info "Starting Edge Gateway..."
    docker-compose up -d edge-gateway
    
    # Wait for edge gateway to be ready
    log_info "Waiting for Edge Gateway to be ready..."
    sleep 10
    
    # Start frontend and monitoring
    log_info "Starting Frontend and Monitoring..."
    docker-compose up -d frontend prometheus grafana
    
    # Start reverse proxy
    log_info "Starting Reverse Proxy..."
    docker-compose up -d traefik
    
    log_success "All services deployed successfully"
}

# Health checks
health_checks() {
    log_info "Performing health checks..."
    
    # Check backend health
    if curl -f http://localhost:8000/health &> /dev/null; then
        log_success "Backend API is healthy"
    else
        log_error "Backend API is not healthy"
    fi
    
    # Check governance gateway health
    if curl -f http://localhost:8080/health &> /dev/null; then
        log_success "Governance Gateway is healthy"
    else
        log_error "Governance Gateway is not healthy"
    fi
    
    # Check edge gateway health
    if curl -f http://localhost:8081/health &> /dev/null; then
        log_success "Edge Gateway is healthy"
    else
        log_error "Edge Gateway is not healthy"
    fi
    
    # Check frontend
    if curl -f http://localhost:3000 &> /dev/null; then
        log_success "Frontend is healthy"
    else
        log_warning "Frontend may not be ready yet"
    fi
    
    log_info "Health checks completed"
}

# Run integration tests
run_tests() {
    if [ "$SKIP_TESTS" = "true" ]; then
        log_warning "Skipping integration tests"
        return
    fi
    
    log_info "Running integration tests..."
    
    # Navigate to integration tests directory
    cd ../integration-tests
    
    # Build tests
    cargo build --test phase0a --test phase0b --test end_to_end --test security
    
    # Run tests
    cargo test --test phase0a
    cargo test --test phase0b
    cargo test --test end_to_end
    cargo test --test security
    
    cd ../deployment
    
    log_success "Integration tests completed"
}

# Show deployment status
show_status() {
    log_info "Deployment Status:"
    echo ""
    docker-compose ps
    echo ""
    log_info "Service URLs:"
    echo "  Backend API: http://localhost:8000"
    echo "  Governance Gateway: http://localhost:8080"
    echo "  Edge Gateway: http://localhost:8081"
    echo "  Frontend: http://localhost:3000"
    echo "  Traefik Dashboard: http://localhost:80"
    echo "  Prometheus: http://localhost:9090"
    echo "  Grafana: http://localhost:3001"
    echo ""
    log_info "To view logs: docker-compose logs -f [service-name]"
    log_info "To stop services: docker-compose down"
    log_info "To restart services: docker-compose restart"
}

# Cleanup function
cleanup() {
    log_info "Cleaning up..."
    docker-compose down
    docker system prune -f
    log_success "Cleanup completed"
}

# Main deployment flow
main() {
    case "${1:-deploy}" in
        "deploy")
            check_prerequisites
            build_services
            deploy_services
            sleep 30  # Wait for all services to start
            health_checks
            run_tests
            show_status
            ;;
        "build")
            check_prerequisites
            build_services
            ;;
        "test")
            run_tests
            ;;
        "health")
            health_checks
            ;;
        "status")
            show_status
            ;;
        "cleanup")
            cleanup
            ;;
        "restart")
            docker-compose restart
            health_checks
            ;;
        "logs")
            docker-compose logs -f "${2:-}"
            ;;
        "stop")
            docker-compose down
            ;;
        *)
            echo "Usage: $0 {deploy|build|test|health|status|cleanup|restart|logs|stop}"
            echo ""
            echo "Commands:"
            echo "  deploy   - Full deployment (default)"
            echo "  build    - Build services only"
            echo "  test     - Run integration tests"
            echo "  health   - Check service health"
            echo "  status   - Show deployment status"
            echo "  cleanup  - Stop and remove services"
            echo "  restart  - Restart all services"
            echo "  logs     - Show logs (optional service name)"
            echo "  stop     - Stop all services"
            exit 1
            ;;
    esac
}

# Trap signals for cleanup
trap cleanup EXIT

# Run main function
main "$@"
