from flask import Flask, redirect, request, jsonify, render_template, url_for
import dns.resolver
import requests
import random   # <-- NUEVA IMPORTACIÓN
import string   # <-- NUEVA IMPORTACIÓN

# =======================================================
# 📌 1. CONFIGURACIÓN
# =======================================================

app = Flask(__name__)

# --- INICIO DE TU CONFIGURACIÓN ---
# ¡Asegúrate de que tus claves reales estén aquí!
BASE_DOMAIN = "ivalogar.es"
ZONE_ID = "543ab8e2-b579-11f0-85e2-0a58644419f7"
IONOS_API_KEY = "afefea2422aa4e25804088e6f8f1463d"
IONOS_API_SECRET = "E3tWdOxQLNiiyTXVVXB9wZgTvBJTAJvjNV4ej9cJRcHFYGRfdwvyELS5tNUW5b9mpZDVJ6pvhvF0U1ImimziMA"
IONOS_API_BASE = "https://api.hosting.ionos.com/dns/v1" 
TTL_SECONDS = 300 
# --- FIN DE TU CONFIGURACIÓN ---
# =======================================================


# -------------------------------------------------------
# A. FUNCIÓN AUXILIAR (NUEVA)
# -------------------------------------------------------
def generate_short_path(length=6):
    """Genera una cadena aleatoria simple para la ruta corta."""
    # Usa letras (mayúsculas/minúsculas) y números
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


# -------------------------------------------------------
# B. RUTA DE REDIRECCIÓN (LECTURA DE DNS)
# -------------------------------------------------------

@app.route('/<short_path>', methods=['GET'])
def redirect_from_short_url(short_path):
    """Maneja la ruta corta, consulta el DNS y redirige."""
    
    dns_name_to_query = f"{short_path}.{BASE_DOMAIN}"
    
    try:
        answers = dns.resolver.resolve(dns_name_to_query, 'TXT')
        full_url = answers[0].strings[0].decode('utf-8')
        return redirect(full_url, code=302)

    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
        return "Error: URL corta no encontrada.", 404
    except Exception as e:
        print(f"Error inesperado durante la resolución DNS: {e}")
        return "Error interno del servidor.", 500


# -------------------------------------------------------
# C. RUTA DEL FORMULARIO WEB (CREACIÓN)
# -------------------------------------------------------

@app.route('/', methods=['GET'])
def index():
    """Muestra el formulario HTML."""
    return render_template('index.html', domain=BASE_DOMAIN)


@app.route('/create', methods=['POST'])
def handle_creation():
    """Procesa el formulario, llama a la API de IONOS y devuelve el resultado."""
    
    # --- ¡CAMBIO IMPORTANTE! ---
    # Ya no leemos 'short_path' del formulario, lo generamos.
    short_path = generate_short_path()
    long_url = request.form.get('long_url', '').strip()

    # La validación ahora solo comprueba la URL larga
    if not long_url:
        return render_template('result.html', success=False, message="La URL larga es obligatoria."), 400

    # Usamos la hipótesis correcta que encontramos (enviar nombre completo)
    full_dns_name = f"{short_path}.{BASE_DOMAIN}"

    new_record = {
        "name": full_dns_name,
        "type": "TXT",
        "content": long_url, 
        "ttl": TTL_SECONDS 
    }

    # Encabezado de autenticación
    auth_value = f"{IONOS_API_KEY}.{IONOS_API_SECRET}"
    headers = {
        "X-API-Key": auth_value, 
        "Content-Type": "application/json"
    }
        
    api_url = f"{IONOS_API_BASE}/zones/{ZONE_ID}/records"

    try:
        response = requests.post(api_url, json=[new_record], headers=headers)
        response.raise_for_status() 

        # ¡IMPORTANTE! La URL acortada ahora es http://127.0.0.1:5000/<short_path>
        # Y la URL "pública" es http://<BASE_DOMAIN>/<short_path>
        
        # Le mostramos al usuario la URL acortada (para probar en local)
        shortened_url_local = url_for('redirect_from_short_url', short_path=short_path, _external=True)
        
        return render_template('result.html', success=True, shortened_url=shortened_url_local, ttl_seconds=TTL_SECONDS)

    except requests.exceptions.HTTPError as errh:
        # Si el error es 409 (Conflicto), significa que el código aleatorio ya existía.
        if errh.response.status_code == 409:
             error_message = "Error: El código generado aleatoriamente ya existe. Por favor, inténtalo de nuevo."
        else:
            error_message = f"Fallo de la API de IONOS ({errh.response.status_code}). Detalle: {errh.response.text}"
        
        return render_template('result.html', success=False, message=error_message), errh.response.status_code
    
    except Exception as e:
        return render_template('result.html', success=False, message=f"Error inesperado: {e}"), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
