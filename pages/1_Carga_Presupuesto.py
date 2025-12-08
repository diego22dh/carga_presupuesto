import streamlit as st
import pandas as pd
from supabase import create_client, Client

# --- PAGE CONFIG ---
st.set_page_config(page_title="Carga Presupuesto", page_icon="📤")
st.title("📤 Carga Presupuesto")

# --- AUTHENTICATION ---
if "user" not in st.session_state:
    st.error("Por favor, inicia sesión para acceder a esta página.")
    st.stop()

# Get user info from session
user = st.session_state["user"]
user_ctro_cto_id = user.get("id_ctro_cto")
is_superuser = (user_ctro_cto_id == 25)

# --- SUPABASE CONNECTION ---
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# --- DATA FETCHING & FILTERING ---
@st.cache_data(ttl=600)
def fetch_data(table_name, columns):
    try:
        return supabase.table(table_name).select(columns).execute().data
    except Exception as e:
        st.error(f"Error cargando datos de '{table_name}': {e}")
        return []

# Fetch all data
all_ctros_cto_data = fetch_data("tbl_ctro_cto", "id, nombre")
users_data = fetch_data("tbl_users", "id, usuario")
partidas_data = fetch_data("tbl_partidas", "id, rubro, pda, pda_gral")

# Filter Centro de Costo data based on user permissions
if is_superuser:
    ctros_cto_data = all_ctros_cto_data
else:
    ctros_cto_data = [cto for cto in all_ctros_cto_data if cto['id'] == user_ctro_cto_id]

# Create mappings and DataFrames
ctros_cto_map = {item['nombre']: item['id'] for item in ctros_cto_data}
users_map = {item['usuario']: item['id'] for item in users_data}
partidas_df = pd.DataFrame(partidas_data)

# --- UI TABS ---
tab1, tab2 = st.tabs(["Carga Manual", "Carga Masiva (CSV/Excel)"])

# --- TAB 1: MANUAL UPLOAD ---
with tab1:
    # ... (The manual upload form logic remains largely the same, but the Centro de Costo dropdown will be filtered)
    st.subheader("Formulario de Carga Manual")
    saldo_manual = st.number_input("Saldo", format="%.2f", key="saldo_manual")
    id_ejercicio_manual = st.number_input("ID Ejercicio", min_value=0, step=1, key="id_ejercicio_manual")
    descripcion_manual = st.text_area("Descripción", key="descripcion_manual")

    st.divider()
    st.write("**Selección de Partida (en cascada)**")
    # ... (Cascading dropdowns logic)
    selected_rubro, selected_pda_gral, selected_pda = None, None, None
    if not partidas_df.empty:
        rubro_list = sorted(partidas_df['rubro'].dropna().unique())
        selected_rubro = st.selectbox("1. Rubro", options=rubro_list)
        if selected_rubro:
            pda_gral_df = partidas_df[partidas_df['rubro'] == selected_rubro]
            pda_gral_list = sorted(pda_gral_df['pda_gral'].dropna().unique())
            selected_pda_gral = st.selectbox("2. PDA Gral", options=pda_gral_list)
            if selected_pda_gral:
                pda_df = pda_gral_df[pda_gral_df['pda_gral'] == selected_pda_gral]
                pda_list = sorted(pda_df['pda'].dropna().unique())
                selected_pda = st.selectbox("3. PDA", options=pda_list)
    
    st.divider()
    # The dropdown is now filtered. If not superuser, it will only show their own ctro_cto.
    selected_ctro_cto = st.selectbox("Centro de Costo", options=list(ctros_cto_map.keys()), disabled=(not is_superuser and len(ctros_cto_map) == 1))
    # Get logged-in user's username
    logged_in_username = st.session_state["user"].get("usuario")
    user_options = list(users_map.keys())
    try:
        default_user_index = user_options.index(logged_in_username)
    except ValueError:
        default_user_index = 0 # Fallback if user not found (shouldn't happen if logged in)

    selected_user = st.selectbox("Usuario", options=user_options, index=default_user_index, disabled=True)

    st.divider()
    if st.button("Guardar Movimiento"):
        # ... (Submission logic remains the same)
        if not all([selected_rubro, selected_pda, selected_pda_gral, selected_ctro_cto, selected_user]):
            st.error("Asegúrate de seleccionar valores para todos los menús desplegables.")
        else:
            match_df = partidas_df[(partidas_df['rubro'] == selected_rubro) & (partidas_df['pda_gral'] == selected_pda_gral) & (partidas_df['pda'] == selected_pda)]
            if len(match_df) != 1:
                st.error(f"Error: Se encontraron {len(match_df)} partidas para la combinación seleccionada.")
            else:
                with st.spinner("Guardando..."):
                    try:
                        id_partida = int(match_df.iloc[0]['id'])
                        id_ctro_cto = int(ctros_cto_map[selected_ctro_cto])
                        id_user = int(users_map[selected_user])
                        new_movimiento = {
                            "id_ctro_cto": id_ctro_cto, "id_partida": id_partida, "saldo": saldo_manual,
                            "id_user": id_user, "id_ejercicio": int(id_ejercicio_manual), "descripcion": descripcion_manual
                        }
                        response = supabase.table("tbl_movimientos").insert(new_movimiento).execute()
                        if hasattr(response, 'error') and response.error:
                            st.error(f"Error al guardar: {response.error.message}")
                        else:
                            st.success("¡Movimiento guardado con éxito!")
                            st.toast("¡Movimiento guardado con éxito!")
                    except Exception as e:
                        st.error(f"Ocurrió un error inesperado: {e}")

# --- TAB 2: BULK UPLOAD ---
with tab2:
    st.subheader("Carga Masiva desde Archivo")
    st.info("""
        **Instrucciones:**
        1. Sube un archivo CSV o Excel (.xlsx).
        2. El archivo debe contener las siguientes columnas obligatorias:
           - `saldo`, `id_ejercicio`, `descripcion`, `rubro`, `pda_gral`, `pda`, `id_ctro_cto`, `nombre_usuario`
        3. Si tu usuario no es administrador, todos los registros deben pertenecer a tu centro de costo (usando el ID correcto).
    """)
    uploaded_file = st.file_uploader("Elige un archivo CSV o Excel", type=["csv", "xlsx"], key="bulk_uploader")
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
            
            # Normalize column names: strip whitespace and convert to lower case
            df.columns = df.columns.str.strip().str.lower()

            # Handle common typo: id_cetro_cto -> id_ctro_cto
            if 'id_cetro_cto' in df.columns:
                df.rename(columns={'id_cetro_cto': 'id_ctro_cto'}, inplace=True)

            st.write("Previsualización de los datos a cargar:")
            st.dataframe(df.head())

            if st.button("Iniciar Carga Masiva"):
                records_to_insert = []
                errors = []
                
                # This set is already filtered based on user permissions from the top of the script
                valid_ctro_cto_ids = {item['id'] for item in ctros_cto_data}

                with st.spinner("Procesando archivo..."):
                    # --- VALIDATION ---
                    required_cols = {'saldo', 'id_ejercicio', 'descripcion', 'rubro', 'pda_gral', 'pda', 'id_ctro_cto', 'nombre_usuario'}
                    if not required_cols.issubset(df.columns):
                        missing_cols = required_cols - set(df.columns)
                        errors.append(f"Error: Faltan las siguientes columnas obligatorias: {', '.join(missing_cols)}")
                    
                    if not errors:
                        # Convert id_ctro_cto to a numeric type, coercing errors to NaN.
                        df['id_ctro_cto'] = pd.to_numeric(df['id_ctro_cto'], errors='coerce')

                        # --- DATA PROCESSING ---
                        for index, row in df.iterrows():
                            try:
                                # Validate and get id_ctro_cto
                                id_ctro_cto = row['id_ctro_cto']
                                if pd.isna(id_ctro_cto):
                                    raise ValueError("El 'id_ctro_cto' está vacío o no es un número válido.")
                                
                                id_ctro_cto = int(id_ctro_cto)

                                if id_ctro_cto not in valid_ctro_cto_ids:
                                    raise ValueError(f"El id_ctro_cto '{id_ctro_cto}' no es válido o no tienes permiso para usarlo.")

                                # Lookups for partida and user
                                match_df = partidas_df[(partidas_df['rubro'] == row['rubro']) & (partidas_df['pda_gral'] == row['pda_gral']) & (partidas_df['pda'] == row['pda'])]
                                if len(match_df) != 1:
                                    raise ValueError(f"No se encontró una partida única para la combinación dada (halladas {len(match_df)}).")
                                
                                id_partida = int(match_df.iloc[0]['id'])
                                id_user = int(users_map[row['nombre_usuario']])
                                
                                record = {
                                    "id_ctro_cto": id_ctro_cto,
                                    "id_partida": id_partida,
                                    "saldo": row['saldo'],
                                    "id_user": id_user,
                                    "id_ejercicio": int(row['id_ejercicio']),
                                    "descripcion": row['descripcion']
                                }
                                records_to_insert.append(record)
                            except KeyError as e:
                                errors.append(f"Fila {index + 2}: Falta la columna requerida o el nombre es incorrecto: {e}")
                            except ValueError as e:
                                errors.append(f"Fila {index + 2}: {e}")
                            except Exception as e:
                                errors.append(f"Fila {index + 2}: Error inesperado - {e}")
                
                if errors:
                    st.error("Se encontraron errores en el archivo y no se pudo cargar:")
                    st.code("\n".join(errors))
                elif not records_to_insert:
                    st.warning("No se encontraron registros válidos para cargar.")
                else:
                    with st.spinner(f"Cargando {len(records_to_insert)} registros..."):
                        try:
                            response = supabase.table("tbl_movimientos").insert(records_to_insert).execute()
                            if hasattr(response, 'error') and response.error:
                                st.error(f"Error en la carga masiva: {response.error.message}")
                            else:
                                st.success(f"¡Éxito! Se han cargado {len(records_to_insert)} registros.")
                                st.toast(f"¡Éxito! Se han cargado {len(records_to_insert)} registros.")
                        except Exception as e:
                            st.error(f"Ocurrió un error inesperado durante la carga: {e}")
        except Exception as e:
            st.error(f"No se pudo procesar el archivo: {e}")
