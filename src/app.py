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

def detect_hallucination(structured_report, transcript):
    """Detect potential hallucination in the structured report"""
    
    # Check for suspiciously specific measurements that might be fabricated
    import re
    
    # Extract numbers from the structured report
    numbers_in_report = re.findall(r'\d+(?:\.\d+)?', structured_report)
    
    # Extract numbers from the original transcript
    numbers_in_transcript = re.findall(r'\d+(?:\.\d+)?', transcript)
    
    # Count how many numbers in report are NOT in transcript
    fabricated_numbers = 0
    for num in numbers_in_report:
        if num not in numbers_in_transcript:
            fabricated_numbers += 1
    
    # If more than 50% of numbers are fabricated, likely hallucination
    if len(numbers_in_report) > 0:
        fabrication_ratio = fabricated_numbers / len(numbers_in_report)
        if fabrication_ratio > 0.5:
            return True, f"Mogelijk hallucinatie gedetecteerd: {fabricated_numbers}/{len(numbers_in_report)} cijfers niet in origineel dictaat"
    
    # Check for suspiciously complete data (all fields filled with specific values)
    if "niet vermeld" not in structured_report and len(numbers_in_report) > 15:
        return True, "Mogelijk hallucinatie: verdacht complete data zonder 'niet vermeld' velden"
    
    return False, None

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

KRITIEKE VEILIGHEIDSREGEL: VERZIN GEEN MEDISCHE GEGEVENS!

Uw taak: Analyseer het dictaat en vul het TTE-template in met ALLEEN de WERKELIJK GENOEMDE BEVINDINGEN.

TEMPLATE STRUCTUUR REGELS:
- BEHOUD ALLE TEMPLATE LIJNEN - laat geen enkele regel weg
- Voor elke lijn: vul alleen in wat expliciet genoemd is
- Voor niet-genoemde parameters: laat die specifieke parameter weg (schrijf NIET "niet vermeld")
- Gebruik logische medische beschrijvingen voor algemene bevindingen

ANTI-HALLUCINATIE REGELS:
- ALLEEN gegevens gebruiken die EXPLICIET in het dictaat staan
- GEEN cijfers verzinnen die niet letterlijk genoemd zijn
- GEEN medische details toevoegen die niet gedicteerd zijn
- VEILIGHEID EERST: beter incomplete data dan verzonnen data

VOORBEELDEN VAN CORRECTE INVULLING:

Als EDD niet genoemd:
- Linker ventrikel: eutroof. Globale functie: goed met LVEF 65% geschat

Als alleen prolaps genoemd:
- Mitralisklep: morfologisch prolaps. insufficiëntie: gering

Als geen specifieke dimensies genoemd:
- Aortadimensies: normaal

VOLLEDIGE TEMPLATE STRUCTUUR (BEHOUD ALLE LIJNEN):

TTE op {today}:
- Linker ventrikel: [vul in wat genoemd is, laat specifieke parameters weg als niet genoemd]
- Regionaal: [vul in wat genoemd is]
- Rechter ventrikel: [vul in wat genoemd is, laat specifieke parameters weg als niet genoemd]
- Diastole: [vul in wat genoemd is, laat specifieke parameters weg als niet genoemd]
- Atria: [vul in wat genoemd is, laat specifieke parameters weg als niet genoemd]
- Aortadimensies: [vul in wat genoemd is, laat specifieke parameters weg als niet genoemd]
- Mitralisklep: [vul in wat genoemd is, laat specifieke parameters weg als niet genoemd]
- Aortaklep: [vul in wat genoemd is, laat specifieke parameters weg als niet genoemd]
- Pulmonalisklep: [vul in wat genoemd is, laat specifieke parameters weg als niet genoemd]
- Tricuspiedklep: [vul in wat genoemd is, laat specifieke parameters weg als niet genoemd]
- Pericard: [vul in wat genoemd is]

Recente biochemie op {today}:
- Hb [alleen als genoemd]
- Creatinine [alleen als genoemd] en eGFR [alleen als genoemd]
- LDL [alleen als genoemd]
- HbA1c [alleen als genoemd]

Conclusie: [ALLEEN gebaseerd op werkelijk genoemde bevindingen]

Beleid:
- Medicatie: [ALLEEN als genoemd]
- Bijkomende investigaties: [ALLEEN als genoemd]
- Controle: [ALLEEN als genoemd]

VEILIGHEIDSCHECK: Controleer of elk cijfer en elke bevinding ECHT in het dictaat staat!
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

        # Check for hallucination
        is_hallucination, hallucination_msg = detect_hallucination(structured, corrected_transcript)
        
        if is_hallucination:
            # If hallucination detected, show warning and original transcript
            error_msg = f"🚨 Mogelijk hallucinatie gedetecteerd!\n\n{hallucination_msg}\n\nHet systeem heeft mogelijk medische gegevens verzonnen die niet in het originele dictaat stonden. Controleer het originele dictaat hieronder en probeer opnieuw met een duidelijker opname.\n\nOrigineel dictaat:\n{corrected_transcript}"
            return render_template('index.html', 
                                 error=error_msg,
                                 verslag_type=verslag_type)

        return render_template('index.html', 
                             transcript=corrected_transcript,
                             structured=structured,
                             verslag_type=verslag_type)

    except Exception as e:
        return render_template('index.html', error=f"Er is een fout opgetreden: {str(e)}")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

