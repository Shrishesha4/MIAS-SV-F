"""add admin managed icd code catalog

Revision ID: 20260415_0021
Revises: 20260415_0020
Create Date: 2026-04-15 12:00:00.000000

"""
from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from alembic import op
import sqlalchemy as sa


revision = '20260415_0021'
down_revision = '20260415_0020'
branch_labels = None
depends_on = None


ICD_SEED_ROWS = [
    ("A09", "Infectious gastroenteritis and colitis, unspecified", "Infectious Diseases"),
    ("A15.0", "Tuberculosis of lung", "Infectious Diseases"),
    ("A16.0", "Tuberculosis of lung, bacteriologically and histologically negative", "Infectious Diseases"),
    ("A37.0", "Whooping cough due to Bordetella pertussis", "Infectious Diseases"),
    ("A38", "Scarlet fever", "Infectious Diseases"),
    ("A41.9", "Sepsis, unspecified organism", "Infectious Diseases"),
    ("B01.9", "Varicella without complication", "Infectious Diseases"),
    ("B05.9", "Measles without complication", "Infectious Diseases"),
    ("B15.9", "Hepatitis A without hepatic coma", "Infectious Diseases"),
    ("B16.9", "Acute hepatitis B without delta-agent and without hepatic coma", "Infectious Diseases"),
    ("B18.1", "Chronic viral hepatitis B without delta-agent", "Infectious Diseases"),
    ("B20", "Human immunodeficiency virus [HIV] disease", "Infectious Diseases"),
    ("B34.9", "Viral infection, unspecified", "Infectious Diseases"),
    ("B35.1", "Tinea unguium (nail fungus)", "Infectious Diseases"),
    ("B37.0", "Candidal stomatitis (oral thrush)", "Infectious Diseases"),
    ("C18.9", "Malignant neoplasm of colon, unspecified", "Neoplasms"),
    ("C34.9", "Malignant neoplasm of unspecified part of bronchus or lung", "Neoplasms"),
    ("C50.9", "Malignant neoplasm of breast, unspecified", "Neoplasms"),
    ("C61", "Malignant neoplasm of prostate", "Neoplasms"),
    ("D50.9", "Iron deficiency anaemia, unspecified", "Blood Diseases"),
    ("E03.9", "Hypothyroidism, unspecified", "Endocrine"),
    ("E05.9", "Thyrotoxicosis, unspecified (Hyperthyroidism)", "Endocrine"),
    ("E10", "Type 1 diabetes mellitus", "Endocrine"),
    ("E11", "Type 2 diabetes mellitus", "Endocrine"),
    ("E11.65", "Type 2 diabetes mellitus with hyperglycemia", "Endocrine"),
    ("E11.9", "Type 2 diabetes mellitus without complications", "Endocrine"),
    ("E13", "Other specified diabetes mellitus", "Endocrine"),
    ("E55.9", "Vitamin D deficiency, unspecified", "Endocrine"),
    ("E66.0", "Obesity due to excess calories", "Endocrine"),
    ("E66.9", "Obesity, unspecified", "Endocrine"),
    ("E78.0", "Pure hypercholesterolaemia", "Endocrine"),
    ("E78.5", "Dyslipidaemia, unspecified", "Endocrine"),
    ("F10.2", "Alcohol dependence syndrome", "Mental Disorders"),
    ("F20.9", "Schizophrenia, unspecified", "Mental Disorders"),
    ("F31.9", "Bipolar affective disorder, unspecified", "Mental Disorders"),
    ("F32.0", "Mild depressive episode", "Mental Disorders"),
    ("F32.1", "Moderate depressive episode", "Mental Disorders"),
    ("F32.2", "Severe depressive episode without psychotic symptoms", "Mental Disorders"),
    ("F33.0", "Recurrent depressive disorder, current episode mild", "Mental Disorders"),
    ("F41.0", "Panic disorder [episodic paroxysmal anxiety]", "Mental Disorders"),
    ("F41.1", "Generalized anxiety disorder", "Mental Disorders"),
    ("F41.9", "Anxiety disorder, unspecified", "Mental Disorders"),
    ("F43.1", "Post-traumatic stress disorder", "Mental Disorders"),
    ("F90.0", "Attention deficit hyperactivity disorder (ADHD)", "Mental Disorders"),
    ("G20", "Parkinson disease", "Nervous System"),
    ("G30.9", "Alzheimer disease, unspecified", "Nervous System"),
    ("G35", "Multiple sclerosis", "Nervous System"),
    ("G40.9", "Epilepsy, unspecified", "Nervous System"),
    ("G43.9", "Migraine, unspecified", "Nervous System"),
    ("G47.0", "Insomnia", "Nervous System"),
    ("H10.9", "Conjunctivitis, unspecified", "Eye"),
    ("H25.9", "Senile cataract, unspecified", "Eye"),
    ("H40.1", "Primary open-angle glaucoma", "Eye"),
    ("H66.9", "Otitis media, unspecified", "Ear"),
    ("I10", "Essential (primary) hypertension", "Circulatory"),
    ("I11.9", "Hypertensive heart disease without heart failure", "Circulatory"),
    ("I20.9", "Angina pectoris, unspecified", "Circulatory"),
    ("I21.9", "Acute myocardial infarction, unspecified", "Circulatory"),
    ("I25.1", "Atherosclerotic heart disease", "Circulatory"),
    ("I25.9", "Chronic ischaemic heart disease, unspecified", "Circulatory"),
    ("I42.9", "Cardiomyopathy, unspecified", "Circulatory"),
    ("I48.9", "Atrial fibrillation, unspecified", "Circulatory"),
    ("I50.9", "Heart failure, unspecified", "Circulatory"),
    ("I63.9", "Cerebral infarction (stroke), unspecified", "Circulatory"),
    ("I64", "Stroke, not specified as haemorrhage or infarction", "Circulatory"),
    ("I73.9", "Peripheral vascular disease, unspecified", "Circulatory"),
    ("J00", "Acute nasopharyngitis [common cold]", "Respiratory"),
    ("J02.9", "Acute pharyngitis, unspecified (sore throat)", "Respiratory"),
    ("J03.9", "Acute tonsillitis, unspecified", "Respiratory"),
    ("J06.9", "Acute upper respiratory infection, unspecified", "Respiratory"),
    ("J11.1", "Influenza with other respiratory manifestations", "Respiratory"),
    ("J18.9", "Pneumonia, unspecified organism", "Respiratory"),
    ("J20.9", "Acute bronchitis, unspecified", "Respiratory"),
    ("J30.1", "Allergic rhinitis due to pollen (hay fever)", "Respiratory"),
    ("J30.9", "Allergic rhinitis, unspecified", "Respiratory"),
    ("J31.0", "Chronic rhinitis", "Respiratory"),
    ("J32.9", "Chronic sinusitis, unspecified", "Respiratory"),
    ("J35.0", "Chronic tonsillitis", "Respiratory"),
    ("J40", "Bronchitis, not specified as acute or chronic", "Respiratory"),
    ("J44.9", "Chronic obstructive pulmonary disease (COPD), unspecified", "Respiratory"),
    ("J45.9", "Asthma, unspecified", "Respiratory"),
    ("K02.9", "Dental caries, unspecified", "Digestive"),
    ("K04.0", "Pulpitis", "Digestive"),
    ("K05.1", "Chronic gingivitis", "Digestive"),
    ("K21.0", "Gastro-esophageal reflux disease (GERD) with esophagitis", "Digestive"),
    ("K25.9", "Gastric ulcer, unspecified", "Digestive"),
    ("K29.7", "Gastritis, unspecified", "Digestive"),
    ("K35.8", "Acute appendicitis, other and unspecified", "Digestive"),
    ("K40.9", "Inguinal hernia, unspecified", "Digestive"),
    ("K50.9", "Crohn disease, unspecified", "Digestive"),
    ("K51.9", "Ulcerative colitis, unspecified", "Digestive"),
    ("K57.9", "Diverticular disease of intestine, unspecified", "Digestive"),
    ("K58.9", "Irritable bowel syndrome without diarrhoea", "Digestive"),
    ("K70.3", "Alcoholic cirrhosis of liver", "Digestive"),
    ("K76.0", "Fatty liver, not elsewhere classified", "Digestive"),
    ("K80.2", "Calculus of gallbladder without cholecystitis", "Digestive"),
    ("L20.9", "Atopic dermatitis, unspecified (eczema)", "Skin"),
    ("L23.9", "Allergic contact dermatitis, unspecified cause", "Skin"),
    ("L30.9", "Dermatitis, unspecified", "Skin"),
    ("L40.9", "Psoriasis, unspecified", "Skin"),
    ("L50.9", "Urticaria, unspecified", "Skin"),
    ("L70.0", "Acne vulgaris", "Skin"),
    ("M06.9", "Rheumatoid arthritis, unspecified", "Musculoskeletal"),
    ("M10.9", "Gout, unspecified", "Musculoskeletal"),
    ("M15.9", "Polyosteoarthritis, unspecified", "Musculoskeletal"),
    ("M17.9", "Osteoarthritis of knee, unspecified", "Musculoskeletal"),
    ("M19.9", "Osteoarthritis, unspecified site", "Musculoskeletal"),
    ("M25.5", "Pain in joint", "Musculoskeletal"),
    ("M32.9", "Systemic lupus erythematosus, unspecified", "Musculoskeletal"),
    ("M47.9", "Spondylosis, unspecified", "Musculoskeletal"),
    ("M54.5", "Low back pain", "Musculoskeletal"),
    ("M54.9", "Dorsalgia, unspecified (back pain)", "Musculoskeletal"),
    ("M79.3", "Panniculitis, unspecified", "Musculoskeletal"),
    ("M80.0", "Postmenopausal osteoporosis with pathological fracture", "Musculoskeletal"),
    ("M81.0", "Postmenopausal osteoporosis", "Musculoskeletal"),
    ("N10", "Acute tubulo-interstitial nephritis (pyelonephritis)", "Genitourinary"),
    ("N18.9", "Chronic kidney disease, unspecified", "Genitourinary"),
    ("N20.0", "Calculus of kidney (kidney stones)", "Genitourinary"),
    ("N30.0", "Acute cystitis", "Genitourinary"),
    ("N39.0", "Urinary tract infection, site not specified", "Genitourinary"),
    ("N40", "Benign prostatic hyperplasia", "Genitourinary"),
    ("N76.0", "Acute vaginitis", "Genitourinary"),
    ("O21.0", "Mild hyperemesis gravidarum", "Pregnancy"),
    ("O24.4", "Gestational diabetes mellitus", "Pregnancy"),
    ("O80", "Single spontaneous delivery", "Pregnancy"),
    ("S06.0", "Concussion", "Injury"),
    ("S42.0", "Fracture of clavicle", "Injury"),
    ("S52.5", "Fracture of lower end of radius", "Injury"),
    ("S72.0", "Fracture of neck of femur", "Injury"),
    ("S82.0", "Fracture of patella", "Injury"),
    ("T78.4", "Allergy, unspecified", "Injury"),
    ("R05", "Cough", "Symptoms"),
    ("R06.0", "Dyspnoea (shortness of breath)", "Symptoms"),
    ("R07.9", "Chest pain, unspecified", "Symptoms"),
    ("R10.4", "Other and unspecified abdominal pain", "Symptoms"),
    ("R11", "Nausea and vomiting", "Symptoms"),
    ("R42", "Dizziness and giddiness", "Symptoms"),
    ("R50.9", "Fever, unspecified", "Symptoms"),
    ("R51", "Headache", "Symptoms"),
    ("R53.1", "Weakness", "Symptoms"),
    ("R55", "Syncope and collapse (fainting)", "Symptoms"),
    ("R63.4", "Abnormal weight loss", "Symptoms"),
    ("Z00.0", "Encounter for general adult medical examination", "Health Factors"),
    ("Z01.0", "Encounter for examination of eyes and vision", "Health Factors"),
    ("Z23", "Encounter for immunization", "Health Factors"),
    ("Z76.0", "Encounter for issue of repeat prescription", "Health Factors"),
]


def _get_table_names(bind) -> set[str]:
    inspector = sa.inspect(bind)
    return set(inspector.get_table_names())


def upgrade() -> None:
    bind = op.get_bind()
    tables = _get_table_names(bind)

    if 'icd_codes' not in tables:
        op.create_table(
            'icd_codes',
            sa.Column('id', sa.String(), nullable=False),
            sa.Column('code', sa.String(), nullable=False),
            sa.Column('description', sa.Text(), nullable=False),
            sa.Column('category', sa.String(), nullable=False, server_default='General'),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(op.f('ix_icd_codes_code'), 'icd_codes', ['code'], unique=True)

    existing_count = bind.execute(sa.text("SELECT COUNT(*) FROM icd_codes")).scalar() or 0
    if existing_count == 0:
        icd_table = sa.table(
            'icd_codes',
            sa.column('id', sa.String()),
            sa.column('code', sa.String()),
            sa.column('description', sa.Text()),
            sa.column('category', sa.String()),
            sa.column('is_active', sa.Boolean()),
            sa.column('created_at', sa.DateTime()),
            sa.column('updated_at', sa.DateTime()),
        )
        now = datetime.utcnow()
        op.bulk_insert(
            icd_table,
            [
                {
                    'id': str(uuid4()),
                    'code': code,
                    'description': description,
                    'category': category,
                    'is_active': True,
                    'created_at': now,
                    'updated_at': now,
                }
                for code, description, category in ICD_SEED_ROWS
            ],
        )


def downgrade() -> None:
    bind = op.get_bind()
    tables = _get_table_names(bind)
    if 'icd_codes' in tables:
        op.drop_index(op.f('ix_icd_codes_code'), table_name='icd_codes')
        op.drop_table('icd_codes')