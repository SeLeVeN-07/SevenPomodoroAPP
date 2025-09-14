# -*- coding: utf-8 -*-
"""
Pomodoro Pro - Streamlit Cloud Version con Supabase y todas las características
Versión Mejorada con Dashboard estilo Tkinter Designer y todas las funcionalidades
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
import os
import logging
from typing import Dict, List, Any, Optional
from uuid import uuid4
import sys, shutil

# Configuración de logging
logging.basicConfig(
    filename='pomodoro_app.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Configuración de Supabase (usa variables de entorno para seguridad)
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://zgvptomznuswsipfihho.supabase.co")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "tu_anon_key")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "tu_service_key")

# Inicializar cliente de Supabase para operaciones normales
@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# Cliente especial para operaciones que necesitan bypass RLS (como registro)
@st.cache_resource
def init_supabase_service():
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

supabase = init_supabase()
supabase_service = init_supabase_service()

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
        'bg': '#2A2F4F',  # Cambiado para coincidir con el diseño
        'fg': '#FFFFFF', 
        'circle_bg': '#917FB3',  # Color de fondos de gráficos
        'text': '#E5BEEC',  # Color de texto similar al header
        'button_bg': '#E5BEEC',  # Color del header
        'button_fg': '#000000',
        'frame_bg': '#2A2F4F',
        'canvas_bg': '#2A2F4F', 
        'progress': '#E5BEEC',
        'border': '#917FB3',
        'highlight': '#E5BEEC',
        'chart1': '#E5BEEC',
        'chart2': '#D9FFCA',  # Color de porcentajes positivos
        'grid': '#917FB3'
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

SCHEMA_VERSION = 3  # Actualizado por las nuevas características

# ==============================================
# Funciones de inicialización y utilidades (Mejoradas)
# ==============================================

def get_default_state():
    """Devuelve el estado por defecto de la aplicación con todas las nuevas características"""
    return {
        # Configuración del temporizador
        'work_duration': 25 * 60,
        'short_break': 5 * 60,
        'long_break': 15 * 60,
        'sessions_before_long': 4,
        'total_sessions': 8,
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
        
        # Configuración general
        'current_theme': 'Oscuro',
        'activities': ['Estudio', 'Trabajo', 'Personal', 'Ejercicio'],
        'current_activity': 'Estudio',
        'tags': ['Urgente', 'Importante', 'Normal', 'Baja prioridad'],
        'tasks': [],
        'completed_tasks': [],
        'projects': [],
        'current_project': "",
        'current_task': "",
        'achievements': {
            'pomodoros_completed': 0,
            'tasks_completed': 0,
            'streak_days': 0,
            'total_hours': 0,
            'weekly_goal_progress': 0,
            'badges': []
        },
        'last_session_date': None,
        'session_history': [],
        'settings': {
            'notifications': True,
            'sound_enabled': True,
            'auto_save': True,
            'high_contrast': False,
            'power_saving': False
        },
        'goals': {
            'weekly_hours': 20,
            'daily_tasks': 5
        },
        'filter_activity': "Todas",
        'filter_project': "Todos",
        'task_status_filter': "Todas",
        'filter_tags': [],
        'sort_by': 'Fecha creación',
        'sort_ascending': False,
        'last_updated': time.time(),
        'force_rerun': False,
        
        # Nuevas características
        'templates': [],
        'reward_coins': 0,
        'rewards': [
            {
                'id': 'lofi_background',
                'name': 'Fondo Lofi',
                'description': 'Desbloquea un fondo de pantalla con estilo Lofi',
                'cost': 10,
                'icon': '🎵'
            },
            {
                'id': 'custom_theme',
                'name': 'Tema Personalizado',
                'description': 'Desbloquea la capacidad de personalizar colores',
                'cost': 20,
                'icon': '🎨'
            },
            {
                'id': 'premium_sounds',
                'name': 'Sonidos Premium',
                'description': 'Paquete de sonidos premium para notificaciones',
                'cost': 15,
                'icon': '🔔'
            }
        ],
        'unlocked_rewards': [],
        'backup_settings': {
            'enabled': True,
            'frequency': 24,  # horas
            'retention': 7,   # días
            'last_backup': None
        },
        'total_planned_sessions': 35,
        'total_planned_tasks': 0
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
        return state['work_duration']

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
        try:
            if re.match(r'^\d{4}-\d{2}-\d{2}$', obj):
                return datetime.datetime.strptime(obj, '%Y-%m-%d').date()
            elif re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', obj):
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

def migrate_state_dict(state: dict):
    """
    Asegura compatibilidad de esquema:
    - Añade 'id' a tasks y completed_tasks si falta
    - Asegura 'completed' y 'created'/'completed_date'
    - Deriva 'current_task_id' desde 'current_task' si falta
    - Marca 'schema_version'
    - Añade campos para nuevas características
    """
    changed = False

    # Asegurar listas
    if 'tasks' not in state or not isinstance(state.get('tasks'), list):
        state['tasks'] = []
        changed = True
    if 'completed_tasks' not in state or not isinstance(state.get('completed_tasks'), list):
        state['completed_tasks'] = []
        changed = True

    # IDs para tasks
    seen_ids = set()
    for t in state['tasks']:
        if not t.get('id'):
            t['id'] = uuid4().hex
            changed = True
        if t['id'] in seen_ids:
            t['id'] = uuid4().hex
            changed = True
        seen_ids.add(t['id'])

        if 'completed' not in t:
            t['completed'] = False
            changed = True
        
        # Asegurar que created_date sea string
        if 'created_date' in t and not isinstance(t['created_date'], str):
            if isinstance(t['created_date'], (date, datetime.datetime)):
                t['created_date'] = t['created_date'].isoformat()
                changed = True
        
        # Asegurar que deadline sea string
        if 'deadline' in t and not isinstance(t['deadline'], str):
            if isinstance(t['deadline'], (date, datetime.datetime)):
                t['deadline'] = t['deadline'].isoformat()
                changed = True

    # IDs para completed_tasks
    seen_done_ids = set()
    for t in state['completed_tasks']:
        if not t.get('id'):
            t['id'] = uuid4().hex
            changed = True
        if t['id'] in seen_done_ids or t['id'] in seen_ids:
            t['id'] = uuid4().hex
            changed = True
        seen_done_ids.add(t['id'])

        if 'completed' not in t:
            t['completed'] = True
            changed = True
        
        # Asegurar que completed_date sea string
        if 'completed_date' in t and not isinstance(t['completed_date'], str):
            if isinstance(t['completed_date'], (date, datetime.datetime)):
                t['completed_date'] = t['completed_date'].isoformat()
                changed = True
        
        # Asegurar que created_date sea string
        if 'created_date' in t and not isinstance(t['created_date'], str):
            if isinstance(t['created_date'], (date, datetime.datetime)):
                t['created_date'] = t['created_date'].isoformat()
                changed = True
        
        # Asegurar que deadline sea string
        if 'deadline' in t and not isinstance(t['deadline'], str):
            if isinstance(t['deadline'], (date, datetime.datetime)):
                t['deadline'] = t['deadline'].isoformat()
                changed = True
            
        # Añadir campos para nuevas características si no existen
        if 'estimated_hours' not in t:
            t['estimated_hours'] = 0
            changed = True
        if 'actual_hours' not in t:
            t['actual_hours'] = 0
            changed = True
        if 'status' not in t:
            t['status'] = 'Por hacer'
            changed = True
        if 'subtasks' not in t:
            t['subtasks'] = []
            changed = True
            
     # Convertir fechas a formato string ISO
    for t in state['tasks'] + state['completed_tasks']:
        if 'created_date' in t and isinstance(t['created_date'], date):
            t['created_date'] = t['created_date'].isoformat()
        
        if 'completed_date' in t and isinstance(t['completed_date'], date):
            t['completed_date'] = t['completed_date'].isoformat()
        
        if 'deadline' in t and isinstance(t['deadline'], date):
            t['deadline'] = t['deadline'].isoformat()

    # IDs para completed_tasks
    seen_done_ids = set()
    for t in state['completed_tasks']:
        if not t.get('id'):
            t['id'] = uuid4().hex
            changed = True
        if t['id'] in seen_done_ids or t['id'] in seen_ids:
            t['id'] = uuid4().hex
            changed = True
        seen_done_ids.add(t['id'])

        if 'completed' not in t:
            t['completed'] = True
            changed = True
        if not t.get('completed_date'):
            t['completed_date'] = date.today().isoformat()
            changed = True

    # current_task_id desde current_task (si aplica)
    if 'current_task_id' not in state and state.get('current_task'):
        name = state.get('current_task')
        project = state.get('current_project')
        matches = [
            t for t in state['tasks']
            if t.get('name') == name and (not project or t.get('project') == project)
        ]
        if matches:
            state['current_task_id'] = matches[0]['id']
            changed = True

    # Añadir nuevas características si no existen
    if 'templates' not in state:
        state['templates'] = []
        changed = True
        
    if 'reward_coins' not in state:
        state['reward_coins'] = 0
        changed = True
        
    if 'rewards' not in state:
        state['rewards'] = [
            {
                'id': 'lofi_background',
                'name': 'Fondo Lofi',
                'description': 'Desbloquea un fondo de pantalla con estilo Lofi',
                'cost': 10,
                'icon': '🎵'
            },
            {
                'id': 'custom_theme',
                'name': 'Tema Personalizado',
                'description': 'Desbloquea la capacidad de personalizar colores',
                'cost': 20,
                'icon': '🎨'
            },
            {
                'id': 'premium_sounds',
                'name': 'Sonidos Premium',
                'description': 'Paquete de sonidos premium para notificaciones',
                'cost': 15,
                'icon': '🔔'
            }
        ]
        changed = True
        
    if 'unlocked_rewards' not in state:
        state['unlocked_rewards'] = []
        changed = True
        
    if 'backup_settings' not in state:
        state['backup_settings'] = {
            'enabled': True,
            'frequency': 24,  # horas
            'retention': 7,   # días
            'last_backup': None
        }
        changed = True
        
    if 'total_planned_sessions' not in state:
        state['total_planned_sessions'] = 35
        changed = True
        
    if 'total_planned_tasks' not in state:
        state['total_planned_tasks'] = 0
        changed = True

    # Asegurar que achievements tenga badges
    if 'achievements' not in state:
        state['achievements'] = {
            'pomodoros_completed': 0,
            'tasks_completed': 0,
            'streak_days': 0,
            'total_hours': 0,
            'weekly_goal_progress': 0,
            'badges': []
        }
        changed = True
    elif 'badges' not in state['achievements']:
        state['achievements']['badges'] = []
        changed = True

    # Versionado
    if state.get('schema_version') != SCHEMA_VERSION:
        state['schema_version'] = SCHEMA_VERSION
        changed = True

    return state, changed

# ==============================================
# Funciones de autenticación y seguridad (Mejoradas)
# ==============================================

def hash_password(password):
    """Hashea la contraseña usando SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(username, password):
    """Registra un nuevo usuario en Supabase usando service role key"""
    try:
        # Verificar si el usuario ya existe usando el cliente de servicio
        response = supabase_service.table('users').select('username').eq('username', username).execute()
        
        if response.data:
            return False, "El nombre de usuario ya existe"
        
        # Crear nuevo usuario con data inicializada
        hashed_pw = hash_password(password)
        default_state = convert_dates_to_iso(get_default_state())
        
        response = supabase_service.table('users').insert({
            'username': username,
            'password_hash': hashed_pw,
            'data': default_state
        }).execute()
        
        return True, "Usuario registrado exitosamente"
    except Exception as e:
        return False, f"Error al registrar usuario: {str(e)}"

def login_user(username, password):
    """Autentica un usuario (versión corregida)"""
    try:
        # Usar el cliente de servicio para bypass RLS
        response = supabase_service.table('users') \
            .select('*') \
            .eq('username', username) \
            .execute()
        
        if not response.data:
            return False, "Usuario no encontrado"
            
        user = response.data[0]
        hashed_pw = hash_password(password)
        
        if user['password_hash'] == hashed_pw:
            st.session_state.authenticated = True
            st.session_state.username = username
            return True, "Inicio de sesión exitoso"
        return False, "Contraseña incorrecta"
    except Exception as e:
        return False, f"Error al iniciar sesión: {str(e)}"

def check_authentication():
    """Verifica si el usuario está autenticado"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'username' not in st.session_state:
        st.session_state.username = None
    return st.session_state.authenticated

def auth_section():
    """Muestra la sección de autenticación"""
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
                            st.session_state.force_rerun = True
                        else:
                            st.error(message)
            
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
                                st.session_state.force_rerun = True
                            else:
                                st.error(message)

# ==============================================
# Funciones de importación/exportación con Supabase (Mejoradas)
# ==============================================

def save_to_supabase():
    if not check_authentication():
        st.error("Debes iniciar sesión para guardar datos")
        return False
    
    try:
        # Usar el estado actual directamente, sin copia
        state = st.session_state.pomodoro_state
        username = st.session_state.username
        
        # Convertir el estado actual a formato ISO
        data_to_save = convert_dates_to_iso(state)
        
        # Usar UPDATE en lugar de UPSERT para no afectar password_hash
        response = supabase_service.table('users').update({
            'data': data_to_save,
            'last_updated': datetime.datetime.now().isoformat()
        }).eq('username', username).execute()
        
        st.success("Datos guardados correctamente!")
        return True
    except Exception as e:
        st.error(f"Error al guardar: {str(e)}")
        return False

def load_from_supabase():
    """Carga datos desde Supabase"""
    if not check_authentication():
        st.error("Debes iniciar sesión para cargar datos")
        return False
    
    try:
        username = st.session_state.username
        
        # Usar cliente de servicio para bypass RLS
        response = supabase_service.table('users') \
            .select('data') \
            .eq('username', username) \
            .execute()
        
        if not response.data:
            st.warning("No se encontraron datos para este usuario")
            return False
            
        imported_data = convert_iso_to_dates(response.data[0]['data'])
        
        # Migración de esquema
        imported_data, changed = migrate_state_dict(imported_data)
        
        # Actualiza el estado completo
        for key, value in imported_data.items():
            st.session_state.pomodoro_state[key] = value
        
        st.success("Datos cargados correctamente!")
        return True
    except Exception as e:
        st.warning(f"No se encontraron datos o error: {str(e)}")
        return False

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
            'notifications': state['settings']['notifications'],
            'sound_enabled': state['settings']['sound_enabled'],
            'auto_save': state['settings']['auto_save'],
            'high_contrast': state['settings']['high_contrast'],
            'power_saving': state['settings']['power_saving']
        },
        'goals': state['goals'],
        'timer_settings': {
            'work_duration': state['work_duration'],
            'short_break': state['short_break'],
            'long_break': state['long_break'],
            'sessions_before_long': state['sessions_before_long'],
            'total_sessions': state['total_sessions']
        },
        'templates': state['templates'],
        'reward_coins': state['reward_coins'],
        'rewards': state['rewards'],
        'unlocked_rewards': state['unlocked_rewards']
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
        
        # Migrar el diccionario importado
        imported_data, _ = migrate_state_dict(imported_data)
        
        # Actualizar estado
        state = st.session_state.pomodoro_state
        
        # Puede venir en formato "export_dict" (con timer_settings) o como estado completo
        state['activities'] = imported_data.get('activities', [])
        state['tasks'] = imported_data.get('tasks', [])
        state['completed_tasks'] = imported_data.get('completed_tasks', [])
        state['projects'] = imported_data.get('projects', [])
        state['achievements'] = imported_data.get('achievements', state['achievements'])
        state['session_history'] = imported_data.get('session_history', [])
        state['settings'] = imported_data.get('settings', state['settings'])
        state['goals'] = imported_data.get('goals', state['goals'])
        state['templates'] = imported_data.get('templates', [])
        state['reward_coins'] = imported_data.get('reward_coins', 0)
        state['rewards'] = imported_data.get('rewards', state['rewards'])
        state['unlocked_rewards'] = imported_data.get('unlocked_rewards', [])

        timer_settings = imported_data.get('timer_settings', None)
        if timer_settings is not None:
            # Import desde backup exportado
            state['work_duration'] = timer_settings.get('work_duration', 25*60)
            state['short_break'] = timer_settings.get('short_break', 5*60)
            state['long_break'] = timer_settings.get('long_break', 15*60)
            state['sessions_before_long'] = timer_settings.get('sessions_before_long', 4)
            state['total_sessions'] = timer_settings.get('total_sessions', 8)
        else:
            # Import de estado completo
            state['work_duration'] = imported_data.get('work_duration', state.get('work_duration', 25*60))
            state['short_break'] = imported_data.get('short_break', state.get('short_break', 5*60))
            state['long_break'] = imported_data.get('long_break', state.get('long_break', 15*60))
            state['sessions_before_long'] = imported_data.get('sessions_before_long', state.get('sessions_before_long', 4))
            state['total_sessions'] = imported_data.get('total_sessions', state.get('total_sessions', 8))

        # Asegura la compatibilidad final ya en session_state (current_task_id, etc.)
        st.session_state.pomodoro_state, _ = migrate_state_dict(st.session_state.pomodoro_state)

        st.success("Datos importados correctamente!")
        st.session_state.force_rerun = True
    except Exception as e:
        st.error(f"Error al importar datos: {str(e)}")

def backup_data():
    """Crea una copia de seguridad adicional"""
    try:
        # Exportar datos a un archivo temporal
        state = st.session_state.pomodoro_state.copy()
        export_dict = {
            'activities': state['activities'],
            'tasks': state['tasks'],
            'completed_tasks': state['completed_tasks'],
            'projects': state['projects'],
            'achievements': state['achievements'],
            'session_history': state['session_history'],
            'settings': state['settings'],
            'goals': state['goals'],
            'timer_settings': {
                'work_duration': state['work_duration'],
                'short_break': state['short_break'],
                'long_break': state['long_break'],
                'sessions_before_long': state['sessions_before_long'],
                'total_sessions': state['total_sessions']
            },
            'templates': state['templates'],
            'reward_coins': state['reward_coins'],
            'rewards': state['rewards'],
            'unlocked_rewards': state['unlocked_rewards']
        }
        
        export_dict = convert_dates_to_iso(export_dict)
        json_str = json.dumps(export_dict, indent=2, ensure_ascii=False, default=json_serial)
        
        backup_name = f"backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(backup_name, "w", encoding="utf-8") as f:
            f.write(json_str)
            
        logging.info(f"Copia de seguridad creada: {backup_name}")
        return True
    except Exception as e:
        logging.error(f"Error al crear backup: {str(e)}")
        return False

def setup_automatic_backups():
    """Configuración de backups automáticos rotativos"""
    state = st.session_state.pomodoro_state
    
    # Verificar si es necesario hacer backup
    if state['backup_settings']['enabled']:
        now = time.time()
        last_backup = state['backup_settings']['last_backup']
        
        if last_backup is None or now - last_backup >= state['backup_settings']['frequency'] * 3600:
            # Hacer backup
            if backup_data():
                state['backup_settings']['last_backup'] = now
                
                # Limpiar backups antiguos
                cleanup_old_backups(state['backup_settings']['retention'])
                
                logging.info("Backup automático completado")
            else:
                logging.error("Error en backup automático")

def cleanup_old_backups(retention_days):
    """Eliminar backups más antiguos que retention_days"""
    backup_dir = "."
    backup_pattern = re.compile(r"backup_\d{8}_\d{6}\.json")
    
    for filename in os.listdir(backup_dir):
        if backup_pattern.match(filename):
            file_path = os.path.join(backup_dir, filename)
            file_time = os.path.getmtime(file_path)
            
            if time.time() - file_time > retention_days * 24 * 3600:
                try:
                    os.remove(file_path)
                    logging.info(f"Eliminado backup antiguo: {filename}")
                except Exception as e:
                    logging.error(f"Error eliminando backup {filename}: {e}")

# ==============================================
# Funciones de registro de sesiones (Mejoradas)
# ==============================================

def log_session():
    """Registra una sesión completada en el historial"""
    state = st.session_state.pomodoro_state
    if state['total_active_time'] >= 0.1:
        # Convertir a horas
        hours = round(state['total_active_time'] / 3600, 2)
        log_entry = {
            'Fecha': datetime.datetime.now().strftime("%Y-%m-%d"),
            'Hora Inicio': state['start_time'].strftime("%H:%M:%S") if state['start_time'] else datetime.datetime.now().strftime("%H:%M:%S"),
            'Tiempo Activo (horas)': hours,
            'Actividad': state['current_activity'],
            'Proyecto': state['current_project'],
            'Tarea': state.get('current_task', '')
        }
        
        # Guardar en el historial de sesiones
        state['session_history'].append(log_entry)
        
        # Actualizar logros
        if state['current_phase'] == "Trabajo":
            state['achievements']['pomodoros_completed'] += 1
            state['achievements']['total_hours'] += hours
            
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
        
        # Ganar monedas por completar sesión
        earn_coins(1, "completar sesión")
        
        # Verificar logros
        setup_achievements()
        
        # Guardar cambios en Supabase
        save_to_supabase()

def play_alarm_sound():
    """Reproduce un sonido de alarma usando HTML5 audio"""
    try:
        # Crear el elemento de audio HTML
        sound_html = """
        <audio autoplay>
            <source src="https://assets.mixkit.co/sfx/preview/mixkit-bell-notification-933.mp3" type="audio/mp3">
        </audio>
        """
        st.components.v1.html(sound_html, height=0)
    except Exception as e:
        st.error(f"Error al reproducir el sonido: {str(e)}")

def on_close():
    """Función que se ejecuta al cerrar la aplicación"""
    # Verificar si el timer estaba corriendo y si hay un start_time válido
    state = st.session_state.pomodoro_state
    if state['timer_running'] and state['start_time'] is not None:
        # Calcular el tiempo activo hasta el momento de cierre
        current_elapsed = time.time() - state['start_time'].timestamp()
        state['total_active_time'] += current_elapsed
    
    # Solo registrar si fue fase de trabajo y hay tiempo acumulado
    if state['current_phase'] == "Trabajo" and state['total_active_time'] >= 0.1:
        log_session()
    
    # Guardar el estado en Supabase
    save_to_supabase()

# ==============================================
# Funciones de UI y Utilidades
# ==============================================

def apply_theme():
    """Aplica el tema seleccionado a la aplicación"""
    state = st.session_state.pomodoro_state
    theme = THEMES[state['current_theme']]
    
    st.markdown(f"""
    <style>
    .stApp {{
        background-color: {theme['bg']};
        color: {theme['fg']};
    }}
    .css-1d391kg, .css-1y4p8pa {{
        background-color: {theme['secondary_bg']};
    }}
    .css-1v0mbdj {{
        color: {theme['text']};
    }}
    .stButton>button {{
        background-color: {theme['button_bg']};
        color: {theme['button_fg']};
        border: none;
        border-radius: 5px;
        padding: 0.5rem 1rem;
    }}
    .stButton>button:hover {{
        background-color: {theme['button_bg']};
        opacity: 0.8;
    }}
    .card {{
        background-color: {theme['card_bg']};
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 5px solid {theme['button_bg']};
        margin-bottom: 1rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }}
    </style>
    """, unsafe_allow_html=True)

def show_toast(message, icon="✅"):
    """Muestra una notificación toast"""
    st.toast(f"{icon} {message}")

def setup_responsive_design():
    """Configura diseño responsivo"""
    st.markdown("""
    <style>
    @media (max-width: 768px) {
        .block-container {
            padding: 1rem;
        }
        .stButton button {
            width: 100%;
        }
        .card {
            padding: 1rem;
        }
    }
    </style>
    """, unsafe_allow_html=True)

def setup_high_contrast_mode():
    """Aplica modo de alto contraste si está habilitado"""
    state = st.session_state.pomodoro_state
    if state['settings']['high_contrast']:
        st.markdown("""
        <style>
        .stApp {
            filter: contrast(1.5);
        }
        .card {
            border: 2px solid #ffffff;
        }
        </style>
        """, unsafe_allow_html=True)

# ==============================================
# Funciones de gestión de tareas
# ==============================================

def create_task(name, project, activity, priority, deadline, tags=None, description="", estimated_hours=0):
    """Crea una nueva tarea"""
    if tags is None:
        tags = []
    
    return {
        'id': hashlib.md5(f"{name}{project}{datetime.datetime.now()}".encode()).hexdigest()[:8],
        'name': name,
        'project': project,
        'activity': activity,
        'priority': priority,
        'deadline': deadline,
        'tags': tags,
        'description': description,
        'estimated_hours': estimated_hours,
        'actual_hours': 0,
        'status': 'Por hacer',
        'subtasks': [],
        'completed': False,
        'created_date': date.today(),
        'completed_date': None
    }

def complete_task(task_id):
    """Marca una tarea como completada"""
    state = st.session_state.pomodoro_state
    
    for i, task in enumerate(state['tasks']):
        if task['id'] == task_id:
            task['completed'] = True
            task['completed_date'] = date.today().isoformat()  # Guardar como string ISO
            completed_task = state['tasks'].pop(i)
            state['completed_tasks'].append(completed_task)
            state['achievements']['tasks_completed'] += 1
            
            # Ganar monedas por completar tarea
            earn_coins(2, "completar tarea")
            
            # Verificar si se alcanza el objetivo diario
            today_str = date.today().isoformat()
            today_completed = sum(1 for t in state['completed_tasks'] 
                                if t.get('completed_date') == today_str)
            
            if today_completed >= state['goals']['daily_tasks']:
                show_toast("🎉 ¡Objetivo diario alcanzado!")
            
            show_toast(f"Tarea '{task['name']}' completada")
            logging.info(f"Tarea completada: {task['name']}")
            
            # Verificar logros
            setup_achievements()
            
            save_to_supabase()
            return True
    
    return False

def edit_task(task_id, **kwargs):
    """Edita una tarea existente"""
    state = st.session_state.pomodoro_state
    all_tasks = state['tasks'] + state['completed_tasks']
    
    for task in all_tasks:
        if task['id'] == task_id:
            for key, value in kwargs.items():
                if key in task:
                    task[key] = value
            show_toast(f"Tarea '{task['name']}' actualizada")
            logging.info(f"Tarea actualizada: {task['name']}")
            save_to_supabase()
            return True
    
    return False

def delete_task(task_id):
    """Elimina una tarea"""
    state = st.session_state.pomodoro_state
    
    for i, task in enumerate(state['tasks']):
        if task['id'] == task_id:
            deleted_task = state['tasks'].pop(i)
            show_toast(f"Tarea '{deleted_task['name']}' eliminada")
            logging.info(f"Tarea eliminada: {deleted_task['name']}")
            save_to_supabase()
            return True
    
    for i, task in enumerate(state['completed_tasks']):
        if task['id'] == task_id:
            deleted_task = state['completed_tasks'].pop(i)
            show_toast(f"Tarea '{deleted_task['name']}' eliminada")
            logging.info(f"Tarea eliminada: {deleted_task['name']}")
            save_to_supabase()
            return True
    
    return False

# ==============================================
# Funciones de filtrado y ordenación
# ==============================================

def filter_tasks(activity_filter="Todas", project_filter="Todos", 
                 status_filter="Todas", tag_filters=None, search_text=""):
    """Filtra tareas según múltiples criterios"""
    if tag_filters is None:
        tag_filters = []
    
    state = st.session_state.pomodoro_state
    filtered_tasks = []
    all_tasks = state['tasks'] + state['completed_tasks']
    
    for task in all_tasks:
        # Asegurar que todas las tareas tengan created_date
        if 'created_date' not in task:
            task['created_date'] = date.today()
            
        # Filtrar por actividad
        if activity_filter != "Todas" and task.get('activity') != activity_filter:
            continue
            
        # Filtrar por proyecto
        if project_filter != "Todos" and task['project'] != project_filter:
            continue
            
        # Filtrar por estado
        if status_filter == "Pendientes" and task['completed']:
            continue
        if status_filter == "Completadas" and not task['completed']:
            continue
            
        # Filtrar por etiquetas
        if tag_filters and not any(tag in task.get('tags', []) for tag in tag_filters):
            continue
            
        # Filtrar por texto de búsqueda
        if search_text and search_text.lower() not in task['name'].lower():
            if search_text.lower() not in task.get('description', '').lower():
                continue
        
        filtered_tasks.append(task)
    
    # Ordenar tareas
    sort_by = state.get('sort_by', 'Fecha creación')
    ascending = state.get('sort_ascending', False)
    
    if sort_by == 'Fecha creación':
        # Convertir a date para comparación si es necesario
        def get_created_date(task):
            created = task['created_date']
            if isinstance(created, str):
                return parse_date(created) or date.today()
            return created
        
        filtered_tasks.sort(key=lambda x: get_created_date(x), reverse=not ascending)
    elif sort_by == 'Prioridad':
        priority_order = {'Urgente': 0, 'Alta': 1, 'Media': 2, 'Baja': 3}
        filtered_tasks.sort(key=lambda x: priority_order.get(x['priority'], 4), reverse=ascending)
    elif sort_by == 'Fecha límite':
        # Convertir a date para comparación si es necesario
        def get_deadline(task):
            deadline = task.get('deadline')
            if not deadline:
                return date.max  # Las sin fecha van al final
            if isinstance(deadline, str):
                return parse_date(deadline) or date.max
            return deadline
        
        filtered_tasks.sort(key=lambda x: get_deadline(x), reverse=not ascending)
    elif sort_by == 'Nombre':
        filtered_tasks.sort(key=lambda x: x['name'].lower(), reverse=ascending)
    elif sort_by == 'Focus Score':
        # Calcular focus score para cada tarea
        for task in filtered_tasks:
            # Urgencia basada en días hasta el deadline
            if task.get('deadline'):
                try:
                    deadline_date = parse_date(task['deadline'])
                    if deadline_date:
                        days_until_deadline = (deadline_date - date.today()).days
                        task['urgency'] = max(0, 10 - days_until_deadline) / 10  # 0-1 scale
                    else:
                        task['urgency'] = 0.3
                except:
                    task['urgency'] = 0.3
            else:
                task['urgency'] = 0.3  # Valor por defecto para tareas sin deadline
            
            # Importancia basada en prioridad
            priority_values = {"Urgente": 1.0, "Alta": 0.8, "Media": 0.5, "Baja": 0.3}
            task['importance'] = priority_values.get(task.get('priority', 'Media'), 0.5)
            
            # Calcular Focus Score
            task['focus_score'] = task['importance'] * task['urgency']
            if task.get('deadline'):
                try:
                    deadline_date = parse_date(task['deadline'])
                    if deadline_date:
                        days_until_deadline = (deadline_date - date.today()).days
                        task['focus_score'] *= max(1, 10 - days_until_deadline) / 10
                except:
                    pass
        
        filtered_tasks.sort(key=lambda x: x.get('focus_score', 0), reverse=not ascending)
    
    return filtered_tasks

def parse_date(date_value):
    """
    Convierte una fecha a objeto date independientemente de su formato original.
    Acepta: string (YYYY-MM-DD), datetime.date, o datetime.datetime
    """
    if isinstance(date_value, str):
        try:
            return datetime.datetime.strptime(date_value, "%Y-%m-%d").date()
        except ValueError:
            try:
                # Intentar otros formatos comunes si es necesario
                return datetime.datetime.fromisoformat(date_value.replace('Z', '+00:00')).date()
            except (ValueError, AttributeError):
                return None
    elif isinstance(date_value, datetime.datetime):
        return date_value.date()
    elif isinstance(date_value, datetime.date):
        return date_value
    return None

# ==============================================
# Funciones de análisis y visualización
# ==============================================

@st.cache_data(ttl=300)
def analyze_data():
    """Analiza los datos para dashboards y estadísticas"""
    state = st.session_state.pomodoro_state
    
    data = {
        'activities': defaultdict(float),
        'projects': defaultdict(float),
        'tags': defaultdict(float),
        'daily_total': defaultdict(float),
        'raw_data': [],
        'completed_by_day': defaultdict(int),
        'priority_stats': defaultdict(int)
    }
    
    # Procesar sesiones de trabajo
    for session in state['session_history']:
        try:
            fecha = session['Fecha']
            # Usar parse_date para manejar cualquier formato
            date_obj = parse_date(fecha)
            if not date_obj:
                continue
                
            fecha_str = date_obj.strftime("%Y-%m-%d")
            duration = session.get('Tiempo Activo (horas)', 0)
            activity = session.get('Actividad', '')
            project = session.get('Proyecto', '')
            
            data['activities'][activity] += duration
            if project:
                data['projects'][project] += duration
            data['daily_total'][fecha_str] += duration
            
            data['raw_data'].append({
                'date': date_obj, 
                'duration': duration, 
                'activity': activity,
                'project': project
            })
        except Exception as e:
            logging.error(f"Error procesando sesión: {e}")
    
    # Procesar tareas completadas
    for task in state['completed_tasks']:
        try:
            completed_date = task.get('completed_date')
            if completed_date:
                comp_date = parse_date(completed_date)
                if not comp_date:
                    continue
                    
                date_str = comp_date.strftime("%Y-%m-%d")
                data['completed_by_day'][date_str] += 1
                
                # Estadísticas de prioridad
                data['priority_stats'][task['priority']] += 1
                
                # Estadísticas de etiquetas
                for tag in task.get('tags', []):
                    data['tags'][tag] += 1
        except Exception as e:
            logging.error(f"Error procesando tarea completada: {e}")
    
    return data

def create_metric_cards():
    """Crea tarjetas de métricas para el dashboard"""
    state = st.session_state.pomodoro_state
    data = analyze_data()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_hours = sum(data['activities'].values())
        st.metric("Horas Totales", f"{total_hours:.1f}h")
    
    with col2:
        total_tasks = state['achievements']['tasks_completed']
        st.metric("Tareas Completadas", total_tasks)
    
    with col3:
        total_pomodoros = state['achievements']['pomodoros_completed']
        st.metric("Pomodoros Completados", total_pomodoros)
    
    with col4:
        streak = state['achievements']['streak_days']
        st.metric("Días Consecutivos", streak)

def create_dashboard_charts():
    """Crea gráficos para el dashboard"""
    data = analyze_data()
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Gráfico de tiempo por actividad
        if data['activities']:
            activities_df = pd.DataFrame({
                'Actividad': list(data['activities'].keys()),
                'Horas': list(data['activities'].values())
            })
            fig = px.pie(activities_df, values='Horas', names='Actividad', 
                        title="Distribución por Actividad")
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Gráfico de tareas completadas por día
        if data['completed_by_day']:
            dates = sorted(data['completed_by_day'].keys())
            counts = [data['completed_by_day'][date] for date in dates]
            
            fig = px.bar(x=dates, y=counts, 
                        title="Tareas Completadas por Día",
                        labels={'x': 'Fecha', 'y': 'Tareas Completadas'})
            st.plotly_chart(fig, use_container_width=True)
    
    # Gráfico de evolución temporal
    if data['daily_total']:
        dates = sorted(data['daily_total'].keys())
        hours = [data['daily_total'][date] for date in dates]
        
        fig = px.area(x=dates, y=hours, 
                     title="Evolución de Horas por Día",
                     labels={'x': 'Fecha', 'y': 'Horas'})
        st.plotly_chart(fig, use_container_width=True)

# ==============================================
# Nuevas implementaciones: Gestión de tareas potente
# ==============================================

def kanban_view():
    """Vista Kanban para gestionar tareas por estados"""
    state = st.session_state.pomodoro_state
    
    # Definir estados para el Kanban
    statuses = ["Por hacer", "En progreso", "En revisión", "Completada"]
    
    # Filtrar tareas no completadas para el Kanban
    pending_tasks = [t for t in state['tasks'] if not t['completed']]
    
    # Crear columnas para cada estado
    cols = st.columns(len(statuses))
    
    for idx, status in enumerate(statuses):
        with cols[idx]:
            st.subheader(status)
            
            # Tareas para este estado
            status_tasks = [t for t in pending_tasks if t.get('status', 'Por hacer') == status]
            
            for task in status_tasks:
                with st.container(border=True):
                    st.write(f"**{task['name']}**")
                    st.caption(f"Proyecto: {task.get('project', 'Ninguno')}")
                    
                    # Mostrar fecha límite si existe
                    if task.get('deadline'):
                        try:
                            deadline_date = parse_date(task['deadline'])
                            if deadline_date:
                                days_left = (deadline_date - date.today()).days
                                color = "red" if days_left < 3 else "orange" if days_left < 7 else "green"
                                st.markdown(f"<span style='color: {color};'>Vence en {days_left} días</span>", 
                                           unsafe_allow_html=True)
                        except Exception as e:
                            logging.error(f"Error mostrando deadline para tarea {task.get('name')}: {e}")
                            st.caption("Fecha límite inválida")
                    
                    # Selector para cambiar estado
                    new_status = st.selectbox(
                        "Cambiar estado",
                        statuses,
                        index=statuses.index(task.get('status', 'Por hacer')),
                        key=f"status_{task['id']}",
                        label_visibility="collapsed"
                    )
                    
                    if new_status != task.get('status', 'Por hacer'):
                        task['status'] = new_status
                        save_to_supabase()
                        st.rerun()
                        
def calendar_view():
    """Vista de calendario para ver deadlines"""
    state = st.session_state.pomodoro_state
    
    # Obtener todas las tareas con deadlines
    all_tasks = state['tasks'] + state['completed_tasks']
    tasks_with_deadlines = [t for t in all_tasks if t.get('deadline')]
    
    if not tasks_with_deadlines:
        st.info("No hay tareas con fechas límite")
        return
    
    # Crear DataFrame para el calendario
    calendar_data = []
    for task in tasks_with_deadlines:
        calendar_data.append({
            'Tarea': task['name'],
            'Fecha': task['deadline'],
            'Proyecto': task.get('project', 'Ninguno'),
            'Estado': 'Completada' if task['completed'] else 'Pendiente'
        })
    
    df = pd.DataFrame(calendar_data)
    
    # Mostrar calendario con plotly
    fig = px.timeline(
        df, 
        x_start="Fecha", 
        x_end="Fecha", 
        y="Proyecto", 
        color="Estado",
        hover_name="Tarea",
        title="Calendario de Tareas"
    )
    
    fig.update_yaxes(autorange="reversed")
    st.plotly_chart(fig, use_container_width=True)

def add_subtasks_to_task(task):
    """Añade subtareas a una tarea existente"""
    if 'subtasks' not in task:
        task['subtasks'] = []
    
    st.subheader("Subtareas")
    
    # Añadir nueva subtarea
    new_subtask = st.text_input("Nueva subtarea", key=f"new_subtask_{task['id']}")
    if st.button("➕ Añadir", key=f"add_subtask_{task['id']}") and new_subtask:
        task['subtasks'].append({
            'id': str(uuid4()),
            'description': new_subtask,
            'completed': False
        })
        save_to_supabase()
        st.rerun()
    
    # Mostrar subtareas existentes
    for i, subtask in enumerate(task['subtasks']):
        col1, col2 = st.columns([1, 10])
        with col1:
            completed = st.checkbox(
                "", 
                value=subtask['completed'],
                key=f"subtask_check_{subtask['id']}"
            )
            if completed != subtask['completed']:
                subtask['completed'] = completed
                save_to_supabase()
        
        with col2:
            st.write(subtask['description'])
        
        if st.button("🗑️", key=f"delete_subtask_{subtask['id']}"):
            task['subtasks'].pop(i)
            save_to_supabase()
            st.rerun()

def task_templates():
    """Sistema de plantillas de tareas"""
    state = st.session_state.pomodoro_state
    
    st.subheader("📋 Plantillas de Tareas")
    
    # Crear nueva plantilla
    with st.expander("➕ Crear Nueva Plantilla"):
        template_name = st.text_input("Nombre de plantilla")
        template_tasks = st.text_area("Tareas (una por línea)")
        
        if st.button("Guardar Plantilla") and template_name and template_tasks:
            state['templates'].append({
                'name': template_name,
                'tasks': [task.strip() for task in template_tasks.split('\n') if task.strip()]
            })
            save_to_supabase()
            st.success("Plantilla guardada")
    
    # Usar plantilla existente
    if state['templates']:
        st.subheader("Usar Plantilla")
        template_names = [t['name'] for t in state['templates']]
        selected_template = st.selectbox("Seleccionar plantilla", template_names)
        
        if selected_template:
            template = next(t for t in state['templates'] if t['name'] == selected_template)
            st.write("Tareas en esta plantilla:")
            for task in template['tasks']:
                st.write(f"- {task}")
            
            if st.button("Aplicar Plantilla"):
                for task_desc in template['tasks']:
                    new_task = create_task(
                        name=task_desc,
                        project=state['current_project'],
                        activity=state['current_activity'],
                        priority="Media",
                        deadline=date.today() + timedelta(days=7)
                    )
                    state['tasks'].append(new_task)
                
                save_to_supabase()
                st.success(f"Plantilla '{selected_template}' aplicada")

def eisenhower_matrix():
    """Matriz de Eisenhower para priorización de tareas"""
    state = st.session_state.pomodoro_state
    
    # Filtrar tareas no completadas
    pending_tasks = [t for t in state['tasks'] if not t['completed']]
    
    # Calcular urgencia e importancia para cada tarea
    for task in pending_tasks:
        # Urgencia basada en días hasta el deadline
        if task.get('deadline'):
            days_until_deadline = (task['deadline'] - date.today()).days
            task['urgency'] = max(0, 10 - days_until_deadline) / 10  # 0-1 scale
        else:
            task['urgency'] = 0.3  # Valor por defecto para tareas sin deadline
        
        # Importancia basada en prioridad
        priority_values = {"Urgente": 1.0, "Alta": 0.8, "Media": 0.5, "Baja": 0.3}
        task['importance'] = priority_values.get(task.get('priority', 'Media'), 0.5)
        
        # Calcular Focus Score
        task['focus_score'] = task['importance'] * task['urgency']
        if task.get('deadline'):
            days_until_deadline = (task['deadline'] - date.today()).days
            task['focus_score'] *= max(1, 10 - days_until_deadline) / 10
    
    # Clasificar tareas en la matriz de Eisenhower
    quadrants = {
        "Urgente e Importante": [t for t in pending_tasks if t['urgency'] > 0.7 and t['importance'] > 0.7],
        "Importante no Urgente": [t for t in pending_tasks if t['urgency'] <= 0.7 and t['importance'] > 0.7],
        "Urgente no Importante": [t for t in pending_tasks if t['urgency'] > 0.7 and t['importance'] <= 0.7],
        "Ni Urgente ni Importante": [t for t in pending_tasks if t['urgency'] <= 0.7 and t['importance'] <= 0.7]
    }
    
    # Mostrar la matriz
    st.subheader("Matrix de Eisenhower")
    
    cols = st.columns(2)
    quadrant_names = list(quadrants.keys())
    
    for i, col in enumerate(cols):
        with col:
            for j in range(2):
                quadrant_idx = i * 2 + j
                if quadrant_idx < len(quadrant_names):
                    quadrant_name = quadrant_names[quadrant_idx]
                    tasks = quadrants[quadrant_name]
                    
                    with st.expander(f"{quadrant_name} ({len(tasks)})", expanded=quadrant_idx==0):
                        for task in sorted(tasks, key=lambda x: x['focus_score'], reverse=True):
                            st.write(f"**{task['name']}**")
                            st.caption(f"Proyecto: {task.get('project', 'Ninguno')}")
                            st.caption(f"Focus Score: {task['focus_score']:.2f}")
                            
                            if task.get('deadline'):
                                days_left = (task['deadline'] - date.today()).days
                                st.caption(f"Vence en {days_left} días")
                            
                            if st.button("Seleccionar", key=f"select_{task['id']}"):
                                state['current_task'] = task['name']
                                state['current_project'] = task.get('project', 'Ninguno')
                                st.session_state.sidebar_nav = "🍅 Temporizador"
                                st.rerun()

def focus_recommendation():
    """Recomendación de tarea focus basada en el focus score"""
    state = st.session_state.pomodoro_state
    
    # Filtrar tareas no completadas
    pending_tasks = [t for t in state['tasks'] if not t['completed']]
    
    if not pending_tasks:
        return None
    
    # Calcular focus score para cada tarea
    for task in pending_tasks:
        # Urgencia basada en días hasta el deadline
        if task.get('deadline'):
            try:
                deadline_date = parse_date(task['deadline'])
                if deadline_date:
                    days_until_deadline = (deadline_date - date.today()).days
                    task['urgency'] = max(0, 10 - days_until_deadline) / 10  # 0-1 scale
                else:
                    task['urgency'] = 0.3
            except Exception as e:
                logging.error(f"Error calculando urgencia para tarea {task.get('name')}: {e}")
                task['urgency'] = 0.3
        else:
            task['urgency'] = 0.3  # Valor por defecto para tareas sin deadline
        
        # Importancia basada en prioridad
        priority_values = {"Urgente": 1.0, "Alta": 0.8, "Media": 0.5, "Baja": 0.3}
        task['importance'] = priority_values.get(task.get('priority', 'Media'), 0.5)
        
        # Calcular Focus Score
        task['focus_score'] = task['importance'] * task['urgency']
        if task.get('deadline'):
            try:
                deadline_date = parse_date(task['deadline'])
                if deadline_date:
                    days_until_deadline = (deadline_date - date.today()).days
                    task['focus_score'] *= max(1, 10 - days_until_deadline) / 10
            except Exception as e:
                logging.error(f"Error calculando focus score para tarea {task.get('name')}: {e}")
    
    # Encontrar la tarea con mayor focus score
    focus_task = max(pending_tasks, key=lambda x: x.get('focus_score', 0))
    return focus_task

def time_tracking():
    """Seguimiento de tiempo estimado vs real"""
    state = st.session_state.pomodoro_state
    
    st.subheader("⏱️ Seguimiento de Tiempo")
    
    # Calcular horas reales desde el historial de sesiones
    for task in state['tasks'] + state['completed_tasks']:
        task_name = task['name']
        task_project = task.get('project', 'Ninguno')
        
        # Sumar horas de sesiones que coinciden con esta tarea
        task_sessions = [
            s for s in state['session_history'] 
            if s.get('Tarea') == task_name and s.get('Proyecto') == task_project
        ]
        
        task['actual_hours'] = sum(s.get('Tiempo Activo (horas)', 0) for s in task_sessions)
    
    # Mostrar comparación
    comparison_data = []
    for task in state['tasks']:
        if task['estimated_hours'] > 0:
            variance = task['actual_hours'] - task['estimated_hours']
            variance_percent = (variance / task['estimated_hours']) * 100 if task['estimated_hours'] > 0 else 0
            
            comparison_data.append({
                'Tarea': task['name'],
                'Proyecto': task.get('project', 'Ninguno'),
                'Estimado (h)': task['estimated_hours'],
                'Real (h)': task['actual_hours'],
                'Desviación (h)': variance,
                'Desviación (%)': variance_percent
            })
    
    if comparison_data:
        df = pd.DataFrame(comparison_data)
        
        # Añadir colores según la desviación
        def color_variance(val):
            color = 'red' if val > 20 else 'orange' if val > 10 else 'green' if val <= 10 else 'black'
            return f'color: {color}'
        
        styled_df = df.style.applymap(color_variance, subset=['Desviación (%)'])
        st.dataframe(styled_df, use_container_width=True)
        
        # Gráfico de desviaciones
        fig = px.bar(
            df, 
            x='Tarea', 
            y='Desviación (%)',
            color='Desviación (%)',
            color_continuous_scale=['red', 'orange', 'green'],
            title='Desviación en Tiempo de Ejecución'
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No hay datos de estimación vs real para mostrar")
        
# ==============================================
# Nuevas implementaciones: Hábitos y gamificación
# ==============================================

def setup_achievements():
    """Configuración del sistema de logros"""
    state = st.session_state.pomodoro_state
    
    # Logros disponibles
    available_badges = [
        {
            'id': 'first_pomodoro',
            'name': 'Primer Pomodoro',
            'description': 'Completa tu primera sesión de trabajo',
            'icon': '🍅',
            'condition': lambda: state['achievements']['pomodoros_completed'] >= 1
        },
        {
            'id': 'pomodoro_50',
            'name': '50 Pomodoros',
            'description': 'Completa 50 sesiones de trabajo',
            'icon': '🔥',
            'condition': lambda: state['achievements']['pomodoros_completed'] >= 50
        },
        {
            'id': 'perfect_week',
            'name': 'Semana Perfecta',
            'description': 'Completa todas las sesiones planificadas en una semana',
            'icon': '⭐',
            'condition': check_perfect_week
        },
        {
            'id': 'no_procrastination',
            'name': 'Sin Procrastinación',
            'description': 'Completa una tarea urgente sin posponerla',
            'icon': '⚡',
            'condition': check_no_procrastination
        }
    ]
    
    # Verificar y otorgar logros
    for badge in available_badges:
        if badge['id'] not in [b['id'] for b in state['achievements']['badges']]:
            if badge['condition']():
                state['achievements']['badges'].append({
                    'id': badge['id'],
                    'name': badge['name'],
                    'description': badge['description'],
                    'icon': badge['icon'],
                    'earned_date': datetime.datetime.now()
                })
                show_toast(f"¡Logro desbloqueado: {badge['icon']} {badge['name']}!")

def check_perfect_week():
    """Verificar si se completó una semana perfecta"""
    state = st.session_state.pomodoro_state
    
    # Obtener sesiones de la última semana
    one_week_ago = datetime.datetime.now() - timedelta(days=7)
    recent_sessions = [
        s for s in state['session_history'] 
        if datetime.datetime.strptime(s['Fecha'], "%Y-%m-%d") >= one_week_ago
    ]
    
    # Verificar si se completaron todas las sesiones planificadas
    planned_sessions = state.get('weekly_goal_sessions', 35)  # Valor por defecto
    return len(recent_sessions) >= planned_sessions

def check_no_procrastination():
    """Verificar si se completó una tarea urgente sin posponerla"""
    # Esta implementación sería más compleja y requeriría
    # seguimiento de cuándo se crearon las tareas urgentes vs cuándo se completaron
    return False  # Placeholder

def show_achievements():
    """Mostrar logros obtenidos"""
    state = st.session_state.pomodoro_state
    
    st.subheader("🏆 Logros")
    
    if not state['achievements']['badges']:
        st.info("Aún no has desbloqueado logros. ¡Sigue trabajando!")
        return
    
    # Mostrar logros obtenidos
    cols = st.columns(3)
    for i, badge in enumerate(state['achievements']['badges']):
        with cols[i % 3]:
            with st.container(border=True):
                st.markdown(f"### {badge['icon']} {badge['name']}")
                st.caption(badge['description'])
                if badge.get('earned_date'):
                    st.caption(f"Obtenido: {badge['earned_date'].strftime('%Y-%m-%d')}")

def earn_coins(amount, reason):
    """Ganar monedas de recompensa"""
    state = st.session_state.pomodoro_state
    state['reward_coins'] += amount
    show_toast(f"+{amount} monedas por {reason}!")
    save_to_supabase()

def rewards_shop():
    """Tienda de recompensas"""
    state = st.session_state.pomodoro_state
    
    st.subheader("🪙 Tienda de Recompensas")
    st.write(f"Monedas disponibles: **{state['reward_coins']}**")
    
    # Mostrar recompensas disponibles
    for reward in state['rewards']:
        if reward['id'] not in state['unlocked_rewards']:
            with st.container(border=True):
                col1, col2 = st.columns([1, 3])
                
                with col1:
                    st.markdown(f"## {reward['icon']}")
                
                with col2:
                    st.write(f"**{reward['name']}**")
                    st.caption(reward['description'])
                    st.write(f"Costo: {reward['cost']} monedas")
                    
                    if st.button("Canjear", key=f"buy_{reward['id']}"):
                        if state['reward_coins'] >= reward['cost']:
                            state['reward_coins'] -= reward['cost']
                            state['unlocked_rewards'].append(reward['id'])
                            show_toast(f"¡Has canjeado {reward['name']}!")
                            save_to_supabase()
                            st.rerun()
                        else:
                            st.error("No tienes suficientes monedas")

# ==============================================
# Nuevas implementaciones: Analítica que empuja a la acción
# ==============================================

def generate_weekly_report():
    """Generar informe semanal automático"""
    state = st.session_state.pomodoro_state
    
    # Obtener datos de la última semana
    one_week_ago = datetime.datetime.now() - timedelta(days=7)
    
    recent_sessions = []
    for session in state['session_history']:
        try:
            # Usar la función parse_date para manejar cualquier formato
            session_date = parse_date(session['Fecha'])
            if session_date and session_date >= one_week_ago.date():
                recent_sessions.append(session)
        except Exception as e:
            logging.error(f"Error procesando sesión en reporte semanal: {e}")
            continue
    
    recent_completed_tasks = []
    for task in state['completed_tasks']:
        try:
            completed_date = task.get('completed_date')
            if completed_date:
                comp_date = parse_date(completed_date)
                if comp_date and comp_date >= one_week_ago.date():
                    recent_completed_tasks.append(task)
        except Exception as e:
            logging.error(f"Error procesando tarea completada en reporte semanal: {e}")
            continue
    
    # Calcular métricas
    total_hours = sum(s.get('Tiempo Activo (horas)', 0) for s in recent_sessions)
    total_tasks = len(recent_completed_tasks)
    
    # Proyectos principales
    project_hours = {}
    for session in recent_sessions:
        project = session.get('Proyecto', 'Sin proyecto')
        project_hours[project] = project_hours.get(project, 0) + session.get('Tiempo Activo (horas)', 0)
    
    top_projects = sorted(project_hours.items(), key=lambda x: x[1], reverse=True)[:3]
    
    # Tareas clave completadas
    key_tasks = [t for t in recent_completed_tasks if t.get('priority') in ['Alta', 'Urgente']][:5]
    
    # Próximos deadlines - CORREGIDO: usar parse_date para comparar fechas
    upcoming_deadlines = []
    for task in state['tasks']:
        if not task['completed'] and task.get('deadline'):
            try:
                deadline_date = parse_date(task['deadline'])
                if deadline_date and deadline_date <= date.today() + timedelta(days=7):
                    upcoming_deadlines.append(task)
            except Exception as e:
                logging.error(f"Error procesando deadline para tarea {task.get('name')}: {e}")
                continue
    
    upcoming_deadlines.sort(key=lambda x: parse_date(x.get('deadline')) or date.max)
    
    # Generar reporte
    report = {
        'periodo': f"{one_week_ago.strftime('%Y-%m-%d')} a {datetime.datetime.now().strftime('%Y-%m-%d')}",
        'total_horas': total_hours,
        'total_tareas': total_tasks,
        'proyectos_principales': top_projects,
        'tareas_clave': key_tasks,
        'proximos_deadlines': upcoming_deadlines,
        'dias_racha': state['achievements']['streak_days']
    }
    
    return report

def show_weekly_report():
    """Mostrar informe semanal"""
    report = generate_weekly_report()
    
    st.subheader("📊 Informe Semanal")
    
    # Métricas principales
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Horas trabajadas", f"{report['total_horas']:.1f}h")
    with col2:
        st.metric("Tareas completadas", report['total_tareas'])
    with col3:
        st.metric("Días de racha", report['dias_racha'])
    
    # Proyectos principales
    st.subheader("📈 Proyectos Principales")
    if report['proyectos_principales']:
        for project, hours in report['proyectos_principales']:
            st.write(f"- **{project}**: {hours:.1f}h")
    else:
        st.info("No hay datos de proyectos esta semana")
    
    # Tareas clave completadas
    st.subheader("✅ Tareas Clave Completadas")
    if report['tareas_clave']:
        for task in report['tareas_clave']:
            st.write(f"- **{task['name']}** ({task.get('priority', 'Sin prioridad')})")
    else:
        st.info("No se completaron tareas clave esta semana")
    
    # Próximos deadlines - CORREGIDO: usar parse_date para calcular días restantes
    st.subheader("📅 Próximos Deadlines")
    if report['proximos_deadlines']:
        for task in report['proximos_deadlines']:
            try:
                # Convertir el deadline a objeto date para calcular días restantes
                deadline_date = parse_date(task['deadline'])
                if deadline_date:
                    days_left = (deadline_date - date.today()).days
                    color = "red" if days_left < 3 else "orange" if days_left < 7 else "green"
                    st.markdown(f"- **{task['name']}**: {task['deadline']} (<span style='color: {color};'>{days_left} días</span>)", 
                               unsafe_allow_html=True)
                else:
                    st.write(f"- **{task['name']}**: {task['deadline']} (Fecha inválida)")
            except Exception as e:
                logging.error(f"Error calculando días restantes para tarea {task.get('name')}: {e}")
                st.write(f"- **{task['name']}**: {task['deadline']} (Error en fecha)")
    else:
        st.info("No hay deadlines próximos")
    
    # Botón para exportar
    if st.button("Exportar Reporte"):
        # Convertir reporte a JSON y ofrecer descarga
        report_json = json.dumps(report, indent=2, default=str)
        b64 = base64.b64encode(report_json.encode()).decode()
        href = f'<a href="data:application/json;base64,{b64}" download="reporte_semanal.json">📥 Descargar reporte</a>'
        st.markdown(href, unsafe_allow_html=True)
        
def productivity_heatmap():
    """Heatmap de productividad 7x24"""
    state = st.session_state.pomodoro_state
    
    if not state['session_history']:
        st.info("No hay datos suficientes para generar el heatmap")
        return
    
    # Preparar datos para el heatmap
    heatmap_data = np.zeros((7, 24))  # 7 días, 24 horas
    
    for session in state['session_history']:
        try:
            # Obtener día de la semana y hora de la sesión
            session_date = datetime.datetime.strptime(session['Fecha'], "%Y-%m-%d")
            day_of_week = session_date.weekday()  # 0=Lunes, 6=Domingo
            start_time = datetime.datetime.strptime(session['Hora Inicio'], "%H:%M:%S")
            hour_of_day = start_time.hour
            
            # Sumar horas a la celda correspondiente
            heatmap_data[day_of_week][hour_of_day] += session.get('Tiempo Activo (horas)', 0)
        except:
            continue
    
    # Crear heatmap
    days = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
    hours = [f"{h:02d}:00" for h in range(24)]
    
    fig = px.imshow(
        heatmap_data,
        labels=dict(x="Hora del día", y="Día de la semana", color="Horas"),
        x=hours,
        y=days,
        aspect="auto",
        color_continuous_scale='Viridis'
    )
    
    fig.update_layout(title="Heatmap de Productividad (7x24)")
    st.plotly_chart(fig, use_container_width=True)

def monthly_trends():
    """Tendencias mensuales de productividad"""
    state = st.session_state.pomodoro_state
    
    if not state['session_history']:
        st.info("No hay datos suficientes para mostrar tendencias")
        return
    
    # Agrupar sesiones por mes
    monthly_data = {}
    for session in state['session_history']:
        try:
            session_date = datetime.datetime.strptime(session['Fecha'], "%Y-%m-%d")
            month_key = session_date.strftime("%Y-%m")
            
            if month_key not in monthly_data:
                monthly_data[month_key] = {
                    'total_hours': 0,
                    'sessions': 0,
                    'tasks_completed': 0
                }
            
            monthly_data[month_key]['total_hours'] += session.get('Tiempo Activo (horas)', 0)
            monthly_data[month_key]['sessions'] += 1
        except:
            continue
    
    # Contar tareas completadas por mes
    for task in state['completed_tasks']:
        if task.get('completed_date'):
            if isinstance(task['completed_date'], str):
                completed_date = datetime.datetime.strptime(task['completed_date'], "%Y-%m-%d").date()
            else:
                completed_date = task['completed_date']
            
            month_key = completed_date.strftime("%Y-%m")
            if month_key in monthly_data:
                monthly_data[month_key]['tasks_completed'] += 1
    
    # Crear DataFrame para visualización
    months = sorted(monthly_data.keys())
    hours = [monthly_data[m]['total_hours'] for m in months]
    sessions = [monthly_data[m]['sessions'] for m in months]
    tasks = [monthly_data[m]['tasks_completed'] for m in months]
    
    # Gráfico de tendencias
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=months, y=hours, name='Horas', line=dict(color='blue')))
    fig.add_trace(go.Scatter(x=months, y=sessions, name='Sesiones', line=dict(color='green')))
    fig.add_trace(go.Scatter(x=months, y=tasks, name='Tareas', line=dict(color='orange')))
    
    fig.update_layout(
        title="Tendencias Mensuales de Productividad",
        xaxis_title="Mes",
        yaxis_title="Cantidad"
    )
    
    st.plotly_chart(fig, use_container_width=True)

def context_productivity():
    """Análisis de productividad por contexto"""
    state = st.session_state.pomodoro_state
    
    # Agrupar sesiones por actividad
    activity_hours = {}
    for session in state['session_history']:
        activity = session.get('Actividad', 'Sin actividad')
        activity_hours[activity] = activity_hours.get(activity, 0) + session.get('Tiempo Activo (horas)', 0)
    
    # Agrupar tareas completadas por actividad
    activity_tasks = {}
    for task in state['completed_tasks']:
        activity = task.get('activity', 'Sin actividad')
        activity_tasks[activity] = activity_tasks.get(activity, 0) + 1
    
    # Calcular eficiencia (tareas por hora)
    activity_efficiency = {}
    for activity in set(activity_hours.keys()) | set(activity_tasks.keys()):
        hours = activity_hours.get(activity, 0)
        tasks = activity_tasks.get(activity, 0)
        efficiency = tasks / hours if hours > 0 else 0
        activity_efficiency[activity] = efficiency
    
    # Mostrar resultados
    st.subheader("📊 Productividad por Contexto")
    
    # Gráfico de horas por actividad
    if activity_hours:
        activities = list(activity_hours.keys())
        hours = list(activity_hours.values())
        
        fig = px.pie(
            values=hours, 
            names=activities, 
            title="Distribución de Horas por Actividad"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Gráfico de eficiencia
    if activity_efficiency:
        efficient_activities = [a for a, e in activity_efficiency.items() if e > 0]
        efficiencies = [activity_efficiency[a] for a in efficient_activities]
        
        if efficient_activities:
            fig = px.bar(
                x=efficient_activities, 
                y=efficiencies,
                title="Eficiencia (Tareas por Hora) por Actividad",
                labels={'x': 'Actividad', 'y': 'Tareas por hora'}
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # Insights accionables
    st.subheader("💡 Insights Accionables")
    
    if activity_efficiency:
        # Encontrar la actividad más y menos eficiente
        most_efficient = max(activity_efficiency.items(), key=lambda x: x[1] if x[1] > 0 else -1)
        least_efficient = min(activity_efficiency.items(), key=lambda x: x[1] if x[1] > 0 else float('inf'))
        
        if most_efficient[1] > 0:
            st.write(f"**Eres más eficiente en '{most_efficient[0]}'**")
            st.write(f"- {most_efficient[1]:.2f} tareas por hora")
            st.write("- Considera dedicar más tiempo a esta actividad")
        
        if least_efficient[1] > 0 and least_efficient[0] != most_efficient[0]:
            st.write(f"**Eres menos eficiente en '{least_efficient[0]}'**")
            st.write(f"- {least_efficient[1]:.2f} tareas por hora")
            st.write("- Considera mejorar tus procesos o buscar capacitación")
    
    # Recomendación de redistribución de tiempo
    if activity_hours and activity_efficiency:
        st.write("**Recomendación de redistribución de tiempo:**")
        
        # Calcular horas ideales basadas en eficiencia
        total_hours = sum(activity_hours.values())
        efficient_activities = {a: e for a, e in activity_efficiency.items() if e > 0}
        
        if efficient_activities:
            total_efficiency = sum(efficient_activities.values())
            recommended_hours = {
                a: (e / total_efficiency) * total_hours 
                for a, e in efficient_activities.items()
            }
            
            for activity, hours in recommended_hours.items():
                current_hours = activity_hours.get(activity, 0)
                difference = hours - current_hours
                
                if abs(difference) > 1:  # Solo mostrar diferencias significativas
                    if difference > 0:
                        st.write(f"- Considera añadir {difference:.1f}h a '{activity}'")
                    else:
                        st.write(f"- Considera reducir {abs(difference):.1f}h de '{activity}'")
                        
def completion_ratio():
    """Ratio de cumplimiento de planificación"""
    state = st.session_state.pomodoro_state
    
    st.subheader("📈 Ratio de Cumplimiento")
    
    # Calcular ratio de pomodoros
    total_planned_sessions = state.get('total_planned_sessions', 0)
    completed_sessions = len(state['session_history'])
    
    if total_planned_sessions > 0:
        session_ratio = (completed_sessions / total_planned_sessions) * 100
    else:
        session_ratio = 0
    
    # Calcular ratio de tareas
    total_planned_tasks = state.get('total_planned_tasks', 0)
    completed_tasks = len(state['completed_tasks'])
    
    if total_planned_tasks > 0:
        task_ratio = (completed_tasks / total_planned_tasks) * 100
    else:
        task_ratio = 0
    
    # Mostrar métricas
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Sesiones completadas", f"{session_ratio:.1f}%", 
                 f"{completed_sessions}/{total_planned_sessions}")
    
    with col2:
        st.metric("Tareas completadas", f"{task_ratio:.1f}%", 
                 f"{completed_tasks}/{total_planned_tasks}")
    
    # Gráfico de ratios
    ratios = [session_ratio, task_ratio]
    labels = ['Sesiones', 'Tareas']
    
    fig = px.bar(
        x=labels, 
        y=ratios,
        title="Ratios de Cumplimiento",
        labels={'x': 'Métrica', 'y': 'Porcentaje de cumplimiento'},
        range_y=[0, 100]
    )
    
    # Añadir línea de objetivo (80%)
    fig.add_hline(y=80, line_dash="dash", line_color="green", annotation_text="Objetivo: 80%")
    
    # Colorear según el rendimiento
    colors = ['green' if r >= 80 else 'orange' if r >= 60 else 'red' for r in ratios]
    fig.update_traces(marker_color=colors)
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Recomendaciones basadas en el rendimiento
    st.subheader("💡 Recomendaciones")
    
    if session_ratio < 80:
        st.write("**Sesiones:** Tu ratio de cumplimiento de sesiones es bajo.")
        st.write("- Considera ajustar tu planificación semanal")
        st.write("- Revisa tus distractores y busca minimizarlos")
    
    if task_ratio < 80:
        st.write("**Tareas:** Tu ratio de cumplimiento de tareas es bajo.")
        st.write("- Revisa si estás estimando correctamente el tiempo requerido")
        st.write("- Considera desglosar tareas grandes en subtareas más manejables")
    
    if session_ratio >= 80 and task_ratio >= 80:
        st.write("¡Excelente rendimiento! Mantén este ritmo de productividad.")

# ==============================================
# Componentes de la UI
# ==============================================

def task_modal(task=None):
    """Modal para crear/editar tareas"""
    state = st.session_state.pomodoro_state
    
    is_edit = task is not None
    title = "✏️ Editar Tarea" if is_edit else "➕ Crear Nueva Tarea"
    
    with st.form(key="task_form", clear_on_submit=not is_edit):
        st.subheader(title)
        
        name = st.text_input("Nombre de la tarea", value=task['name'] if is_edit else "")
        
        col1, col2 = st.columns(2)
        with col1:
            activity = st.selectbox(
                "Actividad",
                state['activities'],
                index=state['activities'].index(task['activity']) if is_edit and task['activity'] in state['activities'] else 0
            )
        with col2:
            priority = st.selectbox(
                "Prioridad",
                ["Baja", "Media", "Alta", "Urgente"],
                index=["Baja", "Media", "Alta", "Urgente"].index(task['priority']) if is_edit else 1
            )
        
        # Proyectos para la actividad seleccionada
        activity_projects = [p for p in state['projects'] if p['activity'] == activity]
        project_options = [p['name'] for p in activity_projects] + ["Ninguno"]
        
        if is_edit and task['project'] not in project_options:
            project_options.append(task['project'])
        
        project = st.selectbox(
            "Proyecto",
            project_options,
            index=project_options.index(task['project']) if is_edit and task['project'] in project_options else len(project_options)-1
        )
        
        deadline = st.date_input(
            "Fecha límite",
            value=task['deadline'] if is_edit else date.today() + timedelta(days=7)
        )
        
        tags = st.multiselect(
            "Etiquetas",
            state['tags'],
            default=task.get('tags', []) if is_edit else []
        )
        
        description = st.text_area(
            "Descripción",
            value=task.get('description', "") if is_edit else "",
            height=100
        )
        
        estimated_hours = st.number_input(
            "Tiempo estimado (horas)",
            min_value=0.0,
            max_value=100.0,
            step=0.5,
            value=task.get('estimated_hours', 0) if is_edit else 0.0
        )
        
        status = st.selectbox(
            "Estado",
            ["Por hacer", "En progreso", "En revisión", "Completada"],
            index=["Por hacer", "En progreso", "En revisión", "Completada"].index(task.get('status', 'Por hacer')) if is_edit else 0
        )
        
        col1, col2 = st.columns(2)
        with col1:
            submit_button = st.form_submit_button("💾 Guardar")
        with col2:
            cancel_button = st.form_submit_button("❌ Cancelar")
        
        if submit_button:
            if not name:
                st.error("El nombre de la tarea es obligatorio")
                return
            
            task_data = {
                'name': name,
                'activity': activity,
                'project': project,
                'priority': priority,
                'deadline': deadline,
                'tags': tags,
                'description': description,
                'estimated_hours': estimated_hours,
                'status': status
            }
            
            if is_edit:
                edit_task(task['id'], **task_data)
            else:
                new_task = create_task(**task_data)
                state['tasks'].append(new_task)
                show_toast(f"Tarea '{name}' creada")
                logging.info(f"Nueva tarea creada: {name}")
            
            save_to_supabase()
            st.session_state.show_task_modal = False
            st.session_state.force_rerun = True
            
        if cancel_button:
            st.session_state.show_task_modal = False
            st.session_state.force_rerun = True
    
    # Añadir sección de subtareas si estamos editando
    if is_edit:
        add_subtasks_to_task(task)

def project_modal(project=None):
    """Modal para crear/editar proyectos"""
    state = st.session_state.pomodoro_state
    
    is_edit = project is not None
    title = "✏️ Editar Proyecto" if is_edit else "➕ Crear Nuevo Proyecto"
    
    with st.form(key="project_form", clear_on_submit=not is_edit):
        st.subheader(title)
        
        name = st.text_input("Nombre del proyecto", value=project['name'] if is_edit else "")
        activity = st.selectbox(
            "Actividad",
            state['activities'],
            index=state['activities'].index(project['activity']) if is_edit and project['activity'] in state['activities'] else 0
        )
        
        description = st.text_area(
            "Descripción",
            value=project.get('description', "") if is_edit else "",
            height=100
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("💾 Guardar"):
                if not name:
                    st.error("El nombre del proyecto es obligatorio")
                    return
                
                if is_edit:
                    # Actualizar proyecto existente
                    project['name'] = name
                    project['activity'] = activity
                    project['description'] = description
                    
                    # Actualizar tareas asociadas
                    for task in state['tasks'] + state['completed_tasks']:
                        if task['project'] == project['name']:
                            task['activity'] = activity
                    
                    show_toast(f"Proyecto '{name}' actualizado")
                    logging.info(f"Proyecto actualizado: {name}")
                else:
                    # Crear nuevo proyecto
                    new_project = {
                        'name': name,
                        'activity': activity,
                        'description': description,
                        'created_date': date.today()
                    }
                    state['projects'].append(new_project)
                    show_toast(f"Proyecto '{name}' creado")
                    logging.info(f"Nuevo proyecto creado: {name}")
                
                save_to_supabase()
                st.session_state.force_rerun = True
                
        with col2:
            if st.form_submit_button("❌ Cancelar"):
                st.session_state.force_rerun = True

# ==============================================
# Pestaña del Temporizador Pomodoro
# ==============================================

def timer_tab():
    """Pestaña del temporizador Pomodoro"""
    state = st.session_state.pomodoro_state
    
    st.title("🍅 Temporizador Pomodoro")
    
    # Inicializar variables de control del temporizador si no existen
    if state['timer_start'] is None:
        state['timer_start'] = None
    if state['last_update'] is None:
        state['last_update'] = None
    if state['paused_time'] is None:
        state['paused_time'] = None
    
    # Selector de actividad
    col1, col2 = st.columns(2)
    with col1:
        if not state['activities']:
            st.warning("No hay actividades disponibles. Agrega actividades en la pestaña de Configuración")
            state['current_activity'] = ""
        else:
            # Asegurar que current_activity esté en la lista de actividades
            if state['current_activity'] not in state['activities']:
                state['current_activity'] = state['activities'][0] if state['activities'] else ""

            state['current_activity'] = st.selectbox(
                "Actividad",
                state['activities'],
                index=state['activities'].index(state['current_activity']) if state['current_activity'] in state['activities'] else 0,
                key="timer_activity_selector"
            )

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
                save_to_supabase()
                st.session_state.force_rerun = True
            elif new_project_name in [p['name'] for p in state['projects']]:
                st.error("Ya existe un proyecto con ese nombre")

    # Selector de proyecto (solo proyectos asociados a la actividad actual)
    available_projects = [p['name'] for p in state['projects'] if p['activity'] == state['current_activity']]
    if available_projects:
        # Si el proyecto actual no está en la lista de disponibles, resetear a "Ninguno" o al primero
        if state['current_project'] not in available_projects:
            state['current_project'] = "Ninguno"

        # Encontrar el índice del proyecto actual en la lista de opciones (available_projects + ["Ninguno"])
        options = available_projects + ["Ninguno"]
        try:
            index = options.index(state['current_project'])
        except ValueError:
            index = 0

        state['current_project'] = st.selectbox(
            "Proyecto",
            options,
            index=index,
            key="timer_project_selector"
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
            # Asegurar que la tarea actual esté en la lista
            if 'current_task' not in state or state['current_task'] not in task_names:
                state['current_task'] = task_names[0] if task_names else ""

            options = ["-- Seleccionar --"] + task_names + ["+ Crear nueva tarea"]
            # Encontrar el índice de la tarea actual
            try:
                index = task_names.index(state['current_task']) + 1
            except ValueError:
                index = 0

            selected_task = st.selectbox(
                "Seleccionar tarea existente", 
                options,
                index=index,
                key="timer_task_selector"
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
                    save_to_supabase()
                    st.session_state.force_rerun = True
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
                save_to_supabase()
                st.session_state.force_rerun = True

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

    # Usar un contenedor para el gráfico que no force rerenderizados completos
    chart_placeholder = st.empty()
    chart_placeholder.plotly_chart(fig, use_container_width=True)

    # Controles del temporizador - ahora con 4 columnas para incluir el botón de reinicio
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("▶️ Iniciar" if not state['timer_running'] else "▶️ Reanudar",
                   use_container_width=True, type="primary", key="start_timer"):
            if not state['timer_running']:
                state['timer_running'] = True
                state['timer_paused'] = False
                state['start_time'] = datetime.datetime.now()
                state['total_active_time'] = 0
                # Iniciar el temporizador
                state['timer_start'] = time.time()
                state['last_update'] = time.time()
                save_to_supabase()
                st.session_state.force_rerun = True

    with col2:
        if st.button("⏸️ Pausar" if state['timer_running'] and not state['timer_paused'] else "▶️ Reanudar",
                   use_container_width=True, disabled=not state['timer_running'], key="pause_timer"):
            if state['timer_running'] and not state['timer_paused']:
                state['timer_paused'] = True
                state['paused_time'] = time.time()
                save_to_supabase()
                st.session_state.force_rerun = True
            elif state['timer_paused']:
                state['timer_paused'] = False
                # Ajustar el tiempo de inicio para compensar la pausa
                pause_duration = time.time() - state['paused_time']
                state['timer_start'] += pause_duration
                state['last_update'] = time.time()
                save_to_supabase()
                st.session_state.force_rerun = True

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
                    save_to_supabase()
                    st.session_state.force_rerun = True
            
            # Determinar siguiente fase
            state['current_phase'] = determine_next_phase(was_work)
            state['remaining_time'] = get_phase_duration(state['current_phase'])
            state['total_active_time'] = 0
            state['timer_running'] = False
            state['timer_paused'] = False
            save_to_supabase()
            st.session_state.force_rerun = True

    with col4:
        if st.button("🔄 Reiniciar", use_container_width=True, key="reset_timer"):
            # Función de reinicio del temporizador
            # Si el temporizador está en ejecución y es fase de trabajo, guardar el tiempo transcurrido
            if state['timer_running'] and state['current_phase'] == "Trabajo" and state['total_active_time'] >= 0.1:
                log_session()
            
            # Si el temporizador está en pausa, no guardar duplicados
            state['timer_running'] = False
            state['timer_paused'] = False
            state['session_count'] = 0
            state['current_phase'] = "Trabajo"
            state['remaining_time'] = state['work_duration']
            state['total_active_time'] = 0
            state['start_time'] = None
            state['paused_time'] = None
            state['timer_start'] = None
            state['last_update'] = None
            state['paused_time'] = None
            st.success("Temporizador reiniciado")
            save_to_supabase()
            st.session_state.force_rerun = True

    # Contador de sesiones
    st.write(f"Sesiones completadas: {state['session_count']}/{state['total_sessions']}")

    # Actualizar el temporizador si está en ejecución
    if state['timer_running'] and not state['timer_paused']:
        current_time = time.time()
        
        # Solo actualizar si last_update no es None y ha pasado al menos 1 segundo
        if state['last_update'] is not None and current_time - state['last_update'] >= 1.0:
            elapsed = current_time - state['last_update']
            state['last_update'] = current_time

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
                
                # Determinar siguiente fase pero NO iniciarla automáticamente
                state['current_phase'] = determine_next_phase(was_work)
                state['remaining_time'] = get_phase_duration(state['current_phase'])
                state['total_active_time'] = 0
                state['timer_running'] = False  # Detener el temporizador
                state['timer_paused'] = False
                
                # Reproducir sonido de alarma
                play_alarm_sound()
                
                st.success(f"¡Fase completada! Presiona 'Iniciar' para comenzar {state['current_phase']}")
                save_to_supabase()
                st.session_state.force_rerun = True
            else:
                # Solo actualizar el gráfico sin forzar un rerun completo
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
                
                chart_placeholder.plotly_chart(fig, use_container_width=True)

    # Forzar actualización de la interfaz si es necesario
    time.sleep(0.1)
    st.rerun()

# ==============================================
# Pestaña de Dashboard (Nueva)
# ==============================================

def dashboard_tab():
    """Pestaña de Dashboard unificado con métricas y gráficos"""
    st.title("📊 Dashboard de Productividad")
    
    # Mostrar métricas principales
    create_metric_cards()
    
    st.divider()
    
    # Añadir recomendación de tarea focus
    focus_task = focus_recommendation()
    if focus_task:
        with st.container(border=True):
            st.subheader("🎯 Tarea Recomendada")
            st.write(f"**{focus_task['name']}**")
            st.caption(f"Proyecto: {focus_task.get('project', 'Ninguno')}")
            st.caption(f"Focus Score: {focus_task.get('focus_score', 0):.2f}")
            
            if st.button("Trabajar en esta tarea"):
                state = st.session_state.pomodoro_state
                state['current_task'] = focus_task['name']
                state['current_project'] = focus_task.get('project', 'Ninguno')
                st.session_state.sidebar_nav = "🍅 Temporizador"
                st.rerun()
    
    # Añadir ratio de cumplimiento
    completion_ratio()
    
    # Mostrar logros
    show_achievements()
    
    # Añadir tienda de recompensas
    with st.expander("🪙 Tienda de Recompensas"):
        rewards_shop()
    
    # Mostrar gráficos
    create_dashboard_charts()
    
    # Resumen de actividad reciente
    st.subheader("Actividad Reciente")
    
    state = st.session_state.pomodoro_state
    recent_tasks = state['completed_tasks'][-5:] if state['completed_tasks'] else []
    
    if recent_tasks:
        for task in reversed(recent_tasks):
            with st.container(border=True):
                st.write(f"✅ **{task['name']}**")
                st.caption(f"Proyecto: {task.get('project', 'Ninguno')} | Completado: {task.get('completed_date', '')}")
    else:
        st.info("No hay actividad reciente para mostrar")

# ==============================================
# Pestaña de Tareas (Mejorada)
# ==============================================

def tasks_tab():
    """Muestra la pestaña de gestión de tareas"""
    state = st.session_state.pomodoro_state
    st.title("📋 Gestión de Tareas y Proyectos")
    
    # Mostrar modales de edición si están activos
    if state.get('editing_task'):
        task_modal(st.session_state.get('editing_task', None))
    if state.get('editing_project'):
        project_modal(st.session_state.get('editing_project', None))
    
    # Añadir selector de vista
    view_option = st.radio(
        "Vista",
        ["Lista", "Kanban", "Calendario", "Jerárquica"],
        horizontal=True,
        key="tasks_view"
    )
    
    if view_option == "Kanban":
        kanban_view()
        return
    elif view_option == "Calendario":
        calendar_view()
        return
    elif view_option == "Jerárquica":
        hierarchical_view()
        return
    
    # Filtros y búsqueda
    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
    
    with col1:
        activity_filter = st.selectbox(
            "Actividad",
            ["Todas"] + state['activities'],
            key="tasks_activity_filter"
        )
        state['filter_activity'] = activity_filter
    
    with col2:
        project_options = ["Todos"] + list(set([t['project'] for t in state['tasks'] + state['completed_tasks'] if t['project'] != "Ninguno"]))
        project_filter = st.selectbox(
            "Proyecto",
            project_options,
            key="tasks_project_filter"
        )
        state['filter_project'] = project_filter
    
    with col3:
        status_filter = st.radio(
            "Estado",
            ["Todas", "Pendientes", "Completadas"],
            horizontal=True,
            key="tasks_status_filter"
        )
        state['task_status_filter'] = status_filter
    
    with col4:
        # Busca el botón "➕ Nueva Tarea" y reemplázalo con:
            if st.button("➕ Nueva Tarea", use_container_width=True, key="new_task_button"):
                st.session_state.show_task_modal = True
                st.session_state.editing_task = None
    
    # Filtros adicionales
    col1, col2 = st.columns(2)
    
    with col1:
        tag_filters = st.multiselect(
            "Etiquetas",
            state['tags'],
            key="tasks_tag_filter"
        )
        state['filter_tags'] = tag_filters
    
    with col2:
        search_text = st.text_input("Buscar", placeholder="Nombre o descripción...", key="tasks_search")
    
    # Ordenación
    col1, col2 = st.columns(2)
    
    with col1:
        sort_by = st.selectbox(
            "Ordenar por",
            ["Fecha creación", "Prioridad", "Fecha límite", "Nombre", "Focus Score"],
            key="tasks_sort_by"
        )
        state['sort_by'] = sort_by
    
    with col2:
        sort_order = st.radio(
            "Orden",
            ["Descendente", "Ascendente"],
            horizontal=True,
            key="tasks_sort_order"
        )
        state['sort_ascending'] = (sort_order == "Ascendente")
    
    # Mostrar tareas filtradas
    filtered_tasks = filter_tasks(
        activity_filter, project_filter, status_filter, 
        tag_filters, search_text
    )
    
    if not filtered_tasks:
        st.info("No hay tareas que coincidan con los filtros")
    else:
        for task in filtered_tasks:
            with st.container(border=True):
                col1, col2, col3 = st.columns([6, 1, 1])
                
                with col1:
                    status = "✅ " if task['completed'] else "⏳ "
                    priority_icon = {"Urgente": "🔴", "Alta": "🟠", "Media": "🟡", "Baja": "🟢"}.get(task['priority'], "⚪")
                    
                    st.write(f"{status}{priority_icon} **{task['name']}**")
                    
                    metadata = f"Proyecto: {task.get('project', 'Ninguno')} | "
                    metadata += f"Prioridad: {task['priority']} | "
                    metadata += f"Vence: {task['deadline']}"
                    
                    if task.get('tags'):
                        metadata += f" | Etiquetas: {', '.join(task['tags'])}"
                    
                    st.caption(metadata)
                    
                    if task.get('description'):
                        with st.expander("Ver descripción"):
                            st.write(task['description'])
                
                with col2:
                    if not task['completed']:
                        if st.button("✓", key=f"complete_{task['id']}"):
                            complete_task(task['id'])
                    else:
                        st.write("✅")
                
                with col3:
                    if st.button("✏️", key=f"edit_{task['id']}"):
                        st.session_state.editing_task = task
                        st.session_state.show_task_modal = True
                        st.session_state.force_rerun = True
                    if st.button("🗑️", key=f"delete_{task['id']}"):
                        delete_task(task['id'])
    
    # Modal de edición de tarea
    if st.session_state.get('show_task_modal', False):
        task_modal(st.session_state.get('editing_task', None))
    
    # Añadir pestaña para plantillas
    st.divider()
    task_templates()
    
    # Añadir matriz de Eisenhower
    st.divider()
    eisenhower_matrix()

# ==============================================
# Pestaña de Proyectos (Mejorada)
# ==============================================

def projects_tab():
    """Pestaña de gestión de proyectos"""
    st.title("📂 Gestión de Proyectos")
    
    state = st.session_state.pomodoro_state
    
    # Botón para crear nuevo proyecto
    if st.button("➕ Nuevo Proyecto"):
        st.session_state.editing_project = {}
        st.session_state.force_rerun = True
    
    # Mostrar proyectos por actividad
    for activity in state['activities']:
        activity_projects = [p for p in state['projects'] if p['activity'] == activity]
        
        if activity_projects:
            st.subheader(f"📁 {activity}")
            
            for project in activity_projects:
                with st.container(border=True):
                    col1, col2 = st.columns([5, 1])
                    
                    with col1:
                        st.write(f"**{project['name']}**")
                        if project.get('description'):
                            st.caption(project['description'])
                        
                        # Mostrar estadísticas del proyecto
                        project_tasks = [t for t in state['tasks'] + state['completed_tasks'] 
                                       if t.get('project') == project['name']]
                        completed_count = sum(1 for t in project_tasks if t['completed'])
                        total_count = len(project_tasks)
                        
                        if total_count > 0:
                            progress = completed_count / total_count
                            st.progress(progress, text=f"{completed_count}/{total_count} tareas completadas")
                    
                    with col2:
                        if st.button("✏️", key=f"edit_proj_{project['name']}"):
                            st.session_state.editing_project = project
                            st.session_state.force_rerun = True
                        if st.button("🗑️", key=f"delete_proj_{project['name']}"):
                            # Eliminar proyecto y mover sus tareas a "Ninguno"
                            for task in state['tasks'] + state['completed_tasks']:
                                if task.get('project') == project['name']:
                                    task['project'] = "Ninguno"
                            state['projects'].remove(project)
                            show_toast(f"Proyecto '{project['name']}' eliminado")
                            logging.info(f"Proyecto eliminado: {project['name']}")
                            save_to_supabase()
                            st.session_state.force_rerun = True
    
    # Modal de edición de proyecto
    if 'editing_project' in st.session_state and st.session_state.editing_project:
        project_modal(st.session_state.editing_project)

# ==============================================
# Pestaña de Estadísticas (Mejorada)
# ==============================================

def stats_tab():
    """Muestra la pestaña de estadísticas"""
    st.title("📈 Estadísticas Detalladas")
    
    if not st.session_state.pomodoro_state['session_history']:
        st.warning("No hay datos de sesiones registrados.")
        return
    
    data = analyze_data()
    
    # Mostrar información de depuración
    if data['errors']:
        with st.expander("⚠️ Errores de procesamiento (click para ver)"):
            for error in data['errors']:
                st.error(error)
    
    # Mostrar resumen de depuración
    with st.expander("🔍 Información de depuración"):
        st.write(f"Total de entradas en historial: {len(st.session_state.pomodoro_state['session_history'])}")
        st.write(f"Total de entradas procesadas: {len(data['raw_data'])}")
        st.write(f"Total de errores: {len(data['errors'])}")
        st.write("Historial completo:")
        st.write(st.session_state.pomodoro_state['session_history'])
    
    # Selector de pestañas
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "Resumen", "Tendencias", "Distribución", "Seguimiento de Tiempo", 
        "Informe Semanal", "Heatmap 7x24", "Tendencias Mensuales", "Productividad por Contexto"
    ])
    
    with tab1:
        col1, col2 = st.columns(2)
        
        with col1:
            # Gráfico de distribución de actividades
            if data['activities']:
                # Filtrar actividades con tiempo significativo
                filtered_activities = {k: v for k, v in data['activities'].items() if v > 0.1}
                
                if filtered_activities:
                    fig = px.pie(
                        values=list(filtered_activities.values()), 
                        names=list(filtered_activities.keys()),
                        title="Distribución de Actividades (horas)"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No hay datos significativos para mostrar")
            else:
                st.info("No hay datos para mostrar")
        
        with col2:
            # Gráfico de tiempo por proyecto
            project_data = {k: v for k, v in data['projects'].items() if v > 0.1}
            
            if project_data:
                fig = px.pie(
                    values=list(project_data.values()), 
                    names=list(project_data.keys()),
                    title="Distribución por Proyecto (horas)"
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
                {'date': r['date'], 'hours': r['duration']} 
                for r in data['raw_data']
            ])
            daily_totals = df_dates.groupby('date').sum().reset_index()
            
            fig = px.line(
                daily_totals, x='date', y='hours',
                title="Evolución del Tiempo por Día",
                labels={'date': 'Fecha', 'hours': 'Horas'}
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay datos suficientes para mostrar tendencias")
    
    with tab3:
        st.subheader("Distribución por Actividad y Proyecto")
        
        if data['raw_data']:
            # Crear matriz para heatmap
            activities = sorted(set(r['activity'] for r in data['raw_data'] if r['activity']))
            projects = sorted(set(r['project'] for r in data['raw_data'] if r['project']))
            
            # Crear matriz de horas por actividad y proyecto
            heatmap_data = np.zeros((len(activities), len(projects)))
            
            for r in data['raw_data']:
                if r['project'] and r['activity']:
                    try:
                        act_idx = activities.index(r['activity'])
                        proj_idx = projects.index(r['project'])
                        heatmap_data[act_idx, proj_idx] += r['duration']
                    except (ValueError, IndexError):
                        # Ignorar entradas que no estén en las listas
                        pass
            
            # Crear heatmap solo si hay datos
            if np.sum(heatmap_data) > 0:
                fig = px.imshow(
                    heatmap_data,
                    labels=dict(x="Proyecto", y="Actividad", color="Horas"),
                    x=projects,
                    y=activities,
                    title="Distribución de Tiempo por Actividad y Proyecto"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No hay datos suficientes para el heatmap")
        else:
            st.info("No hay datos suficientes para el heatmap")
    
    with tab4:
        time_tracking()
    
    with tab5:
        show_weekly_report()
    
    with tab6:
        productivity_heatmap()
    
    with tab7:
        monthly_trends()
    
    with tab8:
        context_productivity()

# ==============================================
# Pestaña de Configuración (Mejorada)
# ==============================================

def settings_tab():
    """Muestra la pestaña de configuración"""
    state = st.session_state.pomodoro_state
    
    st.title("⚙️ Configuración")

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Temporizador", "Apariencia", "Preferencias", "Objetivos", "Datos"])
    
    with tab1:
        st.subheader("⏱️ Configuración del Temporizador")
        
        col1, col2 = st.columns(2)
        
        with col1:
            work_min = st.number_input("Tiempo de trabajo (min)", min_value=5, max_value=60, 
                                     value=state['work_duration'] // 60)
            short_min = st.number_input("Descanso corto (min)", min_value=1, max_value=30, 
                                      value=state['short_break'] // 60)
            long_min = st.number_input("Descanso largo (min)", min_value=5, max_value=60, 
                                     value=state['long_break'] // 60)
        
        with col2:
            sessions_long = st.number_input("Sesiones antes de descanso largo", min_value=1, 
                                          max_value=10, value=state['sessions_before_long'])
            total_sess = st.number_input("Sesiones totales planificadas", min_value=1, 
                                       max_value=20, value=state['total_sessions'])
        
        if st.button("Aplicar Configuración del Temporizador", key="apply_timer_settings"):
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
            show_toast("Configuración del temporizador aplicada")
            save_to_supabase()
    
    with tab2:
        st.subheader("🎨 Personalización")
        
        theme = st.selectbox("Tema", list(THEMES.keys()), 
                           index=list(THEMES.keys()).index(state['current_theme']))
        if theme != state['current_theme']:
            state['current_theme'] = theme
            show_toast("Tema cambiado")
            st.session_state.force_rerun = True
        
        high_contrast = st.checkbox("Modo alto contraste", value=state['settings']['high_contrast'])
        if high_contrast != state['settings']['high_contrast']:
            state['settings']['high_contrast'] = high_contrast
            show_toast("Modo alto contraste " + ("activado" if high_contrast else "desactivado"))
    
    with tab3:
        st.subheader("🔔 Preferencias")
        
        col1, col2 = st.columns(2)
        
        with col1:
            notifications = st.checkbox("Notificaciones", value=state['settings']['notifications'])
            if notifications != state['settings']['notifications']:
                state['settings']['notifications'] = notifications
                show_toast("Notificaciones " + ("activadas" if notifications else "desactivadas"))
        
        with col2:
            auto_save = st.checkbox("Guardado automático", value=state['settings']['auto_save'])
            if auto_save != state['settings']['auto_save']:
                state['settings']['auto_save'] = auto_save
                show_toast("Guardado automático " + ("activado" if auto_save else "desactivado"))
        
        sound_enabled = st.checkbox("Sonidos de notificación", value=state['settings']['sound_enabled'])
        if sound_enabled != state['settings']['sound_enabled']:
            state['settings']['sound_enabled'] = sound_enabled
            show_toast("Sonidos " + ("activados" if sound_enabled else "desactivados"))
        
        power_saving = st.checkbox("Modo ahorro de energía", value=state['settings']['power_saving'])
        if power_saving != state['settings']['power_saving']:
            state['settings']['power_saving'] = power_saving
            show_toast("Modo ahorro de energía " + ("activado" if power_saving else "desactivado"))
    
    with tab4:
        st.subheader("🎯 Objetivos")
        
        weekly_hours = st.number_input("Horas semanales objetivo", min_value=1, max_value=80, 
                                     value=state['goals']['weekly_hours'])
        if weekly_hours != state['goals']['weekly_hours']:
            state['goals']['weekly_hours'] = weekly_hours
            show_toast("Objetivo semanal actualizado")
            save_to_supabase()
        
        daily_tasks = st.number_input("Tareas diarias objetivo", min_value=1, max_value=20, 
                                    value=state['goals']['daily_tasks'])
        if daily_tasks != state['goals']['daily_tasks']:
            state['goals']['daily_tasks'] = daily_tasks
            show_toast("Objetivo diario actualizado")
            save_to_supabase()
        
        planned_sessions = st.number_input("Sesiones semanales planificadas", min_value=1, max_value=100, 
                                         value=state.get('total_planned_sessions', 35))
        if planned_sessions != state.get('total_planned_sessions', 35):
            state['total_planned_sessions'] = planned_sessions
            show_toast("Sesiones planificadas actualizadas")
            save_to_supabase()
        
        planned_tasks = st.number_input("Tareas totales planificadas", min_value=0, max_value=1000, 
                                      value=state.get('total_planned_tasks', 0))
        if planned_tasks != state.get('total_planned_tasks', 0):
            state['total_planned_tasks'] = planned_tasks
            show_toast("Tareas planificadas actualizadas")
            save_to_supabase()
    
    with tab5:
        st.subheader("📊 Gestión de Datos")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Exportar datos**")
            export_data()
            
            st.write("**Respaldar datos**")
            if st.button("Crear copia de seguridad"):
                if backup_data():
                    show_toast("Copia de seguridad creada")
                else:
                    st.error("Error al crear copia de seguridad")
        
        with col2:
            st.write("**Importar datos**")
            uploaded_file = st.file_uploader("Subir archito de backup", type=['json.gz'])
            if uploaded_file is not None:
                import_data(uploaded_file)
            
            st.write("**Gestionar actividades**")
            new_activity = st.text_input("Nueva actividad")
            if st.button("Añadir actividad") and new_activity:
                if new_activity not in state['activities']:
                    state['activities'].append(new_activity)
                    show_toast(f"Actividad '{new_activity}' añadida")
                    save_to_supabase()
            
            if state['activities']:
                activity_to_remove = st.selectbox("Seleccionar actividad a eliminar", state['activities'])
                if st.button("Eliminar actividad"):
                    state['activities'].remove(activity_to_remove)
                    show_toast(f"Actividad '{activity_to_remove}' eliminada")
                    save_to_supabase()
        
        st.divider()
        st.subheader("🛠️ Herramientas de Diagnóstico")
        
        if st.button("Mostrar información de diagnóstico"):
            st.json(state)
        
        if st.button("Reiniciar datos"):
            state['tasks'] = []
            state['completed_tasks'] = []
            state['session_history'] = []
            show_toast("Datos reiniciados")
            save_to_supabase()

# ==============================================
# Pestaña Acerca de (Mejorada)
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
    - 🏆 Sistema de logros y recompensas
    - 🪙 Tienda de recompensas con monedas virtuales
    - 📅 Calendario y planificación avanzada

    ### Cómo usar esta aplicación
    1. Configura tus tiempos preferidos en la pestaña de Configuración
    2. Selecciona una actividad y proyecto
    3. Inicia el temporizador y concéntrate en tu tarea
    4. Toma descansos según las indicaciones
    5. Revisa tus estadísticas para mejorar tu productividad
    """)
    
    st.info("""
    Nota: Esta aplicación almacena tus datos en Supabase para persistencia entre sesiones.
    Tus datos están seguros y solo tú puedes acceder a ellos.
    """)

# ==============================================
# Pestaña de Información (Mejorada)
# ==============================================

def info_tab():
    """Muestra la pestaña de información"""
    st.title("ℹ️ Información and Ayuda")

    tab1, tab2, tab3 = st.tabs(["Instrucciones", "FAQ", "Contacto"])

    with tab1:
        st.header("Instrucciones de Uso")
        st.subheader("Configuración Inicial")
        st.markdown("""
        1. Ve a la pestaña Configuración en la barra lateral
        2. Ajusta los tiempos según tus preferencias
        3. Selecciona un tema visual de tu preferencia
        4. Configura tus objetivos semanales y diarios
        """)

        st.subheader("Uso del Temporizador")
        st.markdown("""
        1. Selecciona una actividad y proyecto (opcional)
        2. Selecciona o crea una tarea específica
        3. Haz clic en **Iniciar** para comenzar la sesión
        4. Concéntrate en tu tarea hasta que suene la alarma
        5. Toma un descanso cuando se te indique
        """)

        st.subheader("Gestión de Tareas")
        st.markdown("""
        1. Usa la vista Jerárquica para ver tu estructura de trabajo
        2. Crea proyectos para organizar tus tareas
        3. Utiliza etiquetas para categorizar tu trabajo
        4. Aprovecha la matriz de Eisenhower para priorizar
        """)

    with tab2:
        st.header("Preguntas Frecuentes")

        with st.expander("¿Cómo cambio la configuración de los tiempos?"):
            st.markdown("Ve a la pestaña **Configuración** y ajusta los valores según tus preferencias.")

        with st.expander("¿Cómo veo mis estadísticas?"):
            st.markdown("Ve a la pestaña **Estadísticas** para ver gráficos y análisis de tu productividad.")

        with st.expander("¿Qué son las monedas de recompensa?"):
            st.markdown("""
            Las monedas de recompensa son una forma de gamificar tu productividad. Ganas monedas por:
            - Completar sesiones de trabajo
            - Terminar tareas
            - Alcanzar objetivos
            - Mantener rachas de productividad
            
            Puedes canjear tus monedas en la tienda de recompensas para desbloquear funciones especiales.
            """)

    with tab3:
        st.header("Contacto y Soporte")
        st.markdown("""
        ### ¿Necesitas ayuda?
        Si tienes problemas con la aplicación o sugerencias para mejorarla,
        por favor contáctanos a través de los siguientes medios:

        - 📧 Email: soporte@pomodoropro.com
        - 🐛 Reportar un error: [GitHub Issues](https://github.com/tu-usuario/pomodoro-pro/issues)

        ### Versión
        Estás usando la versión 2.0.0 de Pomodoro Pro con todas las características
        """)

# ==============================================
# Funciones de utilidad para alertas
# ==============================================

def check_alerts():
    """Verifica alertas y notificaciones para el usuario"""
    state = st.session_state.pomodoro_state
    alerts = []
    
    # Verificar tareas próximas a vencer
    today = date.today()
    for task in state['tasks']:
        # Manejar tanto string como objeto date en el deadline
        if isinstance(task['deadline'], str):
            try:
                deadline = datetime.datetime.strptime(task['deadline'], "%Y-%m-%d").date()
            except (ValueError, TypeError):
                continue
        else:
            deadline = task['deadline']
        
        days_until_due = (deadline - today).days
        if 0 <= days_until_due <= 2:
            alerts.append(f"📅 Tarea '{task['name']}' vence en {days_until_due} días")
    
    # Verificar si hay sesiones de estudio hoy
    today_str = today.strftime("%Y-%m-%d")
    sessions_today = 0
    for session in state['session_history']:
        # Manejar diferentes formatos de fecha en el historial
        session_date = session['Fecha']
        if isinstance(session_date, str):
            if session_date == today_str:
                sessions_today += 1
        elif isinstance(session_date, (datetime.date, datetime.datetime)):
            session_date_str = session_date.strftime("%Y-%m-%d") if isinstance(session_date, datetime.date) else session_date.date().strftime("%Y-%m-%d")
            if session_date_str == today_str:
                sessions_today += 1
    
    if sessions_today == 0:
        alerts.append("ℹ️ Aún no has tenido sesiones de estudio hoy")
    
    # Verificar racha de estudio
    if state['achievements']['streak_days'] > 0:
        alerts.append(f"🔥 ¡Llevas una racha de {state['achievements']['streak_days']} días!")
    
    # Verificar recompensas disponibles
    if state['reward_coins'] > 0:
        affordable_rewards = [r for r in state['rewards'] if r['cost'] <= state['reward_coins'] and r['id'] not in state['unlocked_rewards']]
        if affordable_rewards:
            alerts.append(f"🪙 Tienes {state['reward_coins']} monedas. ¡Puedes canjear recompensas!")
    
    return alerts

def logout():
    """Cierra sesión limpiando todo"""
    # Guardar el estado actual antes de cerrar sesión
    if check_authentication():
        on_close()
    
    st.session_state.clear()
    st.session_state.pomodoro_state = get_default_state()
    st.session_state.force_rerun = True

# ==============================================
# Barra lateral (Mejorada)
# ==============================================

def sidebar():
    """Muestra la barra lateral con navegación y controles"""
    # Mostrar sección de autenticación
    auth_section()
    
    if not check_authentication():
        return
    
    state = st.session_state.pomodoro_state

    with st.sidebar:
        # Aplicar estilo similar al diseño Tkinter
        st.markdown("""
        <style>
        .sidebar .sidebar-content {
            background-color: #2A2F4F;
            color: white;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Header con logo y nombre
        col1, col2 = st.columns([1, 3])
        with col1:
            st.title("🍅")  # Reemplazar con tu logo
        with col2:
            st.title("Pomodoro Pro")
        
        st.divider()

        # Información rápida de progreso - CORREGIDO
        st.subheader("Progreso Hoy", anchor=False)
        today = datetime.datetime.now().date()
        
        # Filtrar sesiones de hoy correctamente
        today_sessions = []
        for session in state['session_history']:
            # Manejar diferentes formatos de fecha
            session_date = session.get('Fecha')
            
            # Convertir a objeto date si es string
            if isinstance(session_date, str):
                try:
                    session_date = datetime.datetime.strptime(session_date, "%Y-%m-%d").date()
                except ValueError:
                    continue
            
            # Si ya es objeto date, comparar directamente
            if isinstance(session_date, datetime.date) and session_date == today:
                today_sessions.append(session)
        
        # Calcular horas totales de hoy
        today_hours = sum(float(session.get('Tiempo Activo (horas)', 0)) for session in today_sessions)
        
        st.metric("Horas hoy", f"{today_hours:.2f}")
        st.metric("Monedas", state['reward_coins'])
        
        # Navegación por pestañas
        st.subheader("Navegación", anchor=False)
        tabs = st.radio("Selecciona una sección:", 
                       ["📊 Dashboard", "🍅 Temporizador", "📋 Tareas", 
                        "📂 Proyectos", "📈 Estadísticas", "⚙️ Configuración", "ℹ️ Info"],
                       key='sidebar_nav')
        
        st.divider()
        
        # Mostrar alertas si existen
        alerts = check_alerts()
        if alerts:
            st.subheader("🔔 Alertas", anchor=False)
            for alert in alerts[:3]:  # Mostrar máximo 3 alertas
                st.warning(alert, icon="⚠️")
            if len(alerts) > 3:
                with st.expander(f"Ver todas las alertas ({len(alerts)})"):
                    for alert in alerts[3:]:
                        st.warning(alert, icon="⚠️")
            st.divider()
        
        # Opciones avanzadas (colapsables)
        with st.expander("Opciones Avanzadas", expanded=False):
            # Gestión de datos en la nube
            st.subheader("☁️ Datos en la Nube")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("💾 Guardar", key="save_cloud"):
                    save_to_supabase()
            
            with col2:
                if st.button("📂 Cargar", key="load_cloud"):
                    if load_from_supabase():
                        st.session_state.force_rerun = True
            
            # Configuración de backups
            st.subheader("📦 Copias de Seguridad")
            if st.button("Crear Backup Local", key="create_backup"):
                if backup_data():
                    show_toast("Backup local creado")
                else:
                    st.error("Error al crear backup")
        
        # Cerrar sesión
        st.divider()
        if st.button("🚪 Cerrar Sesión", key="logout", use_container_width=True):
            logout()

# ==============================================
# Función principal (Mejorada)
# ==============================================

def main():
    """Función principal de la aplicación - Versión mejorada"""
    # Inicializar el estado si no existe
    if 'pomodoro_state' not in st.session_state:
        st.session_state.pomodoro_state = get_default_state()
    
    # Inicializar variables de control
    if 'force_rerun' not in st.session_state:
        st.session_state.force_rerun = False
    
    # Configurar backups automáticos
    setup_automatic_backups()
    
    # Configurar diseño responsivo
    setup_responsive_design()
    
    # Aplicar tema y modo de alto contraste
    apply_theme()
    setup_high_contrast_mode()
    
    # Cargar datos desde Supabase si el usuario está autenticado
    if check_authentication() and not st.session_state.get('data_loaded', False):
        if load_from_supabase():
            st.session_state.data_loaded = True
    
    # Barra lateral mejorada
    sidebar()
    
    # Verificar autenticación - si no está autenticado, no mostrar el contenido principal
    if not check_authentication():
        st.warning("Por favor inicia sesión o regístrate para acceder a Pomodoro Pro")
        return

    # Obtener la pestaña seleccionada
    if 'sidebar_nav' not in st.session_state:
        st.session_state.sidebar_nav = "📊 Dashboard"  # Cambiado a Dashboard por defecto
    
    selected_tab = st.session_state.sidebar_nav

    # Mostrar la pestaña correspondiente
    if selected_tab == "📊 Dashboard":
        dashboard_tab()
    elif selected_tab == "🍅 Temporizador":
        timer_tab()
    elif selected_tab == "📋 Tareas":
        tasks_tab()
    elif selected_tab == "📂 Proyectos":
        projects_tab()
    elif selected_tab == "📈 Estadísticas":
        stats_tab()
    elif selected_tab == "⚙️ Configuración":
        settings_tab()
    elif selected_tab == "ℹ️ Info":
        # Pestañas dentro de Info
        tab1, tab2 = st.tabs(["Acerca de", "Información y Ayuda"])
        with tab1:
            about_tab()
        with tab2:
            info_tab()

    # Control de rerun
    if st.session_state.force_rerun:
        st.session_state.force_rerun = False
        st.rerun()
    
    # Guardado automático
    state = st.session_state.pomodoro_state
    if state['settings']['auto_save'] and state['last_updated'] + 30 < time.time():
        # Solo guardar cada 30 segundos para reducir I/O
        save_to_supabase()
        state['last_updated'] = time.time()

# ==============================================
# Ejecución de la aplicación
# ==============================================

if __name__ == "__main__":
    main()
