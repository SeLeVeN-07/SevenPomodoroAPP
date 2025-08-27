# -*- coding: utf-8 -*-
"""
Pomodoro Pro - Streamlit Cloud Version con Supabase y Autenticación
"""
import streamlit as st
import pandas as pd
import numpy as np
import time
import datetime
from datetime import timedelta, date
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import csv
import json
import base64
import io
import gzip
import re
from collections import defaultdict
from supabase import create_client, Client
import hashlib

# Configuración de Supabase (reemplaza con tus propias credenciales)
SUPABASE_URL = "https://zgvptomznuswsipfihho.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpndnB0b216bnVzd3NpcGZpaGhvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTYzMTAxNjYsImV4cCI6MjA3MTg4NjE2Nn0.Kk9qB8BKxIV7CgLZQdWW568MSpMjYtbceLQDfJvwttk"

# Inicializar cliente de Supabase
@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

# ==============================================
# Configuración inicial y constantes
# ==============================================

# Configuración de la página
st.set_page_config(
    page_title="Pomodoro Pro",
    page_icon="🍅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constantes
THEMES = {
    'Claro': {
        'bg': '#ffffff', 'fg': '#000000', 'circle_bg': '#e0e0e0',
        'text': '#333333', 'button_bg': '#f0f0f0', 'button_fg': '#000000',
        'frame_bg': '#ffffff', 'canvas_bg': '#ffffff', 'progress': '#3498db',
        'border': '#cccccc', 'highlight': '#dddddd', 'chart1': '#3498db',
        'chart2': '#e74c3c', 'grid': '#eeeeee'
    },
    'Oscuro': {
        'bg': '#2d2d2d', 'fg': '#ffffff', 'circle_bg': '#404040',
        'text': '#e0e0e0', 'button_bg': '#505050', 'button_fg': '#ffffff',
        'frame_bg': '#3d3d3d', 'canvas_bg': '#3d3d3d', 'progress': '#2980b9',
        'border': '#606060', 'highlight': '#707070', 'chart1': '#2980b9',
        'chart2': '#c0392b', 'grid': '#404040'
    },
    'Azul Profundo': {
        'bg': '#1a1a2f', 'fg': '#ffffff', 'circle_bg': '#2a2a4f',
        'text': '#b0b0ff', 'button_bg': '#3a3a6f', 'button_fg': '#ffffff',
        'frame_bg': '#2a2a3f', 'canvas_bg': '#2a2a3f', 'progress': '#4a90e2',
        'border': '#4a4a7f', 'highlight': '#5a5a8f', 'chart1': '#4a90e2',
        'chart2': '#ff6b6b', 'grid': '#3a3a5f'
    },
    'Verde Naturaleza': {
        'bg': '#1a2f1a', 'fg': '#e0ffe0', 'circle_bg': '#2a4f2a',
        'text': '#b0ffb0', 'button_bg': '#3a6f3a', 'button_fg': '#ffffff',
        'frame_bg': '#2a3f2a', 'canvas_bg': '#2a3f2a', 'progress': '#2ecc71',
        'border': '#4a7f4a', 'highlight': '#5a8f5a', 'chart1': '#2ecc71',
        'chart2': '#e67e22', 'grid': '#3a5f3a'
    }
}

# ==============================================
# Funciones de inicialización y utilidades
# ==============================================

def get_default_state():
    """Devuelve el estado por defecto de la aplicación"""
    return {
        'work_duration': 45 * 60,
        'short_break': 20 * 60,
        'long_break': 30 * 60,
        'sessions_before_long': 2,
        'total_sessions': 4,
        'session_count': 0,
        'remaining_time': 25 * 60,
        'current_phase': "Trabajo",
        'total_active_time': 0,
        'timer_running': False,
        'timer_paused': False,
        'start_time': None,
        'paused_time': None,
        'timer_start': None,
        'last_update': None,
        'current_theme': 'Claro',
        'activities': [],
        'current_activity': "",
        'sub_activity': "",
        'tasks': [],
        'projects': [],
        'current_project': "",
        'deadlines': [],
        'study_mode': False,
        'study_goals': [],
        'achievements': {
            'pomodoros_completed': 0,
            'tasks_completed': 0,
            'streak_days': 0,
            'total_hours': 0
        },
        'last_session_date': None,
        'completed_tasks': [],
        'editing_task': None,
        'editing_project': None,
        'dragging_item': None,
        'drag_type': None,
        'drag_source': None,
        'session_history': []
    }

def format_time(seconds):
    """Formatea segundos a formato MM:SS"""
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"

def get_phase_color(phase):
    """Devuelve el color correspondiente a cada fase"""
    colors = {
        "Trabajo": '#e74c3c',
        'Descanso Corto': '#2ecc71',
        'Descanso Largo': '#3498db'
    }
    return colors.get(phase, "#e74c3c")

def get_phase_duration(phase):
    """Devuelve la duración de cada fase"""
    state = st.session_state.pomodoro_state
    if phase == "Trabajo":
        return state['work_duration']
    elif phase == "Descanso Corto":
        return state['short_break']
    elif phase == "Descanso Largo":
        return state['long_break']
    else:
        return state['work_duration']  # Valor por defecto

def determine_next_phase(was_work):
    """Determina la siguiente fase basándose en el estado actual"""
    state = st.session_state.pomodoro_state
    if not was_work:
        return "Trabajo"
    
    # Calcular descanso según contador de sesiones
    if state['session_count'] % state['sessions_before_long'] == 0:
        return "Descanso Largo"
    return "Descanso Corto"

def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, (datetime.datetime, date)):
        return obj.isoformat()
    raise TypeError("Type %s not serializable" % type(obj))

# ==============================================
# Funciones de serialización/deserialización de fechas
# ==============================================

def convert_dates_to_iso(obj):
    """
    Recursively convert all date and datetime objects in the data to ISO strings.
    """
    if isinstance(obj, (date, datetime.datetime)):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: convert_dates_to_iso(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_dates_to_iso(element) for element in obj]
    else:
        return obj

def convert_iso_to_dates(obj):
    """
    Recursively convert all ISO date strings in the data to date or datetime objects.
    """
    if isinstance(obj, str):
        # Check if the string matches a date pattern
        try:
            # For date strings (YYYY-MM-DD)
            if re.match(r'^\d{4}-\d{2}-\d{2}$', obj):
                return datetime.datetime.strptime(obj, '%Y-%m-%d').date()
            # For datetime strings (YYYY-MM-DDTHH:MM:SS or with microseconds and timezone)
            elif re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', obj):
                # Try parsing with datetime
                return datetime.datetime.fromisoformat(obj.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            pass
        return obj
    elif isinstance(obj, dict):
        return {k: convert_iso_to_dates(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_iso_to_dates(element) for element in obj]
    else:
        return obj

# ==============================================
# Funciones de autenticación y seguridad
# ==============================================

def hash_password(password):
    """Hashea la contraseña usando SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(username, password):
    """Registra un nuevo usuario en Supabase (versión mejorada)"""
    try:
        # Verificar si el usuario ya existe
        response = supabase.table('users').select('username').eq('username', username).execute()
        
        if response.data:
            return False, "El nombre de usuario ya existe"
        
        # Crear nuevo usuario con data inicializada
        hashed_pw = hash_password(password)
        response = supabase.table('users').insert({
            'username': username,
            'password_hash': hashed_pw,
            'data': {}  # Inicializa data como objeto vacío
        }).execute()
        
        return True, "Usuario registrado exitosamente"
    except Exception as e:
        return False, f"Error al registrar usuario: {str(e)}"

def login_user(username, password):
    """Autentica un usuario (versión mejorada)"""
    try:
        # Obtener usuario usando single() para evitar arrays vacíos
        response = supabase.table('users')
            .select('*')
            .eq('username', username)
            .single()
            .execute()
        
        user = response.data
        hashed_pw = hash_password(password)
        
        if user['password_hash'] == hashed_pw:
            # Establece autenticación en session_state
            st.session_state.authenticated = True
            st.session_state.username = username
            return True, "Inicio de sesión exitoso"
        return False, "Contraseña incorrecta"
    except Exception as e:
        return False, f"Usuario no encontrado o error: {str(e)}"

def check_authentication():
    """Verifica si el usuario está autenticado"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'username' not in st.session_state:
        st.session_state.username = None
    return st.session_state.authenticated

def auth_section():
    """Muestra la sección de autenticación (versión mejorada)"""
    with st.sidebar:
        if not check_authentication():
            st.title("🔒 Autenticación")
            
            tab1, tab2 = st.tabs(["Iniciar Sesión", "Registrarse"])
            
            with tab1:
                with st.form("login_form"):
                    username = st.text_input("Usuario")
                    password = st.text_input("Contraseña", type="password")
                    
                    if st.form_submit_button("Iniciar Sesión"):
                        success, message = login_user(username, password)
                        if success:
                            load_from_supabase()  # Carga datos tras login
                            st.rerun()
                        st.error(message if not success else "")
            
            with tab2:
                with st.form("register_form"):
                    new_user = st.text_input("Nuevo usuario")
                    new_pass = st.text_input("Nueva contraseña", type="password")
                    
                    if st.form_submit_button("Registrarse"):
                        if len(new_user) < 3:
                            st.error("Usuario muy corto (mín. 3 caracteres)")
                        elif len(new_pass) < 6:
                            st.error("Contraseña muy corta (mín. 6 caracteres)")
                        else:
                            success, message = register_user(new_user, new_pass)
                            if success:
                                st.session_state.authenticated = True
                                st.session_state.username = new_user
                                st.rerun()
                            st.error(message if not success else "")

def get_jwt_header():
    """Genera encabezado de autenticación"""
    return {
        'Authorization': f"Bearer {st.session_state.get('jwt_token', '')}",
        'apikey': eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpndnB0b216bnVzd3NpcGZpaGhvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTYzMTAxNjYsImV4cCI6MjA3MTg4NjE2Nn0.Kk9qB8BKxIV7CgLZQdWW568MSpMjYtbceLQDfJvwttk
    }

# ==============================================
# Funciones de importación/exportación con Supabase
# ==============================================

def save_to_supabase():
    """Guarda todos los datos en Supabase (versión optimizada)"""
    if not check_authentication():
        st.error("Debes iniciar sesión para guardar datos")
        return False
    
    try:
        state = st.session_state.pomodoro_state.copy()
        username = st.session_state.username
        
        # Configura autenticación para la solicitud
        supabase.postgrest.auth(f"Bearer {st.session_state.get('jwt_token', '')}")
        
        # Prepara datos comprimiendo fechas
        save_dict = {
            'activities': convert_dates_to_iso(state['activities']),
            'tasks': convert_dates_to_iso(state['tasks']),
            # ... (otros campos igual que antes)
            'last_updated': datetime.datetime.now().isoformat()
        }
        
        # Upsert optimizado
        response = supabase.table('users').upsert({
            'username': username,
            'data': save_dict
        }).execute()
        
        st.success("Datos guardados correctamente!")
        return True
    except Exception as e:
        st.error(f"Error al guardar: {str(e)}")
        return False

def load_from_supabase():
    """Carga datos desde Supabase (versión optimizada)"""
    if not check_authentication():
        st.error("Debes iniciar sesión para cargar datos")
        return False
    
    try:
        username = st.session_state.username
        supabase.postgrest.auth(f"Bearer {st.session_state.get('jwt_token', '')}")
        
        # Query optimizada
        response = supabase.table('users')
            .select('data')
            .eq('username', username)
            .single()
            .execute()
        
        imported_data = convert_iso_to_dates(response.data['data'])
        
        # Actualiza el estado (versión más segura)
        state_fields = ['activities', 'tasks', 'projects', 'achievements', 'session_history']
        for field in state_fields:
            if field in imported_data:
                st.session_state.pomodoro_state[field] = imported_data[field]
        
        st.success("Datos cargados correctamente!")
        return True
    except Exception as e:
        st.warning(f"No se encontraron datos o error: {str(e)}")
        return False

# Mantén las funciones de export/import originales como respaldo
def export_data():
    """Exporta todos los datos a un JSON comprimido (backup local)"""
    state = st.session_state.pomodoro_state.copy()
    
    # Preparar datos para exportación
    export_dict = {
        'activities': state['activities'],
        'tasks': state['tasks'],
        'completed_tasks': state['completed_tasks'],
        'projects': state['projects'],
        'achievements': state['achievements'],
        'session_history': state['session_history'],
        'settings': {
            'work_duration': state['work_duration'],
            'short_break': state['short_break'],
            'long_break': state['long_break'],
            'sessions_before_long': state['sessions_before_long'],
            'total_sessions': state['total_sessions'],
            'current_theme': state['current_theme']
        }
    }
    
    # Convertir fechas a formato ISO
    export_dict = convert_dates_to_iso(export_dict)
    
    # Convertir a JSON y comprimir
    json_str = json.dumps(export_dict, indent=2, ensure_ascii=False, default=json_serial)
    compressed = gzip.compress(json_str.encode('utf-8'))
    
    # Crear archivo descargable
    b64 = base64.b64encode(compressed).decode()
    href = f'<a href="data:application/gzip;base64,{b64}" download="pomodoro_backup.json.gz">Descargar backup</a>'
    st.markdown(href, unsafe_allow_html=True)

def import_data(uploaded_file):
    """Importa datos desde un archivo JSON comprimido (backup local)"""
    try:
        # Descomprimir y cargar
        compressed = uploaded_file.read()
        json_str = gzip.decompress(compressed).decode('utf-8')
        imported_data = json.loads(json_str)
        
        # Convertir cadenas ISO a objetos fecha
        imported_data = convert_iso_to_dates(imported_data)
        
        # Actualizar estado
        state = st.session_state.pomodoro_state
        state['activities'] = imported_data.get('activities', [])
        state['tasks'] = imported_data.get('tasks', [])
        state['completed_tasks'] = imported_data.get('completed_tasks', [])
        state['projects'] = imported_data.get('projects', [])
        state['achievements'] = imported_data.get('achievements', state['achievements'])
        state['session_history'] = imported_data.get('session_history', [])
        
        # Configuración
        settings = imported_data.get('settings', {})
        state['work_duration'] = settings.get('work_duration', 25*60)
        state['short_break'] = settings.get('short_break', 5*60)
        state['long_break'] = settings.get('long_break', 15*60)
        state['sessions_before_long'] = settings.get('sessions_before_long', 4)
        state['total_sessions'] = settings.get('total_sessions', 8)
        state['current_theme'] = settings.get('current_theme', 'Claro')
        
        st.success("Datos importados correctamente!")
        st.rerun()
    except Exception as e:
        st.error(f"Error al importar datos: {str(e)}")

# ==============================================
# Funciones de registro de sesiones
# ==============================================

def log_session():
    """Registra una sesión completada en el historial"""
    state = st.session_state.pomodoro_state
    if state['total_active_time'] >= 0.1:
        minutes = round(state['total_active_time'] / 60, 2)
        log_entry = {
            'Fecha': datetime.datetime.now().strftime("%Y-%m-%d"),
            'Hora Inicio': state['start_time'].strftime("%H:%M:%S") if state['start_time'] else datetime.datetime.now().strftime("%H:%M:%S"),
            'Tiempo Activo (min)': minutes,
            'Actividad': state['current_activity'],
            'Proyecto': state['current_project'],
            'Tarea': state.get('current_task', '')
        }
        
        # Guardar en el historial de sesiones
        state['session_history'].append(log_entry)
        
        # Actualizar logros
        if state['current_phase'] == "Trabajo":
            state['achievements']['pomodoros_completed'] += 1
            state['achievements']['total_hours'] += minutes / 60
            
            # Verificar racha diaria
            today = date.today()
            if state['last_session_date'] != today:
                if state['last_session_date'] and (today - state['last_session_date']).days == 1:
                    state['achievements']['streak_days'] += 1
                elif not state['last_session_date']:
                    state['achievements']['streak_days'] = 1
                else:
                    state['achievements']['streak_days'] = 1
                state['last_session_date'] = today

def analyze_data():
    """Analiza los datos del historial de sesiones"""
    data = {
        'activities': defaultdict(float),
        'projects': defaultdict(float),
        'tasks': defaultdict(float),
        'daily_total': defaultdict(float),
        'raw_data': []
    }
    
    for entry in st.session_state.pomodoro_state['session_history']:
        try:
            date_obj = datetime.datetime.strptime(entry['Fecha'], "%Y-%m-%d").date()
            hour = int(entry['Hora Inicio'].split(':')[0]) if ':' in entry['Hora Inicio'] else 0
            duration = float(entry['Tiempo Activo (min)'])
            activity = entry['Actividad'].strip()
            project = entry.get('Proyecto', '').strip()
            task = entry.get('Tarea', '').strip()

            data['activities'][activity] += duration
            if project:
                data['projects'][project] += duration
            if task:
                data['tasks'][task] += duration
            data['daily_total'][entry['Fecha']] += duration
            data['raw_data'].append({
                'date': date_obj, 'hour': hour, 
                'duration': duration, 'activity': activity,
                'project': project, 'task': task
            })
        except Exception as e:
            print(f"Error procesando entrada: {e}")
    return data

def logout():
    """Cierra sesión limpiando todo"""
    st.session_state.clear()
    st.session_state.pomodoro_state = get_default_state()
    st.rerun()

# ==============================================
# Funciones de gestión de tareas
# ==============================================

def edit_task_modal():
    """Muestra el modal para editar una tarea"""
    state = st.session_state.pomodoro_state
    if state.get('editing_task'):
        task = state['editing_task']
        
        with st.form("edit_task_form"):
            st.subheader("✏️ Editar Tarea")
            
            new_name = st.text_input("Nombre", value=task['name'])
            
            # Obtener actividad actual del proyecto de la tarea
            current_project = next((p for p in state['projects'] if p['name'] == task['project']), None)
            current_activity = current_project['activity'] if current_project else task.get('activity', '')
            
            # Proyectos disponibles para la actividad actual
            available_projects = [p['name'] for p in state['projects'] if p['activity'] == current_activity]
            new_project = st.selectbox(
                "Proyecto",
                ["Ninguno"] + available_projects,
                index=(["Ninguno"] + available_projects).index(task['project']) if task['project'] in ["Ninguno"] + available_projects else 0
            )
            
            new_priority = st.selectbox(
                "Prioridad",
                ["Baja", "Media", "Alta", "Urgente"],
                index=["Baja", "Media", "Alta", "Urgente"].index(task['priority'])
            )
            
            new_deadline = st.date_input("Fecha límite", value=task['deadline'])
            
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("💾 Guardar"):
                    # Actualizar la tarea
                    task['name'] = new_name
                    task['project'] = new_project
                    task['priority'] = new_priority
                    task['deadline'] = new_deadline
                    
                    # Si cambió el proyecto, actualizar la actividad
                    if new_project != "Ninguno":
                        project = next((p for p in state['projects'] if p['name'] == new_project), None)
                        if project:
                            task['activity'] = project['activity']
                    
                    st.success("Tarea actualizada!")
                    state['editing_task'] = None
                    st.rerun()
            
            with col2:
                if st.form_submit_button("❌ Cancelar"):
                    state['editing_task'] = None
                    st.rerun()

def edit_project_modal():
    """Muestra el modal para editar un proyecto"""
    state = st.session_state.pomodoro_state
    if state.get('editing_project'):
        project = state['editing_project']
        
        with st.form("edit_project_form"):
            st.subheader("✏️ Editar Proyecto")
            
            new_name = st.text_input("Nombre", value=project['name'])
            new_activity = st.selectbox(
                "Actividad",
                state['activities'],
                index=state['activities'].index(project['activity']) if project['activity'] in state['activities'] else 0
            )
            
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("💾 Guardar"):
                    old_name = project['name']
                    old_activity = project['activity']
                    
                    # Actualizar el proyecto
                    project['name'] = new_name
                    project['activity'] = new_activity
                    
                    # Actualizar tareas asociadas
                    for task in state['tasks'] + state['completed_tasks']:
                        if task['project'] == old_name and task.get('activity') == old_activity:
                            task['project'] = new_name
                            task['activity'] = new_activity
                    
                    st.success("Proyecto actualizado!")
                    state['editing_project'] = None
                    st.rerun()
            
            with col2:
                if st.form_submit_button("❌ Cancelar"):
                    state['editing_project'] = None
                    st.rerun()

# ==============================================
# Funciones de visualización
# ==============================================

def hierarchical_view():
    """Muestra la vista jerárquica de actividades, proyectos y tareas"""
    state = st.session_state.pomodoro_state
    
    st.subheader("🌳 Vista Jerárquica")
    
    # Creación rápida de proyectos y tareas
    with st.expander("➕ Crear Nuevo Elemento", expanded=False):
        create_col1, create_col2 = st.columns(2)
        
        with create_col1:
            st.write("**Nuevo Proyecto**")
            new_project_name = st.text_input("Nombre del proyecto", key="new_project_name")
            new_project_activity = st.selectbox(
                "Actividad asociada",
                state['activities'],
                key="new_project_activity"
            )
            if st.button("Crear Proyecto", key="create_project"):
                if new_project_name:
                    if new_project_name not in [p['name'] for p in state['projects']]:
                        state['projects'].append({
                            'name': new_project_name,
                            'activity': new_project_activity
                        })
                        st.success("Proyecto creado!")
                        st.rerun()
                    else:
                        st.error("Ya existe un proyecto con ese nombre")

        with create_col2:
            st.write("**Nueva Tarea**")
            new_task_name = st.text_input("Nombre de la tarea", key="new_task_name")
            new_task_project = st.selectbox(
                "Proyecto",
                [p['name'] for p in state['projects']] + ["Ninguno"],
                key="new_task_project"
            )
            new_task_priority = st.selectbox(
                "Prioridad",
                ["Baja", "Media", "Alta", "Urgente"],
                index=1,
                key="new_task_priority"
            )
            new_task_deadline = st.date_input(
                "Fecha límite",
                value=date.today() + timedelta(days=7),
                key="new_task_deadline"
            )
            if st.button("Crear Tarea", key="create_task"):
                if new_task_name:
                    new_task = {
                        'name': new_task_name,
                        'project': new_task_project,
                        'activity': next((p['activity'] for p in state['projects'] if p['name'] == new_task_project), ""),
                        'priority': new_task_priority,
                        'deadline': new_task_deadline,
                        'completed': False,
                        'created': date.today()
                    }
                    state['tasks'].append(new_task)
                    st.success("Tarea creada!")
                    st.rerun()

    # Mostrar estructura jerárquica
    for activity in state['activities']:
        with st.expander(f"📁 {activity}", expanded=True):
            # Proyectos de esta actividad
            activity_projects = [p for p in state['projects'] if p['activity'] == activity]
            
            if not activity_projects:
                st.info("No hay proyectos en esta actividad")
            else:
                for project in activity_projects:
                    col1, col2 = st.columns([5, 1])
                    with col1:
                        st.write(f"📂 **{project['name']}**")
                        
                        # Tareas de este proyecto
                        project_tasks = [t for t in state['tasks'] 
                                       if not t['completed'] 
                                       and t['project'] == project['name'] 
                                       and t.get('activity') == activity]
                        
                        if not project_tasks:
                            st.write("  └ No hay tareas pendientes")
                        else:
                            for task in project_tasks:
                                cols = st.columns([5, 1, 1])
                                with cols[0]:
                                    st.write(f"  └ {task['name']} ({task['priority']}) - Vence: {task['deadline']}")
                                with cols[1]:
                                    if st.button("✏️", key=f"edit_task_{task['name']}_{project['name']}"):
                                        state['editing_task'] = task
                                        st.rerun()
                                with cols[2]:
                                    if st.button("✓", key=f"complete_{task['name']}_{project['name']}"):
                                        task['completed'] = True
                                        task['completed_date'] = date.today()
                                        state['tasks'].remove(task)
                                        state['completed_tasks'].append(task)
                                        state['achievements']['tasks_completed'] += 1
                                        st.success("Tarea completada!")
                                        st.rerun()
                    
                    with col2:
                        if st.button("✏️", key=f"edit_proj_{project['name']}"):
                            state['editing_project'] = project
                            st.rerun()
                        if st.button("🗑️", key=f"delete_proj_{project['name']}"):
                            # Mover tareas a "Ninguno" antes de eliminar
                            for task in state['tasks'] + state['completed_tasks']:
                                if task['project'] == project['name']:
                                    task['project'] = "Ninguno"
                            state['projects'].remove(project)
                            st.success("Proyecto eliminado!")
                            st.rerun()

def display_filtered_tasks(filter_activity, filter_project, task_status):
    """Muestra tareas filtradas con claves únicas para botones"""
    state = st.session_state.pomodoro_state
    
    # Aplicar filtros
    filtered_tasks = []
    for task in state['tasks'] + state['completed_tasks']:
        # Filtrar por actividad
        if filter_activity != "Todas" and task.get('activity') != filter_activity:
            continue
            
        # Filtrar por proyecto
        if filter_project != "Todos" and task['project'] != filter_project:
            continue
            
        # Filtrar por estado
        if task_status == "Pendientes" and task['completed']:
            continue
        if task_status == "Completadas" and not task['completed']:
            continue
            
        filtered_tasks.append(task)
    
    # Mostrar tareas filtradas (VERSIÓN CORREGIDA)
    if not filtered_tasks:
        st.info("No hay tareas que coincidan con los filtros")
    else:
        for i, task in enumerate(filtered_tasks):  # Usar enumerate para índice único
            with st.container(border=True):
                cols = st.columns([4, 1, 1, 1])
                with cols[0]:
                    status = "✅ " if task['completed'] else "📝 "
                    st.write(f"{status}**{task['name']}**")
                    st.caption(f"Proyecto: {task['project']} | Prioridad: {task['priority']} | Vence: {task['deadline']}")
                
                with cols[1]:
                    if st.button("✏️", key=f"edit_{i}_{task['name']}_{task['project']}"):  # Clave única con índice
                        state['editing_task'] = task
                        st.rerun()
                
                with cols[2]:
                    if not task['completed']:
                        if st.button("✓", key=f"complete_{i}_{task['name']}_{task['project']}"):  # Clave única con índice
                            task['completed'] = True
                            task['completed_date'] = date.today()
                            # Encontrar y eliminar la tarea de la lista original
                            for t in state['tasks']:
                                if t['name'] == task['name'] and t['project'] == task['project']:
                                    state['tasks'].remove(t)
                                    break
                            state['completed_tasks'].append(task)
                            state['achievements']['tasks_completed'] += 1
                            st.success("Tarea completada!")
                            st.rerun()
                    else:
                        st.write("✅")
                
                with cols[3]:
                    if st.button("🗑️", key=f"delete_{i}_{task['name']}_{task['project']}"):  # Clave única con índice
                        if task['completed']:
                            state['completed_tasks'].remove(task)
                        else:
                            state['tasks'].remove(task)
                        st.success("Tarea eliminada!")
                        st.rerun()

# ==============================================
# Pestaña de Temporizador
# ==============================================

def timer_tab():
    """Muestra la pestaña del temporizador Pomodoro"""
    state = st.session_state.pomodoro_state
    
    # Mostrar materia actual si está en modo estudio
    if state['study_mode'] and state['current_activity']:
        st.header(f"Actividad: {state['current_activity']}")

    # Selector de actividad
    col1, col2 = st.columns(2)
    with col1:
        if not state['activities']:
            st.warning("No hay actividades disponibles. Agrega actividades en la pestaña de Configuración")
            state['current_activity'] = ""
        else:
            state['current_activity'] = st.selectbox(
                "Actividad",
                state['activities'],
                key="current_activity"
            )

    # Eliminar el campo de subactividad (ya no se usará)
    with col2:
        state['sub_activity'] = ""  # Mantener por compatibilidad pero no mostrar

        # Crear proyecto desde el timer tab
    with st.expander("➕ Crear Proyecto Rápido", expanded=False):
        new_project_name = st.text_input("Nombre del proyecto", key="new_project_timer")
        if st.button("Crear Proyecto", key="create_project_timer"):
            if new_project_name and new_project_name not in [p['name'] for p in state['projects']]:
                state['projects'].append({
                    'name': new_project_name,
                    'activity': state['current_activity']
                })
                st.success("Proyecto creado!")
                st.rerun()
            elif new_project_name in [p['name'] for p in state['projects']]:
                st.error("Ya existe un proyecto con ese nombre")

    # Selector de proyecto (solo proyectos asociados a la actividad actual)
    available_projects = [p['name'] for p in state['projects'] if p['activity'] == state['current_activity']]
    if available_projects:
        state['current_project'] = st.selectbox(
            "Proyecto",
            available_projects + ["Ninguno"],
            key="current_project"
        )
    else:
        st.info("No hay proyectos asociados a esta actividad. Puedes crear uno arriba.")
        state['current_project'] = "Ninguno"

    # Si hay un proyecto seleccionado, mostrar selector de tareas asociadas
    if state['current_project'] != "Ninguno":
        # Obtener tareas no completadas para este proyecto y actividad
        project_tasks = [t for t in state['tasks'] 
                       if not t['completed'] 
                       and t['project'] == state['current_project'] 
                       and t.get('activity') == state['current_activity']]
        
        if project_tasks:
            # Crear selector de tareas existentes
            task_names = [t['name'] for t in project_tasks]
            selected_task = st.selectbox(
                "Seleccionar tarea existente", 
                ["-- Seleccionar --"] + task_names + ["+ Crear nueva tarea"],
                key="select_existing_task"
            )
            
            if selected_task == "+ Crear nueva tarea":
                # Campo para crear nueva tarea
                new_task_name = st.text_input("Nombre de la nueva tarea", key="new_task_name")
                if new_task_name:
                    # Crear la tarea automáticamente al seleccionarla
                    new_task = {
                        'name': new_task_name,
                        'project': state['current_project'],
                        'activity': state['current_activity'],
                        'priority': "Media",
                        'deadline': date.today() + timedelta(days=7),
                        'completed': False,
                        'created': date.today()
                    }
                    state['tasks'].append(new_task)
                    state['current_task'] = new_task_name
                    st.success("Tarea creada!")
                    st.rerun()
            elif selected_task != "-- Seleccionar --":
                state['current_task'] = selected_task
        else:
            # No hay tareas para este proyecto, permitir crear una
            new_task_name = st.text_input("Nombre de la tarea", key="new_task_name_no_existing")
            if new_task_name:
                new_task = {
                    'name': new_task_name,
                    'project': state['current_project'],
                    'activity': state['current_activity'],
                    'priority': "Media",
                    'deadline': date.today() + timedelta(days=7),
                    'completed': False,
                    'created': date.today()
                }
                state['tasks'].append(new_task)
                state['current_task'] = new_task_name
                st.success("Tarea creada!")
                st.rerun()

    # Verificar si hay una actividad seleccionada antes de mostrar el temporizador
    if not state['current_activity']:
        st.error("Selecciona una actividad para comenzar")
        return

    # Visualización del temporizador
    theme = THEMES[state['current_theme']]

    # Crear un círculo de progreso con Plotly
    phase_duration = get_phase_duration(state['current_phase'])
    progress = 1 - (state['remaining_time'] / phase_duration) if phase_duration > 0 else 0

    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = state['remaining_time'],
        number = {'suffix': "s", 'font': {'size': 40}},
        gauge = {
            'axis': {'range': [0, phase_duration], 'visible': False},
            'bar': {'color': get_phase_color(state['current_phase'])},
            'steps': [
                {'range': [0, phase_duration], 'color': theme['circle_bg']}
            ]
        },
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': f"{state['current_phase']} - {format_time(state['remaining_time'])}", 'font': {'size': 24}}
    ))

    fig.update_layout(
        height=300,
        margin=dict(l=10, r=10, t=80, b=10),
        paper_bgcolor=theme['bg'],
        font={'color': theme['text']}
    )

    st.plotly_chart(fig, use_container_width=True)

    # Controles del temporizador
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("▶️ Iniciar" if not state['timer_running'] else "▶️ Reanudar",
                   use_container_width=True, type="primary", key="start_timer"):
            if not state['timer_running']:
                state['timer_running'] = True
                state['timer_paused'] = False
                state['start_time'] = datetime.datetime.now()
                state['total_active_time'] = 0
                # Iniciar el temporizador
                st.session_state.timer_start = time.time()
                st.session_state.last_update = time.time()
                st.rerun()

    with col2:
        if st.button("⏸️ Pausar" if state['timer_running'] and not state['timer_paused'] else "▶️ Reanudar",
                   use_container_width=True, disabled=not state['timer_running'], key="pause_timer"):
            if state['timer_running'] and not state['timer_paused']:
                state['timer_paused'] = True
                state['paused_time'] = time.time()
                st.rerun()
            elif state['timer_paused']:
                state['timer_paused'] = False
                # Ajustar el tiempo de inicio para compensar la pausa
                pause_duration = time.time() - state['paused_time']
                st.session_state.timer_start += pause_duration
                st.session_state.last_update = time.time()
                st.rerun()

    with col3:
        if st.button("⏭️ Saltar Fase", use_container_width=True, key="skip_phase"):
            was_work = state['current_phase'] == "Trabajo"

            # Lógica para sesiones de trabajo
            if was_work:
                state['session_count'] += 1
                if state['total_active_time'] >= 0.1:
                    log_session()
                
                if state['session_count'] >= state['total_sessions']:
                    st.success("¡Todas las sesiones completadas!")
                    state['session_count'] = 0
                    state['current_phase'] = "Trabajo"
                    state['remaining_time'] = state['work_duration']
                    state['timer_running'] = False
                    state['timer_paused'] = False
                    st.rerun()
            
            # Determinar siguiente fase
            state['current_phase'] = determine_next_phase(was_work)
            state['remaining_time'] = get_phase_duration(state['current_phase'])
            state['total_active_time'] = 0
            state['timer_running'] = False
            state['timer_paused'] = False
            st.rerun()

        # Contador de sesiones
    st.write(f"Sesiones completadas: {state['session_count']}/{state['total_sessions']}")

    # Actualizar el temporizador si está en ejecución
    if state['timer_running'] and not state['timer_paused']:
        current_time = time.time()
        elapsed = current_time - st.session_state.last_update
        st.session_state.last_update = current_time

        state['remaining_time'] -= elapsed
        state['total_active_time'] += elapsed

        if state['remaining_time'] <= 0:
            # Fase completada
            was_work = state['current_phase'] == "Trabajo"
            
            if was_work:
                if state['total_active_time'] >= 0.1:
                    log_session()
                state['session_count'] += 1
                
                if state['session_count'] >= state['total_sessions']:
                    st.success("¡Todas las sesiones completadas!")
                    state['session_count'] = 0
                    state['current_phase'] = "Trabajo"
                    state['remaining_time'] = state['work_duration']
                    state['timer_running'] = False
                    state['timer_paused'] = False
                    st.rerun()
            
            # Determinar siguiente fase
            state['current_phase'] = determine_next_phase(was_work)
            state['remaining_time'] = get_phase_duration(state['current_phase'])
            state['total_active_time'] = 0
            st.success(f"¡Fase completada! Iniciando: {state['current_phase']}")
            
            # Mostrar notificación toast
            if was_work:
                st.toast("¡Pomodoro completado! Tómate un descanso.", icon="🎉")
            else:
                st.toast("¡Descanso completado! Volvamos al trabajo.", icon="💪")
            
            st.rerun()

    # Forzar actualización de la interfaz
    time.sleep(0.1)
    st.rerun()

# ==============================================
# Pestaña de Estadísticas
# ==============================================

def stats_tab():
    """Muestra la pestaña de estadísticas"""
    st.title("📊 Estadísticas Avanzadas")
    
    if not st.session_state.pomodoro_state['session_history']:
        st.warning("No hay datos de sesiones registrados.")
        return
    
    data = analyze_data()
    
    # Mostrar métricas principales
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_minutes = sum(data['activities'].values())
        st.metric("Tiempo Total", f"{total_minutes/60:.1f} horas")
    
    with col2:
        total_sessions = len(data['raw_data'])
        st.metric("Sesiones Totales", total_sessions)
    
    with col3:
        avg_session = total_minutes / total_sessions if total_sessions > 0 else 0
        st.metric("Duración Promedio", f"{avg_session:.1f} min")
    
    with col4:
        unique_days = len(data['daily_total'])
        st.metric("Días Activos", unique_days)
    
    # Selector de pestañas
    tab1, tab2, tab3, tab4 = st.tabs(["Visión General", "Tendencias", "Distribución", "Tabla Resumen"])
    
    with tab1:
        col1, col2 = st.columns(2)
        
        with col1:
            # Gráfico de distribución de actividades
            if data['activities']:
                fig = px.pie(
                    values=list(data['activities'].values()), 
                    names=list(data['activities'].keys()),
                    title="Distribución de Actividades"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No hay datos para mostrar")
        
        with col2:
            # Gráfico de tiempo por proyecto
            project_data = defaultdict(float)
            for r in data['raw_data']:
                if r['project']:
                    project_data[r['project']] += r['duration']
            
            if project_data:
                fig = px.pie(
                    values=list(project_data.values()), 
                    names=list(project_data.keys()),
                    title="Distribución por Proyecto"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No hay datos de proyectos para mostrar")
    
    with tab2:
        st.subheader("Análisis de Tendencias")
        
        # Gráfico de líneas - evolución del tiempo
        if data['raw_data']:
            # Agrupar por fecha
            df_dates = pd.DataFrame([
                {'date': r['date'], 'minutes': r['duration']} 
                for r in data['raw_data']
            ])
            daily_totals = df_dates.groupby('date').sum().reset_index()
            
            fig = px.line(
                daily_totals, x='date', y='minutes',
                title="Evolución del Tiempo por Día",
                labels={'date': 'Fecha', 'minutes': 'Minutos'}
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay datos suficientes para mostrar tendencias")
    
    with tab3:
        st.subheader("Distribución por Actividad y Proyecto")
        
        if data['raw_data']:
            # Crear matriz para heatmap
            activities = sorted(set(r['activity'] for r in data['raw_data']))
            projects = sorted(set(r['project'] for r in data['raw_data'] if r['project']))
            
            # Crear matriz de minutos por actividad y proyecto
            heatmap_data = np.zeros((len(activities), len(projects)))
            
            for r in data['raw_data']:
                if r['project']:
                    act_idx = activities.index(r['activity'])
                    proj_idx = projects.index(r['project'])
                    heatmap_data[act_idx, proj_idx] += r['duration']
            
            # Crear heatmap
            fig = px.imshow(
                heatmap_data,
                labels=dict(x="Proyecto", y="Actividad", color="Minutos"),
                x=projects,
                y=activities,
                title="Distribución de Tiempo por Actividad y Proyecto"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay datos suficientes para el heatmap")
    
    with tab4:
        st.subheader("Tabla Resumen de Sesiones")
        
        if data['raw_data']:
            # Crear DataFrame para mostrar
            df_display = pd.DataFrame([{
                'Fecha': r['date'].strftime("%Y-%m-%d"),
                'Hora': f"{r['hour']:02d}:00",
                'Duración (min)': r['duration'],
                'Actividad': r['activity'],
                'Proyecto': r['project'],
                'Tarea': r['task']
            } for r in data['raw_data']])
            
            st.dataframe(df_display, use_container_width=True)
        else:
            st.info("No hay sesiones registradas")

# ==============================================
# Pestaña de Tareas
# ==============================================

def tasks_tab():
    """Muestra la pestaña de gestión de tareas"""
    state = st.session_state.pomodoro_state
    st.title("📋 Gestión de Tareas y Proyectos")
    
    # Mostrar modales de edición si están activos
    if state.get('editing_task'):
        edit_task_modal()
    if state.get('editing_project'):
        edit_project_modal()
    
    # Vista jerárquica principal
    hierarchical_view()
    
    # Lista completa de tareas con filtros
    st.divider()
    st.subheader("📝 Lista Completa de Tareas")
    
    # Filtros
    col1, col2, col3 = st.columns(3)
    with col1:
        filter_activity = st.selectbox(
            "Filtrar por actividad",
            ["Todas"] + state['activities'],
            key="filter_activity"
        )
    with col2:
        available_projects = ["Todos"] + [p['name'] for p in state['projects']]
        if filter_activity != "Todas":
            available_projects = ["Todos"] + [p['name'] for p in state['projects'] if p['activity'] == filter_activity]
        
        filter_project = st.selectbox(
            "Filtrar por proyecto",
            available_projects,
            key="filter_project"
        )
    with col3:
        task_status = st.radio(
            "Estado",
            ["Todas", "Pendientes", "Completadas"],
            horizontal=True,
            key="task_status"
        )
    
    # Aplicar filtros y mostrar tareas
    display_filtered_tasks(filter_activity, filter_project, task_status)

# ==============================================
# Pestaña de Logros
# ==============================================

def show_achievements():
    """Muestra la pestaña de logros"""
    state = st.session_state.pomodoro_state
    achievements = state['achievements']
    
    st.subheader("🏆 Logros y Estadísticas")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Pomodoros Completados", achievements['pomodoros_completed'])
    
    with col2:
        st.metric("Tareas Completadas", achievements['tasks_completed'])
    
    with col3:
        st.metric("Días de Racha", achievements['streak_days'])
    
    with col4:
        st.metric("Horas Totales", f"{achievements['total_hours']:.1f}")

# ==============================================
# Pestaña de Configuración
# ==============================================

def settings_tab():
    """Muestra la pestaña de configuración"""
    state = st.session_state.pomodoro_state
    
    st.title("⚙️ Configuración")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("⏱️ Configuración de Tiempos")
        work_min = st.number_input("Tiempo Pomodoro (min)", min_value=15, max_value=90, 
                                 value=state['work_duration'] // 60, key="work_duration")
        short_min = st.number_input("Descanso Corto (min)", min_value=1, max_value=30, 
                                  value=state['short_break'] // 60, key="short_break")
        long_min = st.number_input("Descanso Largo (min)", min_value=5, max_value=60, 
                                 value=state['long_break'] // 60, key="long_break")
        sessions_long = st.number_input("Sesiones antes de descanso largo", min_value=1, 
                                      max_value=10, value=state['sessions_before_long'], 
                                      key="sessions_long")
        total_sess = st.number_input("Sesiones totales planificadas", min_value=1, 
                                   max_value=20, value=state['total_sessions'], 
                                   key="total_sessions")

        if st.button("Aplicar Configuración", key="apply_settings"):
            # Actualizar el tiempo restante si estamos en la fase correspondiente
            if state['current_phase'] == "Trabajo":
                state['remaining_time'] = work_min * 60
            elif state['current_phase'] == "Descanso Corto":
                state['remaining_time'] = short_min * 60
            elif state['current_phase'] == "Descanso Largo":
                state['remaining_time'] = long_min * 60
                
            state['work_duration'] = work_min * 60
            state['short_break'] = short_min * 60
            state['long_break'] = long_min * 60
            state['sessions_before_long'] = sessions_long
            state['total_sessions'] = total_sess
            st.success("Configuración aplicada!")
            st.rerun()

    with col2:
        st.subheader("🎨 Personalización")
        theme = st.selectbox("Tema", list(THEMES.keys()), 
                           index=list(THEMES.keys()).index(state['current_theme']), 
                           key="theme_select")
        if theme != state['current_theme']:
            state['current_theme'] = theme
            st.success("Tema cambiado!")
            st.rerun()

        st.subheader("📝 Gestión de Actividades")
        new_activity = st.text_input("Nueva actividad", key="new_activity")
        if st.button("Añadir actividad", key="add_activity"):
            if new_activity and new_activity not in state['activities']:
                state['activities'].append(new_activity)
                st.success("Actividad añadida!")
                st.rerun()

        if state['activities']:
            activity_to_remove = st.selectbox("Seleccionar actividad a eliminar", 
                                            state['activities'], 
                                            key="remove_activity")
            if st.button("Eliminar actividad", key="remove_activity_btn"):
                state['activities'].remove(activity_to_remove)
                st.success("Actividad eliminada!")
                st.rerun()

    st.subheader("📂 Gestión de Datos")

    col1, col2 = st.columns(2)

    with col1:
        st.write("Exportar Datos")
        export_data()

    with col2:
        st.write("Importar Datos")
        uploaded_file = st.file_uploader("Subir archivo de backup", 
                                       type=['json.gz'], 
                                       key="upload_backup")
        if uploaded_file is not None:
            import_data(uploaded_file)

    st.subheader("🛠️ Herramientas Avanzadas")
    if st.button("🔄 Reiniciar Datos", key="reset_data"):
        state['activities'] = []
        state['tasks'] = []
        state['completed_tasks'] = []
        state['study_goals'] = []
        state['projects'] = []
        state['session_history'] = []
        st.success("Datos reiniciados (excepto configuración)")
        st.rerun()

# ==============================================
# Pestaña Acerca de
# ==============================================

def about_tab():
    """Muestra la pestaña acerca de"""
    st.title("🍅 Acerca de Pomodoro Pro")
    
    st.markdown("""
    ### ¿Qué es la Técnica Pomodoro?
    La Técnica Pomodoro es un método de gestión del tiempo desarrollado por Francesco Cirillo a finales de los años 1980.
    Esta técnica utiliza un temporizador para dividir el trabajo en intervalos, tradicionalmente de 25 minutos de duración,
    separados por breves descansos.

    ### Características de Pomodoro Pro
    - 🕒 Temporizador configurable con intervalos personalizados
    - 📊 Seguimiento detallado de tu productividad
    - 📝 Gestión de tareas y proyectos
    - 🎓 Modo estudio con objetivos específicos
    - 🎨 Múltiples temas visuales
    - 📈 Estadísticas y análisis de tu rendimiento

    ### Cómo usar esta aplicación
    1. Configura tus tiempos preferidos en la pestaña de Configuración
    2. Selecciona una actividad y proyecto
    3. Inicia el temporizador y concéntrate en tu tarea
    4. Toma descansos según las indicaciones
    5. Revisa tus estadísticas para mejorar tu productividad
    """)
    
    st.info("""
    Nota: Esta aplicación almacena tus datos en la sesión actual del navegador.
    Para conservar tus datos entre sesiones, exporta tus datos regularmente.
    """)

# ==============================================
# Pestaña de Información
# ==============================================

def info_tab():
    """Muestra la pestaña de información"""
    st.title("ℹ️ Información y Ayuda")

    tab1, tab2, tab3 = st.tabs(["Instrucciones", "FAQ", "Contacto"])

    with tab1:
        st.header("Instrucciones de Uso")
        st.subheader("Configuración Inicial")
        st.markdown("""
        1. Ve a la pestaña Configuración en la barra lateral
        2. Ajusta los tiempos según tus preferencias
        3. Selecciona un tema visual de tu preferencia
        """)

        st.subheader("Uso del Temporizador")
        st.markdown("""
        1. Selecciona una actividad y proyecto (opcional)
        2. Haz clic en **Iniciar** para comenzar la sesión
        3. Concéntrate en tu tarea hasta que suene la alarma
        4. Toma un descanso cuando se te indique
        """)

    with tab2:
        st.header("Preguntas Frecuentes")

        with st.expander("¿Cómo cambio la configuración de los tiempos?"):
            st.markdown("Ve a la pestaña **Configuración** y ajusta los valores según tus preferencias.")

        with st.expander("¿Cómo veo mis estadísticas?"):
            st.markdown("Ve a la pestaña **Estadísticas** para ver gráficos y análisis de tu productividad.")

    with tab3:
        st.header("Contacto y Soporte")
        st.markdown("""
        ### ¿Necesitas ayuda?
        Si tienes problemas con la aplicación o sugerencias para mejorarla,
        por favor contáctanos a través de los siguientes medios:

        - 📧 Email: soporte@pomodoropro.com
        - 🐛 Reportar un error: [GitHub Issues](https://github.com/tu-usuario/pomodoro-pro/issues)

        ### Versión
        Estás usando la versión 1.0.0 de Pomodoro Pro
        """)

# ==============================================
# Barra lateral
# ==============================================

def check_alerts():
    """Verifica y muestra alertas importantes en la barra lateral"""
    state = st.session_state.pomodoro_state
    alerts = []
    today = date.today()
    
    # 1. Verificar tareas próximas a vencer (hoy o próximos 3 días)
    for task in state.get('tasks', []):
        if not task.get('completed', False):
            deadline = task.get('deadline')
            
            # Si no hay fecha límite, saltar esta tarea
            if deadline is None:
                continue
                
            # Convertir a date si es string (ajusta el formato según tus datos)
            if isinstance(deadline, str):
                try:
                    # Intentar parsear con diferentes formatos
                    try:
                        deadline = datetime.datetime.strptime(deadline, "%Y-%m-%d").date()
                    except ValueError:
                        # Intentar otro formato si el primero falla
                        deadline = datetime.datetime.strptime(deadline, "%d/%m/%Y").date()
                except ValueError:
                    # Si no se puede parsear, saltar esta tarea
                    continue
            elif isinstance(deadline, datetime.datetime):
                deadline = deadline.date()
            elif not isinstance(deadline, date):
                continue
                
            days_remaining = (deadline - today).days
            
            if days_remaining == 0:
                alerts.append(f"⏰ Hoy: {task.get('name', 'Tarea sin nombre')}")
            elif 0 < days_remaining <= 3:
                alerts.append(f"⚠️ En {days_remaining}d: {task.get('name', 'Tarea sin nombre')}")
            elif days_remaining < 0:
                alerts.append(f"❌ Vencida hace {-days_remaining}d: {task.get('name', 'Tarea sin nombre')}")
    
    # Mostrar alertas si las hay
    if alerts:
        st.sidebar.subheader("🔔 Alertas")
        for alert in alerts:
            st.sidebar.warning(alert)

def sidebar():
    """Muestra la barra lateral con navegación y controles"""
    # Mostrar sección de autenticación
    auth_section()
    
    if not check_authentication():
        return
    
    state = st.session_state.pomodoro_state

    with st.sidebar:
        st.title("Pomodoro Pro 🍅")
        
        # Navegación por pestañas
        st.subheader("Navegación")
        tabs = st.radio("Selecciona una sección:", 
                       ["🍅 Temporizador", "📊 Estadísticas", "📋 Tareas", 
                        "🏆 Logros", "⚙️ Configuración", "ℹ️ Info"],
                       key='sidebar_nav')

        # Mostrar alertas
        check_alerts()

        # Características de estudio
        st.subheader("🎓 Modo Estudio")
        state['study_mode'] = st.checkbox("Activar modo estudio", 
                                        value=state['study_mode'], 
                                        key="study_mode")
        
        # Gestión de datos en la nube
        st.subheader("☁️ Datos en la Nube")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Guardar", key="save_cloud"):
                save_to_supabase()
        
        with col2:
            if st.button("📂 Cargar", key="load_cloud"):
                if load_from_supabase():
                    st.rerun()
        
        # Cerrar sesión
        st.divider()
        if st.button("🚪 Cerrar Sesión", key="logout"):
            st.session_state.authenticated = False
            st.session_state.username = None
            st.session_state.pomodoro_state = get_default_state()
            st.success("Sesión cerrada exitosamente")
            st.rerun()

# ==============================================
# Función principal
# ==============================================

def main():
    """Función principal de la aplicación"""
    # Inicializar el estado si no existe
    if 'pomodoro_state' not in st.session_state:
        st.session_state.pomodoro_state = get_default_state()
    
    # Barra lateral
    sidebar()
    
    # Verificar autenticación - si no está autenticado, no mostrar el contenido principal
    if not check_authentication():
        st.warning("Por favor inicia sesión o regístrate para acceder a Pomodoro Pro")
        return

    # Obtener la pestaña seleccionada
    if 'sidebar_nav' not in st.session_state:
        st.session_state.sidebar_nav = "🍅 Temporizador"
    
    selected_tab = st.session_state.sidebar_nav

    # Mostrar la pestaña correspondiente
    if selected_tab == "🍅 Temporizador":
        timer_tab()
    elif selected_tab == "📊 Estadísticas":
        stats_tab()
    elif selected_tab == "📋 Tareas":
        tasks_tab()
    elif selected_tab == "🏆 Logros":
        show_achievements()
    elif selected_tab == "⚙️ Configuración":
        settings_tab()
    elif selected_tab == "ℹ️ Info":
        # Pestañas dentro de Info
        tab1, tab2 = st.tabs(["Acerca de", "Información y Ayuda"])
        with tab1:
            about_tab()
        with tab2:
            info_tab()

# ==============================================
# Ejecución de la aplicación
# ==============================================

if __name__ == "__main__":
    main()
