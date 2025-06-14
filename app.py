from flask import Flask, render_template, request, redirect, url_for, session, make_response
import os
from prescription import analyze_pdf
from records import add_consultation, add_patient, get_consults, get_patient, get_patients, update_patient, delete_patient_record
import weasyprint
import secrets
import json
from werkzeug.security import check_password_hash


app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

USERNAME = 'admin'
PASSWORD = 'senha123'

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        users = load_users()

        user = next((u for u in users if u['username'] == username), None)

        if user and check_password_hash(user['password'], password):
            session['user'] = username
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='Credenciais inválidas')

    return render_template('login.html')

@app.route('/index')
def index():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    #verify if the user is authenticated
    if 'user' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        pdf_file = request.files.get('pdf_file')

        #if no file is sent, redirects back to the page with an error
        if not pdf_file or pdf_file.filename == '':
            return render_template('upload.html', error='Por favor, selecione um arquivo PDF.')

        #save file temporarily
        temp_pdf_path = f"/tmp/{pdf_file.filename}"
        pdf_file.save(temp_pdf_path)

        #analyze pdf
        diagnostic, prescription, name, gender, age, cpf, phone = analyze_pdf(temp_pdf_path)

        #catalog patient
        patient_id = add_patient(name, age, cpf, gender, phone)

        #catalog consultation with the result
        from datetime import datetime
        today = datetime.today().strftime('%d-%m-%Y')

        add_consultation(
            patient_id,
            f"Data: {today}\n\nDiagnóstico:\n{diagnostic}\n\nPrescrição:\n{prescription}"
        )

        #prepare the final text
        result_text = f"""
Paciente: {name}\nIdade: {age}\nCPF: {cpf}\nSexo: {gender}\nTelefone: {phone}

Consulta cadastrada em {today}.

Diagnóstico:
{diagnostic}

Prescrição sugerida:
{prescription}
"""
        #save result_text in session for later use
        session['result_text'] = result_text

        #render result page
        return render_template('result.html', result_text=result_text)

    return render_template('upload.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route("/download_pdf")
def download_pdf():
    #verify if the user is authenticated
    if 'user' not in session:
        return redirect(url_for('login'))
    
    result_text = session.get('result_text', 'No result available')

    html = render_template("result_pdf.html", result_text=result_text)

    base_url = os.path.abspath(".")

    pdf = weasyprint.HTML(string=html, base_url=base_url).write_pdf()

    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=prescription.pdf'

    return response

@app.route('/catalog')
def catalog():
    #verify if the user is authenticated
    if 'user' not in session:
        return redirect(url_for('login'))

    #search for all registered patients
    patients = get_patients()
    #render the catalog page, passing the list of patients
    return render_template('catalog.html', patients=patients)

@app.route('/patient_result/<int:patient_id>')
def patient_result(patient_id):
    #verify if the user is authenticated
    if 'user' not in session:
        return redirect(url_for('login'))

    #search for the patients data
    patient = get_patient(patient_id)

    #if patient is not found: error
    if patient is None:
        result_text = "Paciente não encontrado."
        return render_template('result.html', result_text=result_text)

    #search all consultations of the patients
    consultations = get_consults(patient_id)

    #if there's no consultation, shows the following message
    if not consultations:
        result_text = f"Paciente: {patient.name}\n\nNenhuma consulta cadastrada."
    else:
        #outputs the last consultation
        latest = consultations[-1]
        result_text = f"""
Paciente: {patient.name}
Idade: {patient.age}
CPF: {patient.cpf}
Sexo: {patient.gender}
Telefone: {patient.phone}

Última consulta:

{latest}
"""

    #renders the result page, showing patient's data
    return render_template('result.html', result_text=result_text)

@app.route('/edit_patient/<int:patient_id>', methods=['GET', 'POST'])
def edit_patient(patient_id):
    #verify if the user is authenticated
    if 'user' not in session:
        return redirect(url_for('login'))

    #search for patient data
    patient = get_patient(patient_id)
    if not patient:
        return "Paciente não encontrado", 404

    #if the form is POST, updates the patient's data
    if request.method == 'POST':
        new_name = request.form['name']
        new_age = request.form['age']
        new_cpf = request.form['cpf']
        new_gender = request.form['gender']
        new_phone = request.form['phone']

        #update the patient's data in the database
        update_patient(patient_id, new_name, new_age, new_cpf, new_gender, new_phone)

        #redirecg to the catalog after editing
        return redirect(url_for('catalog'))

    #if it's a GET, it shows the patient's information
    return render_template('edit_patient.html', patient=patient)

@app.route('/add_consultation/<int:patient_id>', methods=['GET', 'POST'])
def add_consultation_route(patient_id):
    if 'user' not in session:
        return redirect(url_for('login'))

    patient = get_patient(patient_id)
    if not patient:
        return "Paciente não encontrado", 404

    if request.method == 'POST':
        consultation_text = request.form['consultation']
        add_consultation(patient_id, consultation_text)
        return redirect(url_for('add_consultation_route', patient_id=patient_id))

    #load consultations
    raw_consults = get_consults(patient_id)
    consultations = []
    for consult in raw_consults:
        lines = consult.splitlines()
        #summary: only ACIMA or ABAIXO
        summary = [l for l in lines if 'ACIMA' in l.upper() or 'ABAIXO' in l.upper()]
        #search for prescription index
        prescription_lines = []
        for i, l in enumerate(lines):
            if 'Prescrição' in l:
                #everything that comes after
                prescription_lines = [x for x in lines[i+1:] if x.strip()]
                break
        consultations.append({
            'summary': summary,
            'prescription': prescription_lines
        })

    return render_template('add_consultation.html',
                           patient=patient,
                           consultations=consultations)

@app.route('/delete_patient/<int:patient_id>')
def delete_patient(patient_id):
    #verify if the user is authenticated
    if 'user' not in session:
        return redirect(url_for('login'))

    #search for patient's data
    patient = get_patient(patient_id)
    if not patient:
        return "Paciente não encontrado", 404

    #rm the patient from the database
    delete_patient_record(patient_id)

    #redirects to the catalog after rm
    return redirect(url_for('catalog'))

def load_users():
    #load users from users.json
    with open('users.json', 'r', encoding='utf-8') as f:
        return json.load(f)

if __name__ == '__main__':
    #start Flask server as a json
    app.run(debug=True)
