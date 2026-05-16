import ccxt
import config
import time
from datetime import datetime, timezone, timedelta
import gspread
from google.oauth2.service_account import Credentials
import json
import os

exchange = ccxt.bingx()

def conectar_sheets():
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    if creds_json:
        creds_dict = json.loads(creds_json)
    else:
        creds_dict = json.load(open("credenciales.json"))
    scopes = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open("Bot trading").sheet1
    return sheet

def inicializar_sheet(sheet):
    if sheet.row_count == 0 or sheet.cell(1, 1).value != "Fecha":
        sheet.append_row(["Fecha", "Hora", "Tipo", "Precio", "Capital", "BTC operado", "BTC acumulado", "Precio promedio compra", "Ganancia bruta", "Comisión (0.2%)", "Ganancia neta", "Acumulado"])

def registrar_operacion(sheet, tipo, precio, ganancia_bruta, acumulado, btc_acumulado, precio_promedio):
    zona_arg = timezone(timedelta(hours=-3))
    ahora = datetime.now(zona_arg)
    capital_nivel = config.TOTAL_CAPITAL / config.GRID_LEVELS
    comision = capital_nivel * 0.002
    ganancia_neta = ganancia_bruta - comision
    btc_operado = capital_nivel / precio
    sheet.append_row([
        ahora.strftime("%d/%m/%Y"),
        ahora.strftime("%H:%M:%S"),
        tipo,
        precio,
        round(capital_nivel, 2),
        round(btc_operado, 6),
        round(btc_acumulado, 6),
        round(precio_promedio, 2) if precio_promedio else 0,
        round(ganancia_bruta, 4),
        round(comision, 4),
        round(ganancia_neta, 4),
        round(acumulado, 4)
    ])

def obtener_precio_actual():
    ticker = exchange.fetch_ticker(config.SYMBOL)
    return ticker['last']

def calcular_grilla():
    niveles = []
    rango = config.UPPER_PRICE - config.LOWER_PRICE
    paso = rango / config.GRID_LEVELS
    for i in range(config.GRID_LEVELS + 1):
        precio = config.LOWER_PRICE + (paso * i)
        niveles.append(round(precio, 2))
    return niveles

def ejecutar_bot():
    print("🤖 Bot iniciado en modo PAPER TRADING (sin dinero real)")
    sheet = conectar_sheets()
    inicializar_sheet(sheet)
    print(f"Par: {config.SYMBOL}")
    grilla = calcular_grilla()
    print(f"Niveles de grilla: {grilla}")
    capital_por_nivel = config.TOTAL_CAPITAL / config.GRID_LEVELS
    print(f"Capital por nivel: {capital_por_nivel} USDT")
    print("─" * 50)

    ultimo_precio = None
    ganancias = 0
    btc_acumulado = 0
    compras_sin_vender = []

    while True:
        try:
            precio_actual = obtener_precio_actual()
            print(f"\n💲 Precio actual BTC: ${precio_actual:,.2f}")

            for i in range(len(grilla) - 1):
                nivel_compra = grilla[i]
                nivel_venta = grilla[i + 1]
                ganancia_celda = (nivel_venta - nivel_compra) / nivel_compra * capital_por_nivel
                btc_nivel = capital_por_nivel / nivel_compra

                if ultimo_precio and ultimo_precio > nivel_compra and precio_actual <= nivel_compra:
                    btc_acumulado += btc_nivel
                    compras_sin_vender.append(nivel_compra)
                    precio_promedio = sum(compras_sin_vender) / len(compras_sin_vender)
                    print(f"🟢 COMPRA en ${nivel_compra:,.2f} | BTC acumulado: {btc_acumulado:.6f} | Precio promedio: ${precio_promedio:,.2f}")
                    registrar_operacion(sheet, "COMPRA", nivel_compra, 0, ganancias, btc_acumulado, precio_promedio)

                if ultimo_precio and ultimo_precio < nivel_venta and precio_actual >= nivel_venta:
                    ganancias += ganancia_celda
                    if compras_sin_vender:
                        compras_sin_vender.pop(0)
                    btc_acumulado = max(0, btc_acumulado - btc_nivel)
                    precio_promedio = sum(compras_sin_vender) / len(compras_sin_vender) if compras_sin_vender else 0
                    print(f"🔴 VENTA en ${nivel_venta:,.2f} | Ganancia: ${ganancia_celda:.2f} | Total: ${ganancias:.2f}")
                    registrar_operacion(sheet, "VENTA", nivel_venta, ganancia_celda, ganancias, btc_acumulado, precio_promedio)

            ultimo_precio = precio_actual
            time.sleep(10)

        except Exception as e:
            print(f"Error: {e}")
            time.sleep(10)

ejecutar_bot()