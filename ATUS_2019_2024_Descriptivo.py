import pandas as pd
import numpy as np
from pathlib import Path

# --- 1. CARGA DE DATOS ---
df = pd.read_parquet("data/processed/atus_zmm.parquet")

# --- 2. DECODIFICACIÓN SEGÚN DICCIONARIO OFICIAL INEGI ---
MAP_URBANA = {
    0: "Zona Suburbana",
    1: "Urbana - Intersección",
    2: "Urbana - No intersección"
}

MAP_SUBURBANA = {
    0: "Zona Urbana",
    1: "Suburbana - Camino rural",
    2: "Suburbana - Carretera estatal",
    3: "Suburbana - Otro camino"
}

MAP_CAUSAACCI = {
    1: "Conductor",
    2: "Peatón o pasajero",
    3: "Falla del vehículo",
    4: "Mala condición del camino",
    5: "Otra"
}

MAP_CAPAROD = {
    1: "Pavimentada",
    2: "No pavimentada"
}

MAP_TIPACCI = {
    0: 'Certificado cero',
    1: 'Colisión con vehículo automotor',
    2: 'Colisión con peatón (atropellamiento)',
    3: 'Colisión con animal',
    4: 'Colisión con objeto fijo',
    5: 'Volcadura',
    6: 'Caída de pasajero',
    7: 'Salida del camino',
    8: 'Incendio',
    9: 'Colisión con ferrocarril',
    10: 'Colisión con motocicleta',
    11: 'Colisión con ciclista',
    12: 'Otro'
}


# Aplicar mapeos directos
df['URBANA_DESC'] = df['URBANA'].map(MAP_URBANA).fillna("No especificado")
df['SUBURBANA_DESC'] = df['SUBURBANA'].map(MAP_SUBURBANA).fillna("No especificado")
df['CAUSA_DESC'] = df['CAUSAACCI'].map(MAP_CAUSAACCI).fillna("No especificado")
df['RODAMIENTO_DESC'] = df['CAPAROD'].map(MAP_CAPAROD).fillna("No especificado")
df['DESCRIP_TIPACCI'] = df['TIPACCID'].map(MAP_TIPACCI)

# Clasificar entorno sin cuellos de botella
def clasificar_entorno(row):
    if row['URBANA'] in [1, 2]:
        return row['URBANA_DESC']
    elif row['SUBURBANA'] in [1, 2, 3]:
        return row['SUBURBANA_DESC']
    return "Sin clasificar"

df['ENTORNO_VIA'] = df.apply(clasificar_entorno, axis=1)


# ==== SECCION_1 ====# 
# Probabilidades de heridos y defunciones por entorno, entorno-rodamiento, y causa presunta

# --- 3. INDICADORES Y TOTALES GLOBALES ZMM ---
df['TIENE_HERIDOS'] = (df['TOTHERIDOS'] > 0).astype(int)
df['TIENE_MUERTOS'] = (df['TOTMUERTOS'] > 0).astype(int)
df['TIENE_AFECTADOS']= (df['TOTHERIDOS'] + df['TOTMUERTOS'] > 0).map({True: 'Sí', False: 'No'})
df['AFECTADOS']= (df['TOTHERIDOS'] + df['TOTMUERTOS'] ).astype(int)

total_accidentes_zmm = len(df)
total_heridos_df = df['TOTHERIDOS'].sum()
total_muertos_df = df['TOTMUERTOS'].sum()
total_afectados_df = df['AFECTADOS'].sum()


# --- 4. CÁLCULO DE PROBABILIDADES Y PARTICIPACIONES ---

# --- A. Probabilidad Condicional y Participación Global: P(Afectados | Entorno)
prob_entorno = df.groupby('ENTORNO_VIA').agg(
    Total_Accidentes=('ID', 'count'),
    Total_HERIDOS=('TOTHERIDOS', 'sum'),
    Total_MUERTOS=('TOTMUERTOS', 'sum'),
    F_Herido=('TIENE_HERIDOS', 'sum'),
    F_Muerto=('TIENE_MUERTOS', 'sum')

).reset_index()

# Columnas de participación sobre el TOTAL GLOBAL de la ZMM
prob_entorno['Pct_Accidentes_Totales'] = (prob_entorno['Total_Accidentes'] / total_accidentes_zmm) * 100
prob_entorno['Pct_Heridos_Totales'] = (prob_entorno['Total_HERIDOS'] / total_heridos_df) * 100
prob_entorno['Pct_Muertos_Totales'] = (prob_entorno['Total_MUERTOS'] / total_muertos_df) * 100

# Tasa de accidentes con heridos y muertos
prob_entorno['Tasa_Accidentes_con_Heridos (%)'] = (prob_entorno['F_Herido']/ prob_entorno['Total_Accidentes'])*100
prob_entorno['Tasa_Accidentes_con_defunciones (%)'] = (prob_entorno['F_Muerto']/ prob_entorno['Total_Accidentes'])*100

# Reordenar columnas para una lectura ejecutiva limpia en Excel
cols_ordenadas = [
    'ENTORNO_VIA', 
    'Total_Accidentes', 'Pct_Accidentes_Totales',
    'Total_HERIDOS', 'Pct_Heridos_Totales', 'Tasa_Accidentes_con_Heridos (%)',
    'Total_MUERTOS', 'Pct_Muertos_Totales', 'Tasa_Accidentes_con_defunciones (%)'
]
prob_entorno = prob_entorno[cols_ordenadas]



# --- B. Probabilidad Condicional Conjunta y participación global: P(Severidad | Rodamiento n Entorno)
prob_conjunta = df.groupby(['ENTORNO_VIA', 'RODAMIENTO_DESC']).agg(
    Total_Accidentes=('ID', 'count'),
    Total_HERIDOS=('TOTHERIDOS', 'sum'),
    Total_MUERTOS=('TOTMUERTOS', 'sum'),
    F_Herido=('TIENE_HERIDOS', 'sum'),
    F_Muerto=('TIENE_MUERTOS', 'sum')
).reset_index()

# Columnas de participación sobre el TOTAL GLOBAL de la ZMM
prob_conjunta['Pct_Accidentes_Totales_cc'] = (prob_conjunta['Total_Accidentes'] / total_accidentes_zmm) * 100
prob_conjunta['Pct_Heridos_Totales_cc'] = (prob_conjunta['Total_HERIDOS'] / total_heridos_df) * 100
prob_conjunta['Pct_Muertos_Totales_cc'] = (prob_conjunta['Total_MUERTOS'] / total_muertos_df) * 100

# Tasa de accidentes con heridos y muertos
prob_conjunta['Tasa_Accidentes_con_Heridos (%)'] = (prob_conjunta['F_Herido']/ prob_conjunta['Total_Accidentes'])*100
prob_conjunta['Tasa_Accidentes_con_defunciones (%)'] = (prob_conjunta['F_Muerto']/ prob_conjunta['Total_Accidentes'])*100

cols_ordenadas_cc = [
    'ENTORNO_VIA', 'RODAMIENTO_DESC',
    'Total_Accidentes', 'Pct_Accidentes_Totales_cc',
    'Total_HERIDOS', 'Pct_Heridos_Totales_cc', 'Tasa_Accidentes_con_Heridos (%)',
    'Total_MUERTOS', 'Pct_Muertos_Totales_cc', 'Tasa_Accidentes_con_defunciones (%)' 
]

prob_conjunta = prob_conjunta[cols_ordenadas_cc]


# --- C. Probabilidad Condicional por Causa Presunta: P(Severidad | Causa)
prob_causa = df.groupby('CAUSA_DESC').agg(
    Total_Accidentes=('ID', 'count'),
    Total_HERIDOS=('TOTHERIDOS', 'sum'),
    Total_MUERTOS=('TOTMUERTOS', 'sum'),
    F_Herido=('TIENE_HERIDOS', 'sum'),
    F_Muerto=('TIENE_MUERTOS', 'sum')
).reset_index()

# Columnas de participación sobre el TOTAL GLOBAL de la ZMM
prob_causa['Pct_Accidentes_Totales_cu'] = (prob_causa['Total_Accidentes'] / total_accidentes_zmm) * 100
prob_causa['Pct_Heridos_Totales_cu'] = (prob_causa['Total_HERIDOS'] / total_heridos_df) * 100
prob_causa['Pct_Muertos_Totales_cu'] = (prob_causa['Total_MUERTOS'] / total_muertos_df) * 100

# Tasa de accidentes con heridos y muertos
prob_causa['Tasa_Accidentes_con_Heridos (%)'] = (prob_causa['F_Herido']/ total_accidentes_zmm)*100
prob_causa['Tasa_Accidentes_con_defunciones (%)'] = (prob_causa['F_Muerto']/ total_accidentes_zmm)*100

cols_ordenadas_causa = [
    'CAUSA_DESC',
    'Total_Accidentes', 'Pct_Accidentes_Totales_cu',
    'Total_HERIDOS', 'Pct_Heridos_Totales_cu', 'Tasa_Accidentes_con_Heridos (%)',
    'Total_MUERTOS', 'Pct_Muertos_Totales_cu', 'Tasa_Accidentes_con_defunciones (%)'
]


# ==== SECCION_2 ====# 
# Analisis descriptivo: Variables consecuentes cualitativas
#Frecuencia :tipo de accidente, tipo de afectado, tipo de vehiculo

# Tabla 4: Tipos de Accidente (TIPACCID)
tabla_tipo = df.get('TIPACCID_DESC', df['TIPACCID']).value_counts().to_frame(name='Total')
tabla_tipo['Porcentaje'] = (tabla_tipo['Total'] / len(df)) * 100



# ==== SECCION 3 ====# 
# Analisis multivariado tiempo-espacial
# Tabla 1: Evolución por Municipio y mes

col_mun = 'NOM_MUN' if 'NOM_MUN' in df.columns else 'MPIO'
tabla_consolidada = pd.crosstab(
    index=[df['ANIO'], df[col_mun]], 
    columns=df['MES'], 
    margins=True, 
    margins_name='Total'
)

#Tabla 2: Analisis por mes
tabla_mes = df['MES'].value_counts().sort_index().reset_index()
tabla_mes.columns = ['Mes', 'Total_Accidentes']

# Tabla 3: Incidencia por día y hora
tabla_dia = pd.crosstab(
    df['HORA'], 
    df.get('MAP_DIASEMANA',df['DIASEMANA']), margins=True, margins_name='Total') 



#=== SECCION_4 ====#
# Análisis probabilístico: Árbol de probabilidades espaciales y por condiciones

# --- 4. ÁRBOL DE PROBABILIDADES ESPACIALES ---

df_afectados=df[df['TIENE_AFECTADOS'] == 'Sí'].copy()

df_muertos=df[df['TIENE_MUERTOS'] == 'Sí'].copy()

print(f"Total de registros {len(df)}")

pcte_afectados= len(df_afectados)/len(df) # Calcula el porcentaje de registros con afectados sobre el total de registros
print(f"Porcentaje de accidentes con afectados: {pcte_afectados:.2%}")

pcte_muertos= len(df_muertos)/len(df) # Calcula el porcentaje de registros con afectados sobre el total de registros
print(f"Porcentaje de accidentes con muertos: {pcte_muertos:.2%}")

# A. Crear la tabla agrupada por municipio
tabla_afectados_mpio = df.groupby(col_mun).agg(
    Total_Muertos=('TOTMUERTOS', 'sum')
).reset_index()


# B. Probabilidad Global: Prob_por_Entorno
prob_afectados_entorno = df_afectados.groupby(['TIENE_MUERTOS', col_mun, 'ENTORNO_VIA']).agg(
    Total_Accidentes=('ID', 'count'),
    Total_Afectados=('AFECTADOS', 'sum'),
    Total_Muertos=('TOTMUERTOS', 'sum'),

).reset_index()


# Columnas de participación sobre el TOTAL GLOBAL de la ZMM
prob_afectados_entorno['Pct_Accidentes_Totales'] = (prob_afectados_entorno['Total_Accidentes'] / total_accidentes_zmm) * 100
prob_afectados_entorno['Pct_Afectados_Totales'] = (prob_afectados_entorno['Total_Afectados'] / total_afectados_df) * 100
prob_afectados_entorno['Pct_Muertos_Totales'] = (prob_afectados_entorno['Total_Muertos'] / total_muertos_df) * 100


# Reordenar columnas para una lectura ejecutiva limpia en Excel
cols_ordenadas_PM = [
    'TIENE_MUERTOS',
    col_mun, 'ENTORNO_VIA', 
    'Total_Accidentes', 'Pct_Accidentes_Totales',
    'Total_Afectados', 'Pct_Afectados_Totales',
    'Total_Muertos', 'Pct_Muertos_Totales', 
]
prob_afectados_entorno = prob_afectados_entorno[cols_ordenadas_PM]




# ---6. ARBOL DE PROBABILIDADES CONDICIONES ---


# B. Probabilidad Global: Prob_por_condiciones
prob_afectados_causa = df_afectados.groupby(['TIENE_MUERTOS', 'DESCRIP_TIPACCI', 'CAUSA_DESC']).agg(
    Total_Accidentes=('ID', 'count'),
    Total_Afectados=('AFECTADOS', 'sum'),
    Total_Muertos=('TOTMUERTOS', 'sum'),

).reset_index()


# Columnas de participación sobre el TOTAL GLOBAL de la ZMM
prob_afectados_causa['Pct_Accidentes_Totales'] = (prob_afectados_causa['Total_Accidentes'] / total_accidentes_zmm) * 100
prob_afectados_causa['Pct_Afectados_Totales'] = (prob_afectados_causa['Total_Afectados'] / total_afectados_df) * 100
prob_afectados_causa['Pct_Muertos_Totales'] = (prob_afectados_causa['Total_Muertos'] / total_muertos_df) * 100


# Reordenar columnas para una lectura ejecutiva limpia en Excel
cols_ordenadas_PC = [
    'TIENE_MUERTOS',
    'DESCRIP_TIPACCI', 'CAUSA_DESC',
    'Total_Accidentes', 'Pct_Accidentes_Totales',
    'Total_Afectados', 'Pct_Afectados_Totales',
    'Total_Muertos', 'Pct_Muertos_Totales', 
]
prob_afectados_causa = prob_afectados_causa[cols_ordenadas_PC]





# --- 5. EXPORTACIÓN A EXCEL ---
out_dir = Path("docs/reporte_salidas")
out_dir.mkdir(parents=True, exist_ok=True)
excel_path = out_dir / "ATUS_2019_2024_Descriptivo.xlsx"

with pd.ExcelWriter(excel_path) as writer:

    #SECCION 1: Análisis probabilístico: Probabilidades de heridos y defunciones por entorno, entorno-rodamiento, y causa presunta
    prob_entorno.to_excel(writer, sheet_name="Prob_por_Entorno", index=False)
    prob_conjunta.to_excel(writer, sheet_name="Prob_Entorno_CapaRod", index=False)
    prob_causa.to_excel(writer, sheet_name="Prob_por_Causa", index=False)

    #SECCION 2: Análisis descriptivo: Variables consecuentes cualitativas
    tabla_tipo.to_excel(writer, sheet_name="Tipo_Accidente")

    #SECCION 3: Análisis multivariado tiempo-espacial
    tabla_consolidada.to_excel(writer, sheet_name="Accidentes_Municipio_Año")
    tabla_mes.to_excel(writer, sheet_name="Accidentes_Mes")
    tabla_dia.to_excel(writer, sheet_name="Accidentes_Dia_Hora")

    #SECCION 4: Árbol de probabilidades espaciales y por condiciones
    tabla_afectados_mpio.to_excel(writer, sheet_name="Afectados_Mpio")
    prob_afectados_entorno.to_excel(writer, sheet_name="Prob_Muertes_Entorno", index=False)
    prob_afectados_causa.to_excel(writer, sheet_name="Prob_Muertes_Causa", index=False)     
    


print(f"Totales base ZMM: {total_accidentes_zmm:,} Accidentes | {total_heridos_df:,} Heridos | {total_muertos_df:,} Muertos")
print(f"¡Análisis probabilístico exportado exitosamente a {excel_path}!")