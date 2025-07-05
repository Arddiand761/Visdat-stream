import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Set layout ke wide mode dan judul halaman
st.set_page_config(layout="wide", page_title="Dashboard Keuangan Truk Air", initial_sidebar_state="collapsed")

# --- MEMUAT DATA DARI SATU FILE EXCEL ---
@st.cache_data
def load_data():
    # Nama file Excel Anda
    file_path = 'Dataset Keuangan Truk Air Isi Ulang 2024.xlsx'
    
    try:
        # Membaca data dari sheet yang berbeda dalam satu file Excel
        df_keuangan = pd.read_excel(file_path, sheet_name='Dataset Keuangan Truk Air Isi U')
        df_lokasi = pd.read_excel(file_path, sheet_name='lokasi')
        
    except FileNotFoundError:
        st.error(f"File '{file_path}' tidak ditemukan. Pastikan file Excel tersebut berada di direktori yang sama dengan skrip Python Anda.")
        return None, None
    except Exception as e:
        st.error(f"Gagal membaca sheet dari file Excel. Error: {e}")
        st.info("Pastikan nama sheet di file Excel Anda sudah benar: 'Dataset Keuangan Truk Air Isi U' dan 'lokasi'.")
        return None, None

    # --- PEMBERSIHAN DATA ---
    # Mengubah 'Tanggal' menjadi datetime
    df_keuangan['Tanggal'] = pd.to_datetime(df_keuangan['Tanggal'], errors='coerce')

    # Mengisi missing values
    numeric_cols = ['Pemasukan', 'Pengeluaran', 'Volume (L)', 'Jumlah']
    for col in numeric_cols:
        if col in df_keuangan.columns:
            df_keuangan[col] = pd.to_numeric(df_keuangan[col], errors='coerce').fillna(0)

    categorical_cols = ['Jenis Transaksi', 'Plat Nomor', 'Sopir', 'Order']
    for col in categorical_cols:
        if col in df_keuangan.columns:
            df_keuangan[col] = df_keuangan[col].fillna('Tidak Diketahui')

    # Menambahkan kolom 'Bulan' untuk analisis bulanan
    df_keuangan['Bulan'] = df_keuangan['Tanggal'].dt.to_period('M').astype(str)
    
    # Menggabungkan dengan data lokasi
    df_merged = pd.merge(df_keuangan, df_lokasi, left_on='Order', right_on='Nama Lokasi', how='left')
    
    return df_keuangan, df_merged

df_keuangan, df_merged = load_data()

# --- BAGIAN UI DASBOR ---
if df_keuangan is not None:
    # Custom CSS untuk styling
    st.markdown("""
    <style>
    .main > div {
        padding-top: 1rem;
    }
    .metric-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 0.5rem 0;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding-left: 20px;
        padding-right: 20px;
    }
    div[data-testid="metric-container"] {
        background-color: #f0f2f6;
        border: 1px solid #e6e9ef;
        padding: 5% 5% 5% 10%;
        border-radius: 5px;
        border-left: 0.5rem solid #9AD8E1;
        box-shadow: 0 0.15rem 1.75rem 0 rgba(58, 59, 69, 0.15);
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.title("📊 Dashboard Keuangan dan Operasional Truk Air Isi Ulang 2024")
    st.markdown("Dashboard interaktif untuk analisis data keuangan, pengiriman air, dan kinerja operasional")

    # Sidebar untuk filter
    with st.sidebar:
        st.header("🔧 Filter Data")
        
        # Filter bulan
        bulan_options = ['Semua'] + sorted(df_keuangan['Bulan'].unique().tolist())
        selected_bulan = st.selectbox("Pilih Bulan:", bulan_options)
        
        # Filter sopir
        sopir_options = ['Semua'] + sorted(df_keuangan[df_keuangan['Sopir'] != 'Tidak Diketahui']['Sopir'].unique().tolist())
        selected_sopir = st.selectbox("Pilih Sopir:", sopir_options)
        
        # Filter armada
        armada_options = ['Semua'] + sorted(df_keuangan[df_keuangan['Plat Nomor'] != 'Tidak Diketahui']['Plat Nomor'].unique().tolist())
        selected_armada = st.selectbox("Pilih Armada:", armada_options)
    
    # Apply filters
    df_filtered = df_keuangan.copy()
    df_merged_filtered = df_merged.copy()
    
    if selected_bulan != 'Semua':
        df_filtered = df_filtered[df_filtered['Bulan'] == selected_bulan]
        df_merged_filtered = df_merged_filtered[df_merged_filtered['Bulan'] == selected_bulan]
    
    if selected_sopir != 'Semua':
        df_filtered = df_filtered[df_filtered['Sopir'] == selected_sopir]
        df_merged_filtered = df_merged_filtered[df_merged_filtered['Sopir'] == selected_sopir]
    
    if selected_armada != 'Semua':
        df_filtered = df_filtered[df_filtered['Plat Nomor'] == selected_armada]
        df_merged_filtered = df_merged_filtered[df_merged_filtered['Plat Nomor'] == selected_armada]

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📈 Ringkasan Keuangan",
        "💧 Pengiriman Air",
        "🌍 Peta & Demografi",
        "🚚 Analisis Armada",
        "👤 Kinerja Sopir"
    ])

    # --- TAB 1: RINGKASAN KEUANGAN ---
    with tab1:
        st.header("💰 Ringkasan Keuangan")
        
        # KPI Cards menggunakan data yang difilter
        col1, col2, col3, col4 = st.columns(4)
        total_pemasukan = df_filtered['Pemasukan'].sum()
        total_pengeluaran = df_filtered['Pengeluaran'].sum()
        laba_bersih = total_pemasukan - total_pengeluaran
        total_transaksi = len(df_filtered)
        
        col1.metric("Total Pemasukan", f"Rp {total_pemasukan:,.0f}")
        col2.metric("Total Pengeluaran", f"Rp {total_pengeluaran:,.0f}")
        col3.metric("Laba Bersih", f"Rp {laba_bersih:,.0f}")
        col4.metric("Total Transaksi", f"{total_transaksi:,}")

        # Charts dalam dua kolom untuk menghemat ruang
        col1, col2 = st.columns(2)
        
        with col1:
            # Trend keuangan bulanan
            df_bulanan = df_filtered.groupby('Bulan').agg({
                'Pemasukan': 'sum',
                'Pengeluaran': 'sum'
            }).reset_index()
            df_bulanan['Laba Bersih'] = df_bulanan['Pemasukan'] - df_bulanan['Pengeluaran']
            
            fig1 = px.line(df_bulanan, x='Bulan', y=['Pemasukan', 'Pengeluaran'], 
                          title='Trend Pemasukan vs Pengeluaran',
                          height=350)
            fig1.update_layout(margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            # Pie chart jenis transaksi
            jenis_transaksi = df_filtered['Jenis Transaksi'].value_counts()
            fig2 = px.pie(values=jenis_transaksi.values, names=jenis_transaksi.index,
                         title='Distribusi Jenis Transaksi',
                         height=350)
            fig2.update_layout(margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig2, use_container_width=True)

    # --- TAB 2: PENGIRIMAN AIR ---
    with tab2:
        st.header("💧 Analisis Pengiriman Air")

        # KPI untuk volume air
        col1, col2, col3 = st.columns(3)
        total_volume = df_filtered['Volume (L)'].sum()
        avg_volume = df_filtered['Volume (L)'].mean()
        max_volume = df_filtered['Volume (L)'].max()
        
        col1.metric("Total Volume Terkirim", f"{total_volume:,.0f} L")
        col2.metric("Rata-rata Volume", f"{avg_volume:,.1f} L")
        col3.metric("Volume Terbesar", f"{max_volume:,.0f} L")

        # Charts dalam layout yang kompak
        col1, col2 = st.columns(2)
        
        with col1:
            # Volume per bulan
            volume_per_bulan = df_filtered.groupby('Bulan')['Volume (L)'].sum().reset_index()
            fig3 = px.bar(volume_per_bulan, x='Bulan', y='Volume (L)',
                         title='Volume Air per Bulan',
                         height=300)
            fig3.update_layout(margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig3, use_container_width=True)
        
        with col2:
            # Top lokasi pengiriman
            if len(df_filtered) > 0:
                top_lokasi = df_filtered['Order'].value_counts().head(5).reset_index()
                top_lokasi.columns = ['Lokasi', 'Jumlah Order']
                fig4 = px.bar(top_lokasi, x='Jumlah Order', y='Lokasi',
                             orientation='h', title='Top 5 Lokasi Pengiriman',
                             height=300)
                fig4.update_layout(margin=dict(l=0, r=0, t=30, b=0))
                st.plotly_chart(fig4, use_container_width=True)

    # --- TAB 3: DEMOGRAFI & PETA PENGIRIMAN ---
    with tab3:
        st.header("🌍 Peta & Demografi Pengiriman")
        
        # DEBUG INFO - Informasi untuk troubleshooting
        with st.expander("🔍 Debug Info - Klik untuk melihat detail data"):
            st.write("**1. Jenis Transaksi yang tersedia:**")
            jenis_transaksi_unique = df_merged_filtered['Jenis Transaksi'].value_counts()
            st.write(jenis_transaksi_unique)
            
            st.write("**2. Total data setelah filter:**")
            st.write(f"Total baris df_merged_filtered: {len(df_merged_filtered)}")
            
            st.write("**3. Data yang memiliki koordinat:**")
            data_dengan_koordinat = df_merged_filtered.dropna(subset=['Latitude', 'Longitude'])
            st.write(f"Data dengan Latitude/Longitude: {len(data_dengan_koordinat)}")
            
            st.write("**4. Data pengiriman air:**")
            data_pengiriman_all = df_merged_filtered[df_merged_filtered['Jenis Transaksi'].str.contains('Air|air|Pengiriman|pengiriman', na=False)]
            st.write(f"Data yang mengandung kata 'Air' atau 'Pengiriman': {len(data_pengiriman_all)}")
            
            if len(data_pengiriman_all) > 0:
                st.write("**Sample data pengiriman:**")
                st.dataframe(data_pengiriman_all[['Jenis Transaksi', 'Order', 'Latitude', 'Longitude']].head())
        
        # Coba dengan filter yang lebih fleksibel
        df_pengiriman = df_merged_filtered[df_merged_filtered['Jenis Transaksi'].str.contains('Air|air|Pengiriman|pengiriman', na=False)].dropna(subset=['Latitude', 'Longitude'])
        
        if len(df_pengiriman) == 0:
            # Jika masih tidak ada, coba tanpa filter jenis transaksi
            df_pengiriman = df_merged_filtered.dropna(subset=['Latitude', 'Longitude'])
            st.info("⚠️ Tidak ada data dengan jenis transaksi 'Air/Pengiriman', menampilkan semua data dengan koordinat valid")
        
        if len(df_pengiriman) > 0:
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.subheader("📊 Sebaran Order")
                lokasi_counts = df_pengiriman['Order'].value_counts().head(10).reset_index()
                lokasi_counts.columns = ['Lokasi', 'Jumlah Order']
                
                fig_lokasi = px.bar(lokasi_counts, x='Jumlah Order', y='Lokasi',
                                   orientation='h', height=350,
                                   title='Top 10 Lokasi Pengiriman')
                fig_lokasi.update_layout(margin=dict(l=0, r=0, t=30, b=0))
                st.plotly_chart(fig_lokasi, use_container_width=True)
            
            with col2:
                st.subheader("🗺️ Peta Pengiriman")
                # Peta dengan size berdasarkan volume
                df_map = df_pengiriman.groupby(['Latitude', 'Longitude', 'Order']).agg({
                    'Volume (L)': 'sum',
                    'Pemasukan': 'sum'
                }).reset_index()
                
                fig_map = px.scatter_mapbox(df_map, 
                                          lat="Latitude", lon="Longitude",
                                          size="Volume (L)", 
                                          color="Pemasukan",
                                          hover_name="Order",
                                          hover_data={'Volume (L)': True, 'Pemasukan': True},
                                          mapbox_style="open-street-map",
                                          height=350,
                                          zoom=10)
                fig_map.update_layout(margin=dict(l=0, r=0, t=0, b=0))
                st.plotly_chart(fig_map, use_container_width=True)
        else:
            st.warning("Tidak ada data pengiriman air untuk filter yang dipilih")

    # --- TAB 4: ANALISIS ARMADA ---
    with tab4:
        st.header("🚚 Analisis Armada")
        df_armada = df_filtered[df_filtered['Plat Nomor'] != 'Tidak Diketahui']
        
        if len(df_armada) > 0:
            # KPI Armada
            col1, col2, col3 = st.columns(3)
            total_armada = df_armada['Plat Nomor'].nunique()
            armada_terbanyak = df_armada['Plat Nomor'].value_counts().index[0]
            usage_terbanyak = df_armada['Plat Nomor'].value_counts().iloc[0]
            
            col1.metric("Total Armada Aktif", total_armada)
            col2.metric("Armada Terbanyak Digunakan", armada_terbanyak)
            col3.metric("Jumlah Penggunaan", f"{usage_terbanyak} kali")
            
            col1, col2 = st.columns(2)
            with col1:
                # Frekuensi penggunaan armada
                armada_usage = df_armada['Plat Nomor'].value_counts().head(8).reset_index()
                armada_usage.columns = ['Armada', 'Jumlah Penggunaan']
                
                fig_armada = px.bar(armada_usage, x='Jumlah Penggunaan', y='Armada',
                                   orientation='h', title='Frekuensi Penggunaan Armada',
                                   height=350)
                fig_armada.update_layout(margin=dict(l=0, r=0, t=30, b=0))
                st.plotly_chart(fig_armada, use_container_width=True)
            
            with col2:
                # Total pemasukan per armada
                pemasukan_armada = df_armada.groupby('Plat Nomor')['Pemasukan'].sum().sort_values(ascending=False).head(8).reset_index()
                pemasukan_armada.columns = ['Armada', 'Total Pemasukan']
                
                fig_pemasukan = px.bar(pemasukan_armada, x='Total Pemasukan', y='Armada',
                                      orientation='h', title='Total Pemasukan per Armada',
                                      height=350)
                fig_pemasukan.update_layout(margin=dict(l=0, r=0, t=30, b=0))
                st.plotly_chart(fig_pemasukan, use_container_width=True)
        else:
            st.warning("Tidak ada data armada untuk filter yang dipilih")

    # --- TAB 5: KINERJA SOPIR ---
    with tab5:
        st.header("👤 Kinerja Sopir")
        df_sopir = df_filtered[df_filtered['Sopir'] != 'Tidak Diketahui']
        
        if len(df_sopir) > 0:
            # KPI Sopir
            col1, col2, col3 = st.columns(3)
            total_sopir = df_sopir['Sopir'].nunique()
            sopir_terbaik = df_sopir['Sopir'].value_counts().index[0]
            tugas_terbanyak = df_sopir['Sopir'].value_counts().iloc[0]
            
            col1.metric("Total Sopir Aktif", total_sopir)
            col2.metric("Sopir Terbaik", sopir_terbaik)
            col3.metric("Jumlah Tugas", f"{tugas_terbanyak} tugas")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Kinerja sopir
                sopir_counts = df_sopir['Sopir'].value_counts().head(8).reset_index()
                sopir_counts.columns = ['Sopir', 'Jumlah Tugas']
                
                fig_sopir = px.bar(sopir_counts, x='Jumlah Tugas', y='Sopir',
                                  orientation='h', title='Kinerja Sopir (Total Tugas)',
                                  height=350)
                fig_sopir.update_layout(margin=dict(l=0, r=0, t=30, b=0))
                st.plotly_chart(fig_sopir, use_container_width=True)
            
            with col2:
                # Pemasukan per sopir
                pemasukan_sopir = df_sopir.groupby('Sopir')['Pemasukan'].sum().sort_values(ascending=False).head(8).reset_index()
                pemasukan_sopir.columns = ['Sopir', 'Total Pemasukan']
                
                fig_pemasukan_sopir = px.bar(pemasukan_sopir, x='Total Pemasukan', y='Sopir',
                                            orientation='h', title='Total Pemasukan per Sopir',
                                            height=350)
                fig_pemasukan_sopir.update_layout(margin=dict(l=0, r=0, t=30, b=0))
                st.plotly_chart(fig_pemasukan_sopir, use_container_width=True)
        else:
            st.warning("Tidak ada data sopir untuk filter yang dipilih")