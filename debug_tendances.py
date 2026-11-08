import os
import sqlite3

os.chdir(r'e:\pilou\Xena\App_Xena_V5')
import app

conn = sqlite3.connect(':memory:')
conn.execute(
    """
    CREATE TABLE tendances (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        animal_id INTEGER NOT NULL,
        date_reference TEXT NOT NULL,
        temperature_matin REAL,
        temperature_soir REAL,
        humidite_matin INTEGER,
        humidite_soir INTEGER,
        brumisation INTEGER NOT NULL DEFAULT 0 CHECK (brumisation IN (0, 1)),
        eau_changee INTEGER NOT NULL DEFAULT 0 CHECK (eau_changee IN (0, 1)),
        repas_total INTEGER NOT NULL DEFAULT 0,
        insectes_total INTEGER NOT NULL DEFAULT 0,
        vitamine_d3 INTEGER NOT NULL DEFAULT 0 CHECK (vitamine_d3 IN (0, 1)),
        poids REAL,
        poids_unite TEXT DEFAULT 'g',
        taille REAL,
        taille_unite TEXT DEFAULT 'cm',
        notes TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(animal_id, date_reference)
    )
    """
)
resume = {
    'date_reference': '2026-08-01',
    'temperature_matin': 20.0,
    'temperature_soir': 24.0,
    'humidite_matin': 55,
    'humidite_soir': 60,
    'brumisation': 1,
    'eau_changee': 1,
    'repas_total': 2,
    'insectes_total': 1,
    'vitamine_d3': 1,
    'poids': 45.0,
    'poids_unite': 'g',
    'taille': 11.0,
    'taille_unite': 'cm',
    'notes': None,
    'has_data': True,
}
print('source function loaded')
print('tuple_len', len((
    1, resume['date_reference'], resume['temperature_matin'], resume['temperature_soir'],
    resume['humidite_matin'], resume['humidite_soir'], resume['brumisation'], resume['eau_changee'],
    resume['repas_total'], resume['insectes_total'], resume['vitamine_d3'], resume['poids'],
    resume['poids_unite'], resume['taille'], resume['taille_unite'], None,
)))
print('execute start')
result = app.sauvegarder_tendance_journalier(conn, 1, '2026-08-01', resume)
print('result', result)
print('count', conn.execute('SELECT COUNT(*) FROM tendances').fetchone())
conn.close()
