import streamlit as st
import pandas as pd
from supabase import create_client
import io

# --- PAGE CONFIG ---
st.set_page_config(page_title="Informes", page_icon="📊", layout="wide")
st.title("📊 Informes")

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

# --- DELETE CONFIRMATION LOGIC ---
if 'ids_to_delete' in st.session_state and st.session_state['ids_to_delete']:
    ids = st.session_state['ids_to_delete']
    placeholder = st.empty()
    with placeholder.container():
        st.warning(f"**¿Estás seguro de que quieres borrar {len(ids)} movimiento(s) con los siguientes IDs?**")
        st.code(f"{ids}")
        col1, col2 = st.columns(2)
        if col1.button("Sí, borrar ahora", key="confirm_delete"):
            try:
                supabase.table("tbl_movimientos").delete().in_('id', ids).execute()
                st.success(f"{len(ids)} movimiento(s) borrado(s) con éxito.")
                del st.session_state['ids_to_delete']
                if 'movimientos_df' in st.session_state: del st.session_state['movimientos_df']
                placeholder.empty()
                st.rerun()
            except Exception as e:
                st.error(f"Error al borrar los movimientos: {e}")
        if col2.button("No, cancelar", key="cancel_delete"):
            del st.session_state['ids_to_delete']
            placeholder.empty()
            st.rerun()

# --- APP LOGIC ---
st.write("Aquí puedes visualizar y borrar movimientos de la vista `vw_movimientos`.")
if not is_superuser:
    st.info(f"Mostrando solo movimientos para tu centro de costo: {user_ctro_cto_id}")

if st.button("Refrescar / Cargar Movimientos"):
    with st.spinner("Cargando movimientos..."):
        try:
            query = supabase.table("vw_movimientos").select("*")
            # Filter by ctro_cto if user is not a superuser
            if not is_superuser:
                query = query.eq('id_ctro_cto', user_ctro_cto_id)
            
            response = query.order('id', desc=True).execute()
            
            if hasattr(response, 'error') and response.error:
                st.error(f"Error al obtener los datos: {response.error.message}")
                st.session_state['movimientos_df'] = pd.DataFrame()
            elif not response.data:
                st.warning("No se encontraron movimientos para tu centro de costo.")
                st.session_state['movimientos_df'] = pd.DataFrame()
            else:
                df = pd.DataFrame(response.data)
                df["Borrar"] = False
                st.session_state['movimientos_df'] = df
        except Exception as e:
            st.error(f"Ocurrió un error inesperado: {e}")
            st.session_state['movimientos_df'] = pd.DataFrame()

if 'movimientos_df' in st.session_state and not st.session_state['movimientos_df'].empty:
    df = st.session_state['movimientos_df']
    
    col1, col2 = st.columns([3, 1])
    with col1:
        total_saldo = pd.to_numeric(df['saldo']).sum()
        st.metric(label="Saldo Total de Movimientos", value=f"${total_saldo:,.2f}")
    with col2:
        @st.cache_data
        def to_excel(df_to_convert):
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_to_convert.drop(columns=['Borrar']).to_excel(writer, index=False, sheet_name='Movimientos')
            return output.getvalue()
        excel_data = to_excel(df)
        st.download_button(label="📥 Descargar a Excel", data=excel_data, file_name="informe_movimientos.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

    st.divider()
    st.info("Selecciona las filas que deseas eliminar marcando la casilla 'Borrar' y luego presiona el botón 'Borrar Seleccionados'.")
    
    edited_df = st.data_editor(st.session_state['movimientos_df'], key="movimientos_editor", use_container_width=True, hide_index=True)

    if st.button("Borrar Seleccionados"):
        rows_to_delete = edited_df[edited_df["Borrar"] == True]
        if not rows_to_delete.empty:
            ids_to_delete = rows_to_delete["id"].tolist()
            st.session_state['ids_to_delete'] = ids_to_delete
            st.rerun()
        else:
            st.warning("No has seleccionado ningún movimiento para borrar.")