import streamlit as st
from supabase import create_client

# --- SUPABASE CONNECTION ---
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="App de Carga de Datos",
    page_icon="👋",
    layout="centered"
)

# --- LOGIN LOGIC ---
def login():
    st.title("Bienvenido 👋")
    st.write("Por favor, ingresa tus credenciales para continuar.")
    
    with st.form("login_form"):
        username = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        submitted = st.form_submit_button("Iniciar Sesión")

        if submitted:
            if not username or not password:
                st.error("Por favor, ingresa usuario y contraseña.")
                return

            response = supabase.table("tbl_users").select("*").eq("usuario", username).eq("pass", password).execute()
            
            if response.data and len(response.data) == 1:
                user_data = response.data[0]
                st.session_state["logged_in"] = True
                st.session_state["user"] = user_data
                st.rerun()
            else:
                st.error("😕 Usuario o contraseña incorrecta.")

# --- MAIN APP ---
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    login()
else:
    # --- LOGOUT CONFIRMATION LOGIC ---
    if st.session_state.get("logout_request"):
        placeholder = st.empty()
        with placeholder.container():
            st.warning("¿Estás seguro de que quieres cerrar la sesión?")
            col1, col2 = st.columns(2)
            if col1.button("Sí, cerrar sesión", use_container_width=True):
                # Clear session state
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                placeholder.empty()
                st.rerun()
            if col2.button("No, cancelar", use_container_width=True):
                st.session_state.logout_request = False
                placeholder.empty()
                st.rerun()

    # --- SIDEBAR ---
    user = st.session_state.get("user", {})
    st.sidebar.success("Has iniciado sesión correctamente.")
    st.sidebar.markdown(f"**Usuario:** {user.get('usuario', 'N/A')}")
    st.sidebar.markdown(f"**Centro de Costo:** {user.get('id_ctro_cto', 'N/A')}")
    st.sidebar.markdown(f"**Rol:** {user.get('tipo_usuario', 'N/A')}")
    st.sidebar.divider()
    if st.sidebar.button("Cerrar Sesión", use_container_width=True):
        st.session_state.logout_request = True
        st.rerun()

    # --- MAIN PAGE CONTENT ---
    st.title("Página Principal")
    st.write("---")
    st.header("Navegación")
    st.write("Usa la barra lateral a la izquierda para navegar a las diferentes secciones de la aplicación:")
    st.markdown("- **Carga:** Para subir nuevos archivos CSV a Supabase.")
    st.markdown("- **Informes:** Para visualizar datos desde tu base de datos.")