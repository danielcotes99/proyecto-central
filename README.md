# 🧪 Sistema de Esterilización — Streamlit App

## Estructura del proyecto

```
esterilizacion_app/
│── app.py                        ← Página principal (Home)
│── database.py                   ← Módulo de base de datos SQLite
│── esterilizacion.db             ← Base de datos (se crea automáticamente)
│── requirements.txt
└── pages/
    ├── 1_📝_Nuevo_Registro.py    ← Formulario de ingreso
    ├── 2_📊_Visualizar_Datos.py  ← Tabla editable + exportar
    └── 3_📈_Dashboard.py         ← Gráficas y KPIs
```

## Instalación

```bash
pip install streamlit pandas plotly
```

## Ejecutar la app

```bash
cd esterilizacion_app
streamlit run app.py
```

La app abre en: http://localhost:8501

## Acceso desde otras computadoras (red local)

```bash
streamlit run app.py --server.address 0.0.0.0
```

Otros equipos acceden con: http://TU_IP_LOCAL:8501

## Personalización

En `pages/1_📝_Nuevo_Registro.py`, edita las listas al inicio del archivo
para cambiar las opciones de los selectores (sedes, máquinas, operarios, etc.):

```python
SEDES     = ["", "Sede Central", "Sede Norte", ...]
MAQUINAS  = ["", "Autoclave 1", "Autoclave 2", ...]
```
