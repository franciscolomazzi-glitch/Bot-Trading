import os

# Credenciales - se leen desde variables de entorno (Railway)
API_KEY = os.environ.get("API_KEY", "")
SECRET_KEY = os.environ.get("SECRET_KEY", "")

# Configuración del bot
SYMBOL = "BTC/USDT"
LOWER_PRICE = 80000
UPPER_PRICE = 82000
GRID_LEVELS = 13
TOTAL_CAPITAL = 1000