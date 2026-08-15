from flask import Flask, render_template, request, redirect
import sqlite3
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor
import webbrowser
from threading import Timer

app = Flask(__name__)

# =========================
# MODELO IA CLASSIFICAÇÃO
# =========================

X_class = [
    [1, 1, 0],
    [1, 0, 0],
    [0, 0, 1],
    [0, 0, 0],
]

y_class = [
    "Gripe",
    "Infecção Viral",
    "Infarto",
    "Leve"
]

modelo_classificacao = DecisionTreeClassifier()
modelo_classificacao.fit(X_class, y_class)


# =========================
# MODELO IA REGRESSÃO
# =========================

y_reg = [30, 60, 5, 120]

modelo_regressao = DecisionTreeRegressor()
modelo_regressao.fit(X_class, y_reg)


# =========================
# CRIAR BANCO
# =========================

def criar_banco():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pacientes(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            idade INTEGER,
            diagnostico TEXT,
            cor TEXT,
            tempo INTEGER,
            status TEXT DEFAULT 'AGUARDANDO'
        )
    """)

    conn.commit()
    conn.close()


criar_banco()


# =========================
# CLASSIFICAR COR
# =========================

def classificar_cor(tempo):
    if tempo <= 10:
        return "VERMELHO"
    elif tempo <= 30:
        return "AMARELO"
    else:
        return "VERDE"


# =========================
# INDEX
# =========================

@app.route("/", methods=["GET", "POST"])
def index():

    resultado = None

    if request.method == "POST":

        nome = request.form["nome"]
        idade = request.form["idade"]
        sintomas = request.form["sintomas"].lower()

        febre = 1 if "febre" in sintomas else 0
        tosse = 1 if "tosse" in sintomas else 0
        peito = 1 if "peito" in sintomas else 0

        entrada = [[febre, tosse, peito]]

        # Diagnóstico
        diagnostico = modelo_classificacao.predict(entrada)[0]

        # Tempo estimado
        tempo = int(modelo_regressao.predict(entrada)[0])

        # Classificação da prioridade
        cor = classificar_cor(tempo)

        # Salvar no banco
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO pacientes(
                nome,
                idade,
                diagnostico,
                cor,
                tempo
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            nome,
            idade,
            diagnostico,
            cor,
            tempo
        ))

        conn.commit()
        conn.close()

        resultado = {
            "diagnostico": diagnostico,
            "tempo": tempo,
            "cor": cor
        }

    return render_template(
        "index.html",
        resultado=resultado
    )


# =========================
# PAINEL
# =========================

@app.route("/painel")
def painel():

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # Paciente atualmente em atendimento
    cursor.execute("""
        SELECT *
        FROM pacientes
        WHERE status = 'ATENDIMENTO'
        LIMIT 1
    """)

    atendimento = cursor.fetchone()

    # Fila de pacientes
    cursor.execute("""
        SELECT *
        FROM pacientes
        WHERE status = 'AGUARDANDO'
        ORDER BY
            CASE cor
                WHEN 'VERMELHO' THEN 1
                WHEN 'AMARELO' THEN 2
                WHEN 'VERDE' THEN 3
            END,
            id ASC
    """)

    fila = cursor.fetchall()

    conn.close()

    return render_template(
        "painel.html",
        atendimento=atendimento,
        fila=fila
    )


# =========================
# CHAMAR PACIENTE
# =========================

@app.route("/chamar")
def chamar():

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # Verifica se já existe paciente em atendimento
    cursor.execute("""
        SELECT id
        FROM pacientes
        WHERE status = 'ATENDIMENTO'
    """)

    atendimento = cursor.fetchone()

    if atendimento:

        conn.close()

        return redirect("/painel?novo=0")

    # Pega próximo paciente
    cursor.execute("""
        SELECT id, nome, cor
        FROM pacientes
        WHERE status = 'AGUARDANDO'
        ORDER BY
            CASE cor
                WHEN 'VERMELHO' THEN 1
                WHEN 'AMARELO' THEN 2
                WHEN 'VERDE' THEN 3
            END,
            id ASC
        LIMIT 1
    """)

    paciente = cursor.fetchone()

    if paciente:

        cursor.execute("""
            UPDATE pacientes
            SET status = 'ATENDIMENTO'
            WHERE id = ?
        """, (paciente[0],))

        conn.commit()
        conn.close()

        return redirect(
            f"/painel?novo=1&nome={paciente[1]}&cor={paciente[2]}"
        )

    conn.close()

    return redirect("/painel?novo=0")


# =========================
# FINALIZAR
# =========================

@app.route("/finalizar/<int:id>")
def finalizar(id):

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE pacientes
        SET status = 'FINALIZADO'
        WHERE id = ?
    """, (id,))

    conn.commit()
    conn.close()

    return redirect("/painel")


# =========================
# ABRIR NAVEGADOR AUTOMATICAMENTE
# =========================

def abrir_navegador():
    webbrowser.open("http://127.0.0.1:5000")


# =========================
# EXECUTAR
# =========================

if __name__ == "__main__":

    Timer(1, abrir_navegador).start()

    app.run(
        debug=True,
        use_reloader=False
    )