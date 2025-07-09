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
    # Menghitung jumlah missing values sebelum pembersihan
    missing_report = {}
    for col in ['Pemasukan', 'Pengeluaran', 'Volume (L)', 'Jumlah', 'Jenis Transaksi', 'Plat Nomor', 'Sopir', 'Order']:
        if col in df_keuangan.columns:
            missing_report[col] = df_keuangan[col].isna().sum() + (df_keuangan[col].astype(str).str.lower().isin(['tidak diketahui', '', 'unknown'])).sum()
    total_missing = sum(missing_report.values())

    # Mengubah 'Tanggal' menjadi datetime
    df_keuangan['Tanggal'] = pd.to_datetime(df_keuangan['Tanggal'], errors='coerce')

    # Mengisi missing values numerik
    numeric_cols = ['Pemasukan', 'Pengeluaran', 'Volume (L)', 'Jumlah']
    for col in numeric_cols:
        if col in df_keuangan.columns:
            df_keuangan[col] = pd.to_numeric(df_keuangan[col], errors='coerce').fillna(0)

    # Mengisi missing values kategorikal dengan kombinasi mirip atau modus
    categorical_cols = ['Jenis Transaksi', 'Plat Nomor', 'Sopir', 'Order']
    for col in categorical_cols:
        if col in df_keuangan.columns:
            mask_na = df_keuangan[col].isna() | (df_keuangan[col] == 'Tidak Diketahui') | (df_keuangan[col] == '') | (df_keuangan[col].str.lower() == 'unknown')
            for idx in df_keuangan[mask_na].index:
                # Coba cari baris lain yang mirip (selain kolom yang kosong)
                row = df_keuangan.loc[idx]
                subset = df_keuangan.copy()
                for c in categorical_cols:
                    if c != col and pd.notna(row[c]) and row[c] not in ['Tidak Diketahui', '', 'unknown', 'Unknown']:
                        subset = subset[subset[c] == row[c]]
                # Ambil nilai paling sering dari subset mirip
                val = None
                if len(subset) > 0 and subset[col].notna().any():
                    val = subset[col][subset[col].notna() & (subset[col] != 'Tidak Diketahui') & (subset[col] != '') & (subset[col].str.lower() != 'unknown')].mode()
                    if not val.empty:
                        df_keuangan.at[idx, col] = val.iloc[0]
                        continue
                # Jika tidak ada, pakai modus seluruh kolom
                mode_val = df_keuangan[col][df_keuangan[col].notna() & (df_keuangan[col] != 'Tidak Diketahui') & (df_keuangan[col] != '') & (df_keuangan[col].str.lower() != 'unknown')].mode()
                if not mode_val.empty:
                    df_keuangan.at[idx, col] = mode_val.iloc[0]
                else:
                    df_keuangan.at[idx, col] = 'Tidak Diketahui'

    # Menambahkan kolom 'Bulan' untuk analisis bulanan
    df_keuangan['Bulan'] = df_keuangan['Tanggal'].dt.to_period('M').astype(str)
    
    # Menggabungkan dengan data lokasi
    df_merged = pd.merge(df_keuangan, df_lokasi, left_on='Order', right_on='Nama Lokasi', how='left')
    
    return df_keuangan, df_merged, missing_report, total_missing

df_keuangan, df_merged, missing_report, total_missing = load_data()

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

    # Indikator kebersihan data
    def is_data_clean(df, categorical_cols):
        for col in categorical_cols:
            if col in df.columns:
                if df[col].isna().any() or (df[col].astype(str).str.lower().isin(['tidak diketahui', '', 'unknown'])).any():
                    return False
        return True

    data_bersih = is_data_clean(df_keuangan, ['Jenis Transaksi', 'Plat Nomor', 'Sopir', 'Order'])
    if data_bersih:
        st.success('✅ Data sudah bersih dari missing values dan label unknown.')
    else:
        st.warning('⚠️ Data masih mengandung missing values atau label unknown.')

    # Sidebar untuk filter
    with st.sidebar:
        st.header("🔧 Filter Data")
        
        # Filter bulan (pakai radio jika opsinya sedikit)
        bulan_options = ['Semua'] + sorted([b for b in df_keuangan['Bulan'].unique().tolist() if pd.notna(b)])
        if len(bulan_options) <= 7:
            selected_bulan = st.radio("Pilih Bulan:", bulan_options, horizontal=True)
        else:
            selected_bulan = st.select_slider("Pilih Bulan:", options=bulan_options)

        # Filter sopir (pakai radio jika <=7, jika lebih banyak tampilkan top 5 saja)
        sopir_list = df_keuangan[df_keuangan['Sopir'] != 'Tidak Diketahui']['Sopir'].value_counts().index.tolist()
        sopir_options = ['Semua'] + sopir_list[:5]
        selected_sopir = st.radio("Pilih Sopir:", sopir_options, horizontal=True)

        # Filter armada (pakai radio jika <=7, jika lebih banyak tampilkan top 5 saja)
        armada_list = df_keuangan[df_keuangan['Plat Nomor'] != 'Tidak Diketahui']['Plat Nomor'].value_counts().index.tolist()
        armada_options = ['Semua'] + armada_list[:5]
        selected_armada = st.radio("Pilih Armada:", armada_options, horizontal=True)

        # Info missing values (sebelum & sesudah pembersihan) di bawah filter
        st.markdown('---')
        st.subheader('ℹ️ Info Missing Values Dataset')
        with st.expander('Sebelum Pembersihan'):
            st.write(f"Total missing values (termasuk 'Tidak Diketahui', 'unknown', ''): **{total_missing}**")
            st.write(missing_report)
        with st.expander('Setelah Pembersihan'):
            # Hitung ulang cleaned_missing_report di sini agar tetap up-to-date
            cleaned_missing_report = {}
            for col in ['Pemasukan', 'Pengeluaran', 'Volume (L)', 'Jumlah', 'Jenis Transaksi', 'Plat Nomor', 'Sopir', 'Order']:
                if col in df_keuangan.columns:
                    cleaned_missing_report[col] = df_keuangan[col].isna().sum() + (df_keuangan[col].astype(str).str.lower().isin(['tidak diketahui', '', 'unknown'])).sum()
            cleaned_total_missing = sum(cleaned_missing_report.values())
            st.write(f"Total missing values setelah pembersihan: **{cleaned_total_missing}**")
            st.write(cleaned_missing_report)

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

        # Charts dalam layout yang kompak
        col1, _ = st.columns([2.5, 1])
        
        with col1:
            # Grafik kombinasi: Pemasukan & Pengeluaran (bar), Laba Bersih (garis) - lebih detail dan lebih panjang
            df_bulanan = df_filtered.groupby(df_filtered['Tanggal'].dt.strftime('%b %Y')).agg({
                'Pemasukan': 'sum',
                'Pengeluaran': 'sum'
            }).reset_index()
            # Urutkan bulan secara kronologis
            df_bulanan['BulanSort'] = pd.to_datetime(df_bulanan[df_bulanan.columns[0]], format='%b %Y')
            df_bulanan = df_bulanan.sort_values('BulanSort')
            df_bulanan['Laba Bersih'] = df_bulanan['Pemasukan'] - df_bulanan['Pengeluaran']

            fig_combo = go.Figure()
            fig_combo.add_trace(go.Bar(x=df_bulanan[df_bulanan.columns[0]], y=df_bulanan['Pemasukan'], name='Pemasukan', marker_color='#2ca02c'))
            fig_combo.add_trace(go.Bar(x=df_bulanan[df_bulanan.columns[0]], y=df_bulanan['Pengeluaran'], name='Pengeluaran', marker_color='#d62728'))
            fig_combo.add_trace(go.Scatter(x=df_bulanan[df_bulanan.columns[0]], y=df_bulanan['Laba Bersih'], name='Laba Bersih', mode='lines+markers', line=dict(color='#1f77b4', width=3)))
            fig_combo.update_layout(
                barmode='group',
                title='Pengeluaran, Pemasukan, dan Laba Bersih per Bulan',
                height=350,
                margin=dict(l=0, r=0, t=30, b=0),
                xaxis_title='Bulan',
                yaxis_title='Nilai (Rp)'
            )
            st.plotly_chart(fig_combo, use_container_width=True)

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

        # Pilihan tampilan: Analisis atau Peta
        view_option = st.radio(
            "Pilih Tampilan:",
            ["📊 Analisis Pengiriman Air", "🗺️ Peta Pengiriman"],
            horizontal=True
        )

        if view_option == "📊 Analisis Pengiriman Air":
            # Charts dalam layout yang kompak
            col1, _ = st.columns([3, 1])
            
            with col1:
                # Volume per bulan (Line Chart, Bulan Lebih Detail)
                volume_per_bulan = df_filtered.groupby(df_filtered['Tanggal'].dt.strftime('%b %Y'))['Volume (L)'].sum().reset_index()
                # Urutkan bulan secara kronologis
                volume_per_bulan['BulanSort'] = pd.to_datetime(volume_per_bulan[volume_per_bulan.columns[0]], format='%b %Y')
                volume_per_bulan = volume_per_bulan.sort_values('BulanSort')
                fig3 = px.line(volume_per_bulan, x=volume_per_bulan.columns[0], y='Volume (L)',
                             title='Volume Air per Bulan (Detail)',
                             markers=True,
                             height=350)
                fig3.update_traces(line=dict(color='#1f77b4', width=3))
                fig3.update_layout(margin=dict(l=0, r=0, t=30, b=0), xaxis_title='Bulan', yaxis_title='Volume (L)')
                st.plotly_chart(fig3, use_container_width=True)
        
        else:  # Peta Pengiriman
            # Ambil data pengiriman dengan koordinat valid
            df_pengiriman = df_merged_filtered[df_merged_filtered['Jenis Transaksi'].str.contains('Air|air|Pengiriman|pengiriman', na=False)].dropna(subset=['Latitude', 'Longitude'])
            
            if len(df_pengiriman) == 0:
                # Jika tidak ada data dengan filter jenis transaksi, gunakan semua data dengan koordinat valid
                df_pengiriman = df_merged_filtered.dropna(subset=['Latitude', 'Longitude'])
            
            if len(df_pengiriman) > 0:
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    st.subheader("📊 Volume Air Terkirim per Toko")
                    # Grouping berdasarkan lokasi dan sum volume air
                    lokasi_volume = df_pengiriman.groupby('Order')['Volume (L)'].sum().sort_values(ascending=False).head(10).reset_index()
                    lokasi_volume.columns = ['Lokasi', 'Volume Air Terkirim (L)']
                    
                    fig_lokasi = px.bar(lokasi_volume, x='Volume Air Terkirim (L)', y='Lokasi',
                                       orientation='h', 
                                       title='Top 10 Toko - Volume Air Terkirim',
                                       height=300)
                    fig_lokasi.update_layout(margin=dict(l=0, r=0, t=30, b=0))
                    st.plotly_chart(fig_lokasi, use_container_width=True)
                    
                with col2:
                    st.subheader("🗺️ Peta Pengiriman")
                    # Peta dengan size dan warna berdasarkan volume air
                    df_map = df_pengiriman.groupby(['Latitude', 'Longitude', 'Order']).agg({
                        'Volume (L)': 'sum',
                        'Pemasukan': 'sum',
                        'Order': 'count'  # hitung jumlah order per lokasi
                    }).rename(columns={'Order': 'Jumlah Order'}).reset_index()
                    
                    fig_map = px.scatter_mapbox(df_map, 
                                          lat="Latitude", lon="Longitude",
                                          size="Volume (L)", 
                                          color="Volume (L)",
                                          color_continuous_scale="Reds",
                                          hover_name="Order",
                                          hover_data={'Volume (L)': ':,.0f', 'Jumlah Order': True, 'Pemasukan': ':,.0f'},
                                          mapbox_style="open-street-map",
                                          height=350,
                                          zoom=10)
                    fig_map.update_layout(margin=dict(l=0, r=0, t=0, b=0))
                    st.plotly_chart(fig_map, use_container_width=True)
            else:
                st.warning("Tidak ada data pengiriman air dengan koordinat untuk filter yang dipilih")

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
        
        # Ambil data pengiriman dengan koordinat valid
        df_pengiriman = df_merged_filtered[df_merged_filtered['Jenis Transaksi'].str.contains('Air|air|Pengiriman|pengiriman', na=False)].dropna(subset=['Latitude', 'Longitude'])
        
        if len(df_pengiriman) == 0:
            # Jika tidak ada data dengan filter jenis transaksi, gunakan semua data dengan koordinat valid
            df_pengiriman = df_merged_filtered.dropna(subset=['Latitude', 'Longitude'])
        
        if len(df_pengiriman) > 0:
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.subheader("📊 Sebaran Order")
                lokasi_counts = df_pengiriman['Order'].value_counts().head(10).reset_index()
                lokasi_counts.columns = ['Lokasi', 'Jumlah Order']
                
                fig_lokasi = px.bar(lokasi_counts, x='Jumlah Order', y='Lokasi',
                                   orientation='h', 
                                   title='Top 10 Lokasi Pengiriman',
                                   height=280)
                fig_lokasi.update_layout(margin=dict(l=0, r=0, t=30, b=0))
                st.plotly_chart(fig_lokasi, use_container_width=True)
                
               
            with col2:
                st.subheader("🗺️ Peta Pengiriman")
                # Peta dengan size dan warna berdasarkan jumlah order
                df_map = df_pengiriman.groupby(['Latitude', 'Longitude', 'Order']).agg({
                    'Volume (L)': 'sum',
                    'Pemasukan': 'sum',
                    'Order': 'count'  # hitung jumlah order per lokasi
                }).rename(columns={'Order': 'Jumlah Order'}).reset_index()
                
                fig_map = px.scatter_mapbox(df_map, 
                                      lat="Latitude", lon="Longitude",
                                      size="Jumlah Order", 
                                      color="Jumlah Order",
                                      color_continuous_scale="Blues",
                                      hover_name="Order",
                                      hover_data={'Volume (L)': ':,.0f', 'Jumlah Order': True, 'Pemasukan': ':,.0f'},
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
        # Filter armada yang valid (tidak mengandung #### atau tidak diketahui)
        df_armada = df_filtered[
            (df_filtered['Plat Nomor'] != 'Tidak Diketahui') & 
            (~df_filtered['Plat Nomor'].str.contains('####', na=False))
        ]
        
        if len(df_armada) > 0:
            # KPI Armada Utama
            col1, col2, col3, col4 = st.columns(4)
            total_armada = df_armada['Plat Nomor'].nunique()
            armada_terbanyak = df_armada['Plat Nomor'].value_counts().index[0]
            usage_terbanyak = df_armada['Plat Nomor'].value_counts().iloc[0]
            total_volume_armada = df_armada['Volume (L)'].sum()
            
            col1.metric("Total Armada Aktif", total_armada)
            col2.metric("Armada Terbanyak Digunakan", armada_terbanyak)
            col3.metric("Jumlah Penggunaan Tertinggi", f"{usage_terbanyak} kali")
            col4.metric("Total Volume Terangkut", f"{total_volume_armada:,.0f} L")
            
            # Sub-tabs untuk analisis armada yang berbeda
            armada_tab1, armada_tab2 = st.tabs([
                "📊 Sebaran Penggunaan", 
                "🚛 Volume & Efisiensi"
            ])
            
            # Sub-tab 1: Sebaran Penggunaan Armada
            with armada_tab1:
                st.subheader("📈 Sebaran Penggunaan Armada")
                
                col1, col2 = st.columns(2)
                with col1:
                    # Frekuensi penggunaan armada
                    armada_usage = df_armada['Plat Nomor'].value_counts().head(8).reset_index()
                    armada_usage.columns = ['Armada', 'Jumlah Penggunaan']
                    
                    fig_armada = px.bar(armada_usage, x='Jumlah Penggunaan', y='Armada',
                                       orientation='h', title='Frekuensi Penggunaan Armada',
                                       height=300)
                    fig_armada.update_layout(margin=dict(l=0, r=0, t=30, b=0))
                    st.plotly_chart(fig_armada, use_container_width=True)
                
                with col2:
                    # Estimasi biaya perawatan per armada
                    armada_stats = df_armada.groupby('Plat Nomor').agg({
                        'Pemasukan': 'sum',
                        'Pengeluaran': 'sum',
                        'Volume (L)': 'sum'
                    }).reset_index()
                    armada_stats['Estimasi Biaya Perawatan'] = armada_stats['Pengeluaran'] * 0.15  # 15% dari pengeluaran
                    armada_stats = armada_stats.sort_values('Estimasi Biaya Perawatan', ascending=False).head(8)
                    
                    fig_perawatan = px.bar(armada_stats, x='Estimasi Biaya Perawatan', y='Plat Nomor',
                                          orientation='h', title='Estimasi Biaya Perawatan per Armada',
                                          height=300)
                    fig_perawatan.update_layout(margin=dict(l=0, r=0, t=30, b=0))
                    st.plotly_chart(fig_perawatan, use_container_width=True)
            
            # Sub-tab 2: Volume & Efisiensi
            with armada_tab2:
                st.subheader("🚛 Volume & Efisiensi Pengangkutan")
                
                # Hanya menampilkan rata-rata volume per bulan per armada
                df_armada_bulan = df_armada.groupby(['Plat Nomor', 'Bulan'])['Volume (L)'].sum().reset_index()
                avg_volume_per_month = df_armada_bulan.groupby('Plat Nomor')['Volume (L)'].mean().sort_values(ascending=False).head(10).reset_index()
                avg_volume_per_month.columns = ['Armada', 'Rata-rata Volume per Bulan (L)']
                
                fig_avg_volume = px.bar(avg_volume_per_month, x='Rata-rata Volume per Bulan (L)', y='Armada',
                                       orientation='h', title='Rata-rata Volume per Bulan per Armada',
                                       height=400)
                fig_avg_volume.update_layout(margin=dict(l=0, r=0, t=30, b=0))
                st.plotly_chart(fig_avg_volume, use_container_width=True)
                
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