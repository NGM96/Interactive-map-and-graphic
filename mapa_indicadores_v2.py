import os
import pandas as pd
import streamlit as st
import folium
from streamlit_folium import folium_static
import logging
from datetime import datetime
import plotly.express as px

# Configurar logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Definir coordenadas de los partidos
COORDENADAS_PARTIDOS = {
    'Moreno': [-34.650630, -58.789654],
    'Merlo': [-34.666465, -58.728612]
}

# Configuración de la página
st.set_page_config(page_title="Mapa y Gráfico de Indicadores AySA", layout="wide")

# ... (resto del código para cargar datos, etc.)

def obtener_numero_mes(mes):
    meses = {
        'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
        'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
    }
    return meses.get(mes.lower(), 0)

def crear_mapa(df, partidos_seleccionados, indicador, mes_inicio, mes_fin):
    try:
        mapa = folium.Map(location=[-34.61315, -58.37723], zoom_start=10)
        
        # Filtrar por indicador
        datos_filtrados = df[df['INDICADOR DE DESEMPEÑO'] == indicador].copy()
        
        # Obtener la unidad del indicador
        unidad = datos_filtrados['UNIDAD'].iloc[0] if not datos_filtrados.empty else ''
        
        # Obtener meses seleccionados
        meses = [col for col in df.columns if isinstance(col, str) and obtener_numero_mes(col.lower()) > 0]
        meses = sorted(meses, key=obtener_numero_mes)
        inicio_idx = meses.index(mes_inicio)
        fin_idx = meses.index(mes_fin)
        meses_seleccionados = meses[inicio_idx:fin_idx + 1]
        
        for partido, coords in COORDENADAS_PARTIDOS.items():
            if partido not in partidos_seleccionados and 'Todos' not in partidos_seleccionados:
                continue
                
            try:
                datos_partido = datos_filtrados[datos_filtrados['Partido'].str.strip() == partido]
                if datos_partido.empty:
                    continue
                
                # Procesar valores según la unidad
                valores = datos_partido[meses_seleccionados].fillna(0)
                valores = valores.astype(str).apply(lambda x: x.str.replace(',', '.'))
                valores = valores.apply(lambda x: x.str.replace('%', ''))
                valores = valores.astype(float)
                
                # Calcular según tipo de indicador
                if '%' in str(unidad):
                    valor_final = valores.mean().mean()
                    formato_valor = f"{valor_final:.2f}%"
                else:
                    valor_final = valores.sum().sum()
                    formato_valor = f"{valor_final:.2f}"
                
                if not pd.isna(valor_final):
                    folium.CircleMarker(
                        location=coords,
                        radius=10,
                        popup=f"{partido}: {formato_valor}",
                        color='red',
                        fill=True
                    ).add_to(mapa)
                    
            except Exception as e:
                logger.error(f"Error procesando {partido}: {str(e)}")
                continue
                
        return mapa
    except Exception as e:
        logger.error(f"Error en crear_mapa: {str(e)}")
        raise

def crear_grafico(df, partidos_seleccionados, indicador, mes_inicio, mes_fin):
    try:
        datos_combinados = []
        
        # Definir colores para cada partido
        colores = {
            'Moreno': '#FF0000',  # Rojo
            'Merlo': '#0000FF'    # Azul
        }
        
        # Obtener los meses seleccionados
        meses = [col for col in df.columns if isinstance(col, str) and obtener_numero_mes(col.lower()) > 0]
        meses = sorted(meses, key=obtener_numero_mes)
        inicio_idx = meses.index(mes_inicio)
        fin_idx = meses.index(mes_fin)
        meses_seleccionados = meses[inicio_idx:fin_idx + 1]
        
        # Determinar qué partidos procesar
        if 'Todos' in partidos_seleccionados:
            partidos_a_procesar = list(COORDENADAS_PARTIDOS.keys())
        else:
            partidos_a_procesar = partidos_seleccionados
            
        logger.debug(f"Partidos a procesar: {partidos_a_procesar}")
        
        # Filtrar datos para el indicador seleccionado
        datos_filtrados = df[df['INDICADOR DE DESEMPEÑO'] == indicador]
        
        for partido in partidos_a_procesar:
            datos_partido = datos_filtrados[datos_filtrados['Partido'] == partido]
            
            if not datos_partido.empty:
                # Procesar valores numéricos
                valores = datos_partido[meses_seleccionados].fillna(0)
                valores = valores.astype(str).apply(lambda x: x.str.replace(',', '.'))
                valores = valores.apply(lambda x: x.str.replace('%', ''))
                valores = valores.astype(float).iloc[0]
                
                # Agregar datos al listado
                for mes, valor in zip(meses_seleccionados, valores):
                    datos_combinados.append({
                        'Mes': mes,
                        'Valor': valor,
                        'Partido': partido
                    })
        
        if datos_combinados:
            # Crear DataFrame con todos los datos
            df_plot = pd.DataFrame(datos_combinados)
            logger.debug(f"DataFrame para graficar:\n{df_plot}")
            
            # Crear el gráfico de líneas
            fig = px.line(df_plot, 
                         x='Mes', 
                         y='Valor', 
                         color='Partido',
                         color_discrete_map=colores,
                         title=f'Evolución de {indicador}',
                         labels={'Mes': 'Mes', 'Valor': 'Valor del Indicador'},
                         markers=True)
            
            fig.update_layout(
                width=1200,
                height=500,
                margin=dict(l=40, r=40, t=40, b=40),
                legend_title="Partidos",
                showlegend=True
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No hay datos disponibles para graficar")
            logger.warning("No se encontraron datos para generar el gráfico")
            
    except Exception as e:
        logger.error(f"Error en crear_grafico: {str(e)}")
        st.error(f"Error al crear el gráfico: {str(e)}")
        raise

def cargar_datos():
    try:
        # Lee los datos y asegura que exista la columna Partido
        excel_path = os.path.join(os.path.dirname(__file__), 'document.xlsx')
        df_moreno = pd.read_excel(excel_path, sheet_name='Moreno')
        df_moreno['Partido'] = 'Moreno'
        
        df_merlo = pd.read_excel(excel_path, sheet_name='Merlo')
        df_merlo['Partido'] = 'Merlo'

        # Concatenar DataFrames
        df = pd.concat([df_moreno, df_merlo], ignore_index=True)
        
        # Asegurarse de que exista la columna 'Tipo'
        if 'Tipo' not in df.columns:
            st.error("La columna 'Tipo' no existe en el archivo Excel. Por favor, agrégala.")
            return None, None, None, None, None
            
        # Limpiar y convertir datos
        df['Tipo'] = df['Tipo'].fillna('Sin categoría').astype(str).str.strip()
        df['INDICADOR DE DESEMPEÑO'] = df['INDICADOR DE DESEMPEÑO'].fillna('').astype(str).str.strip()
        
        # Convertir columnas de meses
        meses = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 
                 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
        
        for mes in meses:
            if mes in df.columns:
                df[mes] = (df[mes].astype(str)
                          .str.replace(',', '.')
                          .str.replace('%', '')
                          .replace('', '0')
                          .replace('nan', '0')
                          .astype(float))
        
        # Obtener listas únicas
        tipos = sorted(df['Tipo'].unique().tolist())
        indicadores = sorted(df['INDICADOR DE DESEMPEÑO'].unique().tolist())
        partidos = df['Partido'].unique().tolist()
        
        return df, indicadores, meses, partidos, tipos
        
    except Exception as e:
        logger.error(f"Error cargando datos: {str(e)}")
        raise

def main():
    st.title('Mapa y Gráfico de Indicadores AySA')
    
    try:
        # Cargar datos una sola vez
        df, indicadores, meses, partidos, tipos = cargar_datos()
        
        if df is None:
            return
            
        # Agregar opción "Todos"
        partidos = ['Todos'] + partidos
        tipos = ['Todos'] + tipos
        
        # Selectores en la parte superior
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            partidos_seleccionados = st.multiselect(
                'Seleccionar Partidos',
                options=partidos,
                default=['Todos']
            )
        with col2:
            tipo_seleccionado = st.selectbox(
                'Seleccionar Tipo',
                options=tipos,
                index=0
            )
        with col3:
            # Filtrar indicadores según el tipo seleccionado
            if tipo_seleccionado == 'Todos':
                indicadores_filtrados = indicadores
            else:
                indicadores_filtrados = sorted(df[df['Tipo'] == tipo_seleccionado]['INDICADOR DE DESEMPEÑO'].unique().tolist())
            
            indicador = st.selectbox('Seleccionar Indicador', options=indicadores_filtrados, index=0)
        with col4:
            mes_inicio = st.selectbox('Mes Inicio', options=meses, index=0)
        with col5:
            mes_fin = st.selectbox('Mes Fin', options=meses, index=len(meses)-1)

        # Un solo botón centrado
        if st.button('Generar Visualizaciones', use_container_width=True):
            if obtener_numero_mes(mes_inicio) > obtener_numero_mes(mes_fin):
                st.error("El mes de inicio debe ser anterior o igual al mes final")
            else:
                # Contenedor para el mapa con altura reducida
                st.subheader("Mapa de Indicadores")
                mapa = crear_mapa(df, partidos_seleccionados, indicador, mes_inicio, mes_fin)
                folium_static(mapa, width=1400, height=250)  # Cambio de height=500 a height=250
                
                # Espacio entre visualizaciones
                st.markdown("<br>", unsafe_allow_html=True)
                
                # Contenedor para el gráfico
                st.subheader("Gráfico de Evolución")
                crear_grafico(df, partidos_seleccionados, indicador, mes_inicio, mes_fin)
                
    except Exception as e:
        st.error(f"Error en la aplicación: {str(e)}")
        logger.error(f"Error en main: {str(e)}")

if __name__ == "__main__":
    main()