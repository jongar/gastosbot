from telegram.ext import Application, MessageHandler, filters
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import os
from telegram.ext import CommandHandler
import matplotlib.pyplot as plt
import tempfile
import json
from pathlib import Path


# -----------------
# CONFIG
# -----------------

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError(
        "BOT_TOKEN no encontrado en las variables de entorno."
    )

SCOPES = (
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
)

CATEGORIAS = {
    "vivienda",
    "comida",
    "jonathan",
    "lorena",
    "transporte",
    "ahorros",
    "apolo",
    "hogar",
    "entretenimiento",
}


# -----------------
# GOOGLE SHEETS
# -----------------

google_credentials = os.getenv("GOOGLE_CREDENTIALS")

if google_credentials:

    print("☁️ Railway")

    creds = Credentials.from_service_account_info(
        json.loads(google_credentials),
        scopes=SCOPES
    )

else:

    print("💻 Local")

    ruta = Path(__file__).parent / "credenciales.json"

    if not ruta.exists():
        raise FileNotFoundError("No existe credenciales.json")

    creds = Credentials.from_service_account_file(
        ruta,
        scopes=SCOPES
    )

cliente = gspread.authorize(creds)

spreadsheet = cliente.open_by_url("https://docs.google.com/spreadsheets/d/1hmJDlbAIIGPkh0Eg97WU7BmfW-7nsxSGrvPaavrHg_Q/edit?gid=0#gid=0")

hoja = spreadsheet.worksheet("Registro diario")

# -----------------
# BOT
# -----------------

async def registrar(update, context):

    texto = update.message.text.strip()

    lineas = texto.split("\n")

    registros = []
    errores = []
    filas = []

    fecha = datetime.now().strftime("%Y-%m-%d %H:%M")

    for numero, linea in enumerate(lineas, start=1):

        try:

            partes = linea.split()

            if len(partes) < 2:
                raise ValueError()

            if not partes[0].isdigit():
                raise ValueError()

            valor = int(partes[0])

            categoria = partes[1].lower().strip()

            if categoria not in CATEGORIAS:

                errores.append(
                    f"❌ Línea {numero}: categoría inválida"
                )

                continue

            categoria = categoria.title()

            descripcion = " ".join(partes[2:])

            filas.append([
                fecha,
                valor,
                categoria,
                descripcion
            ])

            registros.append(
                f"💰 ${valor:,} | {categoria} | {descripcion}"
            )

        except ValueError:

            errores.append(
                f"❌ Línea {numero}: formato inválido"
            )

    if filas:
        guardar_filas(filas)

    respuesta = ""

    if registros:

        respuesta += (
            f"✅ Registrados: {len(registros)}\n\n"
        )

        respuesta += "\n".join(registros)

    if errores:

        respuesta += (
            "\n\n⚠️ Errores\n"
        )

        respuesta += "\n".join(errores)

    if respuesta == "":

        respuesta = (
            "❌ No se registró ningún gasto"
        )

    await update.message.reply_text(
        respuesta
    )

    
def guardar_filas(filas):

    try:

        siguiente_fila = len(hoja.get_all_values()) + 1

        hoja.insert_rows(
            filas,
            row=siguiente_fila,
            value_input_option="USER_ENTERED"
        )

    except Exception as e:

        print(e)
        raise



async def resumen(update, context):

    datos = hoja.get_all_records()

    if not datos:

        await update.message.reply_text(
            "No hay gastos registrados"
        )

        return

    total = 0
    categorias = {}

    for fila in datos:

        categoria = str(
            fila["CONCEPTO"]
        )

        valor = str(
            fila["VALOR"]
        )

        valor = (
            valor
            .replace("$", "")
            .replace(".", "")
            .replace(",", "")
        )

        valor = float(
            valor
        )

        total += valor

        categorias[categoria] = (
            categorias.get(
                categoria,
                0
            )
            + valor
        )

    top = sorted(
        categorias.items(),
        key=lambda x: x[1],
        reverse=True
    )[:3]

    texto = (
        "📊 Resumen\n\n"
    )

    texto += (
        f"💰 Total gastado\n"
        f"${total:,.0f}\n\n"
    )

    texto += "Top categorías\n"

    emojis = [
        "🥇",
        "🥈",
        "🥉"
    ]

    for i, (
        categoria,
        valor
    ) in enumerate(
        top
    ):

        texto += (
            f"{emojis[i]} "
            f"{categoria}: "
            f"${valor:,.0f}\n"
        )

    await update.message.reply_text(
        texto
    )

async def estado(update, context):

    datos = hoja.get_all_records()

    presupuesto = {
        "Jonathan":667000,
        "Lorena":667000,
        "Apolo":529200,
        "Ahorros":5350000,
        "Hogar":3170000,
        "Entretenimiento":332000,
        "Comida":1588000,
        "Vivienda":1303000
    }

    gastado = {}

    for fila in datos:

        categoria = fila[
            "CONCEPTO"
        ]

        valor = str(
            fila[
                "VALOR"
            ]
        )

        valor = (
            valor
            .replace("$", "")
            .replace(".", "")
            .replace(",", "")
        )

        valor = float(
            valor
        )

        gastado[
            categoria
        ] = (
            gastado.get(
                categoria,
                0
            )
            + valor
        )

    texto = "📍 Estado\n\n"

    for categoria in presupuesto:

        usado = gastado.get(
            categoria,
            0
        )

        porcentaje = min(
            usado /
            presupuesto[
                categoria
            ],
            1
        )

        barra = (
            "█"
            *
            int(
                porcentaje
                *
                10
            )
        )

        barra += (
            "░"
            *
            (
                10
                -
                len(
                    barra
                )
            )
        )

        texto += (
            f"{categoria}\n"
            f"{barra} "
            f"{porcentaje*100:.0f}%\n\n"
        )

    await update.message.reply_text(
        texto
    )
async def top(update, context):

    datos = hoja.get_all_records()

    gastos = []

    for fila in datos:

        try:

            valor = str(
                fila["VALOR"]
            )

            valor = (
                valor
                .replace("$", "")
                .replace(".", "")
                .replace(",", "")
            )

            valor = float(
                valor
            )

            descripcion = str(
                fila[
                    "DESCRIPCION"
                ]
            )

            categoria = str(
                fila[
                    "CONCEPTO"
                ]
            )

            gastos.append(
                (
                    valor,
                    categoria,
                    descripcion
                )
            )

        except Exception as e:
            print(e)

    gastos = sorted(
        gastos,
        reverse=True
    )[:5]

    texto = "🏆 Top gastos\n\n"

    posiciones = [
        "🥇",
        "🥈",
        "🥉",
        "4️⃣",
        "5️⃣"
    ]

    for i, (
        valor,
        categoria,
        descripcion
    ) in enumerate(
        gastos
    ):

        texto += (
            f"{posiciones[i]} "
            f"{descripcion}\n"
            f"${valor:,.0f}\n"
            f"🏷️ {categoria}\n\n"
        )

    await update.message.reply_text(
        texto
    )

async def proyeccion(update, context):

    from datetime import datetime
    import calendar

    datos = hoja.get_all_records()

    total = 0

    for fila in datos:

        try:

            valor = str(
                fila["VALOR"]
            )

            valor = (
                valor
                .replace("$", "")
                .replace(".", "")
                .replace(",", "")
            )

            total += float(
                valor
            )

        except:
            pass

    hoy = datetime.now()

    dia = hoy.day

    dias_mes = calendar.monthrange(
        hoy.year,
        hoy.month
    )[1]

    promedio = (
        total /
        dia
    )

    proyeccion = (
        promedio *
        dias_mes
    )

    presupuesto = 13235900

    disponible = (
        presupuesto
        -
        proyeccion
    )

    if proyeccion < presupuesto * 0.8:
        estado = "🟢 Bajo control"

    elif proyeccion < presupuesto:
        estado = "🟡 Cuidado"

    else:
        estado = "🔴 Sobre presupuesto"

    texto = (
f"""📈 Proyección mensual

💰 Gastado
${total:,.0f}

📆 Promedio diario
${promedio:,.0f}

🎯 Proyección fin de mes
${proyeccion:,.0f}

🏦 Disponible
${disponible:,.0f}

{estado}
"""
    )

    await update.message.reply_text(
        texto
    )

async def insights(update, context):

    datos = hoja.get_all_records()

    presupuesto = {
        "Jonathan":1006200,
        "Lorena":762000,
        "Apolo":460000,
        "Ahorros":5350000,
        "Hogar":2267000,
        "Entretenimiento":332000,
        "Comida":1788700,
        "Vivienda":1270000
    }

    gasto = {}
    total = 0

    for fila in datos:

        try:

            categoria = str(
                fila["CONCEPTO"]
            )

            valor = str(
                fila["VALOR"]
            )

            valor = (
                valor
                .replace("$","")
                .replace(".","")
                .replace(",","")
            )

            valor = float(
                valor
            )

            total += valor

            gasto[categoria] = (
                gasto.get(
                    categoria,
                    0
                )
                + valor
            )

        except:
            pass

    texto = "🧠 Insights\n\n"

    top = max(
        gasto,
        key=gasto.get
    )

    porcentaje = (
        gasto[top]
        /
        total
        *
        100
    )

    texto += (
        f"🥇 Mayor gasto\n"
        f"{top}\n"
        f"${gasto[top]:,.0f}\n"
        f"({porcentaje:.0f}%)\n\n"
    )

    if "Comida" in gasto:

        comida = (
            gasto["Comida"]
            /
            total
            *
            100
        )

        texto += (
            f"🍔 Comida representa "
            f"{comida:.0f}%\n\n"
        )

    if "Ahorros" in gasto:

        ahorro = (
            gasto["Ahorros"]
            /
            total
            *
            100
        )

        texto += (
            f"💰 Inversión representa "
            f"{ahorro:.0f}%\n\n"
        )

    alertas = []

    for cat in presupuesto:

        if cat in gasto:

            uso = (
                gasto[cat]
                /
                presupuesto[cat]
                *
                100
            )

            if uso >= 100:

                alertas.append(
                    f"⚠️ {cat} agotó presupuesto"
                )

            elif uso >= 80:

                alertas.append(
                    f"🟡 {cat} va en {uso:.0f}%"
                )

    if alertas:

        texto += (
            "Alertas\n"
        )

        texto += (
            "\n".join(
                alertas
            )
        )

    await update.message.reply_text(
        texto
    )

async def graph(update, context):

    datos = hoja.get_all_records()

    categorias = {}

    for fila in datos:

        try:

            categoria = str(
                fila["CONCEPTO"]
            )

            valor = str(
                fila["VALOR"]
            )

            valor = (
                valor
                .replace("$","")
                .replace(".","")
                .replace(",","")
            )

            valor = float(
                valor
            )

            categorias[categoria] = (
                categorias.get(
                    categoria,
                    0
                )
                + valor
            )

        except:
            pass

    if not categorias:

        await update.message.reply_text(
            "No hay datos"
        )

        return

    nombres = list(
        categorias.keys()
    )

    valores = list(
        categorias.values()
    )

    plt.figure(
        figsize=(8,8)
    )

    plt.pie(
        valores,
        labels=nombres,
        autopct="%1.0f%%"
    )

    plt.title(
        "Distribución gastos"
    )

    archivo = tempfile.NamedTemporaryFile(
        suffix=".png",
        delete=False
    )

    plt.savefig(
        archivo.name,
        bbox_inches="tight"
    )

    plt.close()

    with open(
        archivo.name,
        "rb"
    ) as imagen:

        await update.message.reply_photo(
            photo=imagen,
            caption="📈 Distribución gastos"
        )

async def help(update, context):

    texto = """
🤖 GastosBot

📝 Registro
Envía:
valor categoria descripcion

Ejemplo:
58000 comida mercado

📊 Comandos

/resumen
Resumen del mes

/estado
Presupuesto consumido

/top
Mayores gastos

/proyeccion
Proyección fin de mes

/insights
Análisis automático

/graph
Gráfica de distribución

/help
Ver comandos
"""

    await update.message.reply_text(
        texto
    )


async def faltante(update, context):

    datos = hoja.get_all_records()

    presupuesto = {
        "Jonathan":1006200,
        "Lorena":762000,
        "Apolo":460000,
        "Ahorros":5350000,
        "Hogar":2267000,
        "Entretenimiento":332000,
        "Comida":1788700,
        "Vivienda":1270000
    }

    gastado = {}

    for fila in datos:

        try:

            categoria = str(
                fila["CONCEPTO"]
            )

            valor = str(
                fila["VALOR"]
            )

            valor = (
                valor
                .replace("$","")
                .replace(".","")
                .replace(",","")
            )

            valor = float(
                valor
            )

            gastado[categoria] = (
                gastado.get(
                    categoria,
                    0
                )
                + valor
            )

        except Exception as e:
            print(e)

    texto = (
        "💸 Disponible presupuesto\n\n"
    )

    for categoria in presupuesto:

        usado = (
            gastado.get(
                categoria,
                0
            )
        )

        restante = (
            presupuesto[
                categoria
            ]
            -
            usado
        )

        porcentaje = (
            usado
            /
            presupuesto[
                categoria
            ]
            *
            100
        )

        if restante >= 0:

            texto += (
                f"🟢 {categoria}\n"
                f"${restante:,.0f} restantes\n"
                f"({porcentaje:.0f}% usado)\n\n"
            )

        else:

            texto += (
                f"🔴 {categoria}\n"
                f"Excedido por "
                f"${abs(restante):,.0f}\n"
                f"({porcentaje:.0f}% usado)\n\n"
            )

    await update.message.reply_text(
        texto
    )


# -----------------
# APP
# -----------------

app = (
    Application
    .builder()
    .token(BOT_TOKEN)
    .build()
)


# COMANDOS
app.add_handler(
    CommandHandler(
        "resumen",
        resumen
    )
)

app.add_handler(
    CommandHandler(
        "estado",
        estado
    )
)

app.add_handler(
    CommandHandler(
        "top",
        top
    )
)

app.add_handler(
    CommandHandler(
        "proyeccion",
        proyeccion
    )
)

app.add_handler(
    CommandHandler(
        "insights",
        insights
    )
)

app.add_handler(
    CommandHandler(
        "graph",
        graph
    )
)

app.add_handler(
    CommandHandler(
        "help",
        help
    )
)

app.add_handler(
    CommandHandler(
        "menu",
        help
    )
)

app.add_handler(
    CommandHandler(
        "faltante",
        faltante
    )
)

# MENSAJES
app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        registrar
    )
)


print(
    "🚀 GastosBot activo"
)

app.run_polling()
