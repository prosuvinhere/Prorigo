import streamlit as st
import pandas as pd
import tempfile
from tabula import read_pdf
import fitz  # PyMuPDF
import os
import json
from PIL import Image
from streamlit_extras.add_vertical_space import add_vertical_space
from streamlit_extras.stylable_container import stylable_container

st.set_page_config(page_title="✨ PDF Table to SurveyJS Converter", layout="wide")

st.markdown("<h1 style='text-align: center; color: #4CAF50;'>📄 PDF Table to SurveyJS JSON Converter</h1>", unsafe_allow_html=True)
st.markdown("Convert PDF tables into editable JSON for [SurveyJS](https://surveyjs.io/), effortlessly!")

# Upload PDF
st.sidebar.header("📤 Upload")
uploaded_file = st.sidebar.file_uploader("Choose a PDF file", type=["pdf"])

# Function to convert DataFrames to SurveyJS JSON
def convert_tables_to_json(tables):
    all_elements = []
    for idx, table in enumerate(tables):
        columns = [
            {"name": col, "title": col, "cellType": "text"}
            for col in table.columns
        ]
        row_data = {}
        rows = []
        for i in range(len(table)):
            row_name = f"Row {i + 1}"
            rows.append(row_name)
            row_data[row_name] = {
                col: str(table.iloc[i][col]) if pd.notna(table.iloc[i][col]) else ""
                for col in table.columns
            }
        element = {
            "type": "matrixdropdown",
            "name": f"Table {idx + 1}",
            "defaultValue": row_data,
            "columns": columns,
            "rows": rows
        }
        all_elements.append(element)
    return {"pages": [{"name": "page1", "elements": all_elements}]}

if uploaded_file is not None:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        temp_file.write(uploaded_file.getbuffer())
        temp_file_path = temp_file.name

    st.markdown("## 🖼️ PDF Preview")
    try:
        pdf_document = fitz.open(temp_file_path)
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            st.image(img, caption=f"📄 Page {page_num+1}", use_container_width=True)
        pdf_document.close()
    except Exception as preview_error:
        st.error(f"❌ Error previewing PDF: {preview_error}")

    st.markdown("## 📊 Table Extraction & Editor")
    try:
        tables = read_pdf(temp_file_path, pages='all', multiple_tables=True, pandas_options={'header': 0})
        if tables:
            df = tables[0].fillna("")
            st.info("✔️ Table successfully extracted! You can trim and edit below.")
            trim_range = st.slider("🔧 Trim rows from top and bottom:", 0, len(df)-1, (0, len(df)-1))
            trimmed_df = df.iloc[trim_range[0]:trim_range[1]+1]

            with stylable_container(
                key="data_editor_box",
                css_styles="border: 1px solid #4CAF50; padding: 1em; border-radius: 1em;"
            ):
                edited_df = st.data_editor(trimmed_df, use_container_width=True)

            st.markdown("Split Table")
            num_splits = st.number_input("How many parts to split the table into?", min_value=1, max_value=len(edited_df), value=1)
            split_points = [
                st.number_input(f"Enter split index for part {i+1}", 0, len(edited_df)-1, int(i*len(edited_df)/num_splits))
                for i in range(1, num_splits)
            ]
            split_points = [0] + split_points + [len(edited_df)]
            split_tables = [edited_df.iloc[split_points[i]:split_points[i+1]] for i in range(len(split_points)-1)]

            for idx, table in enumerate(split_tables):
                st.markdown(f"### 📥 Split Table {idx+1}")
                st.dataframe(table, use_container_width=True)
                st.download_button(f"Download Split Table {idx+1} as CSV", table.to_csv(index=False), f"split_table_{idx+1}.csv", "text/csv")

            combined_json = convert_tables_to_json(split_tables)
            st.markdown("## 🧾 Combined SurveyJS JSON")
            st.markdown("[🎯 Test this JSON in SurveyJS Creator](https://surveyjs.io/create-free-survey)")
            st.json(combined_json)

            st.download_button("⬇️ Download JSON", json.dumps(combined_json, indent=2), "combined_tables.json", "application/json")

        else:
            st.warning("⚠️ No tables found in the PDF.")
    except Exception as e:
        st.error(f"🚫 Error: {e}")

    os.unlink(temp_file_path)

st.markdown("---")
st.markdown("Made with ❤️ using Streamlit")