import streamlit as st
import pandas as pd
import sqlite3
import numpy as np




# ==== SIMPLE BUILT-IN PASSWORD PROTECTION (no secrets needed) ====



PASSWORD = "gritlab"

def check_password():
    """Returns True if the user entered the correct password."""
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if not st.session_state["password_correct"]:
        st.title("🔐 Password Required")

        pwd = st.text_input("Enter password:", type="password")

        if st.button("Submit"):
            if pwd == PASSWORD:
                st.session_state["password_correct"] = True
                st.rerun()   # ✅ FIXED — this works on Streamlit Cloud
            else:
                st.error("❌ Incorrect password. Try again.")

        return False

    return True



# ---------------------------------------------------
# CONNECT TO DATABASE
# ---------------------------------------------------
DB_PATH = "csv4db/kibera_survey.sqlite"
con = sqlite3.connect(DB_PATH)

# ---------------------------------------------------
# LOAD TABLE NAMES
# ---------------------------------------------------
tables = pd.read_sql(
    "SELECT name FROM sqlite_master WHERE type='table';", con
)["name"].tolist()


# ---------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------
st.set_page_config(page_title="Kibera Query Tool", layout="wide")

st.title("Kibera User Interface")

st.markdown(
    """
    <a href="https://docs.google.com/spreadsheets/d/1J9xJLYzacIQPhaeuDCdkEWLOpli0vMrk72n_T1QTtGE/edit?gid=1118359261#gid=1118359261"
       target="_blank"
       style="background-color:#007bff; padding:10px 18px; color:white; text-decoration:none; border-radius:5px;">
       Kibera Codebook
    </a>
    """,
    unsafe_allow_html=True
)


st.markdown("### Available Tables")
st.markdown(", ".join(tables))

st.markdown("---")


# ---------------------------------------------------
# SESSION STATE
# ---------------------------------------------------
if "custom_df" not in st.session_state:
    st.session_state.custom_df = None

if "pivot_generated" not in st.session_state:
    st.session_state.pivot_generated = False


# ---------------------------------------------------
# SIDEBAR — GROUPED QUERY
# ---------------------------------------------------
st.sidebar.header("Grouped Query")

master_cols = pd.read_sql("PRAGMA table_info(master);", con)["name"].tolist()

group_col = st.sidebar.selectbox("Group By:", master_cols)
run_group = st.sidebar.button("Run Grouped Query")

grouped_area = st.empty()


# ---------------------------------------------------
# SIDEBAR — PIVOT
# ---------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.header("Pivot Table (Custom Query Only)")

enable_pivot = st.sidebar.checkbox("Enable Pivot Table", value=False)

pivot_row = None
pivot_col = None


# ---------------------------------------------------
# MAIN PAGE — CUSTOM SQL
# ---------------------------------------------------
st.subheader("Custom SQL Query")

default_sql = "SELECT * FROM master LIMIT 10;"
custom_sql = st.text_area("Enter SQL Query:", value=default_sql, height=180)

run_custom = st.button("Run Custom Query")
custom_results_area = st.empty()

pivot_area = st.empty()
pivot_download_area = st.empty()


# ---------------------------------------------------
# GROUPED QUERY EXECUTION (INCLUDE NA)
# ---------------------------------------------------
if run_group:
    sql_group = f"""
        SELECT 
            COALESCE(CAST({group_col} AS TEXT), 'NA') AS value,
            COUNT(*) AS count
        FROM master
        GROUP BY COALESCE(CAST({group_col} AS TEXT), 'NA');
    """

    grouped_df = pd.read_sql(sql_group, con)
    grouped_area.dataframe(grouped_df, use_container_width=True)

    st.sidebar.download_button(
        "Download Grouped CSV",
        grouped_df.to_csv(index=False),
        file_name=f"grouped_{group_col}.csv",
        mime="text/csv"
    )


# ---------------------------------------------------
# CUSTOM QUERY EXECUTION (PRESERVE NA)
# ---------------------------------------------------
if run_custom:
    try:
        df = pd.read_sql(custom_sql, con)

        # ✅ Keep NA values — do NOT auto-remove
        df = df.replace({None: np.nan})

        st.session_state.custom_df = df
        st.session_state.pivot_generated = False  # reset pivot state

        custom_results_area.dataframe(df, use_container_width=True)

        st.download_button(
            "Download Custom Results CSV",
            df.to_csv(index=False),
            file_name="custom_query_results.csv",
            mime="text/csv"
        )

    except Exception as e:
        custom_results_area.error(f"Error: {e}")

elif st.session_state.custom_df is not None:
    custom_results_area.dataframe(st.session_state.custom_df, use_container_width=True)


# ---------------------------------------------------
# PIVOT TABLE EXECUTION (INCLUDE NA)
# ---------------------------------------------------
if enable_pivot and st.session_state.custom_df is not None:

    st.subheader("Pivot Table (From Custom Query Results)")

    df = st.session_state.custom_df.copy()

    # ensure NA is preserved and treated as category
    df = df.astype("object").where(pd.notnull(df), "NA")

    cols = df.columns.tolist()

    pivot_row = st.sidebar.selectbox("Pivot Row:", cols)
    pivot_col = st.sidebar.selectbox("Pivot Column:", cols)

    run_pivot = st.sidebar.button("Generate Pivot Table")

    if run_pivot:

        df2 = df.copy()

        # ✅ Expand summarized rows if count column exists
        if "count" in df2.columns:
            df2 = df2.loc[df2.index.repeat(df2["count"].astype(int))]

        # ✅ Pivot INCLUDING NA as category
        pivot = (
            df2.groupby([pivot_row, pivot_col], dropna=False)
            .size()
            .reset_index(name="count")
            .pivot_table(
                index=pivot_row,
                columns=pivot_col,
                values="count",
                fill_value=0,
                dropna=False
            )
        )

        pivot["Total"] = pivot.sum(axis=1)
        total_row = pivot.sum(axis=0).to_frame().T
        total_row.index = ["Total"]

        pivot = pd.concat([pivot, total_row])

        st.session_state.pivot_generated = True
        st.session_state.pivot_table = pivot

    # ✅ Display pivot without clearing results
    if st.session_state.pivot_generated:
        pivot_area.dataframe(st.session_state.pivot_table, use_container_width=True)

        pivot_download_area.download_button(
            "Download Pivot CSV",
            st.session_state.pivot_table.to_csv(),
            file_name="pivot_table.csv",
            mime="text/csv"
        )
