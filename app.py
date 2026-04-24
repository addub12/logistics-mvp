import streamlit as st
import pandas as pd
import pydeck as pdk
from streamlit_gsheets import GSheetsConnection

# 1. Конфигурация страницы
st.set_page_config(page_title="Logistics Standard MVP", layout="wide", initial_sidebar_state="expanded")

# Кастомный дизайн (CSS) - Исправлены цвета текста на белых плашках
st.markdown("""
    <style>
   .main { background-color: #f0f2f6; }
   
   /* Стилизация карточек метрик */
   [data-testid="stMetric"] {
        background-color: #ffffff !important; 
        padding: 20px !important; 
        border-radius: 12px !important; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.07) !important; 
        border-left: 6px solid #0052cc !important;
   }
   
   /* Принудительный цвет для заголовка метрики (Label) */
   [data-testid="stMetricLabel"] > div {
        color: #555555 !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
   }
   
   /* Принудительный цвет для значения метрики (Value) */
   [data-testid="stMetricValue"] > div {
        color: #0052cc !important;
        font-weight: 800 !important;
   }

   .timeline-container { 
        display: flex; 
        justify-content: space-between; 
        margin: 20px 0; 
        padding: 15px; 
        background: #ffffff; 
        border-radius: 8px; 
        border: 1px solid #e0e0e0;
    }
   .step { text-align: center; width: 19%; font-size: 0.7rem; color: #444; }
   .step-icon { 
        width: 22px; height: 22px; 
        border-radius: 50%; 
        margin: 0 auto 5px; 
        line-height: 22px; 
        color: white; 
        font-weight: bold; 
        font-size: 0.8rem;
    }
   .completed { background-color: #28a745; }
   .in-progress { background-color: #ffc107; }
   .planned { background-color: #dee2e6; color: #6c757d; }
   .risk-alert { color: #dc3545; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# 2. Подключение к данным
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=300)
def load_data():
    try:
        shipments = conn.read(worksheet="Main_Shipments")
        docs = conn.read(worksheet="Documents")
        return shipments, docs
    except Exception as e:
        st.error(f"Ошибка чтения данных: {e}")
        return None, None

df_ship, df_docs = load_data()

if df_ship is None:
    st.stop()

# 3. Sidebar (Навигация)
with st.sidebar:
    st.title("📦 Logistics Portal")
    st.info("Тариф: **STANDARD**")
    
    unique_clients = df_ship['client_name'].unique()
    user_company = st.selectbox("Клиент:", unique_clients)
    st.markdown("---")
    st.success("🔔 Telegram Bot: Connected")
    
    menu = st.radio("Разделы:", ["🏠 Обзор", "🚢 Мои грузы", "📑 Документы", "📊 KPI Аналитика"])
    st.markdown("---")
    st.button("💬 Чат с менеджером")

# Фильтр по компании
client_data = df_ship[df_ship['client_name'] == user_company].copy()

# 4. Вкладка: ОБЗОР
if menu == "🏠 Обзор":
    st.header(f"Рабочий стол: {user_company}")
    
    # Метрики
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("В пути сейчас", len(client_data[client_data['status']!= 'Завершено']))
    with m2:
        risks = len(client_data[client_data['eta_predicted'] > client_data['eta_planned']])
        st.metric("Риски задержек", risks, delta=f"{risks} объекта", delta_color="inverse")
    with m3:
        st.metric("На таможне", len(client_data[client_data['status'] == 'Таможня']))
    with m4:
        st.metric("OTIF (тек. мес)", "94.2%")

    # Карта
    st.subheader("География текущих поставок")
    if not client_data.empty:
        view_state = pdk.ViewState(latitude=client_data['lat'].mean(), longitude=client_data['lon'].mean(), zoom=3)
        layer = pdk.Layer(
            "ScatterplotLayer",
            client_data,
            get_position=["lon", "lat"],
            get_color=[0, 82, 204, 200],
            get_radius=150000,
            pickable=True
        )
        st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip={"text": "Груз: {shipment_id}\nСтатус: {status}"}))

# 5. Вкладка: МОИ ГРУЗЫ
elif menu == "🚢 Мои грузы":
    st.header("Активные перевозки")
    
    # Функция для генерации динамического таймлайна в зависимости от статуса
    def generate_timeline(status):
        stages = ["Склад", "Порт/ЖД", "В пути", "Таможня", "Финиш"]
        
        status_map = {
            "Склад консолидации": 0,
            "В пути": 2, 
            "Таможня": 3,
            "Завершено": 4
        }
        
        current_stage_index = status_map.get(status, 2) 
        
        timeline_html = '<div class="timeline-container">'
        
        for i, stage in enumerate(stages):
            if i < current_stage_index:
                timeline_html += f'<div class="step"><div class="step-icon completed">✓</div>{stage}</div>'
            elif i == current_stage_index:
                if status == "Завершено":
                     timeline_html += f'<div class="step"><div class="step-icon completed">✓</div>{stage}</div>'
                else:
                    timeline_html += f'<div class="step"><div class="step-icon in-progress">...</div>{stage}</div>'
            else:
                timeline_html += f'<div class="step"><div class="step-icon planned">○</div>{stage}</div>'
                
        timeline_html += '</div>'
        return timeline_html

    for _, ship in client_data.iterrows():
        is_delayed = ship['eta_predicted'] > ship['eta_planned']
        status_icon = "🔴" if is_delayed else "🟢"
        
        with st.expander(f"{status_icon} ID {ship['shipment_id']} | {ship['origin']} ➔ {ship['destination']}"):
            c1, c2 = st.columns([5, 6])
            with c1:
                # Отрисовка динамического таймлайна
                st.markdown(generate_timeline(ship['status']), unsafe_allow_html=True)
                st.write(f"**Текущий статус:** {ship['status']}")
            
            with c2:
                st.write(f"**План (ETA):** {ship['eta_planned']}")
                p_eta_style = "risk-alert" if is_delayed else ""
                st.markdown(f"**Прогноз (pETA):** <span class='{p_eta_style}'>{ship['eta_predicted']}</span>", unsafe_allow_html=True)

# 6. Вкладка: ДОКУМЕНТЫ
elif menu == "📑 Документы":
    st.header("Электронный архив документов")
    ship_ids = client_data['shipment_id'].tolist()
    relevant_docs = df_docs[df_docs['shipment_id'].isin(ship_ids)]
    st.dataframe(relevant_docs, use_container_width=True, hide_index=True)

# 7. Вкладка: АНАЛИТИКА
elif menu == "📊 KPI Аналитика":
    st.header("Эффективность логистики")
    col_kpi1, col_kpi2 = st.columns(2)
    
    with col_kpi1:
        st.subheader("Надежность OTIF %")
        otif_history = pd.DataFrame({
            'Месяц': ['Янв', 'Фев', 'Мар', 'Апр'], 
            'OTIF %': [89.0, 91.5, 92.8, 94.2]
        })
        st.line_chart(otif_history.set_index('Месяц'))
        
    with col_kpi2:
        st.subheader("Виды транспорта")
        mode_counts = client_data['mode'].value_counts()
        st.bar_chart(mode_counts)
