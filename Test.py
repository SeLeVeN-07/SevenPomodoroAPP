# -*- coding: utf-8 -*-
"""
Pomodoro Pro - Versión Mejorada y Corregida
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
SUPABASE_KEY = os.getenv('SUPABASE_KEY', "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZE...")

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
            'total_hours': 0
        },
        'last_session_date': None,
        'session_history': [],
        'username': "",
        'display_name': ""
    }

# ==============================================
# Funciones de autenticación mejoradas
# ==============================================

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

def save_user_data():
    if 'user' in st.session_state and st.session_state.user and 'pomodoro_state' in st.session_state:
        try:
            state = st.session_state.pomodoro_state.copy()
            
            def convert_datetime(obj):
                if isinstance(obj, (datetime.datetime, datetime.date)):
                    return obj.isoformat()
                elif isinstance(obj, (list, tuple)):
                    return [convert_datetime(item) for item in obj]
                elif isinstance(obj, dict):
                    return {k: convert_datetime(v) for k, v in obj.items()}
                return obj
            
            serialized_data = convert_datetime(state)
            
            response = supabase.table('user_data').upsert({
                'user_id': st.session_state.user.user.id,
                'email': st.session_state.user.user.email,
                'pomodoro_data': serialized_data,
                'last_updated': datetime.datetime.now().isoformat()
            }).execute()
            
            st.session_state.last_saved = datetime.datetime.now()
            return True
        except Exception as e:
            logger.error(f"Error al guardar: {str(e)}")
            return False
    return False

def load_user_data():
    if 'user' in st.session_state and st.session_state.user:
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
                
                return parse_datetime(data)
        except Exception as e:
            logger.error(f"Error al cargar datos: {str(e)}")
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

def auto_save():
    if 'user' in st.session_state and st.session_state.user and 'pomodoro_state' in st.session_state:
        try:
            if 'last_saved' not in st.session_state or \
               (datetime.datetime.now() - st.session_state.last_saved).seconds > 30:
                if save_user_data():
                    st.session_state.last_saved = datetime.datetime.now()
                    st.toast("Datos guardados automáticamente", icon="💾")
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

def sidebar():
    auth_section()
    
    if 'user' in st.session_state and st.session_state.user:
        state = st.session_state.pomodoro_state
        
        # Mostrar información del usuario
        st.sidebar.title(f"🍅 Pomodoro Pro")
        if state['display_name']:
            st.sidebar.write(f"Bienvenido, {state['display_name']}")
        else:
            st.sidebar.write(f"Bienvenido, {st.session_state.user.user.email}")
        
        # Navegación
        st.sidebar.radio(
            "Navegación",
            ["🍅 Temporizador", "📊 Estadísticas", "⚙️ Configuración"],
            key='current_tab'
        )
        
        # Cerrar sesión
        if st.sidebar.button("Cerrar sesión"):
            supabase.auth.sign_out()
            st.session_state.clear()
            st.rerun()

def main():
    # Inicialización del estado
    if 'pomodoro_state' not in st.session_state:
        st.session_state.pomodoro_state = get_default_state()
        
        # Cargar datos del usuario si está autenticado
        if 'user' in st.session_state and st.session_state.user:
            user_data = load_user_data()
            if user_data:
                st.session_state.pomodoro_state.update(user_data)
            
            profile = load_user_profile()
            if profile:
                st.session_state.pomodoro_state['username'] = profile.get('username', '')
                st.session_state.pomodoro_state['display_name'] = profile.get('display_name', '')
    
    # Barra lateral
    sidebar()
    
    # Contenido principal
    if 'user' in st.session_state and st.session_state.user:
        # Guardado automático
        auto_save()
        
        # Mostrar pestaña seleccionada
        current_tab = st.session_state.get('current_tab', "🍅 Temporizador")
        
        if current_tab == "🍅 Temporizador":
            timer_tab()
        elif current_tab == "📊 Estadísticas":
            stats_tab()
        elif current_tab == "⚙️ Configuración":
            settings_tab()
    
    else:
        # Pantalla de bienvenida para usuarios no autenticados
        st.title("🍅 Pomodoro Pro")
        st.markdown("""
        ### ¡Bienvenido a Pomodoro Pro!
        
        Para comenzar:
        1. Crea una cuenta o inicia sesión en la barra lateral
        2. Configura tus tiempos preferidos
        3. Comienza a mejorar tu productividad
        
        **Características:**
        - Temporizador Pomodoro personalizable
        - Seguimiento de tu progreso
        - Estadísticas detalladas
        - Almacenamiento en la nube
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
        Pomodoro Pro v2.0 | Desarrollado con Streamlit y Supabase | © 2023
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
        
           
