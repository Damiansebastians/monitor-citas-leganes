# Monitor de Citas - Registro Civil

Script que monitoriza automáticamente la disponibilidad de citas y envía una alerta por correo electrónico si detecta citas disponibles.

## Funcionamiento

1. Cada 5 minutos, GitHub Actions lanza el script en la nube  
2. El script navega a la web, selecciona el centro y servicio  
3. Pulsa "Continuar" y espera 7 segundos  
4. **Si aparece el popup** "No hay disponibilidad" → termina sin enviar nada  
5. **Si NO aparece el popup** → envía alerta a los destinatarios configurados  
