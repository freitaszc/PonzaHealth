import json
import os

PATIENTS_FILE = 'patients.json'
CONSULTS_FILE = 'consults.json'

#simple patient class
class Patient:
    def __init__(self, id, name, age, cpf, gender, phone):
        self.id = id
        self.name = name
        self.age = age
        self.cpf = cpf
        self.gender = gender
        self.phone = phone

#load all patients
def get_patients():
    if not os.path.exists(PATIENTS_FILE):
        return []

    with open(PATIENTS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    patients = []
    for item in data:
        patient = Patient(
            id=item.get('id'),
            name=item.get('name', ''),
            age=item.get('age', 0),
            cpf=item.get('cpf', ''),
            gender=item.get('gender', ''),
            phone=item.get('phone', '')
        )
        patients.append(patient)

    return patients

#returns a patient by his ID
def get_patient(patient_id):
    patients = get_patients()
    for patient in patients:
        if patient.id == patient_id:
            return patient
    return None

#add a new patient
def add_patient(name, age, cpf, gender, phone):
    patients = get_patients()

    #generate a new ID
    new_id = 1
    if patients:
        new_id = max(patient.id for patient in patients) + 1

    new_patient = Patient(new_id, name, int(age), cpf, gender, phone)
    patients.append(new_patient)

    save_patients(patients)

    return new_id

def update_patient(patient_id, name, age, cpf, gender, phone):
    patients = get_patients()

    for patient in patients:
        if patient.id == patient_id:
            patient.name = name
            patient.age = int(age)
            patient.cpf = cpf
            patient.gender = gender
            patient.phone = phone
            break

    save_patients(patients)

#catalog all patients on the JSON file
def save_patients(patients):
    patients_data = []
    for patient in patients:
        patients_data.append({
            "id": patient.id,
            "name": patient.name,
            "age": patient.age,
            "cpf": patient.cpf,
            "gender": patient.gender,
            "phone": patient.phone
        })

    with open(PATIENTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(patients_data, f, indent=4, ensure_ascii=False)

#add a new consultation to a patient
def add_consultation(patient_id, consultation_text):
    consults = {}

    #if file exists, it loads the consultations
    if os.path.exists(CONSULTS_FILE):
        with open(CONSULTS_FILE, 'r', encoding='utf-8') as f:
            consults = json.load(f)

    #guarantees that patient_id is a string to support JSON
    patient_id_str = str(patient_id)

    #creates a list to a patient if it doesn't exist
    if patient_id_str not in consults:
        consults[patient_id_str] = []

    #add a new consultation
    consults[patient_id_str].append(consultation_text)

    #save again
    with open(CONSULTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(consults, f, indent=4, ensure_ascii=False)

#to return consultations of a patient
def get_consults(patient_id):
    if not os.path.exists(CONSULTS_FILE):
        return []

    with open(CONSULTS_FILE, 'r', encoding='utf-8') as f:
        consults = json.load(f)

    patient_id_str = str(patient_id)
    return consults.get(patient_id_str, [])

def delete_patient_record(patient_id):
    patients = get_patients()
    patients = [p for p in patients if p.id != patient_id]
    save_patients(patients)

    if os.path.exists(CONSULTS_FILE):
        with open(CONSULTS_FILE, 'r', encoding='utf-8') as f:
            consults = json.load(f)

        patient_id_str = str(patient_id)
        if patient_id_str in consults:
            del consults[patient_id_str]

        with open(CONSULTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(consults, f, indent=4, ensure_ascii=False)
