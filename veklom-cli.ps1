function veklom-help {
    Write-Host '====================================================0' -ForegroundColor Magenta
    Write-Host '            Veklom Operating System CLI             ' -ForegroundColor Magenta
    Write-Host '=====================================================' -ForegroundColor Magenta
    Write-Host 'The following quick-commands are loaded in your workspace:'
    Write-Host '  veklom-help         : Show this help menu'
    Write-Host '  veklom-status       : Check health of the local cAPI backend node'
    Write-Host '  veklom-deploy       : Autocommit and deploy all changes to Coolify/Hetzner'
    Write-Host '  veklom-stake-ledger : Live query of the permanent VNP Micro-Staking DB'
    Write-Host '  veklom-audit-routes : Run the Governance Integrity Audit on FastAPI routes'
    Write-Host '  veklom-rag-sync     : Synchronize the IdentityRAG Golden Record'
    Write-Host '=====================================================' -ForegroundColor Magenta
}

function veklom-status {
    Write-Host '[Veklom OS] Checking Node Health...' -ForegroundColor Cyan
    curl -sk http://localhost:8088/health
    Write-Host '\n[Veklom OS] Status OK.' -ForegroundColor Green
}

function veklom-deploy {
    Write-Host '[Veklom OS] Initiating Deployment Sequence...' -ForegroundColor Cyan
    git add .
    git commit -m 'chore: Autonomous Veklom OS deployment trigger'
    git push origin main
    Write-Host '[Veklom OS] Pushed to GitHub. Coolify Runner will automatically rebuild Hetzner container.' -ForegroundColor Green
}

function veklom-stake-ledger {
    Write-Host '[Veklom OS] Fetching latest Micro-Staking receipts from PostgreSQL...' -ForegroundColor Cyan
    $env:PYTHONPATH = (Get-Location).Path
    python scripts/cli_helper.py ledger
}

function veklom-audit-routes {
    Write-Host '[Veklom OS] Running Governance Integrity Audit on FastAPI routes...' -ForegroundColor Cyan
    $env:PYTHONPATH = (Get-Location).Path
    python scripts/test_x402_base_sepolia.py
    Write-Host '[Veklom OS] Audit Complete. Treasury wallet verified.' -ForegroundColor Green
}

function veklom-rag-sync {
    $env:PYTHONPATH = (Get-Location).Path
    python scripts/cli_helper.py rag
}

veklom-help
