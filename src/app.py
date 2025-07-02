import io
import os
import datetime
import openai
from flask import Flask, request, render_template, redirect, url_for
from openai import OpenAI

app = Flask(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def call_gpt(messages, model="gpt-4o", temperature=0.0):
    """Call GPT with error handling"""
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/transcribe', methods=['POST'])
def transcribe():
    try:
        # Get form data
        verslag_type = request.form.get('verslag_type', 'TTE')
        
        # Handle file upload
        if 'audio_file' in request.files:
            audio_file = request.files['audio_file']
            if audio_file.filename != '':
                # Process audio file with Whisper
                if verslag_type == 'Anamnese':
                    prompt = "Dit is een conversatie tussen een arts en een patiënt in het West-Vlaams dialect. Transcribeer de volledige conversatie."
                else:
                    prompt = "Dit is een medische dictatie in het Nederlands van een cardioloog. Transcribeer de volledige dictatie."
                
                try:
                    # Convert FileStorage to the format expected by OpenAI
                    audio_file.seek(0)  # Reset file pointer to beginning
                    transcript = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=(audio_file.filename, audio_file.read(), audio_file.content_type),
                        prompt=prompt,
                        temperature=0.0
                    )
                    corrected_transcript = transcript.text
                except Exception as e:
                    return render_template('index.html', error=f"Transcriptie fout: {str(e)}")
            else:
                return render_template('index.html', error="⚠️ Geen bestand geselecteerd.")
        else:
            return render_template('index.html', error="⚠️ Geen bestand geselecteerd.")

        # Get today's date
        today = datetime.datetime.now().strftime("%d-%m-%Y")
        
        # Generate report based on type
        if verslag_type == 'TTE':
            template_instruction = f"""
BELANGRIJK: U krijgt een intuïtief dictaat van een cardioloog. Dit betekent dat de informatie:
- Niet in de juiste volgorde staat
- In informele bewoordingen kan zijn
- Correcties kan bevatten
- Heen en weer kan springen tussen onderwerpen

Uw taak: Organiseer dit intuïtieve dictaat in het EXACTE TTE-format hieronder.

KRITIEK: 
- Volg het template EXACT - GEEN vrije tekst, GEEN genummerde lijsten, GEEN narratieve beschrijving
- Gebruik ALLEEN de exacte template structuur hieronder
- GEEN extra tekst voor of na het template
- GEEN "Verslag:" header - begin direct met "TTE op {today}:"
- GEEN procesdetails of uitleg - ALLEEN het template

REGELS:
- Volg het template format EXACT regeltje per regeltje
- Vul alle velden in - laat GEEN lijnen weg van de template
- Bij specifieke metingen: gebruik exacte cijfers zoals gedicteerd
- Bij ontbrekende metingen: laat (...) staan of gebruik beschrijvende termen uit template
- GEEN vrije tekst - ALLEEN de exacte template structuur
- GEEN genummerde lijsten - ALLEEN template format
- Behoud alle cijfers en metingen exact zoals gedicteerd
- Interpreteer informele taal naar correcte medische terminologie

BEGIN DIRECT MET:

TTE op {today}:
- Linker ventrikel: (...)troof met EDD (...) mm, IVS (...) mm, PW (...) mm. Globale functie: (goed/licht gedaald/matig gedaald/ernstig gedaald) met LVEF (...)% (geschat/monoplane/biplane)
- Regionaal: (geen kinetiekstoornissen/zone van hypokinesie/zone van akinesie)
- Rechter ventrikel: (...)troof, globale functie: (...) met TAPSE (...) mm en RV S' (...) cm/s
- Diastole: (normaal/vertraagde relaxatie/dysfunctie graad 2/dysfunctie graad 3) met E (...) cm/s, A (...) cm/s, E DT (...) ms, E' septaal (...) cm/s, E/E' (…). L-golf: (ja/neen)
- Atria: LA (normaal/licht gedilateerd/sterk gedilateerd) (...) mm, (…) mL, RA (…) mL
- Aortadimensies: sinus (…) mm, sinotubulair (…) mm, ascendens (…) mm
- Mitralisklep: morfologisch (normaal/sclerotisch/verdikt/prolaps/restrictief). insufficiëntie: (…) ; stenose: geen
- Aortaklep: (tricuspied/bicuspied), morfologisch (normaal/sclerotisch/mild verkalkt/matig verkalkt/ernstig verkalkt). Functioneel: geen tekort
- Pulmonalisklep: insufficiëntie: (…) ; stenose: geen
- Tricuspiedklep: insufficiëntie: (…) ; geschatte RVSP: (…) mmHg of niet opmeetbaar + CVD (…) mmHg gezien vena cava inferior: (…) mm, variabiliteit: (…) 
- Pericard: (…)  

Recente biochemie op {today}:
- Hb (…) g/dL
- Creatinine (…) mg/dL en eGFR (…) mL/min
- LDL (…) mg/dL
- HbA1c (…)%

Conclusie:

Beleid:
- Medicatie ongewijzigd/gewijzigd: …
- Bijkomende investigaties: …
- Controle over … maand
"""
        else:
            # Default template for other types
            template_instruction = f"""
Maak een medisch verslag van het volgende dictaat:

{corrected_transcript}

Gebruik professionele medische terminologie en structuur.
"""

        # Generate structured report
        structured = call_gpt([
            {"role": "system", "content": template_instruction},
            {"role": "user", "content": corrected_transcript}
        ])
        
        # Clean the output to ensure only the template format is returned
        if "Verslag:" in structured:
            structured = structured.split("Verslag:")[-1].strip()
        
        # Remove any processing details that might appear before the template
        lines = structured.split('\n')
        template_start = -1
        for i, line in enumerate(lines):
            if line.strip().startswith('TTE op') or line.strip().startswith('TEE op') or line.strip().startswith('Spoedconsult'):
                template_start = i
                break
        
        if template_start >= 0:
            structured = '\n'.join(lines[template_start:])

        return render_template('index.html', 
                             transcript=corrected_transcript,
                             structured=structured,
                             verslag_type=verslag_type)

    except Exception as e:
        return render_template('index.html', error=f"Er is een fout opgetreden: {str(e)}")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

