<#
.SYNOPSIS
    Cross-platform PowerShell task runner for the Real-Time Stock Order Matching Engine.
.EXAMPLE
    .\run.ps1 up
    .\run.ps1 test
    .\run.ps1 simulate
    .\run.ps1 down
#>

param (
    [Parameter(Mandatory=$true, Position=0)]
    [ValidateSet("up", "down", "restart", "logs", "test", "lint", "simulate", "help")]
    [string]$Command
)

switch ($Command) {
    "up" {
        Write-Host "Starting stock trading infrastructure (Kafka, Cassandra, Kafdrop, Engine, UI)..." -ForegroundColor Cyan
        docker compose up -d
    }
    "down" {
        Write-Host "Stopping all Docker containers..." -ForegroundColor Yellow
        docker compose down
    }
    "restart" {
        Write-Host "Restarting Docker containers..." -ForegroundColor Yellow
        docker compose restart
    }
    "logs" {
        docker compose logs -f
    }
    "test" {
        Write-Host "Running pytest test suite..." -ForegroundColor Green
        python -m pytest tests -v
    }
    "lint" {
        Write-Host "Running ruff check..." -ForegroundColor Green
        python -m ruff check .
    }
    "simulate" {
        Write-Host "Starting synthetic market order simulator..." -ForegroundColor Cyan
        python scripts/market_simulator.py --symbol AAPL --count 15 --rate 2.0
    }
    "help" {
        Write-Host "Available commands: up, down, restart, logs, test, lint, simulate" -ForegroundColor White
    }
}
