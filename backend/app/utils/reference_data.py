"""Reference data for ICD-10 codes, medicines, and related autocomplete data."""

# Common ICD-10 codes organized by category
ICD10_CODES = [
    # Infectious diseases (A00-B99)
    {"code": "A09", "description": "Infectious gastroenteritis and colitis, unspecified", "category": "Infectious Diseases"},
    {"code": "A15.0", "description": "Tuberculosis of lung", "category": "Infectious Diseases"},
    {"code": "A16.0", "description": "Tuberculosis of lung, bacteriologically and histologically negative", "category": "Infectious Diseases"},
    {"code": "A37.0", "description": "Whooping cough due to Bordetella pertussis", "category": "Infectious Diseases"},
    {"code": "A38", "description": "Scarlet fever", "category": "Infectious Diseases"},
    {"code": "A41.9", "description": "Sepsis, unspecified organism", "category": "Infectious Diseases"},
    {"code": "B01.9", "description": "Varicella without complication", "category": "Infectious Diseases"},
    {"code": "B05.9", "description": "Measles without complication", "category": "Infectious Diseases"},
    {"code": "B15.9", "description": "Hepatitis A without hepatic coma", "category": "Infectious Diseases"},
    {"code": "B16.9", "description": "Acute hepatitis B without delta-agent and without hepatic coma", "category": "Infectious Diseases"},
    {"code": "B18.1", "description": "Chronic viral hepatitis B without delta-agent", "category": "Infectious Diseases"},
    {"code": "B20", "description": "Human immunodeficiency virus [HIV] disease", "category": "Infectious Diseases"},
    {"code": "B34.9", "description": "Viral infection, unspecified", "category": "Infectious Diseases"},
    {"code": "B35.1", "description": "Tinea unguium (nail fungus)", "category": "Infectious Diseases"},
    {"code": "B37.0", "description": "Candidal stomatitis (oral thrush)", "category": "Infectious Diseases"},

    # Neoplasms (C00-D49)
    {"code": "C18.9", "description": "Malignant neoplasm of colon, unspecified", "category": "Neoplasms"},
    {"code": "C34.9", "description": "Malignant neoplasm of unspecified part of bronchus or lung", "category": "Neoplasms"},
    {"code": "C50.9", "description": "Malignant neoplasm of breast, unspecified", "category": "Neoplasms"},
    {"code": "C61", "description": "Malignant neoplasm of prostate", "category": "Neoplasms"},
    {"code": "D50.9", "description": "Iron deficiency anaemia, unspecified", "category": "Blood Diseases"},

    # Endocrine (E00-E89)
    {"code": "E03.9", "description": "Hypothyroidism, unspecified", "category": "Endocrine"},
    {"code": "E05.9", "description": "Thyrotoxicosis, unspecified (Hyperthyroidism)", "category": "Endocrine"},
    {"code": "E10", "description": "Type 1 diabetes mellitus", "category": "Endocrine"},
    {"code": "E11", "description": "Type 2 diabetes mellitus", "category": "Endocrine"},
    {"code": "E11.65", "description": "Type 2 diabetes mellitus with hyperglycemia", "category": "Endocrine"},
    {"code": "E11.9", "description": "Type 2 diabetes mellitus without complications", "category": "Endocrine"},
    {"code": "E13", "description": "Other specified diabetes mellitus", "category": "Endocrine"},
    {"code": "E55.9", "description": "Vitamin D deficiency, unspecified", "category": "Endocrine"},
    {"code": "E66.0", "description": "Obesity due to excess calories", "category": "Endocrine"},
    {"code": "E66.9", "description": "Obesity, unspecified", "category": "Endocrine"},
    {"code": "E78.0", "description": "Pure hypercholesterolaemia", "category": "Endocrine"},
    {"code": "E78.5", "description": "Dyslipidaemia, unspecified", "category": "Endocrine"},

    # Mental disorders (F00-F99)
    {"code": "F10.2", "description": "Alcohol dependence syndrome", "category": "Mental Disorders"},
    {"code": "F20.9", "description": "Schizophrenia, unspecified", "category": "Mental Disorders"},
    {"code": "F31.9", "description": "Bipolar affective disorder, unspecified", "category": "Mental Disorders"},
    {"code": "F32.0", "description": "Mild depressive episode", "category": "Mental Disorders"},
    {"code": "F32.1", "description": "Moderate depressive episode", "category": "Mental Disorders"},
    {"code": "F32.2", "description": "Severe depressive episode without psychotic symptoms", "category": "Mental Disorders"},
    {"code": "F33.0", "description": "Recurrent depressive disorder, current episode mild", "category": "Mental Disorders"},
    {"code": "F41.0", "description": "Panic disorder [episodic paroxysmal anxiety]", "category": "Mental Disorders"},
    {"code": "F41.1", "description": "Generalized anxiety disorder", "category": "Mental Disorders"},
    {"code": "F41.9", "description": "Anxiety disorder, unspecified", "category": "Mental Disorders"},
    {"code": "F43.1", "description": "Post-traumatic stress disorder", "category": "Mental Disorders"},
    {"code": "F90.0", "description": "Attention deficit hyperactivity disorder (ADHD)", "category": "Mental Disorders"},

    # Nervous system (G00-G99)
    {"code": "G20", "description": "Parkinson disease", "category": "Nervous System"},
    {"code": "G30.9", "description": "Alzheimer disease, unspecified", "category": "Nervous System"},
    {"code": "G35", "description": "Multiple sclerosis", "category": "Nervous System"},
    {"code": "G40.9", "description": "Epilepsy, unspecified", "category": "Nervous System"},
    {"code": "G43.9", "description": "Migraine, unspecified", "category": "Nervous System"},
    {"code": "G47.0", "description": "Insomnia", "category": "Nervous System"},

    # Eye (H00-H59)
    {"code": "H10.9", "description": "Conjunctivitis, unspecified", "category": "Eye"},
    {"code": "H25.9", "description": "Senile cataract, unspecified", "category": "Eye"},
    {"code": "H40.1", "description": "Primary open-angle glaucoma", "category": "Eye"},

    # Ear (H60-H95)
    {"code": "H66.9", "description": "Otitis media, unspecified", "category": "Ear"},

    # Circulatory (I00-I99)
    {"code": "I10", "description": "Essential (primary) hypertension", "category": "Circulatory"},
    {"code": "I11.9", "description": "Hypertensive heart disease without heart failure", "category": "Circulatory"},
    {"code": "I20.9", "description": "Angina pectoris, unspecified", "category": "Circulatory"},
    {"code": "I21.9", "description": "Acute myocardial infarction, unspecified", "category": "Circulatory"},
    {"code": "I25.1", "description": "Atherosclerotic heart disease", "category": "Circulatory"},
    {"code": "I25.9", "description": "Chronic ischaemic heart disease, unspecified", "category": "Circulatory"},
    {"code": "I42.9", "description": "Cardiomyopathy, unspecified", "category": "Circulatory"},
    {"code": "I48.9", "description": "Atrial fibrillation, unspecified", "category": "Circulatory"},
    {"code": "I50.9", "description": "Heart failure, unspecified", "category": "Circulatory"},
    {"code": "I63.9", "description": "Cerebral infarction (stroke), unspecified", "category": "Circulatory"},
    {"code": "I64", "description": "Stroke, not specified as haemorrhage or infarction", "category": "Circulatory"},
    {"code": "I73.9", "description": "Peripheral vascular disease, unspecified", "category": "Circulatory"},

    # Respiratory (J00-J99)
    {"code": "J00", "description": "Acute nasopharyngitis [common cold]", "category": "Respiratory"},
    {"code": "J02.9", "description": "Acute pharyngitis, unspecified (sore throat)", "category": "Respiratory"},
    {"code": "J03.9", "description": "Acute tonsillitis, unspecified", "category": "Respiratory"},
    {"code": "J06.9", "description": "Acute upper respiratory infection, unspecified", "category": "Respiratory"},
    {"code": "J11.1", "description": "Influenza with other respiratory manifestations", "category": "Respiratory"},
    {"code": "J18.9", "description": "Pneumonia, unspecified organism", "category": "Respiratory"},
    {"code": "J20.9", "description": "Acute bronchitis, unspecified", "category": "Respiratory"},
    {"code": "J30.1", "description": "Allergic rhinitis due to pollen (hay fever)", "category": "Respiratory"},
    {"code": "J30.9", "description": "Allergic rhinitis, unspecified", "category": "Respiratory"},
    {"code": "J31.0", "description": "Chronic rhinitis", "category": "Respiratory"},
    {"code": "J32.9", "description": "Chronic sinusitis, unspecified", "category": "Respiratory"},
    {"code": "J35.0", "description": "Chronic tonsillitis", "category": "Respiratory"},
    {"code": "J40", "description": "Bronchitis, not specified as acute or chronic", "category": "Respiratory"},
    {"code": "J44.9", "description": "Chronic obstructive pulmonary disease (COPD), unspecified", "category": "Respiratory"},
    {"code": "J45.9", "description": "Asthma, unspecified", "category": "Respiratory"},

    # Digestive (K00-K95)
    {"code": "K02.9", "description": "Dental caries, unspecified", "category": "Digestive"},
    {"code": "K04.0", "description": "Pulpitis", "category": "Digestive"},
    {"code": "K05.1", "description": "Chronic gingivitis", "category": "Digestive"},
    {"code": "K21.0", "description": "Gastro-esophageal reflux disease (GERD) with esophagitis", "category": "Digestive"},
    {"code": "K25.9", "description": "Gastric ulcer, unspecified", "category": "Digestive"},
    {"code": "K29.7", "description": "Gastritis, unspecified", "category": "Digestive"},
    {"code": "K35.8", "description": "Acute appendicitis, other and unspecified", "category": "Digestive"},
    {"code": "K40.9", "description": "Inguinal hernia, unspecified", "category": "Digestive"},
    {"code": "K50.9", "description": "Crohn disease, unspecified", "category": "Digestive"},
    {"code": "K51.9", "description": "Ulcerative colitis, unspecified", "category": "Digestive"},
    {"code": "K57.9", "description": "Diverticular disease of intestine, unspecified", "category": "Digestive"},
    {"code": "K58.9", "description": "Irritable bowel syndrome without diarrhoea", "category": "Digestive"},
    {"code": "K70.3", "description": "Alcoholic cirrhosis of liver", "category": "Digestive"},
    {"code": "K76.0", "description": "Fatty liver, not elsewhere classified", "category": "Digestive"},
    {"code": "K80.2", "description": "Calculus of gallbladder without cholecystitis", "category": "Digestive"},

    # Skin (L00-L99)
    {"code": "L20.9", "description": "Atopic dermatitis, unspecified (eczema)", "category": "Skin"},
    {"code": "L23.9", "description": "Allergic contact dermatitis, unspecified cause", "category": "Skin"},
    {"code": "L30.9", "description": "Dermatitis, unspecified", "category": "Skin"},
    {"code": "L40.9", "description": "Psoriasis, unspecified", "category": "Skin"},
    {"code": "L50.9", "description": "Urticaria, unspecified", "category": "Skin"},
    {"code": "L70.0", "description": "Acne vulgaris", "category": "Skin"},

    # Musculoskeletal (M00-M99)
    {"code": "M06.9", "description": "Rheumatoid arthritis, unspecified", "category": "Musculoskeletal"},
    {"code": "M10.9", "description": "Gout, unspecified", "category": "Musculoskeletal"},
    {"code": "M15.9", "description": "Polyosteoarthritis, unspecified", "category": "Musculoskeletal"},
    {"code": "M17.9", "description": "Osteoarthritis of knee, unspecified", "category": "Musculoskeletal"},
    {"code": "M19.9", "description": "Osteoarthritis, unspecified site", "category": "Musculoskeletal"},
    {"code": "M25.5", "description": "Pain in joint", "category": "Musculoskeletal"},
    {"code": "M32.9", "description": "Systemic lupus erythematosus, unspecified", "category": "Musculoskeletal"},
    {"code": "M47.9", "description": "Spondylosis, unspecified", "category": "Musculoskeletal"},
    {"code": "M54.5", "description": "Low back pain", "category": "Musculoskeletal"},
    {"code": "M54.9", "description": "Dorsalgia, unspecified (back pain)", "category": "Musculoskeletal"},
    {"code": "M79.3", "description": "Panniculitis, unspecified", "category": "Musculoskeletal"},
    {"code": "M80.0", "description": "Postmenopausal osteoporosis with pathological fracture", "category": "Musculoskeletal"},
    {"code": "M81.0", "description": "Postmenopausal osteoporosis", "category": "Musculoskeletal"},

    # Genitourinary (N00-N99)
    {"code": "N10", "description": "Acute tubulo-interstitial nephritis (pyelonephritis)", "category": "Genitourinary"},
    {"code": "N18.9", "description": "Chronic kidney disease, unspecified", "category": "Genitourinary"},
    {"code": "N20.0", "description": "Calculus of kidney (kidney stones)", "category": "Genitourinary"},
    {"code": "N30.0", "description": "Acute cystitis", "category": "Genitourinary"},
    {"code": "N39.0", "description": "Urinary tract infection, site not specified", "category": "Genitourinary"},
    {"code": "N40", "description": "Benign prostatic hyperplasia", "category": "Genitourinary"},
    {"code": "N76.0", "description": "Acute vaginitis", "category": "Genitourinary"},

    # Pregnancy (O00-O9A)
    {"code": "O21.0", "description": "Mild hyperemesis gravidarum", "category": "Pregnancy"},
    {"code": "O24.4", "description": "Gestational diabetes mellitus", "category": "Pregnancy"},
    {"code": "O80", "description": "Single spontaneous delivery", "category": "Pregnancy"},

    # Injury (S00-T88)
    {"code": "S06.0", "description": "Concussion", "category": "Injury"},
    {"code": "S42.0", "description": "Fracture of clavicle", "category": "Injury"},
    {"code": "S52.5", "description": "Fracture of lower end of radius", "category": "Injury"},
    {"code": "S72.0", "description": "Fracture of neck of femur", "category": "Injury"},
    {"code": "S82.0", "description": "Fracture of patella", "category": "Injury"},
    {"code": "T78.4", "description": "Allergy, unspecified", "category": "Injury"},

    # Symptoms/Signs (R00-R99)
    {"code": "R05", "description": "Cough", "category": "Symptoms"},
    {"code": "R06.0", "description": "Dyspnoea (shortness of breath)", "category": "Symptoms"},
    {"code": "R07.9", "description": "Chest pain, unspecified", "category": "Symptoms"},
    {"code": "R10.4", "description": "Other and unspecified abdominal pain", "category": "Symptoms"},
    {"code": "R11", "description": "Nausea and vomiting", "category": "Symptoms"},
    {"code": "R42", "description": "Dizziness and giddiness", "category": "Symptoms"},
    {"code": "R50.9", "description": "Fever, unspecified", "category": "Symptoms"},
    {"code": "R51", "description": "Headache", "category": "Symptoms"},
    {"code": "R53.1", "description": "Weakness", "category": "Symptoms"},
    {"code": "R55", "description": "Syncope and collapse (fainting)", "category": "Symptoms"},
    {"code": "R63.4", "description": "Abnormal weight loss", "category": "Symptoms"},

    # Factors influencing health (Z00-Z99)
    {"code": "Z00.0", "description": "Encounter for general adult medical examination", "category": "Health Factors"},
    {"code": "Z01.0", "description": "Encounter for examination of eyes and vision", "category": "Health Factors"},
    {"code": "Z23", "description": "Encounter for immunization", "category": "Health Factors"},
    {"code": "Z76.0", "description": "Encounter for issue of repeat prescription", "category": "Health Factors"},
]


# Common medicines organized by therapeutic category
MEDICINES_DATABASE = [
    # Analgesics / Pain Relief
    {"name": "Paracetamol", "generic": "Acetaminophen", "category": "Analgesic", "common_dosages": ["500mg", "650mg", "1000mg"], "common_frequencies": ["Every 4-6 hours", "Every 6 hours", "Three times daily"], "form": "Tablet"},
    {"name": "Ibuprofen", "generic": "Ibuprofen", "category": "NSAID", "common_dosages": ["200mg", "400mg", "600mg"], "common_frequencies": ["Every 6-8 hours", "Three times daily"], "form": "Tablet"},
    {"name": "Diclofenac", "generic": "Diclofenac Sodium", "category": "NSAID", "common_dosages": ["25mg", "50mg", "75mg"], "common_frequencies": ["Twice daily", "Three times daily"], "form": "Tablet"},
    {"name": "Naproxen", "generic": "Naproxen Sodium", "category": "NSAID", "common_dosages": ["250mg", "500mg"], "common_frequencies": ["Twice daily"], "form": "Tablet"},
    {"name": "Aspirin", "generic": "Acetylsalicylic acid", "category": "NSAID/Antiplatelet", "common_dosages": ["75mg", "150mg", "300mg", "325mg"], "common_frequencies": ["Once daily", "Every 4-6 hours"], "form": "Tablet"},
    {"name": "Tramadol", "generic": "Tramadol Hydrochloride", "category": "Opioid Analgesic", "common_dosages": ["50mg", "100mg"], "common_frequencies": ["Every 4-6 hours", "Twice daily"], "form": "Capsule"},
    {"name": "Morphine", "generic": "Morphine Sulfate", "category": "Opioid Analgesic", "common_dosages": ["5mg", "10mg", "15mg", "30mg"], "common_frequencies": ["Every 4 hours", "Every 12 hours (SR)"], "form": "Tablet"},

    # Antibiotics
    {"name": "Amoxicillin", "generic": "Amoxicillin", "category": "Antibiotic (Penicillin)", "common_dosages": ["250mg", "500mg", "875mg"], "common_frequencies": ["Three times daily", "Twice daily"], "form": "Capsule"},
    {"name": "Augmentin", "generic": "Amoxicillin/Clavulanate", "category": "Antibiotic (Penicillin)", "common_dosages": ["375mg", "625mg", "1000mg"], "common_frequencies": ["Twice daily", "Three times daily"], "form": "Tablet"},
    {"name": "Azithromycin", "generic": "Azithromycin", "category": "Antibiotic (Macrolide)", "common_dosages": ["250mg", "500mg"], "common_frequencies": ["Once daily"], "form": "Tablet"},
    {"name": "Ciprofloxacin", "generic": "Ciprofloxacin", "category": "Antibiotic (Fluoroquinolone)", "common_dosages": ["250mg", "500mg", "750mg"], "common_frequencies": ["Twice daily"], "form": "Tablet"},
    {"name": "Levofloxacin", "generic": "Levofloxacin", "category": "Antibiotic (Fluoroquinolone)", "common_dosages": ["250mg", "500mg", "750mg"], "common_frequencies": ["Once daily"], "form": "Tablet"},
    {"name": "Cephalexin", "generic": "Cefalexin", "category": "Antibiotic (Cephalosporin)", "common_dosages": ["250mg", "500mg"], "common_frequencies": ["Four times daily", "Three times daily"], "form": "Capsule"},
    {"name": "Ceftriaxone", "generic": "Ceftriaxone", "category": "Antibiotic (Cephalosporin)", "common_dosages": ["250mg", "500mg", "1g", "2g"], "common_frequencies": ["Once daily", "Twice daily"], "form": "Injection"},
    {"name": "Doxycycline", "generic": "Doxycycline", "category": "Antibiotic (Tetracycline)", "common_dosages": ["100mg"], "common_frequencies": ["Twice daily", "Once daily"], "form": "Capsule"},
    {"name": "Metronidazole", "generic": "Metronidazole", "category": "Antibiotic/Antiprotozoal", "common_dosages": ["200mg", "400mg", "500mg"], "common_frequencies": ["Three times daily"], "form": "Tablet"},
    {"name": "Clindamycin", "generic": "Clindamycin", "category": "Antibiotic", "common_dosages": ["150mg", "300mg"], "common_frequencies": ["Four times daily", "Three times daily"], "form": "Capsule"},
    {"name": "Cotrimoxazole", "generic": "Sulfamethoxazole/Trimethoprim", "category": "Antibiotic", "common_dosages": ["480mg", "960mg"], "common_frequencies": ["Twice daily"], "form": "Tablet"},
    {"name": "Nitrofurantoin", "generic": "Nitrofurantoin", "category": "Antibiotic (Urinary)", "common_dosages": ["50mg", "100mg"], "common_frequencies": ["Four times daily", "Twice daily"], "form": "Capsule"},

    # Antifungals
    {"name": "Fluconazole", "generic": "Fluconazole", "category": "Antifungal", "common_dosages": ["50mg", "150mg", "200mg"], "common_frequencies": ["Once daily", "Once weekly"], "form": "Capsule"},
    {"name": "Clotrimazole", "generic": "Clotrimazole", "category": "Antifungal (Topical)", "common_dosages": ["1%"], "common_frequencies": ["Twice daily", "Three times daily"], "form": "Cream"},

    # Antivirals
    {"name": "Acyclovir", "generic": "Aciclovir", "category": "Antiviral", "common_dosages": ["200mg", "400mg", "800mg"], "common_frequencies": ["Five times daily", "Twice daily"], "form": "Tablet"},
    {"name": "Oseltamivir", "generic": "Oseltamivir", "category": "Antiviral", "common_dosages": ["75mg"], "common_frequencies": ["Twice daily"], "form": "Capsule"},

    # Cardiovascular
    {"name": "Amlodipine", "generic": "Amlodipine Besylate", "category": "Calcium Channel Blocker", "common_dosages": ["2.5mg", "5mg", "10mg"], "common_frequencies": ["Once daily"], "form": "Tablet"},
    {"name": "Atenolol", "generic": "Atenolol", "category": "Beta Blocker", "common_dosages": ["25mg", "50mg", "100mg"], "common_frequencies": ["Once daily"], "form": "Tablet"},
    {"name": "Metoprolol", "generic": "Metoprolol Tartrate", "category": "Beta Blocker", "common_dosages": ["25mg", "50mg", "100mg"], "common_frequencies": ["Twice daily", "Once daily"], "form": "Tablet"},
    {"name": "Propranolol", "generic": "Propranolol", "category": "Beta Blocker", "common_dosages": ["10mg", "20mg", "40mg", "80mg"], "common_frequencies": ["Twice daily", "Three times daily"], "form": "Tablet"},
    {"name": "Losartan", "generic": "Losartan Potassium", "category": "ARB", "common_dosages": ["25mg", "50mg", "100mg"], "common_frequencies": ["Once daily"], "form": "Tablet"},
    {"name": "Telmisartan", "generic": "Telmisartan", "category": "ARB", "common_dosages": ["20mg", "40mg", "80mg"], "common_frequencies": ["Once daily"], "form": "Tablet"},
    {"name": "Enalapril", "generic": "Enalapril Maleate", "category": "ACE Inhibitor", "common_dosages": ["2.5mg", "5mg", "10mg", "20mg"], "common_frequencies": ["Once daily", "Twice daily"], "form": "Tablet"},
    {"name": "Ramipril", "generic": "Ramipril", "category": "ACE Inhibitor", "common_dosages": ["1.25mg", "2.5mg", "5mg", "10mg"], "common_frequencies": ["Once daily"], "form": "Capsule"},
    {"name": "Hydrochlorothiazide", "generic": "Hydrochlorothiazide", "category": "Diuretic", "common_dosages": ["12.5mg", "25mg", "50mg"], "common_frequencies": ["Once daily"], "form": "Tablet"},
    {"name": "Furosemide", "generic": "Frusemide", "category": "Loop Diuretic", "common_dosages": ["20mg", "40mg", "80mg"], "common_frequencies": ["Once daily", "Twice daily"], "form": "Tablet"},
    {"name": "Spironolactone", "generic": "Spironolactone", "category": "Potassium-sparing Diuretic", "common_dosages": ["25mg", "50mg", "100mg"], "common_frequencies": ["Once daily", "Twice daily"], "form": "Tablet"},
    {"name": "Atorvastatin", "generic": "Atorvastatin Calcium", "category": "Statin", "common_dosages": ["10mg", "20mg", "40mg", "80mg"], "common_frequencies": ["Once daily (at night)"], "form": "Tablet"},
    {"name": "Rosuvastatin", "generic": "Rosuvastatin Calcium", "category": "Statin", "common_dosages": ["5mg", "10mg", "20mg", "40mg"], "common_frequencies": ["Once daily"], "form": "Tablet"},
    {"name": "Clopidogrel", "generic": "Clopidogrel Bisulfate", "category": "Antiplatelet", "common_dosages": ["75mg", "150mg", "300mg"], "common_frequencies": ["Once daily"], "form": "Tablet"},
    {"name": "Warfarin", "generic": "Warfarin Sodium", "category": "Anticoagulant", "common_dosages": ["1mg", "2mg", "5mg"], "common_frequencies": ["Once daily"], "form": "Tablet"},
    {"name": "Digoxin", "generic": "Digoxin", "category": "Cardiac Glycoside", "common_dosages": ["0.0625mg", "0.125mg", "0.25mg"], "common_frequencies": ["Once daily"], "form": "Tablet"},

    # Diabetes
    {"name": "Metformin", "generic": "Metformin Hydrochloride", "category": "Biguanide", "common_dosages": ["500mg", "850mg", "1000mg"], "common_frequencies": ["Twice daily", "Three times daily"], "form": "Tablet"},
    {"name": "Glimepiride", "generic": "Glimepiride", "category": "Sulfonylurea", "common_dosages": ["1mg", "2mg", "3mg", "4mg"], "common_frequencies": ["Once daily"], "form": "Tablet"},
    {"name": "Glipizide", "generic": "Glipizide", "category": "Sulfonylurea", "common_dosages": ["5mg", "10mg"], "common_frequencies": ["Once daily", "Twice daily"], "form": "Tablet"},
    {"name": "Sitagliptin", "generic": "Sitagliptin Phosphate", "category": "DPP-4 Inhibitor", "common_dosages": ["25mg", "50mg", "100mg"], "common_frequencies": ["Once daily"], "form": "Tablet"},
    {"name": "Insulin Glargine", "generic": "Insulin Glargine", "category": "Insulin (Long-acting)", "common_dosages": ["10 units", "20 units", "As prescribed"], "common_frequencies": ["Once daily (bedtime)"], "form": "Injection"},
    {"name": "Insulin Aspart", "generic": "Insulin Aspart", "category": "Insulin (Rapid-acting)", "common_dosages": ["As prescribed"], "common_frequencies": ["Before meals"], "form": "Injection"},

    # Respiratory
    {"name": "Salbutamol", "generic": "Albuterol", "category": "Bronchodilator (SABA)", "common_dosages": ["100mcg/puff", "2mg", "4mg"], "common_frequencies": ["As needed", "Four times daily"], "form": "Inhaler"},
    {"name": "Ipratropium", "generic": "Ipratropium Bromide", "category": "Bronchodilator (Anticholinergic)", "common_dosages": ["20mcg/puff", "500mcg/2ml"], "common_frequencies": ["Four times daily"], "form": "Inhaler"},
    {"name": "Budesonide", "generic": "Budesonide", "category": "Corticosteroid (Inhaled)", "common_dosages": ["100mcg", "200mcg", "400mcg"], "common_frequencies": ["Twice daily"], "form": "Inhaler"},
    {"name": "Fluticasone", "generic": "Fluticasone Propionate", "category": "Corticosteroid (Inhaled)", "common_dosages": ["50mcg", "125mcg", "250mcg"], "common_frequencies": ["Twice daily"], "form": "Inhaler"},
    {"name": "Montelukast", "generic": "Montelukast Sodium", "category": "Leukotriene Inhibitor", "common_dosages": ["4mg", "5mg", "10mg"], "common_frequencies": ["Once daily (evening)"], "form": "Tablet"},
    {"name": "Theophylline", "generic": "Theophylline", "category": "Methylxanthine", "common_dosages": ["100mg", "200mg", "300mg"], "common_frequencies": ["Twice daily"], "form": "Tablet"},

    # Gastrointestinal
    {"name": "Omeprazole", "generic": "Omeprazole", "category": "Proton Pump Inhibitor", "common_dosages": ["20mg", "40mg"], "common_frequencies": ["Once daily (before breakfast)", "Twice daily"], "form": "Capsule"},
    {"name": "Pantoprazole", "generic": "Pantoprazole Sodium", "category": "Proton Pump Inhibitor", "common_dosages": ["20mg", "40mg"], "common_frequencies": ["Once daily", "Twice daily"], "form": "Tablet"},
    {"name": "Ranitidine", "generic": "Ranitidine", "category": "H2 Blocker", "common_dosages": ["150mg", "300mg"], "common_frequencies": ["Twice daily", "Once daily (at night)"], "form": "Tablet"},
    {"name": "Domperidone", "generic": "Domperidone", "category": "Prokinetic/Antiemetic", "common_dosages": ["10mg"], "common_frequencies": ["Three times daily (before meals)"], "form": "Tablet"},
    {"name": "Ondansetron", "generic": "Ondansetron", "category": "Antiemetic", "common_dosages": ["4mg", "8mg"], "common_frequencies": ["Every 8 hours", "Twice daily"], "form": "Tablet"},
    {"name": "Loperamide", "generic": "Loperamide Hydrochloride", "category": "Antidiarrhoeal", "common_dosages": ["2mg"], "common_frequencies": ["After each loose stool (max 16mg/day)"], "form": "Capsule"},
    {"name": "ORS", "generic": "Oral Rehydration Salts", "category": "Rehydration", "common_dosages": ["1 sachet in 1L water"], "common_frequencies": ["After each loose motion"], "form": "Sachet"},
    {"name": "Lactulose", "generic": "Lactulose", "category": "Laxative", "common_dosages": ["10ml", "15ml", "30ml"], "common_frequencies": ["Once daily", "Twice daily"], "form": "Syrup"},
    {"name": "Sucralfate", "generic": "Sucralfate", "category": "Mucosal Protectant", "common_dosages": ["1g"], "common_frequencies": ["Four times daily (before meals and at bedtime)"], "form": "Tablet"},

    # Antihistamines / Allergy
    {"name": "Cetirizine", "generic": "Cetirizine Hydrochloride", "category": "Antihistamine (2nd gen)", "common_dosages": ["5mg", "10mg"], "common_frequencies": ["Once daily"], "form": "Tablet"},
    {"name": "Levocetirizine", "generic": "Levocetirizine", "category": "Antihistamine (2nd gen)", "common_dosages": ["5mg"], "common_frequencies": ["Once daily (at night)"], "form": "Tablet"},
    {"name": "Loratadine", "generic": "Loratadine", "category": "Antihistamine (2nd gen)", "common_dosages": ["10mg"], "common_frequencies": ["Once daily"], "form": "Tablet"},
    {"name": "Fexofenadine", "generic": "Fexofenadine Hydrochloride", "category": "Antihistamine (2nd gen)", "common_dosages": ["60mg", "120mg", "180mg"], "common_frequencies": ["Once daily", "Twice daily"], "form": "Tablet"},
    {"name": "Chlorpheniramine", "generic": "Chlorpheniramine Maleate", "category": "Antihistamine (1st gen)", "common_dosages": ["4mg"], "common_frequencies": ["Three times daily"], "form": "Tablet"},

    # Corticosteroids
    {"name": "Prednisolone", "generic": "Prednisolone", "category": "Corticosteroid", "common_dosages": ["5mg", "10mg", "20mg", "40mg"], "common_frequencies": ["Once daily (morning)", "Twice daily"], "form": "Tablet"},
    {"name": "Dexamethasone", "generic": "Dexamethasone", "category": "Corticosteroid", "common_dosages": ["0.5mg", "4mg", "8mg"], "common_frequencies": ["Once daily", "As directed"], "form": "Tablet"},
    {"name": "Hydrocortisone", "generic": "Hydrocortisone", "category": "Corticosteroid", "common_dosages": ["10mg", "20mg", "1% cream"], "common_frequencies": ["Two-three times daily"], "form": "Tablet/Cream"},
    {"name": "Betamethasone", "generic": "Betamethasone", "category": "Corticosteroid (Topical)", "common_dosages": ["0.025%", "0.05%", "0.1%"], "common_frequencies": ["Twice daily"], "form": "Cream"},

    # Psychiatric / CNS
    {"name": "Escitalopram", "generic": "Escitalopram Oxalate", "category": "SSRI Antidepressant", "common_dosages": ["5mg", "10mg", "20mg"], "common_frequencies": ["Once daily"], "form": "Tablet"},
    {"name": "Sertraline", "generic": "Sertraline Hydrochloride", "category": "SSRI Antidepressant", "common_dosages": ["25mg", "50mg", "100mg"], "common_frequencies": ["Once daily"], "form": "Tablet"},
    {"name": "Fluoxetine", "generic": "Fluoxetine Hydrochloride", "category": "SSRI Antidepressant", "common_dosages": ["10mg", "20mg", "40mg"], "common_frequencies": ["Once daily (morning)"], "form": "Capsule"},
    {"name": "Amitriptyline", "generic": "Amitriptyline", "category": "TCA Antidepressant", "common_dosages": ["10mg", "25mg", "50mg", "75mg"], "common_frequencies": ["Once daily (at night)"], "form": "Tablet"},
    {"name": "Alprazolam", "generic": "Alprazolam", "category": "Benzodiazepine", "common_dosages": ["0.25mg", "0.5mg", "1mg"], "common_frequencies": ["Twice daily", "Three times daily"], "form": "Tablet"},
    {"name": "Diazepam", "generic": "Diazepam", "category": "Benzodiazepine", "common_dosages": ["2mg", "5mg", "10mg"], "common_frequencies": ["Twice daily", "Three times daily"], "form": "Tablet"},
    {"name": "Clonazepam", "generic": "Clonazepam", "category": "Benzodiazepine", "common_dosages": ["0.25mg", "0.5mg", "1mg", "2mg"], "common_frequencies": ["Twice daily"], "form": "Tablet"},
    {"name": "Olanzapine", "generic": "Olanzapine", "category": "Atypical Antipsychotic", "common_dosages": ["2.5mg", "5mg", "10mg", "15mg"], "common_frequencies": ["Once daily"], "form": "Tablet"},
    {"name": "Risperidone", "generic": "Risperidone", "category": "Atypical Antipsychotic", "common_dosages": ["0.5mg", "1mg", "2mg", "3mg"], "common_frequencies": ["Once daily", "Twice daily"], "form": "Tablet"},
    {"name": "Lithium", "generic": "Lithium Carbonate", "category": "Mood Stabilizer", "common_dosages": ["300mg", "450mg"], "common_frequencies": ["Two-three times daily"], "form": "Tablet"},
    {"name": "Carbamazepine", "generic": "Carbamazepine", "category": "Anticonvulsant", "common_dosages": ["100mg", "200mg", "400mg"], "common_frequencies": ["Twice daily", "Three times daily"], "form": "Tablet"},
    {"name": "Valproic Acid", "generic": "Sodium Valproate", "category": "Anticonvulsant", "common_dosages": ["200mg", "300mg", "500mg"], "common_frequencies": ["Twice daily", "Three times daily"], "form": "Tablet"},
    {"name": "Levetiracetam", "generic": "Levetiracetam", "category": "Anticonvulsant", "common_dosages": ["250mg", "500mg", "750mg", "1000mg"], "common_frequencies": ["Twice daily"], "form": "Tablet"},
    {"name": "Zolpidem", "generic": "Zolpidem Tartrate", "category": "Sedative/Hypnotic", "common_dosages": ["5mg", "10mg"], "common_frequencies": ["Once daily (at bedtime)"], "form": "Tablet"},

    # Thyroid
    {"name": "Levothyroxine", "generic": "Levothyroxine Sodium", "category": "Thyroid Hormone", "common_dosages": ["25mcg", "50mcg", "75mcg", "100mcg", "125mcg"], "common_frequencies": ["Once daily (empty stomach, morning)"], "form": "Tablet"},
    {"name": "Carbimazole", "generic": "Carbimazole", "category": "Antithyroid", "common_dosages": ["5mg", "10mg", "20mg"], "common_frequencies": ["Once daily", "Two-three times daily"], "form": "Tablet"},

    # Vitamins / Supplements
    {"name": "Vitamin D3", "generic": "Cholecalciferol", "category": "Vitamin", "common_dosages": ["1000 IU", "2000 IU", "60000 IU"], "common_frequencies": ["Once daily", "Once weekly"], "form": "Tablet/Sachet"},
    {"name": "Calcium + Vitamin D", "generic": "Calcium Carbonate + Cholecalciferol", "category": "Supplement", "common_dosages": ["500mg + 250 IU", "600mg + 400 IU"], "common_frequencies": ["Once daily", "Twice daily"], "form": "Tablet"},
    {"name": "Iron + Folic Acid", "generic": "Ferrous Sulfate + Folic Acid", "category": "Supplement", "common_dosages": ["100mg + 0.5mg", "200mg + 0.4mg"], "common_frequencies": ["Once daily", "Twice daily"], "form": "Tablet"},
    {"name": "Vitamin B12", "generic": "Methylcobalamin", "category": "Vitamin", "common_dosages": ["500mcg", "1000mcg", "1500mcg"], "common_frequencies": ["Once daily"], "form": "Tablet"},
    {"name": "Multivitamin", "generic": "Multivitamin", "category": "Supplement", "common_dosages": ["1 tablet"], "common_frequencies": ["Once daily"], "form": "Tablet"},
    {"name": "Zinc", "generic": "Zinc Sulfate", "category": "Supplement", "common_dosages": ["20mg", "50mg"], "common_frequencies": ["Once daily"], "form": "Tablet"},
    {"name": "Folic Acid", "generic": "Folic Acid", "category": "Vitamin", "common_dosages": ["1mg", "5mg"], "common_frequencies": ["Once daily"], "form": "Tablet"},

    # Topical / Dermatological
    {"name": "Calamine Lotion", "generic": "Calamine", "category": "Antipruritc (Topical)", "common_dosages": ["Apply thin layer"], "common_frequencies": ["Two-three times daily"], "form": "Lotion"},
    {"name": "Mupirocin", "generic": "Mupirocin", "category": "Antibiotic (Topical)", "common_dosages": ["2%"], "common_frequencies": ["Three times daily"], "form": "Ointment"},
    {"name": "Silver Sulfadiazine", "generic": "Silver Sulfadiazine", "category": "Antibacterial (Topical)", "common_dosages": ["1%"], "common_frequencies": ["Once-twice daily"], "form": "Cream"},

    # Others
    {"name": "Methotrexate", "generic": "Methotrexate", "category": "DMARD/Antimetabolite", "common_dosages": ["2.5mg", "7.5mg", "10mg", "15mg"], "common_frequencies": ["Once weekly"], "form": "Tablet"},
    {"name": "Allopurinol", "generic": "Allopurinol", "category": "Xanthine Oxidase Inhibitor", "common_dosages": ["100mg", "300mg"], "common_frequencies": ["Once daily"], "form": "Tablet"},
    {"name": "Colchicine", "generic": "Colchicine", "category": "Anti-gout", "common_dosages": ["0.5mg", "1mg"], "common_frequencies": ["Twice daily", "Three times daily"], "form": "Tablet"},
    {"name": "Tamsulosin", "generic": "Tamsulosin Hydrochloride", "category": "Alpha Blocker", "common_dosages": ["0.4mg"], "common_frequencies": ["Once daily"], "form": "Capsule"},
    {"name": "Sildenafil", "generic": "Sildenafil Citrate", "category": "PDE5 Inhibitor", "common_dosages": ["25mg", "50mg", "100mg"], "common_frequencies": ["As needed"], "form": "Tablet"},
]


# Common dosage forms
DOSAGE_FORMS = [
    "Tablet", "Capsule", "Syrup", "Suspension", "Injection",
    "Inhaler", "Cream", "Ointment", "Gel", "Drops",
    "Patch", "Suppository", "Lotion", "Powder", "Sachet",
    "Spray", "Solution", "Nebulizer Solution",
]

# Common frequencies
FREQUENCIES = [
    "Once daily",
    "Twice daily",
    "Three times daily",
    "Four times daily",
    "Every 4 hours",
    "Every 6 hours",
    "Every 8 hours",
    "Every 12 hours",
    "Once weekly",
    "As needed (PRN)",
    "Before meals",
    "After meals",
    "At bedtime",
    "Before breakfast",
    "Before lunch",
    "Before dinner",
    "With food",
    "On empty stomach",
    "Morning and evening",
]

# Common durations
DURATIONS = [
    "3 days", "5 days", "7 days", "10 days", "14 days",
    "21 days", "1 month", "2 months", "3 months", "6 months",
    "1 year", "Ongoing", "As directed", "Until review",
]


def search_icd10(query: str, limit: int = 20) -> list:
    """Search ICD-10 codes by code or description."""
    if not query or len(query) < 1:
        return ICD10_CODES[:limit]
    
    query_lower = query.lower()
    results = []
    
    # Exact code match first
    for item in ICD10_CODES:
        if item["code"].lower() == query_lower:
            results.append(item)
    
    # Code starts with
    for item in ICD10_CODES:
        if item["code"].lower().startswith(query_lower) and item not in results:
            results.append(item)
    
    # Description contains
    for item in ICD10_CODES:
        if query_lower in item["description"].lower() and item not in results:
            results.append(item)
    
    # Category contains
    for item in ICD10_CODES:
        if query_lower in item["category"].lower() and item not in results:
            results.append(item)
    
    return results[:limit]


def search_medicines(query: str, limit: int = 20) -> list:
    """Search medicines by name, generic name, or category."""
    if not query or len(query) < 1:
        return MEDICINES_DATABASE[:limit]
    
    query_lower = query.lower()
    results = []
    
    # Name starts with
    for item in MEDICINES_DATABASE:
        if item["name"].lower().startswith(query_lower):
            results.append(item)
    
    # Generic starts with
    for item in MEDICINES_DATABASE:
        if item["generic"].lower().startswith(query_lower) and item not in results:
            results.append(item)
    
    # Name contains
    for item in MEDICINES_DATABASE:
        if query_lower in item["name"].lower() and item not in results:
            results.append(item)
    
    # Generic contains
    for item in MEDICINES_DATABASE:
        if query_lower in item["generic"].lower() and item not in results:
            results.append(item)
    
    # Category contains
    for item in MEDICINES_DATABASE:
        if query_lower in item["category"].lower() and item not in results:
            results.append(item)
    
    return results[:limit]
