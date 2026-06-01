# Script PowerShell para iniciar o sistema completo de RH
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "🚀 Iniciando Sistema Completo de RH" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Abrindo:" -ForegroundColor Yellow
Write-Host "  1. Streamlit (Interface Web)" -ForegroundColor White
Write-Host "  2. LangGraph Studio (Visualização do Grafo)" -ForegroundColor White
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan


## Como rodar o projeto inteiro : bash run_completo.sh
# Ativar ambiente virtual
& .\.venv\Scripts\Activate.ps1

# Abrir Streamlit em nova janela
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; .\.venv\Scripts\Activate.ps1; streamlit run app_streamlit.py"

# Aguardar 2 segundos
Start-Sleep -Seconds 2

# Abrir LangGraph Studio em nova janela
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; .\.venv\Scripts\Activate.ps1; langgraph dev"

Write-Host ""
Write-Host "✅ Ambos os serviços foram iniciados!" -ForegroundColor Green
Write-Host ""
Write-Host "📱 Streamlit: http://localhost:8501" -ForegroundColor Cyan
Write-Host "📊 LangGraph Studio: https://smith.langchain.com/studio/" -ForegroundColor Cyan
Write-Host ""
Write-Host "Pressione qualquer tecla para fechar..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
