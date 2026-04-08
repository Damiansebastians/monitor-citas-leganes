"""
monitor_citas.py — Versión GitHub Actions
==========================================
Las credenciales se leen desde variables de entorno (GitHub Secrets).
No edites este archivo para cambiar credenciales; usa los Secrets del repositorio.
"""

import asyncio
import random
import logging
import smtplib
import sys
import io
import os
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# ─────────────────────────────────────────────────────────────────────────────
#  CONFIGURACION
# ─────────────────────────────────────────────────────────────────────────────

TARGET_URL    = "https://gestiona7.madrid.org/ctac_cita/registro#"
CENTRO_TEXT   = "Registro Civil de Legan\u00e9s"
SERVICIO_TEXT = "CITA PREJURAS"

WAIT_FOR_MODAL_SECONDS = 7
JITTER_MIN = 1.5
JITTER_MAX = 4.0

# Credenciales leídas desde variables de entorno (GitHub Secrets)
SMTP_HOST     = "smtp.gmail.com"
SMTP_PORT     = 587
SMTP_USER     = os.environ["SMTP_USER"]
SMTP_PASSWORD = os.environ["SMTP_PASSWORD"]
EMAIL_FROM    = os.environ["SMTP_USER"]
EMAIL_TO      = [
    "damiansebastians@gmail.com",
    "antonella.lemosrodriguez@gmail.com",
]
EMAIL_SUBJECT = "[ALERTA] CITAS DISPONIBLES - Registro Civil de Legan\u00e9s - CITA PREJURAS"

# ─────────────────────────────────────────────────────────────────────────────

stdout_utf8 = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(stdout_utf8)],
)
log = logging.getLogger(__name__)


def jitter(min_s: float = JITTER_MIN, max_s: float = JITTER_MAX) -> None:
    delay = random.uniform(min_s, max_s)
    time.sleep(delay)


def send_alert_email() -> None:
    log.info(f"[EMAIL] Enviando alerta a: {', '.join(EMAIL_TO)}")
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    body_html = f"""
    <html><body style="font-family:Arial,sans-serif;color:#222;max-width:600px;margin:auto;">
      <div style="background:#c0392b;padding:18px 24px;border-radius:8px 8px 0 0;">
        <h2 style="color:#fff;margin:0;">ALERTA: Citas disponibles</h2>
      </div>
      <div style="border:1px solid #ddd;border-top:none;padding:24px;border-radius:0 0 8px 8px;">
        <p style="font-size:15px;">Se han detectado <strong>citas disponibles</strong>:</p>
        <table style="border-collapse:collapse;width:100%;margin:16px 0;">
          <tr style="background:#f5f5f5;">
            <td style="padding:10px 16px;font-weight:bold;border:1px solid #ddd;">Centro</td>
            <td style="padding:10px 16px;border:1px solid #ddd;">{CENTRO_TEXT}</td>
          </tr>
          <tr>
            <td style="padding:10px 16px;font-weight:bold;border:1px solid #ddd;">Servicio</td>
            <td style="padding:10px 16px;border:1px solid #ddd;">{SERVICIO_TEXT}</td>
          </tr>
          <tr style="background:#f5f5f5;">
            <td style="padding:10px 16px;font-weight:bold;border:1px solid #ddd;">Detectado</td>
            <td style="padding:10px 16px;border:1px solid #ddd;">{now}</td>
          </tr>
        </table>
        <p style="text-align:center;margin-top:24px;">
          <a href="{TARGET_URL}"
             style="background:#c0392b;color:#fff;padding:12px 28px;
                    border-radius:6px;text-decoration:none;font-size:15px;
                    font-weight:bold;display:inline-block;">
            Solicitar cita ahora
          </a>
        </p>
        <hr style="margin-top:28px;border:none;border-top:1px solid #eee;">
        <small style="color:#999;">monitor_citas.py &mdash; Portal de Justicia Comunidad de Madrid</small>
      </div>
    </body></html>
    """
    msg = MIMEMultipart("alternative")
    msg["Subject"] = EMAIL_SUBJECT
    msg["From"]    = EMAIL_FROM
    msg["To"]      = ", ".join(EMAIL_TO)
    msg.attach(MIMEText(body_html, "html", "utf-8"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
    log.info("[EMAIL] Correo enviado correctamente.")


async def check_availability() -> bool:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="es-ES",
        )
        page = await context.new_page()
        try:
            log.info(f"[PASO 1] Navegando a {TARGET_URL} ...")
            await page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=30_000)
            jitter()

            solicitar_btn = page.locator(
                "a:has-text('SOLICITAR CITA'), button:has-text('SOLICITAR CITA')"
            )
            if await solicitar_btn.count() > 0:
                log.info("[PASO 2] Pulsando 'SOLICITAR CITA' ...")
                await solicitar_btn.first.click()
                await page.wait_for_load_state("domcontentloaded")
                jitter()

            log.info(f"[PASO 3] Seleccionando centro: '{CENTRO_TEXT}' ...")
            await page.wait_for_selector("#combo1", timeout=15_000)
            selected = await page.evaluate(
                """
                (texto) => {
                    const sel = document.getElementById('combo1');
                    for (let i = 0; i < sel.options.length; i++) {
                        if (sel.options[i].text.trim() === texto) {
                            sel.selectedIndex = i;
                            sel.dispatchEvent(new Event('change', { bubbles: true }));
                            return sel.options[i].value;
                        }
                    }
                    return null;
                }
                """,
                CENTRO_TEXT,
            )
            if not selected:
                raise ValueError(f"No se encontro '{CENTRO_TEXT}' en el combo.")
            log.info(f"[PASO 3] Centro seleccionado (value={selected}).")
            jitter()

            await page.wait_for_selector("#comboServicios", state="visible", timeout=15_000)
            jitter(0.8, 2.0)

            log.info(f"[PASO 4] Seleccionando servicio: '{SERVICIO_TEXT}' ...")
            selected_svc = await page.evaluate(
                """
                (texto) => {
                    const sel = document.getElementById('comboServicios');
                    for (let i = 0; i < sel.options.length; i++) {
                        if (sel.options[i].text.trim() === texto) {
                            sel.selectedIndex = i;
                            sel.dispatchEvent(new Event('change', { bubbles: true }));
                            return sel.options[i].value;
                        }
                    }
                    return null;
                }
                """,
                SERVICIO_TEXT,
            )
            if not selected_svc:
                raise ValueError(f"No se encontro '{SERVICIO_TEXT}' en el combo.")
            log.info(f"[PASO 4] Servicio seleccionado (value={selected_svc}).")
            jitter()

            log.info("[PASO 5] Pulsando 'Continuar' ...")
            continuar = page.locator("input[value='Continuar'], button:has-text('Continuar')")
            await continuar.first.click()

            log.info(f"[PASO 6] Esperando modal (max {WAIT_FOR_MODAL_SECONDS}s) ...")
            try:
                await page.wait_for_selector(
                    ".ui-dialog:visible", timeout=WAIT_FOR_MODAL_SECONDS * 1_000
                )
                content = await page.locator(".ui-dialog:visible").text_content() or ""
                if "No hay disponibilidad" in content:
                    log.info("[RESULTADO] SIN DISPONIBILIDAD.")
                    return False
                else:
                    log.warning(f"[RESULTADO] Modal inesperado: {content[:80]!r} -> alerta por precaucion.")
                    return True
            except PlaywrightTimeoutError:
                log.info("[RESULTADO] Modal NO detectado. POSIBLE DISPONIBILIDAD.")
                return True

        except Exception as exc:
            log.exception(f"[ERROR] {exc}")
            return False
        finally:
            await browser.close()


async def main() -> None:
    log.info("=" * 55)
    log.info("  Monitor de citas - Registro Civil de Leganes")
    log.info(f"  Centro  : {CENTRO_TEXT}")
    log.info(f"  Servicio: {SERVICIO_TEXT}")
    log.info("=" * 55)

    hay_citas = await check_availability()

    if hay_citas:
        log.info("[ALERTA] CITAS DISPONIBLES. Enviando correo ...")
        send_alert_email()
        log.info("[FIN] Alerta enviada.")
    else:
        log.info("[FIN] Sin disponibilidad. Sin alerta.")

    sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
