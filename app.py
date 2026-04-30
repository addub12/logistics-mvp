import streamlit as st
import pandas as pd
import pydeck as pdk
from streamlit_gsheets import GSheetsConnection

# 1. Конфигурация страницы
st.set_page_config(
    page_title="Falcon Group | L-Control Dashboard", 
    page_icon="🦅", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# --- ИНТЕГРАЦИЯ КОРПОРАТИВНОГО СТИЛЯ (CSS) ---
st.markdown("""
    <style>
    /* Темно-синий фон для боковой панели */
    [data-testid="stSidebar"] {
        background-color: #0b2239;
    }
    
    /* Белый текст в боковой панели */
    [data-testid="stSidebar"] * {
        color: white !important;
    }

    /* Стилизация кнопок (корпоративный красный) */
    div.stButton > button:first-child {
        background-color: #c41230;
        color: white;
        border: none;
        border-radius: 4px;
    }
    div.stButton > button:first-child:hover {
        background-color: #a30e27;
        color: white;
    }

    /* Стилизация активной вкладки (красный акцент) */
    .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
        color: #c41230 !important;
        border-bottom-color: #c41230 !important;
    }
    
    /* Цвет значений метрик (темно-синий) */
    [data-testid="stMetricValue"] {
        color: #0b2239;
    }
    </style>
""", unsafe_allow_html=True)

# 2. Подключение к данным
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read()
except Exception as e:
    st.error(f"Ошибка подключения к Google Sheets: {e}")
    st.stop()

# 3. Боковая панель
# Вставьте путь к вашему файлу логотипа или URL. Например: "logo.png" или "https://..."
# Если файл лежит в той же папке, что и скрипт, просто укажите его имя.
LOGO_PATH = "https://drive.google.com/file/d/1XYyzKTzjs7GDDQkyTmDajid9igJ_2Gep" 

st.sidebar.image(LOGO_PATH, use_container_width=True)
st.sidebar.markdown("<br>", unsafe_allow_html=True) # Небольшой отступ

st.sidebar.title("Личный кабинет")

clients = df['client_name'].unique()
selected_client = st.sidebar.selectbox("Выберите компанию:", clients)

client_data = df[df['client_name'] == selected_client]

st.sidebar.markdown("---")
manager_name = client_data['manager_name'].iloc[0]
st.sidebar.subheader("Ваш менеджер")
st.sidebar.info(f"👤 {manager_name}")
if st.sidebar.button("💬 Написать в чат"):
    st.sidebar.success("Чат открыт (внутренняя система Falcon)")

# 4. Главный экран: Верхние метрики
st.title(f"Мониторинг грузов: {selected_client}")

shipment_ids = client_data['shipment_id'].unique()
selected_shipment_id = st.selectbox("Выберите номер груза для деталей:", shipment_ids)
ship = client_data[client_data['shipment_id'] == selected_shipment_id].iloc[0]

col1, col2, col3, col4 = st.columns(4)

balance = ship['balance']
col1.metric("Текущий баланс", f"{balance:,.0f} ₽", delta="К оплате" if balance < 0 else "Ок", delta_color="normal" if balance >= 0 else "inverse")

demurrage = ship['demurrage_free_days']
col2.metric("Дней до платного хранения", f"{demurrage} дн.", delta="- Внимание" if demurrage <= 3 else "Ок", delta_color="inverse" if demurrage <= 3 else "normal")

delay = int(ship['delay_days'])
col3.metric("Задержка (План/Факт)", f"{delay} дн.", delta=f"+{delay} дн." if delay > 0 else "В графике", delta_color="inverse" if delay > 0 else "normal")

congestion = ship['border_congestion']
col4.metric("Затор на границе", congestion, delta="Влияет на ETA" if congestion == "Высокий" else None, delta_color="inverse" if congestion == "Высокий" else "normal")

# 5. Основной контент
tab1, tab2, tab3, tab4 = st.tabs(["📍 Карта и Трекинг", "💰 Финансы и Таможня", "📑 Документы и Фото", "📈 Аналитика"])

with tab1:
    st.subheader("Местоположение 24/7 (п. 2.1)")
    view_state = pdk.ViewState(latitude=ship['lat'], longitude=ship['lon'], zoom=5, pitch=0)
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=pd.DataFrame([{'lat': ship['lat'], 'lon': ship['lon']}]),
        get_position="[lon, lat]",
        # Заменили цвет маркера на корпоративный красный (RGB: 196, 18, 48) для контраста
        get_color="[196, 18, 48, 200]", 
        get_radius=25000,
    )
    st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view_state))
    
    c1, c2 = st.columns(2)
    with c1:
        st.info(f"**Статус:** {ship['status']}")
        st.write(f"**Прогноз прибытия (ETA):** {ship['eta_predicted']}")
    with c2:
        st.warning(f"**Дней простоя на терминале:** {ship['terminal_idle_days']} дн. (п. 4.2)")

with tab2:
    st.subheader("Финансовый и таможенный контроль")
    f1, f2 = st.columns(2)
    
    with f1:
        with st.container(border=True):
            st.markdown("#### Валютный калькулятор (п. 1.2)")
            st.write(f"Текущий курс: **{ship['exchange_rate']} ₽**")
            st.success("Фиксация курса сегодня сэкономит вам ~12,400 ₽")
        
        with st.container(border=True):
            st.markdown("#### Таможенные платежи (п. 1.3)")
            st.write(f"Прогноз налогов: **{ship['customs_fee_forecast']:,.0f} ₽**")
            st.caption("Бюджет спланирован без сюрпризов")

    with f2:
        with st.container(border=True):
            st.subheader("Статус оформления (п. 3)")
            st.write(f"📂 **Документы:** {ship['customs_doc_status']}")
            st.write(f"📑 **Декларация (ДТ):** {ship['customs_dt_status']}")
            
            if ship['inspection_alert'] == "Да":
                st.error("⚠️ Назначен таможенный досмотр! (п. 3.3)")
            else:
                st.success("✅ Проверка проходит без досмотров")
            
            st.write(f"🛡️ **Страхование:** {ship['insurance_status']} (п. 6.2)")

with tab3:
    st.subheader("Архив и Фотоотчеты")
    a1, a2 = st.columns(2)
    with a1:
        st.write("📷 **Лента фотоотчетов (п. 5.1):**")
        photos = str(ship['photo_links']).split(',')
        for p in photos:
            st.image("https://via.placeholder.com/400x200?text=Cargo+Photo", caption=f"Отчет: {p.strip()}")
            
    with a2:
        st.write("📂 **Цифровой архив (п. 5.2):**")
        st.button(f"Скачать документы по грузу {selected_shipment_id}")
        st.caption(f"Ссылка на Drive: {ship['docs_folder_link']}")

with tab4:
    st.subheader("Эффективность и LTV")
    st.write("Здесь будет накапливаться история ваших перевозок для анализа маржинальности и сроков.")
    chart_data = pd.DataFrame({'Этап': ['Закупка', 'Транзит', 'Таможня', 'Склад'], 'Дней': [5, 12, 3, 2]})
    # Добавлен параметр color для графика в корпоративном красном цвете
    st.bar_chart(chart_data, x='Этап', y='Дней', color="#c41230")
