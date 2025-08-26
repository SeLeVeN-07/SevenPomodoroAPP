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

# Inicializar cliente Supabase
@st.cache_resource
def init_supabase():
    try:
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        client.table('user_data').select('*').limit(1).execute()
        logger.info("Conexión a Supabase establecida correctamente")
        return client
    except Exception as e:
        logger.error(f"Error al conectar con Supabase: {str(e)}")
        st.error(f"Error al conectar con la base de datos: {str(e)}")
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

# Estado por defecto
def get_default_state():
    if 'pomodoro_state' in st.session_state:
        return st.session_state.pomodoro_state
    
    default_state = {
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
        'session_history': [],
        'username': "",
        'display_name': ""
    }
    
    st.session_state.pomodoro_state = default_state
    return default_state

# Funciones de persistencia
def save_user_data():
    if 'user' in st.session_state and st.session_state.user and 'pomodoro_state' in st.session_state:
        try:
            state = st.session_state.pomodoro_state.copy()
            
            def convert_datetime(obj):
                if isinstance(obj, (datetime.datetime, datetime.date)):
                    return obj.isoformat()
                elif isinstance(obj, list):
                    return [convert_datetime(item) for item in obj]
                elif isinstance(obj, dict):
                    return {key: convert_datetime(value) for key, value in obj.items()}
                return obj
            
            serialized_data = convert_datetime(state)
            
            user_id = st.session_state.user.user.id
            response = supabase.table('user_data').upsert({
                'user_id': user_id,
                'email': st.session_state.user.user.email,
                'pomodoro_data': serialized_data,
                'last_updated': datetime.datetime.now().isoformat()
            }).execute()
            
            st.session_state.last_saved = datetime.datetime.now()
            logger.info("Datos guardados en Supabase")
            return True
        except Exception as e:
            logger.error(f"Error al guardar datos: {str(e)}")
            return False
    return False

def load_user_data():
    if 'user' in st.session_state and st.session_state.user:
        try:
            user_id = st.session_state.user.user.id
            response = supabase.table('user_data').select('*').eq('user_id', user_id).execute()
            
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
                    elif isinstance(obj, list):
                        return [parse_datetime(item) for item in obj]
                    elif isinstance(obj, dict):
                        return {key: parse_datetime(value) for key, value in obj.items()}
                    return obj
                
                loaded_data = parse_datetime(data)
                st.session_state.pomodoro_state = loaded_data
                logger.info("Datos cargados desde Supabase")
                return loaded_data
        
        except Exception as e:
            logger.error(f"Error al cargar datos de Supabase: {str(e)}")
            st.error(f"Error al cargar datos: {str(e)}")
    
    if 'pomodoro_state' in st.session_state:
        logger.info("Usando datos locales de session_state")
        return st.session_state.pomodoro_state
    
    logger.info("Cargando estado por defecto")
    return get_default_state()

# Funciones del temporizador
def timer_tab():
    state = st.session_state.pomodoro_state
    
    with st.form(key='timer_form'):
        if state['study_mode'] and state['current_activity']:
            st.header(f"Actividad: {state['current_activity']}")

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

        with col2:
            state['sub_activity'] = ""

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
                'steps': [
                    {'range': [0, phase_duration], 'color': theme['circle_bg']}
                ]
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

        col1, col2, col3 = st.columns(3)

        with col1:
            start_pause = st.form_submit_button(
                "▶️ Iniciar" if not state['timer_running'] else "▶️ Reanudar",
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

    if start_pause:
        handle_timer_start(state)
    elif 'pause_resume' in locals() and pause_resume:
        handle_timer_pause(state)
    elif skip:
        handle_skip_phase(state)

    update_timer(state)

def handle_timer_start(state):
    if not state['timer_running']:
        state['timer_running'] = True
        state['timer_paused'] = False
        state['start_time'] = datetime.datetime.now()
        state['total_active_time'] = 0
        state['timer_start'] = time.monotonic()
        state['last_update'] = time.monotonic()
        st.rerun()

def handle_timer_pause(state):
    if state['timer_running'] and not state['timer_paused']:
        state['timer_paused'] = True
        state['paused_time'] = time.monotonic()
        st.rerun()
    elif state['timer_paused']:
        state['timer_paused'] = False
        pause_duration = time.monotonic() - state['paused_time']
        state['timer_start'] += pause_duration
        state['last_update'] = time.monotonic()
        st.rerun()

def handle_skip_phase(state):
    was_work = state['current_phase'] == "Trabajo"

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
    
    state['current_phase'] = determine_next_phase(was_work)
    state['remaining_time'] = get_phase_duration(state['current_phase'])
    state['total_active_time'] = 0
    state['timer_running'] = False
    state['timer_paused'] = False
    st.rerun()

def update_timer(state):
    if state['timer_running'] and not state['timer_paused']:
        current_time = time.monotonic()
        elapsed = current_time - state['last_update']
        state['last_update'] = current_time

        state['remaining_time'] -= elapsed
        state['total_active_time'] += elapsed

        if state['remaining_time'] <= 0:
            handle_phase_completion(state)

def handle_phase_completion(state):
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
    
    state['current_phase'] = determine_next_phase(was_work)
    state['remaining_time'] = get_phase_duration(state['current_phase'])
    state['total_active_time'] = 0
    
    if was_work:
        st.toast("¡Pomodoro completado! Tómate un descanso.", icon="🎉")
    else:
        st.toast("¡Descanso completado! Volvamos al trabajo.", icon="💪")
    
    st.success(f"¡Fase completada! Iniciando: {state['current_phase']}")
    st.rerun()

def determine_next_phase(was_work):
    state = st.session_state.pomodoro_state
    if not was_work:
        return "Trabajo"
    
    if state['session_count'] % state['sessions_before_long'] == 0:
        return "Descanso Largo"
    return "Descanso Corto"

def get_phase_duration(phase):
    state = st.session_state.pomodoro_state
    if phase == "Trabajo":
        return state['work_duration']
    elif phase == "Descanso Corto":
        return state['short_break']
    elif phase == "Descanso Largo":
        return state['long_break']
    else:
        return state['work_duration']

def log_session():
    state = st.session_state.pomodoro_state
    if state['total_active_time'] >= 0.1:
        minutes = round(state['total_active_time'] / 60, 2)
        log_entry = {
            'Fecha': datetime.datetime.now().date().isoformat(),
            'Hora Inicio': (state['start_time'] or datetime.datetime.now()).strftime("%H:%M:%S"),
            'Tiempo Activo (min)': minutes,
            'Actividad': state['current_activity'],
            'Proyecto': state['current_project'],
            'Tarea': state.get('current_task', '')
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

# Funciones de autenticación
def auth_section():
    if 'user' not in st.session_state:
        st.session_state.user = None
    
    if not st.session_state.user:
        tab1, tab2 = st.tabs(["Iniciar Sesión", "Registrarse"])
        
        with tab1:
            with st.form("login_form"):
                email = st.text_input("Correo electrónico")
                password = st.text_input("Contraseña", type="password")
                
                if st.form_submit_button("Ingresar"):
                    if not email or not password:
                        st.error("Por favor completa todos los campos")
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
            with st.form("signup_form"):
                new_email = st.text_input("Correo electrónico (registro)")
                new_password = st.text_input("Contraseña (registro)", type="password")
                confirm_password = st.text_input("Confirmar contraseña", type="password")
                username = st.text_input("Nombre de usuario")
                display_name = st.text_input("Nombre para mostrar (opcional)")
                
                if st.form_submit_button("Crear cuenta"):
                    if not new_email or not new_password or not confirm_password or not username:
                        st.error("Por favor completa todos los campos obligatorios")
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
                                supabase.table('user_profiles').insert({
                                    'user_id': user_id,
                                    'email': new_email,
                                    'username': username,
                                    'display_name': display_name or username,
                                    'created_at': datetime.datetime.now().isoformat()
                                }).execute()
                            
                            st.success("¡Cuenta creada! Por favor inicia sesión.")
                        except Exception as e:
                            st.error(f"Error al registrar: {str(e)}")
    else:
        if st.sidebar.button("Cerrar sesión"):
            supabase.auth.sign_out()
            st.session_state.user = None
            st.session_state.pomodoro_state = None
            st.rerun()

def check_session():
    if 'user' in st.session_state and st.session_state.user:
        try:
            user = supabase.auth.get_user()
            if not user:
                st.session_state.user = None
                st.rerun()
        except:
            st.session_state.user = None
            st.rerun()

# Función principal
def main():
    if 'pomodoro_state' not in st.session_state:
        if 'user' in st.session_state and st.session_state.user:
            user_data = load_user_data()
            if user_data:
                st.session_state.pomodoro_state = user_data
            else:
                st.session_state.pomodoro_state = get_default_state()
        else:
            st.session_state.pomodoro_state = get_default_state()
    
    # Barra lateral
    if 'user' in st.session_state and st.session_state.user:
        state = st.session_state.pomodoro_state
        check_session()

        display_name = state.get('display_name', '')
        email = st.session_state.user.user.email
        st.sidebar.title(f"🍅 Pomodoro Pro")
        st.sidebar.write(f"Bienvenido, {display_name or email}")

        st.sidebar.radio(
            "Navegación",
            ["🍅 Temporizador", "📋 Tareas", "📊 Estadísticas", "⚙️ Configuración", "ℹ️ Info"],
            key='sidebar_nav'
        )

        if st.sidebar.button("Cerrar sesión"):
            supabase.auth.sign_out()
            st.session_state.clear()
            st.rerun()
    else:
        auth_section()
    
    # Solo mostrar la aplicación si el usuario está autenticado
    if 'user' in st.session_state and st.session_state.user:
        selected_tab = st.session_state.get('sidebar_nav', "🍅 Temporizador")

        if selected_tab == "🍅 Temporizador":
            timer_tab()
        elif selected_tab == "📊 Estadísticas":
            st.write("Estadísticas (por implementar)")
        elif selected_tab == "📋 Tareas":
            st.write("Gestión de tareas (por implementar)")
        elif selected_tab == "⚙️ Configuración":
            st.write("Configuración (por implementar)")
        elif selected_tab == "ℹ️ Info":
            st.write("Información (por implementar)")
    else:
        st.title("🍅 Pomodoro Pro")
        st.markdown("""
        ### Bienvenido a Pomodoro Pro
        
        Para comenzar a usar la aplicación, por favor:
        1. Crea una cuenta o inicia sesión en la barra lateral
        2. Personaliza tu perfil con nombre de usuario
        3. Tus datos se guardarán automáticamente en la nube
        4. Podrás acceder a tu información desde cualquier dispositivo
        
        **Características principales:**
        - Temporizador Pomodoro configurable
        - Gestión de tareas y proyectos
        - Seguimiento de productividad
        - Estadísticas detalladas
        - Almacenamiento en la nube
        - Perfiles de usuario personalizables
        """)

if __name__ == "__main__":
    main()
