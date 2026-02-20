#!/bin/bash

# Docker Management Helper Script
# Usage: ./docker.sh <command>

COMMAND=${1:-help}

show_help() {
    echo ""
    echo "====================================="
    echo " Chatbot Docker Management"
    echo "====================================="
    echo ""
    echo "Usage: ./docker.sh <command>"
    echo ""
    echo "Commands:"
    echo "  up           - Start all services"
    echo "  down         - Stop all services"
    echo "  restart      - Restart all services"
    echo "  status       - Show service status"
    echo "  logs         - View all logs"
    echo "  redis        - Start Redis only"
    echo "  postgres     - Start PostgreSQL only"
    echo "  minimal      - Start PostgreSQL + Redis only"
    echo "  full         - Start all services (including Milvus)"
    echo "  dev          - Start with Redis Commander UI"
    echo "  clean        - Stop and remove all containers"
    echo "  reset        - Stop and remove all data (⚠️ WARNING)"
    echo "  redis-cli    - Connect to Redis CLI"
    echo "  psql         - Connect to PostgreSQL CLI"
    echo "  help         - Show this help message"
    echo ""
}

start_all() {
    echo "🚀 Starting all services..."
    docker-compose up -d
    echo "✅ Services started! Run './docker.sh status' to check health."
}

stop_all() {
    echo "🛑 Stopping all services..."
    docker-compose down
    echo "✅ Services stopped!"
}

restart_all() {
    echo "🔄 Restarting all services..."
    docker-compose restart
    echo "✅ Services restarted!"
}

show_status() {
    echo "📊 Service Status:"
    docker-compose ps
}

show_logs() {
    echo "📋 Viewing logs (Ctrl+C to exit)..."
    docker-compose logs -f
}

start_redis() {
    echo "🚀 Starting Redis only..."
    docker-compose up -d redis
    echo "✅ Redis started!"
}

start_postgres() {
    echo "🚀 Starting PostgreSQL only..."
    docker-compose up -d postgres
    echo "✅ PostgreSQL started!"
}

start_minimal() {
    echo "🚀 Starting minimal setup (PostgreSQL + Redis)..."
    docker-compose up -d postgres redis
    echo "✅ Minimal services started!"
}

start_full() {
    echo "🚀 Starting full setup (all services)..."
    docker-compose up -d
    echo "✅ All services started!"
}

start_dev() {
    echo "🚀 Starting with development tools..."
    docker-compose --profile dev up -d
    echo "✅ Services started with Redis Commander UI!"
    echo "🌐 Redis Commander: http://localhost:8081"
    echo "🌐 MinIO Console: http://localhost:9001"
}

clean_services() {
    echo "🧹 Cleaning up containers..."
    docker-compose down
    echo "✅ Containers removed!"
}

reset_all() {
    read -p "⚠️  This will DELETE ALL DATA! Are you sure? (yes/no): " confirmation
    if [ "$confirmation" = "yes" ]; then
        echo "🗑️  Removing all containers and volumes..."
        docker-compose down -v
        echo "✅ All data removed!"
    else
        echo "❌ Reset cancelled."
    fi
}

connect_redis_cli() {
    echo "🔌 Connecting to Redis CLI..."
    docker exec -it chatbot-redis redis-cli
}

connect_psql() {
    echo "🔌 Connecting to PostgreSQL CLI..."
    docker exec -it chatbot-postgres psql -U chatbot -d chatbot_db
}

# Main command router
case $COMMAND in
    up)
        start_all
        ;;
    down)
        stop_all
        ;;
    restart)
        restart_all
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    redis)
        start_redis
        ;;
    postgres)
        start_postgres
        ;;
    minimal)
        start_minimal
        ;;
    full)
        start_full
        ;;
    dev)
        start_dev
        ;;
    clean)
        clean_services
        ;;
    reset)
        reset_all
        ;;
    redis-cli)
        connect_redis_cli
        ;;
    psql)
        connect_psql
        ;;
    help)
        show_help
        ;;
    *)
        echo "❌ Unknown command: $COMMAND"
        show_help
        ;;
esac
