# 👨‍⚕️ User Guide

## Overview

The Enhanced Medical Dictation App transforms audio recordings into structured medical reports using advanced AI analysis. The app features a revolutionary two-part raadpleging flow that separates intelligent history collection from clinical examination documentation.

## 🚀 Getting Started

### Accessing the Application
1. Open your web browser
2. Navigate to your deployed application URL
3. You'll see the main interface with recording and upload options

### Basic Workflow
1. **Select report type** from the dropdown menu
2. **Choose specific options** (for raadpleging: history vs examination)
3. **Record audio or upload file**
4. **Review the generated report**
5. **Copy to clipboard** for use in your medical records

## 🔍 Enhanced Raadpleging Flow

### Part 1: Smart History Collection (Anamnese)

**When to use**: For doctor-patient conversations where you want intelligent extraction of medical history.

**How it works**:
1. Select "Raadpleging (Enhanced)" from dropdown
2. Choose "📝 Anamnese (Intelligente gesprekanalyse)"
3. Record or upload the doctor-patient conversation
4. The system will analyze and extract:
   - Reason for encounter (concise summary)
   - Chief complaints with full details
   - Relevant medical history
   - Red flags requiring attention
   - Information gaps that need follow-up

**Example Input**: 
> "Dokter: Goedemorgen, waarmee kan ik u helpen?  
> Patiënt: Ik heb sinds gisteren pijn op de borst. Het voelt drukkend aan en wordt erger bij inspanning..."

**Example Output**:
```
Reden van komst: pijn op borst

Hoofdklachten:
1. pijn op de borst
   - Onset: sinds gisteren
   - Karakter: drukkend
   - Verergering: bij inspanning
   - Bron: "Ik heb sinds gisteren pijn op de borst..."

⚠️ Aandachtspunten:
- Patiënt meldt: pijn wordt erger bij inspanning
```

### Part 2: Clinical Examination (Onderzoek)

**When to use**: For dictating technical investigation results (ECG, echo, exercise tests, etc.).

**How it works**:
1. Select "Raadpleging (Enhanced)" from dropdown
2. Choose "🔬 Onderzoek (Gestructureerde dictatie)"
3. Dictate your examination findings naturally
4. The system will:
   - Auto-detect investigation type
   - Fill structured templates
   - Maintain fixed order
   - Mark missing information as "[niet vermeld]"

**Example Input**:
> "ECG toont sinusritme met frequentie van 75 per minuut. PR interval is 160 ms. QRS is smal."

**Example Output**:
```
ECG op 01-07-2025:
- Ritme: sinusritme met ventriculair antwoord aan 75/min
- PR: normaal 160 ms
- QRS: [niet vermeld] as, smal
- Repolarisatie: [niet vermeld]
- QTc: [niet vermeld]
```

## 📋 Investigation Types

### ECG Analysis
**Use for**: Electrocardiogram findings
**Template includes**: Rhythm, rate, PR interval, QRS morphology, repolarization, QTc

### Exercise Testing (Fietsproef)
**Use for**: Stress test results
**Template includes**: Maximum watts, heart rate response, blood pressure, symptoms, ECG changes

### Echocardiography (TTE/TEE)
**Use for**: Ultrasound heart examinations
**Template includes**: Ventricular function, valve assessment, chamber dimensions, diastolic function

### Device Interrogation
**Use for**: Pacemaker/ICD check results
**Template includes**: Battery status, lead parameters, pacing percentages, arrhythmia episodes

### Holter Monitoring
**Use for**: 24-48 hour rhythm monitoring
**Template includes**: Heart rate statistics, arrhythmia burden, symptom correlation

## 🎤 Recording Tips

### Audio Quality
- **Use a quiet environment** to minimize background noise
- **Speak clearly** and at a normal pace
- **Hold device close** to your mouth (15-20cm)
- **Avoid interruptions** during recording

### Content Guidelines
- **Be specific** with measurements and findings
- **Use standard medical terminology**
- **Include units** (mm, mmHg, %, etc.)
- **State when findings are normal** rather than omitting them

### For History Collection
- **Include both doctor and patient voices**
- **Let conversations flow naturally**
- **Don't worry about perfect grammar** - the system will correct it
- **Include relevant context** and patient responses

### For Clinical Examinations
- **Dictate findings systematically**
- **Include all measured values**
- **State normal findings explicitly**
- **Use consistent terminology**

## 🛡️ Safety Features

### No Data Fabrication
- **NEVER makes up measurements** or findings
- **Only extracts explicitly mentioned information**
- **Clearly marks missing data** as "[niet vermeld]"
- **Provides source validation** for all extractions

### Quality Indicators
- **Confidence scores** show reliability of extractions
- **Missing field alerts** highlight incomplete information
- **Source text references** allow verification
- **Range validation** flags unusual measurements

## 📊 Understanding Output

### Confidence Information
- **High confidence (>0.8)**: Information clearly stated with context
- **Medium confidence (0.5-0.8)**: Information mentioned but may need verification
- **Low confidence (<0.5)**: Information unclear or ambiguous

### Missing Fields
- **"[niet vermeld]"**: Information not mentioned in the recording
- **Empty sections**: Entire categories not discussed
- **Incomplete sentences**: Removed when measurements missing

### Red Flags
- **Concerning symptoms**: Acute, severe, or emergency presentations
- **Inconsistencies**: Conflicting information in the recording
- **Critical gaps**: Missing essential information for diagnosis

## 🔧 Advanced Features

### API Access
Use the REST API for integration with other systems:

```bash
# History analysis
curl -X POST /api/analyze_history \
  -H "Content-Type: application/json" \
  -d '{"transcript": "conversation text"}'

# Examination analysis
curl -X POST /api/analyze_examination \
  -H "Content-Type: application/json" \
  -d '{"transcript": "examination findings", "investigation_type": "ECG"}'
```

### Batch Processing
For multiple recordings:
1. Process each recording individually
2. Use consistent investigation types
3. Review and validate all outputs
4. Combine results as needed

## 🚨 Troubleshooting

### Common Issues

#### Poor Transcription Quality
- **Check audio quality**: Ensure clear recording without background noise
- **Speak clearly**: Avoid mumbling or speaking too quickly
- **Use medical terminology**: Standard terms are better recognized

#### Missing Information
- **Be explicit**: State findings clearly rather than implying them
- **Include units**: Always specify measurements with units
- **Repeat important findings**: Mention critical information multiple times

#### Wrong Investigation Type
- **Use specific keywords**: Mention "ECG", "echo", "exercise test" explicitly
- **Manual selection**: Choose investigation type manually if auto-detection fails
- **Check output**: Verify the detected type matches your intention

#### Template Formatting Issues
- **Review missing fields**: Check which required information wasn't provided
- **Re-record if needed**: Add missing critical information
- **Manual editing**: Copy output and edit manually if necessary

### Getting Help
1. **Check the FAQ** in this guide
2. **Review example recordings** for best practices
3. **Contact support** for technical issues
4. **Report bugs** via GitHub issues

## 📈 Best Practices

### Workflow Integration
1. **Plan your dictation**: Know what information you need to include
2. **Use consistent terminology**: Stick to standard medical language
3. **Review before finalizing**: Always check the generated report
4. **Keep recordings organized**: Use descriptive filenames
5. **Backup important data**: Save critical reports separately

### Quality Assurance
- **Double-check measurements**: Verify all numerical values
- **Review clinical logic**: Ensure findings make medical sense
- **Validate against source**: Compare output with original recording
- **Get second opinions**: Have colleagues review complex cases

### Efficiency Tips
- **Use templates consistently**: Stick to the same format for similar cases
- **Batch similar recordings**: Process multiple ECGs or echos together
- **Learn keyboard shortcuts**: Use Ctrl+C to copy reports quickly
- **Customize workflows**: Adapt the process to your practice needs

---

**Questions?** Check the [Installation Guide](INSTALLATION.md) or [API Reference](API_REFERENCE.md) for more technical details.

