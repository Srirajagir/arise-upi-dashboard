import streamlit as st
import pandas as pd
import plotly.express as px

# Page styling configurations
st.set_page_config(
    page_title="Arise UPI Mandate Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern card styling
st.markdown("""
    <style>
    div[data-testid="metric-container"] {
        background-color: rgba(240, 242, 246, 0.4);
        border: 1px solid rgba(220, 224, 230, 0.6);
        padding: 15px;
        border-radius: 10px;
    }
    </style>
""", unsafe_with_html=True)

st.title("📊 UPI Mandate Adoption Dashboard")
st.markdown("Analyze client registration rates and staff performance rankings across regions, divisions, and branches.")

# 1. File Upload Handler
uploaded_file = st.sidebar.file_uploader(
    "Upload Report (TSV or Excel format)", 
    type=["tsv", "csv", "xlsx"]
)

def clean_and_process_data(file):
    # Determine parsing engine based on extension
    if file.name.endswith('xlsx'):
        df = pd.read_excel(file)
    else:
        # Fallback to TSV/CSV delimiter auto-detection
        df = pd.read_csv(file, sep=None, engine='python')
        
    # Strip whitespace from column headers
    df.columns = df.columns.str.strip()
    
    # Standardize UPI registration column data
    df['UPIRegister'] = df['UPIRegister'].fillna('NotRegistered').astype(str).str.strip()
    
    # Generate direct boolean columns for clean grouping calculations
    df['Is_Registered'] = df['UPIRegister'].apply(lambda x: 1 if x.lower() == 'registered' else 0)
    df['Is_Not_Registered'] = df['UPIRegister'].apply(lambda x: 1 if x.lower() != 'registered' else 0)
    
    return df

def generate_metrics_profile(dataframe, groupby_column):
    # Consolidate raw tracking fields
    profile = dataframe.groupby(groupby_column).agg(
        Total_Clients=('UPIRegister', 'count'),
        Registered_Count=('Is_Registered', 'sum'),
        Pending_Count=('Is_Not_Registered', 'sum')
    ).reset_index()
    
    # Compute relative adoption percentages
    profile['Yes %'] = (profile['Registered_Count'] / profile['Total_Clients'] * 100).round(1)
    profile['No %'] = (profile['Pending_Count'] / profile['Total_Clients'] * 100).round(1)
    
    # Calculate performance tier ranks
    profile['Rank'] = profile['Yes %'].rank(ascending=False, method='dense').astype(int)
    
    # Categorize status tiers
    def define_status(pct):
        if pct >= 30: return "🟢 On Track"
        elif pct >= 20: return "🟠 Watch"
        return "🔴 Critical"
        
    profile['Status'] = profile['Yes %'].apply(define_status)
    return profile.sort_values(by='Rank')

if uploaded_file is not None:
    # Load and prepare master dataset
    raw_df = clean_and_process_data(uploaded_file)
    
    # 2. Sidebar Interactive Control Filters
    st.sidebar.header("Navigation Filters")
    
    regions = ["All Regions"] + sorted(list(raw_df['AriseRegion'].dropna().unique()))
    selected_region = st.sidebar.selectbox("Region Scope", regions)
    
    # Dynamic cascading filter isolation
    if selected_region != "All Regions":
        filtered_df = raw_df[raw_df['AriseRegion'] == selected_region]
        divisions = ["All Divisions"] + sorted(list(filtered_df['RegionID'].dropna().unique()))
    else:
        filtered_df = raw_df.copy()
        divisions = ["All Divisions"] + sorted(list(raw_df['RegionID'].dropna().unique()))
        
    selected_division = st.sidebar.selectbox("Division Scope", divisions)
    
    if selected_division != "All Divisions":
        filtered_df = filtered_df[filtered_df['RegionID'] == selected_division]
        branches = ["All Branches"] + sorted(list(filtered_df['OurBranchID'].dropna().unique()))
    else:
        branches = ["All Branches"] + sorted(list(filtered_df['OurBranchID'].dropna().unique()))
        
    selected_branch = st.sidebar.selectbox("Branch Scope", branches)
    
    if selected_branch != "All Branches":
        filtered_df = filtered_df[filtered_df['OurBranchID'] == selected_branch]

    # 3. Aggregated System Summary Cards
    total_clients = len(filtered_df)
    total_registered = filtered_df['Is_Registered'].sum()
    total_pending = filtered_df['Is_Not_Registered'].sum()
    overall_yes_pct = (total_registered / total_clients * 100).round(1) if total_clients > 0 else 0
    overall_no_pct = (total_pending / total_clients * 100).round(1) if total_clients > 0 else 0

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total Clients", f"{total_clients:,}")
    m2.metric("Registered (Yes)", f"{total_registered:,}")
    m3.metric("Pending (No)", f"{total_pending:,}")
    m4.metric("Overall Yes %", f"{overall_yes_pct}%")
    m5.metric("Overall No %", f"{overall_no_pct}%")
    
    st.markdown("---")
    
    # 4. Data Visualization Breakdown Tabs
    t1, t2, t3, t4 = st.tabs(["Region Analysis", "Division Analysis", "Branch Performance", "Staff Rankings"])
    
    with t1:
        st.subheader("Regional Performance Profiles")
        region_profile = generate_metrics_profile(filtered_df, 'AriseRegion')
        st.dataframe(region_profile, use_container_width=True, hide_index=True)
        
        fig_reg = px.bar(region_profile, x='AriseRegion', y='Yes %', color='Status', title="Regional Yes % Distribution")
        st.plotly_chart(fig_reg, use_container_width=True)

    with t2:
        st.subheader("Division Performance Profiles")
        division_profile = generate_metrics_profile(filtered_df, 'RegionID')
        st.dataframe(division_profile, use_container_width=True, hide_index=True)

    with t3:
        st.subheader("Branch Performance Profiles")
        branch_profile = generate_metrics_profile(filtered_df, 'OurBranchID')
        st.dataframe(branch_profile, use_container_width=True, hide_index=True)
        
        fig_br = px.bar(branch_profile.head(15), x='OurBranchID', y='Yes %', title="Top 15 Branches by Registration Rate")
        st.plotly_chart(fig_br, use_container_width=True)

    with t4:
        st.subheader("Credit Officer Performance Rankings")
        staff_profile = generate_metrics_profile(filtered_df, 'CreditOfficerID')
        
        # Individual Staff Filter Dropdown inside tab view
        staff_list = ["All Staff"] + sorted(list(staff_profile['CreditOfficerID'].astype(str).unique()))
        selected_staff = st.selectbox("Search / Isolate Specific Staff ID", staff_list)
        
        if selected_staff != "All Staff":
            display_staff = staff_profile[staff_profile['CreditOfficerID'].astype(str) == selected_staff]
            st.dataframe(display_staff, use_container_width=True, hide_index=True)
        else:
            st.dataframe(staff_profile, use_container_width=True, hide_index=True)

else:
    st.info("💡 Please upload your TSV or Excel report file in the sidebar to populate the performance dashboards.")