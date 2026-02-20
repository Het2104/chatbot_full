# Docker Management Helper Script
# Usage: .\docker.ps1 <command>

param(
    [Parameter(Position=0)]
    [string]$Command = "help"
)

function Show-Help {
    Write-Host ""
    Write-Host "=====================================" -ForegroundColor Cyan
    Write-Host " Chatbot Docker Management" -ForegroundColor Cyan
    Write-Host "=====================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Usage: .\docker.ps1 <command>" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Commands:" -ForegroundColor Green
    Write-Host "  up           - Start all services" -ForegroundColor White
    Write-Host "  down         - Stop all services" -ForegroundColor White
    Write-Host "  restart      - Restart all services" -ForegroundColor White
    Write-Host "  status       - Show service status" -ForegroundColor White
    Write-Host "  logs         - View all logs" -ForegroundColor White
    Write-Host "  redis        - Start Redis only" -ForegroundColor White
    Write-Host "  postgres     - Start PostgreSQL only" -ForegroundColor White
    Write-Host "  minimal      - Start PostgreSQL + Redis only" -ForegroundColor White
    Write-Host "  full         - Start all services (including Milvus)" -ForegroundColor White
    Write-Host "  dev          - Start with Redis Commander UI" -ForegroundColor White
    Write-Host "  clean        - Stop and remove all containers" -ForegroundColor White
    Write-Host "  reset        - Stop and remove all data (⚠️ WARNING)" -ForegroundColor Red
    Write-Host "  redis-cli    - Connect to Redis CLI" -ForegroundColor White
    Write-Host "  psql         - Connect to PostgreSQL CLI" -ForegroundColor White
    Write-Host "  help         - Show this help message" -ForegroundColor White
    Write-Host ""
}

function Start-AllServices {
    Write-Host "🚀 Starting all services..." -ForegroundColor Green
    docker-compose up -d
    Write-Host "✅ Services started! Run '.\docker.ps1 status' to check health." -ForegroundColor Green
}

function Stop-AllServices {
    Write-Host "🛑 Stopping all services..." -ForegroundColor Yellow
    docker-compose down
    Write-Host "✅ Services stopped!" -ForegroundColor Green
}

function Restart-AllServices {
    Write-Host "🔄 Restarting all services..." -ForegroundColor Yellow
    docker-compose restart
    Write-Host "✅ Services restarted!" -ForegroundColor Green
}

function Show-Status {
    Write-Host "📊 Service Status:" -ForegroundColor Cyan
    docker-compose ps
}

function Show-Logs {
    Write-Host "📋 Viewing logs (Ctrl+C to exit)..." -ForegroundColor Cyan
    docker-compose logs -f
}

function Start-RedisOnly {
    Write-Host "🚀 Starting Redis only..." -ForegroundColor Green
    docker-compose up -d redis
    Write-Host "✅ Redis started!" -ForegroundColor Green
}

function Start-PostgresOnly {
    Write-Host "🚀 Starting PostgreSQL only..." -ForegroundColor Green
    docker-compose up -d postgres
    Write-Host "✅ PostgreSQL started!" -ForegroundColor Green
}

function Start-Minimal {
    Write-Host "🚀 Starting minimal setup (PostgreSQL + Redis)..." -ForegroundColor Green
    docker-compose up -d postgres redis
    Write-Host "✅ Minimal services started!" -ForegroundColor Green
}

function Start-Full {
    Write-Host "🚀 Starting full setup (all services)..." -ForegroundColor Green
    docker-compose up -d
    Write-Host "✅ All services started!" -ForegroundColor Green
}

function Start-Dev {
    Write-Host "🚀 Starting with development tools..." -ForegroundColor Green
    docker-compose --profile dev up -d
    Write-Host "✅ Services started with Redis Commander UI!" -ForegroundColor Green
    Write-Host "🌐 Redis Commander: http://localhost:8081" -ForegroundColor Cyan
    Write-Host "🌐 MinIO Console: http://localhost:9001" -ForegroundColor Cyan
}

function Clean-Services {
    Write-Host "🧹 Cleaning up containers..." -ForegroundColor Yellow
    docker-compose down
    Write-Host "✅ Containers removed!" -ForegroundColor Green
}

function Reset-All {
    $confirmation = Read-Host "⚠️  This will DELETE ALL DATA! Are you sure? (yes/no)"
    if ($confirmation -eq "yes") {
        Write-Host "🗑️  Removing all containers and volumes..." -ForegroundColor Red
        docker-compose down -v
        Write-Host "✅ All data removed!" -ForegroundColor Green
    } else {
        Write-Host "❌ Reset cancelled." -ForegroundColor Yellow
    }
}

function Connect-RedisCLI {
    Write-Host "🔌 Connecting to Redis CLI..." -ForegroundColor Cyan
    docker exec -it chatbot-redis redis-cli
}

function Connect-PSQL {
    Write-Host "🔌 Connecting to PostgreSQL CLI..." -ForegroundColor Cyan
    docker exec -it chatbot-postgres psql -U chatbot -d chatbot_db
}

# Main command router
switch ($Command.ToLower()) {
    "up"        { Start-AllServices }
    "down"      { Stop-AllServices }
    "restart"   { Restart-AllServices }
    "status"    { Show-Status }
    "logs"      { Show-Logs }
    "redis"     { Start-RedisOnly }
    "postgres"  { Start-PostgresOnly }
    "minimal"   { Start-Minimal }
    "full"      { Start-Full }
    "dev"       { Start-Dev }
    "clean"     { Clean-Services }
    "reset"     { Reset-All }
    "redis-cli" { Connect-RedisCLI }
    "psql"      { Connect-PSQL }
    "help"      { Show-Help }
    default     { 
        Write-Host "❌ Unknown command: $Command" -ForegroundColor Red
        Show-Help 
    }
}
