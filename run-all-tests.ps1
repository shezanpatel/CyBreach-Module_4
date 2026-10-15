$ErrorActionPreference = "Stop"

$root = $PSScriptRoot
$pythonLauncher = Get-Command py -ErrorAction SilentlyContinue
if (-not $pythonLauncher) {
    throw "Python 3.12 and the Windows Python launcher (py) are required. Install Python 3.12, then rerun this script."
}

function Invoke-CheckedCommand {
    param(
        [Parameter(Mandatory = $true)][string]$Executable,
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [Parameter(Mandatory = $true)][string]$Description
    )

    & $Executable @Arguments | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw "$Description failed with exit code $LASTEXITCODE."
    }
}

function Initialize-TestEnvironment {
    param(
        [Parameter(Mandatory = $true)][string]$EnvironmentPath,
        [Parameter(Mandatory = $true)][string]$RequirementsPath
    )

    $python = Join-Path $EnvironmentPath "Scripts\python.exe"
    if (-not (Test-Path $python)) {
        Write-Host "Creating Python 3.12 environment: $EnvironmentPath"
        Invoke-CheckedCommand -Executable $pythonLauncher.Source `
            -Arguments @("-3.12", "-m", "venv", $EnvironmentPath) `
            -Description "Creating Python environment"
    }

    if (-not (Test-Path $python)) {
        throw "Python environment was not created at $EnvironmentPath."
    }

    $pythonVersion = & $python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
    if ($LASTEXITCODE -ne 0 -or $pythonVersion -ne "3.12") {
        throw "$EnvironmentPath must use Python 3.12. Remove or rename that environment and rerun this script."
    }

    Write-Host "Installing dependencies from $RequirementsPath"
    Invoke-CheckedCommand -Executable $python `
        -Arguments @("-m", "pip", "install", "-r", $RequirementsPath) `
        -Description "Installing test dependencies"

    return $python
}

function Ensure-WalletTestDatabase {
    $containerName = "wallet-pytest-db"
    $containers = & docker ps -a --filter "name=^/$containerName$" --format "{{.Names}}"
    if ($LASTEXITCODE -ne 0) {
        throw "Docker is unavailable. Start Docker Desktop and rerun this script."
    }

    if ($containers -notcontains $containerName) {
        Write-Host "Creating Wallet test PostgreSQL container on port 55432."
        Invoke-CheckedCommand -Executable "docker" -Arguments @(
            "run", "--name", $containerName,
            "-e", "POSTGRES_USER=wallet_user",
            "-e", "POSTGRES_PASSWORD=wallet_password",
            "-e", "POSTGRES_DB=wallet_db",
            "-p", "55432:5432",
            "-d", "postgres:16-alpine"
        ) -Description "Starting Wallet test database"
    }
    else {
        $running = & docker inspect --format "{{.State.Running}}" $containerName
        if ($LASTEXITCODE -ne 0) {
            throw "Could not inspect the existing $containerName container."
        }
        if ($running -ne "true") {
            Invoke-CheckedCommand -Executable "docker" `
                -Arguments @("start", $containerName) `
                -Description "Starting Wallet test database"
        }
    }

    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        & docker exec $containerName pg_isready -U wallet_user -d wallet_db *> $null
        if ($LASTEXITCODE -eq 0) {
            return
        }
        Start-Sleep -Seconds 2
    }

    throw "Wallet PostgreSQL did not become ready on port 55432."
}

$basePython = Initialize-TestEnvironment `
    -EnvironmentPath (Join-Path $root ".venv") `
    -RequirementsPath (Join-Path $root "services\pod_delta\requirements.txt")
Invoke-CheckedCommand -Executable $basePython `
    -Arguments @("-m", "pip", "install", "-r", (Join-Path $root "services\pod_beta\requirements.txt")) `
    -Description "Installing Pod Beta dependencies"
Invoke-CheckedCommand -Executable $basePython `
    -Arguments @("-m", "pip", "install", "-r", (Join-Path $root "tests\requirements.txt")) `
    -Description "Installing root test dependencies"
$gammaPython = Initialize-TestEnvironment `
    -EnvironmentPath (Join-Path $root "services\pod_gamma\.venv") `
    -RequirementsPath (Join-Path $root "services\pod_gamma\requirements.txt")
$walletDirectory = Join-Path $root "services\wallet_service"
$walletPython = Initialize-TestEnvironment `
    -EnvironmentPath (Join-Path $walletDirectory ".venv312") `
    -RequirementsPath (Join-Path $walletDirectory "requirements.txt")

$suites = @(
    @{
        Name = "root + pod_beta"
        Directory = $root
        Python = $basePython
    },
    @{
        Name = "pod_gamma"
        Directory = Join-Path $root "services\pod_gamma"
        Python = $gammaPython
    },
    @{
        Name = "pod_delta"
        Directory = Join-Path $root "services\pod_delta"
        Python = $basePython
    }
)

$failedSuites = [System.Collections.Generic.List[string]]::new()
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

try {
    Ensure-WalletTestDatabase
    Write-Host "`n=== wallet_service: preparing test database ==="
    Push-Location $walletDirectory
    try {
        & $walletPython -c "import os, psycopg; from pathlib import Path; from app.main import Base, engine; Base.metadata.create_all(bind=engine); connection=psycopg.connect(os.environ['DATABASE_URL'].replace('postgresql+psycopg://','postgresql://')); connection.execute(Path('migrations/008_wallet_audit_trail.sql').read_text()); connection.commit(); connection.close()"
        if ($LASTEXITCODE -ne 0) {
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
finally {
    foreach ($name in $walletVariables.Keys) {
        [Environment]::SetEnvironmentVariable($name, $previousWalletVariables[$name], "Process")
    }
}

if ($failedSuites.Count -eq 0) {
    Write-Host "`nAll test suites passed."
}
else {
    Write-Host "`nFailed suites: $($failedSuites -join ', ')"
    exit 1
}
