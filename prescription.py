from PyPDF2 import PdfReader
import json
import re

#read the PDF and return the text as a list of lines
def read_pdf(file_path):
    try:
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""

        lines = text.splitlines()
        lines = [line.strip() for line in lines if line.strip()]
        if not lines:
            print(f"[read_pdf] Aviso: PDF lido, mas nenhum texto extraído.")
            return []

        return lines
    
    except Exception as e:
        print(f"Erro lendo o arquivo: {e}")
        return []

def extract_patient_info(lines):
    name = ""
    gender = ""
    birth_date = ""
    age = 0
    cpf = ""
    phone = ""

    for line in lines:
        line = line.strip()

        #name
        if line.startswith("Paciente "):
            name = line.replace("Paciente ", "").strip()

        #CPF
        cpf_match = re.search(r'CPF\s+(\d{3}\.\d{3}\.\d{3}-\d{2})', line)
        if cpf_match:
            cpf = cpf_match.group(1)

        #gender and birthday
        elif "Sexo" in line and "Dt nasc." in line:
            match = re.search(r"Sexo\s+([MF])\s+Dt nasc\. (\d{2}/\d{2}/\d{4})", line)
            if match:
                gender = match.group(1)
                birth_date = match.group(2)

                from datetime import datetime
                try:
                    birth_date_dt = datetime.strptime(birth_date, "%d/%m/%Y")
                    today = datetime.today()
                    age = today.year - birth_date_dt.year - ((today.month, today.day) < (birth_date_dt.month, birth_date_dt.day))
                except:
                    age = 0

    return name, gender, age, cpf, phone

#read the JSON file with the references (ideal values and medication suggestions)
def read_references(references_path):
    try:
        with open(references_path, "r", encoding="utf-8") as f:
            references = json.load(f)
            return references
    except FileNotFoundError:
        print(f"[read_references] Arquivo não encontrado: {references_path}")
    except json.JSONDecodeError as e:
        print(f"[read_references] JSON inválido em '{references_path}': {e}")
    return None

#parse min and max values from strings with hifen in the middle, like ("75-90ml")
def parse_min_max(ideal_text: str):
    m = re.search(r"([0-9]+(?:[.,][0-9]+)?)[^\d]+([0-9]+(?:[.,][0-9]+)?)", ideal_text)
    if not m:
        return None, None
    try:
        min_val = float(m.group(1).replace(",", "."))
        max_val = float(m.group(2).replace(",", "."))
        return min_val, max_val
    except ValueError:
        return None, None

#compare references with extracted values from the PDF
def scan_results(lines: list[str], references: dict, gender) -> dict:
    results = {}

    #pattern to find the first number in a line (integer or decimal)
    number_pattern = re.compile(r"([0-9]+(?:[.,][0-9]+)?)")

    for test_name, test_info in references.items():
        found = False
        synonyms = [s.lower() for s in test_info.get("synonyms", [])] + [test_name.lower()]

        for line in lines:
            lower_line = line.lower()
            if any(term in lower_line for term in synonyms):
                found = True

                match = number_pattern.search(line)
                if match:
                    raw_value = match.group(1).replace(",", ".")
                    try:
                        extracted_value = float(raw_value)
                    except ValueError:
                        extracted_value = None
                else:
                    extracted_value = None

                medication_suggestion = None
                ideal_data = test_info.get("ideal")

                if isinstance(ideal_data, dict):
                    ideal_text = ideal_data.get(gender)
                    if ideal_text is None:
                        first_key = next(iter(ideal_data))
                        ideal_text = ideal_data[first_key]
                else:
                    ideal_text = ideal_data

                min_val, max_val = parse_min_max(str(ideal_text))
                if min_val is None or max_val is None:
                    continue

                if extracted_value is not None and min_val is not None and extracted_value < min_val:
                    medication_suggestion = test_info.get("medications", {}).get("low")
                elif extracted_value is not None and max_val is not None and extracted_value > max_val:
                    medication_suggestion = test_info.get("medications", {}).get("high")

                #save ideal_text
                results[test_name] = {
                    "extracted_value": extracted_value,
                    "line": line.strip(),
                    "ideal": ideal_text,
                    "medication_suggestion": medication_suggestion
                }
                break

        if not found:
            results[test_name] = {
                "extracted_value": None,
                "line": None,
                "ideal": None,
                "medication_suggestion": None
            }

    return results

#function used by the website - returns a full text string ready to display
def analyze_pdf(file_path, references_path="references.json"):
    lines = read_pdf(file_path)
    references = read_references(references_path)
    
    if lines is None or references is None:
        return "Erro ao ler o PDF ou as referências.", "", "", "", 0, "", ""

    #extract patient's data
    name, gender, age, cpf, phone = extract_patient_info(lines)

    #get the correct gender
    results = scan_results(lines, references, gender)

    #build the final result text to show on the website
    diagnostic_text = ""
    prescription_text = ""

    for test, info in results.items():
        extracted = info["extracted_value"]
        ideal_text = info["ideal"]
        suggestion = info["medication_suggestion"]

        if extracted is None or ideal_text is None:
            continue

        min_val, max_val = parse_min_max(str(ideal_text))
        if min_val is None or max_val is None:
            continue

        if extracted < min_val:
            diagnostic_text += f"{test}: valor extraído {extracted} está ABAIXO do valor ideal ({min_val}–{max_val}).\n"
            if suggestion:
                prescription_text += f"- {test}: {suggestion}\n"
        elif extracted > max_val:
            diagnostic_text += f"{test}: valor extraído {extracted} está ACIMA do valor ideal ({min_val}–{max_val}).\n"
            if suggestion:
                prescription_text += f"- {test}: {suggestion}\n"
        else:
            diagnostic_text += f"{test}: valor extraído {extracted} está dentro do valor ideal ({min_val}–{max_val}).\n"

    return diagnostic_text, prescription_text, name, gender, age, cpf, phone