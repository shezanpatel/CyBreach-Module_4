$ErrorActionPreference = "Continue"

$root = $PSScriptRoot
$basePython = Join-Path $root ".venv\Scripts\python.exe"
$failedSuites = [System.Collections.Generic.List[string]]::new()

$suites = @(
    @{
        Name = "root + pod_beta"
        Directory = $root
        Python = $basePython
    },
    @{
        Name = "pod_gamma"
        Directory = Join-Path $root "services\pod_gamma"
        Python = $basePython
    },
    @{
        Name = "pod_delta"
        Directory = Join-Path $root "services\pod_delta"
        Python = Join-Path $root "services\pod_delta\.venv\Scripts\python.exe"
    }
)

foreach ($suite in $suites) {
    Write-Host "`n=== $($suite.Name) ==="
    Push-Location $suite.Directory
    try {
        & $suite.Python -m pytest -q
        if ($LASTEXITCODE -ne 0) {
            $failedSuites.Add($suite.Name)
        }
    }
    finally {
        Pop-Location
    }
}

$walletVariables = @{
    APP_NAME = "CyBreach Wallet Service"
    APP_VERSION = "1.0.0"
    POSTGRES_USER = "wallet_user"
    POSTGRES_PASSWORD = "wallet_password"
    POSTGRES_DB = "wallet_db"
    POSTGRES_HOST = "localhost"
    POSTGRES_PORT = "55432"
    DATABASE_URL = "postgresql+psycopg://wallet_user:wallet_password@localhost:55432/wallet_db"
    KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"
    JWT_SECRET_KEY = "local-test-only-secret-key-not-for-production"
    SERVICE_API_KEY = "local-test-only-service-key"
}
$previousWalletVariables = @{}
foreach ($name in $walletVariables.Keys) {
    $previousWalletVariables[$name] = [Environment]::GetEnvironmentVariable($name, "Process")
    [Environment]::SetEnvironmentVariable($name, $walletVariables[$name], "Process")
}

$walletDirectory = Join-Path $root "services\wallet_service"
$walletPython = Join-Path $walletDirectory ".venv312\Scripts\python.exe"
$walletDatabaseReady = $false

try {
    docker exec wallet-pytest-db pg_isready -U wallet_user -d wallet_db *> $null
    $walletDatabaseReady = $LASTEXITCODE -eq 0

    if (-not $walletDatabaseReady) {
        Write-Host "`nWallet tests skipped: wallet-pytest-db is not ready."
        $failedSuites.Add("wallet_service (database unavailable)")
    }
    elseif (-not (Test-Path $walletPython)) {
        Write-Host "`nWallet tests skipped: Python environment services\wallet_service\.venv312 is missing."
        $failedSuites.Add("wallet_service (Python environment missing)")
    }
    else {
        Write-Host "`n=== wallet_service: preparing test database ==="
        Push-Location $walletDirectory
        try {
            & $walletPython -c "import os, psycopg; from pathlib import Path; from app.main import Base, engine; Base.metadata.create_all(bind=engine); connection=psycopg.connect(os.environ['DATABASE_URL'].replace('postgresql+psycopg://','postgresql://')); connection.execute(Path('migrations/008_wallet_audit_trail.sql').read_text()); connection.commit(); connection.close()"
            $databaseSetupExitCode = $LASTEXITCODE

            if ($databaseSetupExitCode -ne 0) {
                Write-Host "Wallet tests skipped: database schema setup failed."
                $failedSuites.Add("wallet_service (database setup failed)")
            }
            else {
                Write-Host "`n=== wallet_service ==="
                & $walletPython -m pytest -q
                if ($LASTEXITCODE -ne 0) {
                    $failedSuites.Add("wallet_service")
                }
            }
        }
        finally {
            Pop-Location
        }
    }
}
finally {
    foreach ($name in $walletVariables.Keys) {
        [Environment]::SetEnvironmentVariable($name, $previousWalletVariables[$name], "Process")
    }
}

if ($failedSuites.Count -eq 0) {
    Write-Host "`nAll test suites passed."
}
else {
    Write-Host "`nFailed or skipped suites: $($failedSuites -join ', ')"
    exit 1
}
