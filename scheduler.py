"""
IPAJM Analytics — scheduler.py
Automação de Atualização Diária

Funcionalidades:
  • Baixa novos arquivos XLSX do repositório / FTP / pasta de entrada
  • Executa o ETL (etl_process.py)
  • Regenera insights (analysis.py)
  • Envia e-mail de relatório (sucesso ou falha)
  • Registra logs estruturados em arquivo rotativo
  • Executa via schedule (daemon) ou invocação direta (cron/PythonAnywhere)

Uso:
  python scheduler.py                    # executa UMA rodada agora
  python scheduler.py --daemon           # loop contínuo (roda todo dia às 03:00)
  python scheduler.py --test-email       # apenas envia e-mail de teste

PythonAnywhere (scheduled task):
  /home/usuario/.virtualenvs/venv/bin/python /home/ubuntu/Analytics_Gabriel/scheduler.py
"""

import os
import sys
import time
import logging
import logging.handlers
import smtplib
import traceback
import argparse
import importlib
import subprocess
from datetime import datetime, date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

# ──────────────────────────────────────────────────────────────
# Configurações — edite este bloco
# ──────────────────────────────────────────────────────────────
BASE_PATH   = Path("/home/ubuntu/Analytics_Gabriel")
LOG_DIR     = BASE_PATH / "logs"
LOG_FILE    = LOG_DIR / "scheduler.log"
LOCK_FILE   = BASE_PATH / ".scheduler.lock"

# Horário da execução diária no modo daemon (HH:MM)
DAILY_TIME  = "03:00"

# ── E-mail (preencha ou use variáveis de ambiente)
EMAIL_FROM    = os.getenv("IPAJM_EMAIL_FROM",    "analytics@ipajm.es.gov.br")
EMAIL_TO      = os.getenv("IPAJM_EMAIL_TO",      "ti@ipajm.es.gov.br")
SMTP_HOST     = os.getenv("IPAJM_SMTP_HOST",     "smtp.gmail.com")
SMTP_PORT     = int(os.getenv("IPAJM_SMTP_PORT", "587"))
SMTP_USER     = os.getenv("IPAJM_SMTP_USER",     "")   # deixe vazio para desativar e-mail
SMTP_PASS     = os.getenv("IPAJM_SMTP_PASS",     "")

# ── Fontes de dados (ajuste conforme a origem real)
# Exemplo para pasta de entrada monitorada:
DATA_INPUT_DIR  = BASE_PATH / "data_input"
DATA_FILENAMES  = {
    "ATIVOS":       "SERVIDORES ATIVOS.xlsx",
    "INATIVOS":     "SERVIDORES INATIVOS.xlsx",
    "PENSIONISTAS": "SERVIDORES PENSIONISTAS.xlsx",
}

# ──────────────────────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────────────────────
LOG_DIR.mkdir(parents=True, exist_ok=True)

handler_file    = logging.handlers.RotatingFileHandler(
    LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=10, encoding="utf-8"
)
handler_console = logging.StreamHandler(sys.stdout)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[handler_file, handler_console]
)
log = logging.getLogger("ipajm.scheduler")

# ──────────────────────────────────────────────────────────────
# Lock — impede execuções paralelas
# ──────────────────────────────────────────────────────────────
def acquire_lock() -> bool:
    if LOCK_FILE.exists():
        age = time.time() - LOCK_FILE.stat().st_mtime
        if age < 3600:   # trava válida por 1 hora
            log.warning("Outra instância em execução (lock ativo há %ds). Abortando.", int(age))
            return False
        log.warning("Lock antigo encontrado (%.1f h). Removendo.", age / 3600)
    LOCK_FILE.write_text(str(os.getpid()))
    return True

def release_lock():
    LOCK_FILE.unlink(missing_ok=True)

# ──────────────────────────────────────────────────────────────
# Checagem de arquivos de entrada
# ──────────────────────────────────────────────────────────────
def check_input_files() -> dict:
    """
    Verifica se os arquivos de dados existem em DATA_INPUT_DIR.
    Retorna dict com status de cada arquivo.
    """
    DATA_INPUT_DIR.mkdir(parents=True, exist_ok=True)
    status = {}
    for cat, fname in DATA_FILENAMES.items():
        src = DATA_INPUT_DIR / fname
        dst = BASE_PATH / fname
        if src.exists():
            # Copia para o diretório principal apenas se for mais novo
            if not dst.exists() or src.stat().st_mtime > dst.stat().st_mtime:
                import shutil
                shutil.copy2(src, dst)
                status[cat] = f"✅ Copiado ({src.stat().st_size / 1024:.1f} KB)"
                log.info("Arquivo atualizado: %s → %s", src.name, dst)
            else:
                status[cat] = "⏭  Sem alterações"
                log.info("Sem mudanças em: %s", fname)
        elif dst.exists():
            status[cat] = "⚠️  Usando arquivo existente"
            log.warning("Arquivo de entrada ausente, usando cópia anterior: %s", fname)
        else:
            status[cat] = "❌ NÃO ENCONTRADO"
            log.error("Arquivo obrigatório não encontrado: %s", fname)
    return status

# ──────────────────────────────────────────────────────────────
# Execução do ETL e análise
# ──────────────────────────────────────────────────────────────
def run_module(module_name: str, function_name: str):
    """Importa e executa uma função de um módulo Python no BASE_PATH."""
    if str(BASE_PATH) not in sys.path:
        sys.path.insert(0, str(BASE_PATH))
    mod = importlib.import_module(module_name)
    importlib.reload(mod)           # garante código atualizado
    func = getattr(mod, function_name)
    func()

def run_etl() -> tuple[bool, str]:
    log.info("▶ Iniciando ETL...")
    t0 = time.time()
    try:
        run_module("etl_process", "run_etl")
        elapsed = time.time() - t0
        log.info("✅ ETL concluído em %.1fs.", elapsed)
        return True, f"ETL ok ({elapsed:.1f}s)"
    except Exception:
        msg = traceback.format_exc()
        log.error("❌ Falha no ETL:\n%s", msg)
        return False, msg

def run_analysis() -> tuple[bool, str]:
    log.info("▶ Gerando insights...")
    t0 = time.time()
    try:
        run_module("analysis", "generate_insights")
        elapsed = time.time() - t0
        log.info("✅ Insights gerados em %.1fs.", elapsed)
        return True, f"Insights ok ({elapsed:.1f}s)"
    except Exception:
        msg = traceback.format_exc()
        log.error("❌ Falha na análise:\n%s", msg)
        return False, msg

# ──────────────────────────────────────────────────────────────
# Validação pós-processamento
# ──────────────────────────────────────────────────────────────
def validate_output() -> tuple[bool, dict]:
    """Verifica se o parquet e o JSON foram gerados e não estão corrompidos."""
    checks = {}
    ok = True

    parquet = BASE_PATH / "data_processed.parquet"
    if parquet.exists() and parquet.stat().st_size > 1024:
        try:
            import pandas as pd
            df = pd.read_parquet(parquet)
            checks["parquet"] = f"✅ {len(df):,} linhas, {parquet.stat().st_size / 1024**2:.1f} MB"
        except Exception as e:
            checks["parquet"] = f"❌ Corrompido: {e}"
            ok = False
    else:
        checks["parquet"] = "❌ Ausente ou vazio"
        ok = False

    insights_f = BASE_PATH / "insights.json"
    if insights_f.exists() and insights_f.stat().st_size > 100:
        checks["insights.json"] = f"✅ {insights_f.stat().st_size / 1024:.1f} KB"
    else:
        checks["insights.json"] = "❌ Ausente ou vazio"
        ok = False

    return ok, checks

# ──────────────────────────────────────────────────────────────
# Reinicialização do Dash (PythonAnywhere touch-reload)
# ──────────────────────────────────────────────────────────────
def reload_app():
    """
    No PythonAnywhere, tocar o arquivo WSGI faz o Gunicorn recarregar o app.
    Detecta e toca qualquer arquivo .wsgi no diretório pai.
    """
    wsgi_candidates = list(BASE_PATH.parent.glob("**/*.wsgi")) + \
                      list(BASE_PATH.glob("*.wsgi"))
    for wsgi in wsgi_candidates:
        wsgi.touch()
        log.info("App recarregado via touch: %s", wsgi)
        return
    log.info("Nenhum arquivo WSGI encontrado para reload (modo local).")

# ──────────────────────────────────────────────────────────────
# E-mail de relatório
# ──────────────────────────────────────────────────────────────
def build_email_body(success: bool, file_status: dict,
                     etl_result: str, analysis_result: str,
                     validation: dict, duration_s: float) -> str:
    status_icon = "✅ SUCESSO" if success else "❌ FALHA"
    ts = datetime.now().strftime("%d/%m/%Y às %H:%M:%S")
    files_html = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in file_status.items())
    valid_html  = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in validation.items())

    return f"""
<html><body style="font-family:DM Sans,Arial,sans-serif;background:#0d190c;color:#e8f5e6;padding:24px">
  <div style="max-width:640px;margin:0 auto">
    <div style="background:#172615;border-radius:12px;padding:24px;border:1px solid rgba(45,90,40,0.4)">
      <h2 style="color:#3db836;margin:0 0 4px">IPAJM Analytics</h2>
      <p style="color:#7da878;margin:0 0 20px;font-size:13px">Relatório de Atualização Diária · {ts}</p>

      <div style="background:#0f2e0d;border-radius:8px;padding:14px 18px;margin-bottom:20px;
                  border-left:4px solid {'#3db836' if success else '#e05050'}">
        <strong style="font-size:18px;color:{'#3db836' if success else '#e05050'}">{status_icon}</strong>
        <span style="margin-left:10px;color:#e8f5e6">Duração total: {duration_s:.1f}s</span>
      </div>

      <h3 style="color:#7da878;font-size:13px;letter-spacing:.1em;text-transform:uppercase">
        Arquivos de Entrada</h3>
      <table style="width:100%;border-collapse:collapse;margin-bottom:20px;font-size:13px">
        <tr style="background:#0a1f09">
          <th style="text-align:left;padding:8px 12px;color:#3f6039">Categoria</th>
          <th style="text-align:left;padding:8px 12px;color:#3f6039">Status</th>
        </tr>
        {files_html}
      </table>

      <h3 style="color:#7da878;font-size:13px;letter-spacing:.1em;text-transform:uppercase">
        Resultado do Processamento</h3>
      <pre style="background:#0a1f09;border-radius:6px;padding:12px;font-size:12px;
                  color:#c8f4c5;overflow:auto">{etl_result}
{analysis_result}</pre>

      <h3 style="color:#7da878;font-size:13px;letter-spacing:.1em;text-transform:uppercase;
                  margin-top:20px">Validação dos Artefatos</h3>
      <table style="width:100%;border-collapse:collapse;font-size:13px">
        <tr style="background:#0a1f09">
          <th style="text-align:left;padding:8px 12px;color:#3f6039">Arquivo</th>
          <th style="text-align:left;padding:8px 12px;color:#3f6039">Status</th>
        </tr>
        {valid_html}
      </table>

      <p style="margin-top:24px;font-size:11px;color:#3f6039;text-align:center">
        IPAJM · Sistema de Analytics Institucional · Automação v2.0</p>
    </div>
  </div>
</body></html>"""

def send_email(subject: str, html_body: str):
    if not SMTP_USER or not SMTP_PASS:
        log.info("E-mail desativado (SMTP_USER/PASS não configurados).")
        return
    try:
        msg = MIMEMultipart("alternative")
        msg["From"]    = EMAIL_FROM
        msg["To"]      = EMAIL_TO
        msg["Subject"] = subject
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as s:
            s.ehlo()
            s.starttls()
            s.login(SMTP_USER, SMTP_PASS)
            s.sendmail(EMAIL_FROM, [EMAIL_TO], msg.as_string())
        log.info("E-mail enviado para %s.", EMAIL_TO)
    except Exception:
        log.error("Falha ao enviar e-mail:\n%s", traceback.format_exc())

# ──────────────────────────────────────────────────────────────
# Pipeline principal
# ──────────────────────────────────────────────────────────────
def run_pipeline():
    log.info("=" * 60)
    log.info("IPAJM · Atualização Diária Iniciada — %s",
             datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
    log.info("=" * 60)

    if not acquire_lock():
        return False

    t_start = time.time()
    success = True

    try:
        # 1. Arquivos
        file_status = check_input_files()

        # 2. ETL
        etl_ok, etl_msg = run_etl()
        success = success and etl_ok

        # 3. Análise
        ana_ok, ana_msg = run_analysis()
        success = success and ana_ok

        # 4. Validação
        valid_ok, valid_checks = validate_output()
        success = success and valid_ok

        # 5. Reload do app
        if success:
            reload_app()

    except Exception:
        etl_msg = traceback.format_exc()
        ana_msg = ""
        file_status = {"erro": "Exceção inesperada"}
        valid_checks = {}
        success = False
        log.critical("Exceção não tratada:\n%s", etl_msg)
    finally:
        release_lock()

    duration = time.time() - t_start
    status_str = "SUCESSO" if success else "FALHA"
    log.info("Pipeline finalizado: %s em %.1fs", status_str, duration)

    # 6. E-mail
    subject = f"[IPAJM Analytics] Atualização {date.today():%d/%m/%Y} — {status_str}"
    body    = build_email_body(
        success, file_status, etl_msg, ana_msg, valid_checks, duration
    )
    send_email(subject, body)

    return success

# ──────────────────────────────────────────────────────────────
# Modo Daemon — loop contínuo com schedule
# ──────────────────────────────────────────────────────────────
def run_daemon():
    try:
        import schedule
    except ImportError:
        log.error("Pacote 'schedule' não instalado. Execute: pip install schedule")
        sys.exit(1)

    log.info("Modo daemon iniciado. Execução diária agendada para %s.", DAILY_TIME)
    schedule.every().day.at(DAILY_TIME).do(run_pipeline)

    while True:
        schedule.run_pending()
        time.sleep(30)

# ──────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="IPAJM Analytics — Scheduler de Atualização Diária"
    )
    parser.add_argument("--daemon",       action="store_true",
                        help="Executa em loop contínuo (1× ao dia)")
    parser.add_argument("--test-email",   action="store_true",
                        help="Envia e-mail de teste e sai")
    parser.add_argument("--skip-email",   action="store_true",
                        help="Suprime envio de e-mail nesta execução")
    args = parser.parse_args()

    if args.test_email:
        log.info("Enviando e-mail de teste...")
        send_email(
            "[IPAJM Analytics] Teste de Configuração",
            build_email_body(True, {"TESTE": "✅ Ok"}, "ETL ok", "Insights ok",
                             {"parquet": "✅", "insights.json": "✅"}, 0.1)
        )
        return

    if args.skip_email:
        global SMTP_USER
        SMTP_USER = ""   # desativa envio

    if args.daemon:
        run_daemon()
    else:
        ok = run_pipeline()
        sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
