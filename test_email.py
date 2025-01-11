import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def test_email():
    from_email = "hugoaromerop@gmail.com"  # Tu correo de Gmail
    from_password = "bczv ayqp tmvq avqx"  # Genera una contraseña de aplicación en Gmail
    to_email = "adptriana@gmail.com"  # Correo destino

    subject = "Prueba de Correo"
    body = "Este es un correo de prueba desde el Sistema SACCE."

    # Configuración del mensaje
    message = MIMEMultipart()
    message["From"] = from_email
    message["To"] = to_email
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))

    try:
        # Cambiar a Gmail SMTP
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(from_email, from_password)
        server.sendmail(from_email, to_email, message.as_string())
        server.quit()
        print(f"Correo enviado exitosamente a {to_email}")
    except Exception as e:
        print(f"Error al enviar el correo: {e}")

test_email()
