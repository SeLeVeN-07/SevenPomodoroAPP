# -*- coding: utf-8 -*-
"""
Pomodoro Pro - Versión Mejorada con Gestión de Tareas y Perfil de Usuario
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
from collections import defaultdict
from supabase import create_client, Client
import os
import re
import logging
import uuid

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuración de la página
st.set_page_config(
    page_title="Pomodoro Pro",
    page_icon="🍅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configuración de Supabase
SUPABASE_URL = os.getenv('SUPABASE_URL', "https://puyhhnglmjjpzzlpltkj.supabase.co")
SUPABASE_KEY = os.getenv('SUPABASE_KEY', "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InB1eWhobmdsbWpqcHp6bHBsdGtqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTYyMjgxMDIsImV4cCI6MjA3MTgwNDEwMn0.AEnoGRTO0Ex0tQU1r-oUkolpjf85t4mGTCrLG86sgow")

@st.cache_resource
def init_supabase():
    try:
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        client.table('user_data').select('*').limit(1).execute()
        logger.info("Conexión a Supabase establecida")
        return client
    except Exception as e:
        logger.error(f"Error al conectar con Supabase: {str(e)}")
        st.error(f"Error de conexión: {str(e)}")
        return None

supabase = init_supabase()

# Constantes y configuración
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
    }
}

# Estado por defecto
def get_default_state():
    """Estado inicial con todos los campos necesarios"""
    return {
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
        'current_theme': 'Claro',
        'activities': ["Estudio", "Trabajo"],
        'current_activity': "",
        'tasks': [],
        'projects': [],
        'achievements': {
            'pomodoros_completed': 0,
            'tasks_completed': 0,
            'streak_days': 0,
            'total_hours': 0,
            'completed_projects': 0
        },
        'last_session_date': None,
        'session_history': [],
        'username': "",
        'display_name': "",
        'task_id_counter': 0,
        'editing_task_id': None,
        'editing_project_id': None,
        'data_version': 2  # Versión del esquema de datos
    }

def validate_state(state):
    """Valida y repara el estado cargado, asegurando consistencia de datos"""
    default_state = get_default_state()
    
    # 1. Verificar que todos los campos obligatorios existan
    for key in default_state:
        if key not in state:
            state[key] = default_state[key]
            logger.warning(f"Campo faltante '{key}' restaurado a valor por defecto")
    
    # 2. Validar estructura de tareas
    if not isinstance(state['tasks'], list):
        state['tasks'] = []
        logger.warning("Estructura de tareas inválida - reinicializada")
    else:
        # Validar cada tarea individualmente
        valid_tasks = []
        for task in state['tasks']:
            if not isinstance(task, dict):
                continue
                
            valid_task = {
                'id': task.get('id', str(uuid.uuid4())),
                'name': task.get('name', 'Tarea sin nombre').strip(),
                'description': task.get('description', '').strip(),
                'priority': task.get('priority', 'Media') if task.get('priority') in ['Baja', 'Media', 'Alta'] else 'Media',
                'due_date': task.get('due_date'),
                'project': task.get('project', ''),
                'completed': bool(task.get('completed', False)),
                'created_at': task.get('created_at', datetime.datetime.now().isoformat()),
                'completed_at': task.get('completed_at')
            }
            
            # Validar fecha de vencimiento
            if valid_task['due_date']:
                try:
                    if isinstance(valid_task['due_date'], str):
                        valid_task['due_date'] = datetime.date.fromisoformat(valid_task['due_date'])
                    elif not isinstance(valid_task['due_date'], (datetime.date, datetime.datetime)):
                        valid_task['due_date'] = None
                except ValueError:
                    valid_task['due_date'] = None
            
            valid_tasks.append(valid_task)
        
        state['tasks'] = valid_tasks
    
    # 3. Validar estructura de proyectos
    if not isinstance(state['projects'], list):
        state['projects'] = []
        logger.warning("Estructura de proyectos inválida - reinicializada")
    else:
        valid_projects = []
        existing_names = set()
        
        for project in state['projects']:
            if not isinstance(project, dict):
                continue
                
            # Generar ID si no existe
            if 'id' not in project or not project['id']:
                project['id'] = str(uuid.uuid4())
            
            # Validar nombre
            name = project.get('name', '').strip()
            if not name:
                name = f"Proyecto {len(valid_projects) + 1}"
            
            # Evitar duplicados
            lower_name = name.lower()
            if lower_name in existing_names:
                name = f"{name} ({project['id'][:4]})"
                lower_name = name.lower()
            
            existing_names.add(lower_name)
            
            valid_projects.append({
                'id': project['id'],
                'name': name,
                'created_at': project.get('created_at', datetime.datetime.now().isoformat()),
                'task_count': project.get('task_count', 0)
            })
        
        state['projects'] = valid_projects
    
    # 4. Validar sesiones de historial
    if not isinstance(state['session_history'], list):
        state['session_history'] = []
    else:
        valid_history = []
        for session in state['session_history']:
            if not isinstance(session, dict):
                continue
                
            valid_session = {
                'Fecha': session.get('Fecha'),
                'Hora Inicio': session.get('Hora Inicio', ''),
                'Tiempo Activo (min)': float(session.get('Tiempo Activo (min)', 0)),
                'Actividad': session.get('Actividad', '')
            }
            
            # Validar fecha
            if valid_session['Fecha']:
                try:
                    if isinstance(valid_session['Fecha'], str):
                        valid_session['Fecha'] = datetime.date.fromisoformat(valid_session['Fecha'])
                    elif not isinstance(valid_session['Fecha'], (datetime.date, datetime.datetime)):
                        valid_session['Fecha'] = datetime.date.today()
                except ValueError:
                    valid_session['Fecha'] = datetime.date.today()
            
            valid_history.append(valid_session)
        
        # Ordenar por fecha (más reciente primero)
        state['session_history'] = sorted(
            valid_history,
            key=lambda x: x['Fecha'] if x['Fecha'] else datetime.date.min,
            reverse=True
        )[:1000]  # Limitar a 1000 registros
    
    # 5. Validar logros
    if not isinstance(state['achievements'], dict):
        state['achievements'] = default_state['achievements']
    else:
        for key in default_state['achievements']:
            if key not in state['achievements']:
                state['achievements'][key] = default_state['achievements'][key]
    
    # 6. Validar fechas importantes
    date_fields = ['last_session_date', 'start_time', 'paused_time']
    for field in date_fields:
        if field in state and state[field]:
            try:
                if isinstance(state[field], str):
                    state[field] = datetime.datetime.fromisoformat(state[field])
                elif not isinstance(state[field], (datetime.date, datetime.datetime)):
                    state[field] = None
            except ValueError:
                state[field] = None
    
    # 7. Validar configuración del temporizador
    timer_settings = [
        ('work_duration', 25 * 60, 1 * 60, 120 * 60),
        ('short_break', 5 * 60, 1 * 60, 30 * 60),
        ('long_break', 15 * 60, 5 * 60, 60 * 60),
        ('sessions_before_long', 4, 1, 10),
        ('total_sessions', 8, 1, 20)
    ]
    
    for setting, default, min_val, max_val in timer_settings:
        if not isinstance(state[setting], (int, float)) or not (min_val <= state[setting] <= max_val):
            state[setting] = default
            logger.warning(f"Configuración inválida '{setting}' - restaurada a valor por defecto")
    
    # 8. Validar fase actual
    if state['current_phase'] not in ['Trabajo', 'Descanso Corto', 'Descanso Largo']:
        state['current_phase'] = 'Trabajo'
    
    # 9. Validar tema
    if state['current_theme'] not in THEMES:
        state['current_theme'] = 'Claro'
    
    # 10. Actualizar versión de datos
    state['data_version'] = default_state['data_version']
    
    return state

# ==============================================
# Funciones de autenticación mejoradas
# ==============================================
def initialize_session_state():
    """Inicializa el estado de la sesión de forma robusta"""
    try:
        with st.spinner("Cargando datos..."):
            if 'user' in st.session_state and st.session_state.user:
                # Cargar datos existentes
                user_data = load_user_data()
                st.session_state.pomodoro_state = validate_state(user_data) if user_data else get_default_state()
                
                # Guardar estado inicial si es nuevo usuario
                if not user_data:
                    save_user_data()
                
                # Cargar perfil
                load_user_profile_data()
            else:
                st.session_state.pomodoro_state = get_default_state()
    except Exception as e:
        logger.error(f"Error al inicializar estado: {str(e)}")
        st.session_state.pomodoro_state = get_default_state()
        st.error("Error al cargar datos. Usando configuración por defecto.")

def improved_auto_save():
    """Guardado automático mejorado con verificación de cambios"""
    if 'last_saved' not in st.session_state:
        st.session_state.last_saved = datetime.datetime.min
    
    time_since_last_save = (datetime.datetime.now() - st.session_state.last_saved).total_seconds()
    
    if time_since_last_save > 15:  # Guardar cada 15 segundos
        save_user_data()
        
def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_username(username):
    if not username:
        return False
    pattern = r'^[a-zA-Z0-9_-]{3,20}$'
    return re.match(pattern, username) is not None

def auth_section():
    if 'user' not in st.session_state:
        st.session_state.user = None
    
    if not st.session_state.user:
        tab1, tab2 = st.tabs(["Iniciar Sesión", "Registrarse"])
        
        with tab1:
            with st.form("login_form", clear_on_submit=True):
                email = st.text_input("Correo electrónico")
                password = st.text_input("Contraseña", type="password")
                
                submitted = st.form_submit_button("Ingresar")
                if submitted:
                    if not email or not password:
                        st.error("Por favor completa todos los campos")
                    elif not validate_email(email):
                        st.error("Por favor ingresa un email válido")
                    else:
                        try:
                            user = supabase.auth.sign_in_with_password({
                                "email": email,
                                "password": password
                            })
                            st.session_state.user = user
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al iniciar sesión: {str(e)}")
        
        with tab2:
            with st.form("signup_form", clear_on_submit=True):
                new_email = st.text_input("Correo electrónico (registro)")
                new_password = st.text_input("Contraseña (registro)", type="password")
                confirm_password = st.text_input("Confirmar contraseña", type="password")
                username = st.text_input("Nombre de usuario")
                display_name = st.text_input("Nombre para mostrar (opcional)")
                
                submitted = st.form_submit_button("Crear cuenta")
                if submitted:
                    if not all([new_email, new_password, confirm_password, username]):
                        st.error("Por favor completa todos los campos obligatorios")
                    elif not validate_email(new_email):
                        st.error("Por favor ingresa un email válido")
                    elif not validate_username(username):
                        st.error("Nombre de usuario inválido (3-20 caracteres, solo letras, números, guiones y guiones bajos)")
                    elif new_password != confirm_password:
                        st.error("Las contraseñas no coinciden")
                    else:
                        try:
                            user = supabase.auth.sign_up({
                                "email": new_email,
                                "password": new_password
                            })
                            
                            if user:
                                user_id = user.user.id
                                supabase.table('user_profiles').upsert({
                                    'user_id': user_id,
                                    'email': new_email,
                                    'username': username,
                                    'display_name': display_name or username,
                                    'created_at': datetime.datetime.now().isoformat()
                                }).execute()
                            
                            st.success("¡Cuenta creada! Por favor inicia sesión.")
                        except Exception as e:
                            st.error(f"Error al registrar: {str(e)}")

# ==============================================
# Funciones de persistencia mejoradas
# ==============================================
# Añadir esta función y llamarla periódicamente
def sync_data():
    if 'user' in st.session_state and st.session_state.user and 'pomodoro_state' in st.session_state:
        try:
            # Obtener última versión de los datos
            remote_data = load_user_data()
            if remote_data:
                remote_time = datetime.datetime.fromisoformat(remote_data.get('last_updated', '1970-01-01'))
                local_time = st.session_state.pomodoro_state.get('last_updated', datetime.datetime.min)
                
                if remote_time > local_time:
                    # Fusionar datos inteligentemente
                    st.session_state.pomodoro_state = merge_data(
                        st.session_state.pomodoro_state, 
                        remote_data
                    )
                    st.toast("Datos sincronizados desde la nube", icon="☁️")
        except Exception as e:
            logger.error(f"Error en sincronización: {str(e)}")

def merge_data(local, remote):
    """Fusión inteligente de datos locales y remotos"""
    merged = local.copy()
    
    # Preferir datos más recientes
    for key in remote:
        if key not in merged or remote[key] is not None:
            merged[key] = remote[key]
    
    # Mantener algunos datos locales importantes
    if 'timer_running' in local:
        merged['timer_running'] = local['timer_running']
    if 'timer_paused' in local:
        merged['timer_paused'] = local['timer_paused']
    
    return merged
# Añadir esta función y llamarla periódicamente
def check_connection():
    try:
        if supabase:
            # Verificar si Supabase responde
            supabase.table('user_data').select('*').limit(1).execute()
            return True
    except Exception as e:
        logger.error(f"Error de conexión con Supabase: {str(e)}")
        return False
    return False

# Modificar las funciones de guardado y carga
def save_user_data():
    if 'user' in st.session_state and st.session_state.user and 'pomodoro_state' in st.session_state:
        try:
            # Convertir el estado a JSON seguro
            state = st.session_state.pomodoro_state.copy()
            
            # Asegurar que los datos importantes estén actualizados
            state['last_updated'] = datetime.datetime.now().isoformat()
            
            # Serialización robusta
            def json_serial(obj):
                if isinstance(obj, (datetime.datetime, datetime.date)):
                    return obj.isoformat()
                raise TypeError(f"Type {type(obj)} not serializable")
            
            serialized_data = json.dumps(state, default=json_serial)
            
            # Guardado con verificación
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = supabase.table('user_data').upsert({
                        'user_id': st.session_state.user.user.id,
                        'email': st.session_state.user.user.email,
                        'pomodoro_data': json.loads(serialized_data),
                        'last_updated': datetime.datetime.now().isoformat()
                    }).execute()
                    
                    if response.data:
                        st.session_state.last_saved = datetime.datetime.now()
                        return True
                    
                except Exception as e:
                    logger.warning(f"Intento {attempt + 1} fallido al guardar: {str(e)}")
                    if attempt == max_retries - 1:
                        logger.error(f"Error al guardar después de {max_retries} intentos: {str(e)}")
                        return False
                    time.sleep(1)  # Esperar antes de reintentar
            
            return False
        except Exception as e:
            logger.error(f"Error inesperado al guardar: {str(e)}")
            return False
    return False

def load_user_data():
    if 'user' in st.session_state and st.session_state.user:
        try:
            # Intentar hasta 3 veces con reintentos
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = supabase.table('user_data').select('*').eq(
                        'user_id', st.session_state.user.user.id
                    ).execute()
                    
                    if response.data:
                        data = response.data[0]['pomodoro_data']
                        
                        def parse_datetime(obj):
                            if isinstance(obj, str):
                                try:
                                    return datetime.datetime.fromisoformat(obj)
                                except ValueError:
                                    try:
                                        return datetime.date.fromisoformat(obj)
                                    except ValueError:
                                        return obj
                            elif isinstance(obj, (list, tuple)):
                                return [parse_datetime(item) for item in obj]
                            elif isinstance(obj, dict):
                                return {k: parse_datetime(v) for k, v in obj.items()}
                            return obj
                        
                        parsed_data = parse_datetime(data)
                        logger.info("Datos cargados exitosamente")
                        return parsed_data
                    return None
                except Exception as e:
                    logger.warning(f"Intento {attempt + 1} fallido al cargar: {str(e)}")
                    if attempt == max_retries - 1:
                        logger.error(f"Error al cargar después de {max_retries} intentos: {str(e)}")
                        st.error("Error al cargar datos. Intente recargar la página.")
                        return None
                    time.sleep(1)  # Esperar 1 segundo antes de reintentar
        except Exception as e:
            logger.error(f"Error inesperado al cargar: {str(e)}")
            st.error("Error al cargar datos del usuario")
    
    return None

def load_user_profile():
    if 'user' in st.session_state and st.session_state.user:
        try:
            response = supabase.table('user_profiles').select('*').eq(
                'user_id', st.session_state.user.user.id
            ).execute()
            
            if response.data:
                return response.data[0]
        except Exception as e:
            logger.error(f"Error al cargar perfil: {str(e)}")
    
    return None

# Modificar la función auto_save()
def auto_save():
    if 'user' in st.session_state and st.session_state.user and 'pomodoro_state' in st.session_state:
        try:
            # Guardar cada 5 segundos o cuando hay cambios importantes
            now = datetime.datetime.now()
            last_saved = st.session_state.get('last_saved', datetime.datetime.min)
            
            if (now - last_saved).total_seconds() > 5 or st.session_state.get('force_save', False):
                if save_user_data():
                    st.session_state.last_saved = now
                    if 'force_save' in st.session_state:
                        del st.session_state['force_save']
        except Exception as e:
            logger.error(f"Error en auto-guardado: {str(e)}")

# ==============================================
# Funciones del temporizador mejoradas
# ==============================================

def format_time(seconds):
    mins, secs = divmod(int(seconds), 60)
    return f"{mins:02d}:{secs:02d}"

def get_phase_color(phase):
    colors = {
        "Trabajo": '#e74c3c',
        'Descanso Corto': '#2ecc71',
        'Descanso Largo': '#3498db'
    }
    return colors.get(phase, "#e74c3c")

def get_phase_duration(phase):
    state = st.session_state.pomodoro_state
    if phase == "Trabajo":
        return state['work_duration']
    elif phase == "Descanso Corto":
        return state['short_break']
    elif phase == "Descanso Largo":
        return state['long_break']
    return state['work_duration']

def determine_next_phase(was_work):
    state = st.session_state.pomodoro_state
    if not was_work:
        return "Trabajo"
    
    if state['session_count'] % state['sessions_before_long'] == 0:
        return "Descanso Largo"
    return "Descanso Corto"

def update_timer(state):
    try:
        if state['timer_running'] and not state['timer_paused']:
            current_time = time.monotonic()
            elapsed = current_time - state['last_update']
            state['last_update'] = current_time

            state['remaining_time'] -= elapsed
            state['total_active_time'] += elapsed

            if state['remaining_time'] <= 0:
                handle_phase_completion(state)
    except Exception as e:
        logger.error(f"Error en update_timer: {str(e)}")
        st.error("Error en el temporizador. Reiniciando...")
        reset_timer(state)

def reset_timer(state):
    state['timer_running'] = False
    state['timer_paused'] = False
    state['remaining_time'] = get_phase_duration(state['current_phase'])
    state['total_active_time'] = 0
    state['start_time'] = None
    state['paused_time'] = None
    state['timer_start'] = None
    state['last_update'] = None
    save_user_data()

def handle_phase_completion(state):
    was_work = state['current_phase'] == "Trabajo"
    
    if was_work:
        state['session_count'] += 1
        if state['total_active_time'] >= 0.1:
            log_session()
        
        if state['session_count'] >= state['total_sessions']:
            st.success("¡Todas las sesiones completadas!")
            state['session_count'] = 0
    
    state['current_phase'] = determine_next_phase(was_work)
    state['remaining_time'] = get_phase_duration(state['current_phase'])
    state['total_active_time'] = 0
    
    if was_work:
        st.toast("¡Pomodoro completado! Tómate un descanso.", icon="🎉")
    else:
        st.toast("¡Descanso completado! Volvamos al trabajo.", icon="💪")
    
    st.rerun()

def log_session():
    state = st.session_state.pomodoro_state
    if state['total_active_time'] >= 0.1:
        minutes = round(state['total_active_time'] / 60, 2)
        log_entry = {
            'Fecha': datetime.datetime.now().date().isoformat(),
            'Hora Inicio': (state['start_time'] or datetime.datetime.now()).strftime("%H:%M:%S"),
            'Tiempo Activo (min)': minutes,
            'Actividad': state['current_activity']
        }
        
        state['session_history'].append(log_entry)
        
        if len(state['session_history']) > 1000:
            state['session_history'] = state['session_history'][-1000:]
        
        update_achievements(state, minutes)
        save_user_data()

def update_achievements(state, minutes):
    if state['current_phase'] == "Trabajo":
        state['achievements']['pomodoros_completed'] += 1
        state['achievements']['total_hours'] += minutes / 60
        
        today = date.today()
        if state['last_session_date'] != today:
            if state['last_session_date'] and (today - state['last_session_date']).days == 1:
                state['achievements']['streak_days'] += 1
            elif not state['last_session_date']:
                state['achievements']['streak_days'] = 1
            else:
                state['achievements']['streak_days'] = 1
            state['last_session_date'] = today

# ==============================================
# Funciones de gestión de tareas
# ==============================================

def generate_task_id(state):
    """Genera un ID único para tareas usando UUID"""
    return str(uuid.uuid4())

def add_task(state, name, description="", priority="Media", due_date=None, project=""):
    """
    Añade una nueva tarea al estado con verificación de datos
    """
    try:
        if not name or not isinstance(name, str):
            raise ValueError("Nombre de tarea no válido")
            
        task = {
            'id': generate_task_id(state),
            'name': name.strip(),
            'description': description.strip() if description else "",
            'priority': priority if priority in ["Baja", "Media", "Alta"] else "Media",
            'due_date': due_date if isinstance(due_date, (datetime.date, type(None))) else None,
            'project': project if project in [p['id'] for p in state['projects']] else "",
            'completed': False,
            'created_at': datetime.datetime.now().isoformat(),
            'completed_at': None
        }
        
        state['tasks'].append(task)
        st.session_state['force_save'] = True
        logger.info(f"Tarea añadida: {task['name']}")
        return task
        
    except Exception as e:
        logger.error(f"Error al agregar tarea: {str(e)}")
        st.error("Error al agregar tarea. Verifica los datos.")
        return None

def update_task(state, task_id, **kwargs):
    """
    Actualiza una tarea existente con validación de datos
    """
    try:
        task = next((t for t in state['tasks'] if t['id'] == task_id), None)
        if not task:
            raise ValueError("Tarea no encontrada")
            
        # Validar y actualizar campos
        if 'name' in kwargs:
            task['name'] = kwargs['name'].strip() if kwargs['name'] else task['name']
        
        if 'description' in kwargs:
            task['description'] = kwargs['description'].strip() if kwargs['description'] else task['description']
        
        if 'priority' in kwargs and kwargs['priority'] in ["Baja", "Media", "Alta"]:
            task['priority'] = kwargs['priority']
            
        if 'due_date' in kwargs:
            task['due_date'] = kwargs['due_date'] if isinstance(kwargs['due_date'], (datetime.date, type(None))) else task['due_date']
            
        if 'project' in kwargs:
            task['project'] = kwargs['project'] if kwargs['project'] in [p['id'] for p in state['projects']] else task['project']
            
        if 'completed' in kwargs:
            task['completed'] = bool(kwargs['completed'])
            task['completed_at'] = datetime.datetime.now().isoformat() if kwargs['completed'] else None
            if kwargs['completed']:
                state['achievements']['tasks_completed'] += 1
        
        st.session_state['force_save'] = True
        logger.info(f"Tarea actualizada: {task['name']}")
        return True
        
    except Exception as e:
        logger.error(f"Error al actualizar tarea: {str(e)}")
        st.error("Error al actualizar tarea")
        return False

def delete_task(state, task_id):
    """
    Elimina una tarea con confirmación y registro
    """
    try:
        initial_count = len(state['tasks'])
        state['tasks'] = [t for t in state['tasks'] if t['id'] != task_id]
        
        if len(state['tasks']) < initial_count:
            st.session_state['force_save'] = True
            logger.info(f"Tarea eliminada: ID {task_id}")
            return True
        return False
    except Exception as e:
        logger.error(f"Error al eliminar tarea: {str(e)}")
        return False

def add_project(state, name):
    """
    Añade un nuevo proyecto con validación
    """
    try:
        if not name or not isinstance(name, str) or len(name.strip()) < 3:
            raise ValueError("Nombre de proyecto no válido")
            
        # Verificar si el proyecto ya existe
        if any(p['name'].lower() == name.strip().lower() for p in state['projects']):
            raise ValueError("El proyecto ya existe")
            
        project = {
            'id': str(uuid.uuid4()),
            'name': name.strip(),
            'created_at': datetime.datetime.now().isoformat(),
            'task_count': 0
        }
        
        state['projects'].append(project)
        st.session_state['force_save'] = True
        logger.info(f"Proyecto añadido: {project['name']}")
        return project
        
    except Exception as e:
        logger.error(f"Error al agregar proyecto: {str(e)}")
        st.error(f"No se pudo agregar el proyecto: {str(e)}")
        return None

def update_project(state, project_id, new_name):
    """
    Actualiza un proyecto existente
    """
    try:
        project = next((p for p in state['projects'] if p['id'] == project_id), None)
        if not project:
            raise ValueError("Proyecto no encontrado")
            
        if not new_name or not isinstance(new_name, str) or len(new_name.strip()) < 3:
            raise ValueError("Nombre de proyecto no válido")
            
        # Verificar si el nuevo nombre ya existe
        if any(p['name'].lower() == new_name.strip().lower() and p['id'] != project_id for p in state['projects']):
            raise ValueError("Ya existe un proyecto con ese nombre")
            
        old_name = project['name']
        project['name'] = new_name.strip()
        
        # Actualizar referencia en tareas
        for task in state['tasks']:
            if task['project'] == project_id:
                task['project'] = project_id
                
        st.session_state['force_save'] = True
        logger.info(f"Proyecto actualizado: {old_name} -> {project['name']}")
        return True
        
    except Exception as e:
        logger.error(f"Error al actualizar proyecto: {str(e)}")
        st.error(f"No se pudo actualizar el proyecto: {str(e)}")
        return False

def delete_project(state, project_id):
    """
    Elimina un proyecto y actualiza tareas relacionadas
    """
    try:
        project = next((p for p in state['projects'] if p['id'] == project_id), None)
        if not project:
            return False
            
        # Mover tareas a "Sin proyecto"
        tasks_updated = 0
        for task in state['tasks']:
            if task['project'] == project_id:
                task['project'] = ""
                tasks_updated += 1
                
        # Eliminar proyecto
        state['projects'] = [p for p in state['projects'] if p['id'] != project_id]
        
        st.session_state['force_save'] = True
        logger.info(f"Proyecto eliminado: {project['name']} (Tareas actualizadas: {tasks_updated})")
        return True
        
    except Exception as e:
        logger.error(f"Error al eliminar proyecto: {str(e)}")
        st.error("Error al eliminar proyecto")
        return False

# ==============================================
# Interfaz de usuario mejorada
# ==============================================

def timer_tab():
    state = st.session_state.pomodoro_state
    
    with st.form(key='timer_form'):
        # Selector de actividad
        state['current_activity'] = st.selectbox(
            "Actividad",
            state['activities'],
            index=state['activities'].index(state['current_activity']) 
            if state['current_activity'] in state['activities'] else 0
        )

        # Visualización del temporizador
        theme = THEMES[state['current_theme']]
        phase_duration = get_phase_duration(state['current_phase'])
        progress = 1 - (state['remaining_time'] / phase_duration) if phase_duration > 0 else 0

        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=state['remaining_time'],
            number={'suffix': "s", 'font': {'size': 40}},
            gauge={
                'axis': {'range': [0, phase_duration], 'visible': False},
                'bar': {'color': get_phase_color(state['current_phase'])},
                'steps': [{'range': [0, phase_duration], 'color': theme['circle_bg']}]
            },
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': f"{state['current_phase']} - {format_time(state['remaining_time'])}", 'font': {'size': 24}}
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
            start_pause = st.form_submit_button(
                "▶️ Iniciar" if not state['timer_running'] else "⏸️ Pausar",
                use_container_width=True,
                type="primary"
            )

        with col2:
            if state['timer_running']:
                pause_resume = st.form_submit_button(
                    "⏸️ Pausar" if not state['timer_paused'] else "▶️ Reanudar",
                    use_container_width=True
                )
            else:
                st.form_submit_button("⏸️ Pausar", disabled=True, use_container_width=True)

        with col3:
            skip = st.form_submit_button("⏭️ Saltar Fase", use_container_width=True)

        st.write(f"Sesiones completadas: {state['session_count']}/{state['total_sessions']}")

    # Manejo de eventos
    if start_pause:
        if not state['timer_running']:
            state['timer_running'] = True
            state['timer_paused'] = False
            state['start_time'] = datetime.datetime.now()
            state['total_active_time'] = 0
            state['timer_start'] = time.monotonic()
            state['last_update'] = time.monotonic()
        else:
            state['timer_running'] = False
        st.rerun()
    
    elif 'pause_resume' in locals() and pause_resume:
        if state['timer_running'] and not state['timer_paused']:
            state['timer_paused'] = True
            state['paused_time'] = time.monotonic()
        elif state['timer_paused']:
            state['timer_paused'] = False
            pause_duration = time.monotonic() - state['paused_time']
            state['timer_start'] += pause_duration
            state['last_update'] = time.monotonic()
        st.rerun()
    
    elif skip:
        was_work = state['current_phase'] == "Trabajo"
        
        if was_work:
            state['session_count'] += 1
            if state['total_active_time'] >= 0.1:
                log_session()
            
            if state['session_count'] >= state['total_sessions']:
                st.success("¡Todas las sesiones completadas!")
                state['session_count'] = 0
        
        state['current_phase'] = determine_next_phase(was_work)
        state['remaining_time'] = get_phase_duration(state['current_phase'])
        state['total_active_time'] = 0
        state['timer_running'] = False
        state['timer_paused'] = False
        st.rerun()

    # Actualización del temporizador
    update_timer(state)

def tasks_tab():
    state = st.session_state.pomodoro_state
    
    st.title("📋 Gestión de Tareas")
    
    # Formulario para agregar/editar tarea
    with st.expander("➕ Agregar Nueva Tarea", expanded=state['editing_task_id'] is not None):
        editing_task = None
        if state['editing_task_id'] is not None:
            for task in state['tasks']:
                if task['id'] == state['editing_task_id']:
                    editing_task = task
                    break
        
        with st.form("task_form"):
            if editing_task:
                st.subheader("✏️ Editar Tarea")
            else:
                st.subheader("➕ Nueva Tarea")
            
            name = st.text_input("Nombre de la tarea", 
                                value=editing_task['name'] if editing_task else "")
            description = st.text_area("Descripción", 
                                    value=editing_task['description'] if editing_task else "")
            
            col1, col2 = st.columns(2)
            with col1:
                priority = st.selectbox(
                    "Prioridad",
                    ["Baja", "Media", "Alta"],
                    index=["Baja", "Media", "Alta"].index(editing_task['priority']) if editing_task else 1
                )
            
            with col2:
                due_date = st.date_input(
                    "Fecha de vencimiento",
                    value=editing_task['due_date'] if editing_task and editing_task['due_date'] else datetime.date.today()
                )
            
            # Selector de proyecto
            project_options = [""] + [project['name'] for project in state['projects']]
            project_index = 0
            if editing_task and editing_task['project']:
                for i, project in enumerate(state['projects']):
                    if project['name'] == editing_task['project']:
                        project_index = i + 1
                        break
            
            project = st.selectbox(
                "Proyecto",
                project_options,
                index=project_index
            )
            
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("💾 Guardar"):
                    if name:
                        if editing_task:
                            update_task(state, editing_task['id'], name, description, priority, due_date, project)
                            st.success("Tarea actualizada!")
                        else:
                            add_task(state, name, description, priority, due_date, project)
                            st.success("Tarea agregada!")
                        state['editing_task_id'] = None
                        st.rerun()
                    else:
                        st.error("El nombre de la tarea es obligatorio")
            
            with col2:
                if st.form_submit_button("❌ Cancelar"):
                    state['editing_task_id'] = None
                    st.rerun()
    
    # Gestión de proyectos
    with st.expander("📂 Gestión de Proyectos"):
        st.subheader("Proyectos")
        
        # Formulario para agregar/editar proyecto
        editing_project = None
        if state['editing_project_id'] is not None:
            for project in state['projects']:
                if project['id'] == state['editing_project_id']:
                    editing_project = project
                    break
        
        with st.form("project_form"):
            if editing_project:
                st.write("✏️ Editar proyecto")
                project_name = st.text_input("Nombre del proyecto", value=editing_project['name'])
            else:
                st.write("➕ Nuevo proyecto")
                project_name = st.text_input("Nombre del proyecto")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("💾 Guardar"):
                    if project_name:
                        if editing_project:
                            update_project(state, editing_project['id'], project_name)
                            st.success("Proyecto actualizado!")
                        else:
                            add_project(state, project_name)
                            st.success("Proyecto agregado!")
                        state['editing_project_id'] = None
                        st.rerun()
                    else:
                        st.error("El nombre del proyecto es obligatorio")
            
            with col2:
                if st.form_submit_button("❌ Cancelar"):
                    state['editing_project_id'] = None
                    st.rerun()
        
        # Lista de proyectos
        if state['projects']:
            st.write("---")
            st.write("Lista de proyectos:")
            for project in state['projects']:
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.write(f"• {project['name']}")
                with col2:
                    if st.button("✏️", key=f"edit_project_{project['id']}"):
                        state['editing_project_id'] = project['id']
                        st.rerun()
                with col3:
                    if st.button("🗑️", key=f"delete_project_{project['id']}"):
                        delete_project(state, project['id'])
                        st.success("Proyecto eliminado!")
                        st.rerun()
        else:
            st.info("No hay proyectos creados")
    
    # Lista de tareas
    st.subheader("📝 Lista de Tareas")
    
    # Filtros
    col1, col2, col3 = st.columns(3)
    with col1:
        filter_status = st.selectbox("Filtrar por estado", ["Todas", "Pendientes", "Completadas"])
    with col2:
        filter_priority = st.selectbox("Filtrar por prioridad", ["Todas", "Baja", "Media", "Alta"])
    with col3:
        project_options = ["Todos"] + [project['name'] for project in state['projects']]
        filter_project = st.selectbox("Filtrar por proyecto", project_options)
    
    # Aplicar filtros
    filtered_tasks = state['tasks']
    if filter_status == "Pendientes":
        filtered_tasks = [task for task in filtered_tasks if not task['completed']]
    elif filter_status == "Completadas":
        filtered_tasks = [task for task in filtered_tasks if task['completed']]
    
    if filter_priority != "Todas":
        filtered_tasks = [task for task in filtered_tasks if task['priority'] == filter_priority]
    
    if filter_project != "Todos":
        filtered_tasks = [task for task in filtered_tasks if task['project'] == filter_project]
    
    # Mostrar tareas
    if not filtered_tasks:
        st.info("No hay tareas que coincidan con los filtros")
    else:
        for task in filtered_tasks:
            with st.container(border=True):
                col1, col2 = st.columns([4, 1])
                with col1:
                    status_icon = "✅ " if task['completed'] else "⏳ "
                    priority_color = {
                        "Baja": "blue",
                        "Media": "orange",
                        "Alta": "red"
                    }
                    
                    st.write(f"{status_icon} **{task['name']}**")
                    st.caption(f"📅 Vence: {task['due_date'].strftime('%d/%m/%Y') if task['due_date'] else 'Sin fecha'} | "
                            f"🔺 Prioridad: :{priority_color[task['priority']]}[{task['priority']}] | "
                            f"📂 Proyecto: {task['project'] or 'Ninguno'}")
                    
                    if task['description']:
                        st.write(f"📝 {task['description']}")
                
                with col2:
                    if not task['completed']:
                        if st.button("✅ Completar", key=f"complete_{task['id']}"):
                            complete_task(state, task['id'])
                            st.success("Tarea completada!")
                            st.rerun()
                    
                    col2_1, col2_2 = st.columns(2)
                    with col2_1:
                        if st.button("✏️", key=f"edit_{task['id']}"):
                            state['editing_task_id'] = task['id']
                            st.rerun()
                    with col2_2:
                        if st.button("🗑️", key=f"delete_{task['id']}"):
                            delete_task(state, task['id'])
                            st.success("Tarea eliminada!")
                            st.rerun()

def stats_tab():
    state = st.session_state.pomodoro_state
    
    st.title("📊 Estadísticas")
    
    if not state['session_history']:
        st.warning("No hay datos de sesiones registrados")
        return
    
    # Métricas principales
    col1, col2, col3 = st.columns(3)
    with col1:
        total_pomodoros = state['achievements']['pomodoros_completed']
        st.metric("Pomodoros completados", total_pomodoros)
    with col2:
        total_hours = state['achievements']['total_hours']
        st.metric("Horas totales", f"{total_hours:.1f}")
    with col3:
        streak = state['achievements']['streak_days']
        st.metric("Racha actual (días)", streak)
    
    # Gráfico de actividad por día
    try:
        df = pd.DataFrame(state['session_history'])
        df['Fecha'] = pd.to_datetime(df['Fecha'])
        df['Duración (h)'] = df['Tiempo Activo (min)'] / 60
        
        daily = df.groupby('Fecha')['Duración (h)'].sum().reset_index()
        
        fig = px.bar(daily, x='Fecha', y='Duración (h)',
                     title="Tiempo por día",
                     labels={'Fecha': 'Fecha', 'Duración (h)': 'Horas'})
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Error al generar gráficos: {str(e)}")

def settings_tab():
    state = st.session_state.pomodoro_state
    
    st.title("⚙️ Configuración")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("⏱️ Temporizador")
        work_min = st.number_input("Trabajo (min)", min_value=1, max_value=120, 
                                 value=state['work_duration'] // 60)
        short_min = st.number_input("Descanso corto (min)", min_value=1, max_value=30, 
                                  value=state['short_break'] // 60)
        long_min = st.number_input("Descanso largo (min)", min_value=1, max_value=60, 
                                 value=state['long_break'] // 60)
        sessions_long = st.number_input("Sesiones antes de descanso largo", min_value=1, 
                                      max_value=10, value=state['sessions_before_long'])
        total_sess = st.number_input("Sesiones totales", min_value=1, 
                                   max_value=20, value=state['total_sessions'])

        if st.button("💾 Guardar configuración"):
            state['work_duration'] = work_min * 60
            state['short_break'] = short_min * 60
            state['long_break'] = long_min * 60
            state['sessions_before_long'] = sessions_long
            state['total_sessions'] = total_sess
            
            if state['current_phase'] == "Trabajo":
                state['remaining_time'] = state['work_duration']
            elif state['current_phase'] == "Descanso Corto":
                state['remaining_time'] = state['short_break']
            elif state['current_phase'] == "Descanso Largo":
                state['remaining_time'] = state['long_break']
            
            save_user_data()
            st.success("Configuración guardada!")
            st.rerun()

    with col2:
        st.subheader("👤 Perfil de Usuario")
        
        # Cargar perfil de usuario
        user_profile = load_user_profile()
        if user_profile:
            current_username = user_profile.get('username', '')
            current_display_name = user_profile.get('display_name', '')
        else:
            current_username = ''
            current_display_name = ''
        
        new_username = st.text_input("Nombre de usuario", value=current_username)
        new_display_name = st.text_input("Nombre para mostrar", value=current_display_name)
        
        if st.button("💾 Actualizar Perfil"):
            if not validate_username(new_username):
                st.error("El nombre de usuario debe tener entre 3 y 20 caracteres y solo puede contener letras, números, guiones y guiones bajos")
            else:
                try:
                    user_id = st.session_state.user.user.id
                    supabase.table('user_profiles').upsert({
                        'user_id': user_id,
                        'username': new_username,
                        'display_name': new_display_name or new_username,
                        'updated_at': datetime.datetime.now().isoformat()
                    }).execute()
                    
                    # Actualizar estado local
                    state['username'] = new_username
                    state['display_name'] = new_display_name or new_username
                    
                    st.success("Perfil actualizado!")
                    save_user_data()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al actualizar perfil: {str(e)}")
        
        st.subheader("🎨 Apariencia")
        theme = st.selectbox("Tema", list(THEMES.keys()), 
                           index=list(THEMES.keys()).index(state['current_theme']))
        
        if theme != state['current_theme']:
            state['current_theme'] = theme
            st.rerun()
        
        st.subheader("📝 Actividades")
        new_activity = st.text_input("Nueva actividad")
        if st.button("➕ Añadir") and new_activity:
            if new_activity not in state['activities']:
                state['activities'].append(new_activity)
                save_user_data()
                st.rerun()
        
        if state['activities']:
            activity_to_remove = st.selectbox("Eliminar actividad", state['activities'])
            if st.button("➖ Eliminar"):
                state['activities'].remove(activity_to_remove)
                if state['current_activity'] == activity_to_remove:
                    state['current_activity'] = ""
                save_user_data()
                st.rerun()

def sidebar():
    auth_section()
    
    if 'user' in st.session_state and st.session_state.user:
        state = st.session_state.pomodoro_state
        
        st.sidebar.title(f"🍅 Pomodoro Pro")
        
        if state['display_name']:
            st.sidebar.write(f"Bienvenido, {state['display_name']}")
            if state['username']:
                st.sidebar.caption(f"@{state['username']}")
        else:
            st.sidebar.write(f"Bienvenido, {st.session_state.user.user.email}")
        
        st.sidebar.radio(
            "Navegación",
            ["🍅 Temporizador", "📋 Tareas", "📊 Estadísticas", "⚙️ Configuración"],
            key='current_tab'
        )
        
        # Botón de cierre de sesión mejorado
        if st.sidebar.button("Cerrar sesión", key="logout_button"):
            # Crear un contenedor para mensajes
            logout_container = st.empty()
            logout_container.info("Guardando datos antes de cerrar sesión...")
            
            try:
                # Guardar datos de forma síncrona
                if 'pomodoro_state' in st.session_state:
                    save_success = save_user_data()
                    if not save_success:
                        logout_container.error("Error al guardar datos. Intenta nuevamente.")
                        return
                
                # Pequeña pausa para asegurar el guardado
                time.sleep(1)
                
                # Cerrar sesión en Supabase
                supabase.auth.sign_out()
                
                # Limpiar solo lo necesario
                keys_to_keep = ['_theme', '_last_flush_time']  # Mantener configuraciones de Streamlit
                new_state = {k: v for k, v in st.session_state.items() if k in keys_to_keep}
                st.session_state.clear()
                st.session_state.update(new_state)
                
                # Mostrar confirmación
                logout_container.success("Sesión cerrada correctamente. Redirigiendo...")
                time.sleep(1)
                st.rerun()
                
            except Exception as e:
                logger.error(f"Error en cierre de sesión: {str(e)}")
                logout_container.error(f"Error al cerrar sesión: {str(e)}")
                
def main():
    # Inicialización del estado con verificación mejorada
    if 'pomodoro_state' not in st.session_state:
        try:
            # Mostrar indicador de carga
            with st.spinner("Cargando datos..."):
                # Primero intentar cargar de Supabase si el usuario está autenticado
                if 'user' in st.session_state and st.session_state.user:
                    user_data = load_user_data()
                    
                    if user_data:
                        # Validar y limpiar los datos cargados
                        validated_data = validate_state(user_data)
                        st.session_state.pomodoro_state = validated_data
                        logger.info("Datos cargados desde Supabase")
                    else:
                        # Usar estado por defecto si no hay datos
                        st.session_state.pomodoro_state = get_default_state()
                        logger.info("Usando estado por defecto (sin datos previos)")
                    
                    # Forzar guardado inicial para crear registro si no existe
                    if save_user_data():
                        logger.info("Guardado inicial completado")
                    else:
                        logger.warning("Hubo un problema con el guardado inicial")
                else:
                    # Usuario no autenticado - estado por defecto
                    st.session_state.pomodoro_state = get_default_state()
                    logger.info("Estado inicializado para usuario no autenticado")
                
                # Cargar perfil de usuario si está autenticado
                if 'user' in st.session_state and st.session_state.user:
                    profile = load_user_profile()
                    if profile:
                        st.session_state.pomodoro_state['username'] = profile.get('username', '')
                        st.session_state.pomodoro_state['display_name'] = profile.get('display_name', '')
                        logger.info("Perfil de usuario cargado")
        except Exception as e:
            logger.error(f"Error crítico al inicializar estado: {str(e)}")
            st.error("Error al cargar datos. Usando configuración por defecto.")
            st.session_state.pomodoro_state = get_default_state()
            
            if st.button("Reintentar carga de datos"):
                st.session_state.clear()
                st.rerun()

    # Verificar y mantener la sesión activa con manejo mejorado
    if 'user' in st.session_state and st.session_state.user:
        try:
            # Verificar si el token sigue siendo válido
            user = supabase.auth.get_user()
            if not user:
                logger.warning("Sesión expirada o inválida - limpiando estado")
                # Limpiar solo lo necesario manteniendo configuraciones
                keys_to_keep = ['_theme', '_last_flush_time']
                new_state = {k: v for k, v in st.session_state.items() if k in keys_to_keep}
                st.session_state.clear()
                st.session_state.update(new_state)
                st.rerun()
        except Exception as e:
            logger.error(f"Error al verificar sesión: {str(e)}")
            # Limpieza parcial del estado
            if 'user' in st.session_state:
                del st.session_state['user']
            if 'pomodoro_state' in st.session_state:
                del st.session_state['pomodoro_state']
            st.rerun()
    
    # Barra lateral
    sidebar()
    
    # Contenido principal
    if 'user' in st.session_state and st.session_state.user:
        try:
            # Guardado automático mejorado
            if 'last_saved' not in st.session_state:
                st.session_state.last_saved = datetime.datetime.now()
            
            # Guardar cada 10 segundos o cuando hay cambios importantes
            now = datetime.datetime.now()
            if (now - st.session_state.last_saved).total_seconds() > 10 or st.session_state.get('force_save', False):
                if save_user_data():
                    st.session_state.last_saved = now
                    if 'force_save' in st.session_state:
                        del st.session_state['force_save']
            
            # Mostrar pestaña seleccionada
            current_tab = st.session_state.get('current_tab', "🍅 Temporizador")
            
            if current_tab == "🍅 Temporizador":
                timer_tab()
            elif current_tab == "📋 Tareas":
                tasks_tab()
            elif current_tab == "📊 Estadísticas":
                stats_tab()
            elif current_tab == "⚙️ Configuración":
                settings_tab()
            
            # Verificación periódica de consistencia de datos
            if 'last_validation' not in st.session_state or \
               (datetime.datetime.now() - st.session_state.last_validation).seconds > 60:
                st.session_state.pomodoro_state = validate_state(st.session_state.pomodoro_state)
                st.session_state.last_validation = datetime.datetime.now()
                
        except Exception as e:
            logger.error(f"Error en la interfaz principal: {str(e)}")
            st.error("¡Oops! Algo salió mal. Por favor recarga la página.")
            if st.button("Recargar aplicación"):
                # Limpieza selectiva en lugar de clear() completo
                keys_to_keep = ['_theme', '_last_flush_time', 'pomodoro_state']
                new_state = {k: v for k, v in st.session_state.items() if k in keys_to_keep}
                st.session_state.clear()
                st.session_state.update(new_state)
                st.rerun()
    
    else:
        # Pantalla de bienvenida para usuarios no autenticados
        show_guest_content()

def show_guest_content():
    """Muestra el contenido para usuarios no autenticados"""
    st.title("🍅 Pomodoro Pro")
    st.markdown("""
    ### ¡Bienvenido a Pomodoro Pro!
    
    Para comenzar:
    1. Crea una cuenta o inicia sesión en la barra lateral
    2. Configura tus tiempos preferidos
    3. Comienza a mejorar tu productividad
    
    **Características:**
    - Temporizador Pomodoro personalizable
    - Gestión de tareas y proyectos
    - Seguimiento de tu progreso
    - Estadísticas detalladas
    - Almacenamiento en la nube
    - Perfil de usuario personalizable
    """)
    
    # Sección de demostración
    st.divider()
    st.subheader("Demostración del Temporizador")
    
    # Mostrar un temporizador de ejemplo (solo visualización)
    demo_time = st.slider("Tiempo de demostración (minutos)", 1, 60, 25)
    demo_phase = st.selectbox("Fase de demostración", ["Trabajo", "Descanso Corto", "Descanso Largo"])
    
    # Visualización del temporizador de demo
    theme = THEMES['Claro']  # Usar tema claro para la demo
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=demo_time * 60,
        number={'suffix': "s", 'font': {'size': 40}},
        gauge={
            'axis': {'range': [0, demo_time * 60], 'visible': False},
            'bar': {'color': get_phase_color(demo_phase)},
            'steps': [{'range': [0, demo_time * 60], 'color': theme['circle_bg']}]
        },
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': f"{demo_phase} - {format_time(demo_time * 60)}", 'font': {'size': 24}}
    ))
    fig.update_layout(height=300, margin=dict(l=10, r=10, t=80, b=10))
    st.plotly_chart(fig, use_container_width=True)
    
    # Sección de información adicional
    st.divider()
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("¿Qué es Pomodoro?")
        st.markdown("""
        La Técnica Pomodoro es un método de gestión del tiempo que:
        - Divide el trabajo en intervalos de 25 minutos
        - Separa cada intervalo con breves descansos
        - Mejora la concentración y productividad
        - Reduce la fatiga mental
        """)
    
    with col2:
        st.subheader("Beneficios Clave")
        st.markdown("""
        - ✅ Mayor enfoque en las tareas
        - ⏱️ Mejor gestión del tiempo
        - 📈 Seguimiento de tu progreso
        - 🧠 Menos estrés y fatiga
        """)
    
    # Footer
    st.divider()
    st.markdown("""
    <div style="text-align: center; color: #666; font-size: 0.9em;">
    Pomodoro Pro v2.1 | Desarrollado con Streamlit y Supabase | © 2023
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    # Verificar y mantener la sesión activa
    if 'user' in st.session_state and st.session_state.user:
        try:
            # Verificar si el token sigue siendo válido
            user = supabase.auth.get_user()
            if not user:
                st.session_state.user = None
                st.session_state.pomodoro_state = None
                st.rerun()
        except Exception as e:
            logger.error(f"Error al verificar sesión: {str(e)}")
            st.session_state.user = None
            st.session_state.pomodoro_state = None
            st.rerun()
    
    try:
        main()
    except Exception as e:
        logger.error(f"Error crítico: {str(e)}")
        st.error("¡Oops! Algo salió mal. Por favor recarga la página.")
        if st.button("Recargar aplicación"):
            st.session_state.clear()
            st.rerun()
